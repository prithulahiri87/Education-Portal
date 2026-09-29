"""Record rules: conversion, quote math, and delete guards."""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.domain import STAGE_PROBABILITY
from app.models import Account, Contact, Lead, Opportunity, Quote, QuoteLineItem, utcnow

TWOPLACES = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That record conflicts with an existing relationship")


def require_row(db, model, record_id, label):
    row = db.get(model, record_id) if record_id else None
    if row is None:
        raise HTTPException(status_code=422, detail=label + " was not found")
    return row


def get_or_404(db, model, record_id):
    if not record_id or len(record_id) > 36:
        raise HTTPException(status_code=404, detail="Record not found")
    row = db.get(model, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return row


def search_pattern(term):
    if term is None:
        return None
    text = term.strip()[:100]
    if not text:
        return None
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return "%" + escaped + "%"


def paginate(db, statement, limit, offset):
    safe_limit = min(max(limit, 1), 200)
    safe_offset = max(offset, 0)
    counted = statement.order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(counted)) or 0
    rows = list(db.scalars(statement.limit(safe_limit).offset(safe_offset)).all())
    return total, rows


def assign(row, data):
    for key, value in data.items():
        setattr(row, key, value)
    return row


def prepare_opportunity(db, data, existing=None):
    if existing is None:
        account_id = data["account_id"]
        contact_id = data.get("primary_contact_id")
        stage = data.get("stage", "Prospecting")
    else:
        account_id = data.get("account_id", existing.account_id)
        if "primary_contact_id" in data:
            contact_id = data.get("primary_contact_id")
        else:
            contact_id = existing.primary_contact_id
        stage = data.get("stage", existing.stage)
    account = require_row(db, Account, account_id, "Account")
    if existing is not None and account.id != existing.account_id:
        quote_count = db.scalar(
            select(func.count()).select_from(Quote).where(Quote.opportunity_id == existing.id)
        )
        if quote_count:
            raise HTTPException(
                status_code=409,
                detail="Move quotes off this opportunity before changing the account",
            )
    if contact_id:
        contact = require_row(db, Contact, contact_id, "Primary contact")
        if contact.account_id != account.id:
            raise HTTPException(
                status_code=422,
                detail="Primary contact must belong to the opportunity account",
            )
    if data.get("probability") is None and (existing is None or "stage" in data):
        data["probability"] = STAGE_PROBABILITY[stage]
    if data.get("probability") is None:
        data.pop("probability", None)
    data["account_id"] = account.id
    data["primary_contact_id"] = contact_id
    return data


def prepare_quote(db, data, existing=None):
    if existing is None:
        opportunity_id = data["opportunity_id"]
        contact_id = data.get("contact_id")
    else:
        opportunity_id = data.get("opportunity_id", existing.opportunity_id)
        if "contact_id" in data:
            contact_id = data.get("contact_id")
        else:
            contact_id = existing.contact_id
    opportunity = require_row(db, Opportunity, opportunity_id, "Opportunity")
    if contact_id:
        contact = require_row(db, Contact, contact_id, "Contact")
        if contact.account_id != opportunity.account_id:
            raise HTTPException(
                status_code=422,
                detail="Contact must belong to the opportunity account",
            )
    data["opportunity_id"] = opportunity_id
    data["account_id"] = opportunity.account_id
    data["contact_id"] = contact_id
    return data


def recompute_quote(db, quote):
    lines = list(
        db.scalars(
            select(QuoteLineItem)
            .where(QuoteLineItem.quote_id == quote.id)
            .order_by(QuoteLineItem.sort_order, QuoteLineItem.created_at)
        ).all()
    )
    subtotal = Decimal("0.00")
    for line in lines:
        discount = line.discount_percent or Decimal("0.00")
        net = money(line.quantity * line.unit_price * (Decimal("1") - (discount / Decimal("100"))))
        line.line_total = net
        subtotal += net
    subtotal = money(subtotal)
    header_discount = money(subtotal * ((quote.discount_percent or Decimal("0.00")) / Decimal("100")))
    taxable = money(subtotal - header_discount)
    tax = money(taxable * ((quote.tax_percent or Decimal("0.00")) / Decimal("100")))
    quote.subtotal = subtotal
    quote.discount_amount = header_discount
    quote.tax_amount = tax
    quote.grand_total = money(taxable + tax)
    if quote.status == "Accepted":
        opportunity = db.get(Opportunity, quote.opportunity_id)
        if opportunity is not None:
            opportunity.amount = quote.grand_total
    return quote


def convert_lead(db, lead, body):
    if lead.status == "Converted":
        raise HTTPException(status_code=409, detail="Lead is already converted")
    full_name = (lead.first_name + " " + lead.last_name).strip()
    account = Account(
        name=body.account_name or lead.company or full_name,
        type="Prospect",
        phone=lead.phone,
        description=lead.description,
    )
    db.add(account)
    db.flush()
    contact = Contact(
        account_id=account.id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        title=lead.title,
        email=lead.email,
        phone=lead.phone,
    )
    db.add(contact)
    db.flush()
    opportunity = None
    if body.create_opportunity:
        close_date = body.close_date or (utcnow().date() + timedelta(days=30))
        opportunity = Opportunity(
            account_id=account.id,
            primary_contact_id=contact.id,
            name=body.opportunity_name or ((lead.company or full_name) + " opportunity"),
            stage="Prospecting",
            amount=Decimal("0.00"),
            probability=STAGE_PROBABILITY["Prospecting"],
            close_date=close_date,
            description=lead.description,
        )
        db.add(opportunity)
        db.flush()
    lead.status = "Converted"
    lead.converted_account_id = account.id
    lead.converted_contact_id = contact.id
    lead.converted_opportunity_id = opportunity.id if opportunity is not None else None
    return lead, account, contact, opportunity


def delete_account(db, account):
    blockers = []
    if db.scalar(select(func.count()).select_from(Contact).where(Contact.account_id == account.id)):
        blockers.append("contacts")
    if db.scalar(select(func.count()).select_from(Opportunity).where(Opportunity.account_id == account.id)):
        blockers.append("opportunities")
    if db.scalar(select(func.count()).select_from(Quote).where(Quote.account_id == account.id)):
        blockers.append("quotes")
    if blockers:
        raise HTTPException(
            status_code=409,
            detail="Remove related " + ", ".join(blockers) + " before deleting this account",
        )
    db.execute(update(Lead).where(Lead.converted_account_id == account.id).values(converted_account_id=None))
    db.delete(account)


def delete_contact(db, contact):
    db.execute(
        update(Opportunity)
        .where(Opportunity.primary_contact_id == contact.id)
        .values(primary_contact_id=None)
    )
    db.execute(update(Quote).where(Quote.contact_id == contact.id).values(contact_id=None))
    db.execute(update(Lead).where(Lead.converted_contact_id == contact.id).values(converted_contact_id=None))
    db.delete(contact)


def delete_opportunity(db, opportunity):
    quote_count = db.scalar(
        select(func.count()).select_from(Quote).where(Quote.opportunity_id == opportunity.id)
    )
    if quote_count:
        raise HTTPException(status_code=409, detail="Remove quotes before deleting this opportunity")
    db.execute(
        update(Lead)
        .where(Lead.converted_opportunity_id == opportunity.id)
        .values(converted_opportunity_id=None)
    )
    db.delete(opportunity)


def delete_quote(db, quote):
    db.delete(quote)


def next_sort_order(db, quote_id):
    current = db.scalar(select(func.max(QuoteLineItem.sort_order)).where(QuoteLineItem.quote_id == quote_id))
    return (current or 0) + 1
