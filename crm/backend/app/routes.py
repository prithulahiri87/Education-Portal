"""HTTP routes for the six sales objects, quote lines, and the desk summary."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import CLOSED_STAGES, OPEN_QUOTE_STATUSES, OPPORTUNITY_STAGES
from app.models import Account, Contact, Lead, Opportunity, Quote, QuoteLineItem
from app.schemas import (
    AccountRead,
    AccountUpdate,
    AccountWrite,
    ContactRead,
    ContactUpdate,
    ContactWrite,
    ConvertLead,
    ConvertResult,
    DashboardRead,
    LeadRead,
    LeadUpdate,
    LeadWrite,
    LineRead,
    LineUpdate,
    LineWrite,
    LineWriteResult,
    OpportunityRead,
    OpportunityUpdate,
    OpportunityWrite,
    QuoteRead,
    QuoteUpdate,
    QuoteWrite,
    StageTotal,
)
from app.services import (
    assign,
    commit,
    delete_account,
    delete_contact,
    delete_opportunity,
    delete_quote,
    get_or_404,
    next_sort_order,
    paginate,
    prepare_opportunity,
    prepare_quote,
    recompute_quote,
    require_row,
    search_pattern,
)
from app.services import convert_lead as convert_lead_record

router = APIRouter(prefix="/api")


def _page(db, statement, limit, offset):
    return paginate(db, statement, limit, offset)


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)):
    counts = {
        "leads": db.scalar(select(func.count()).select_from(Lead)) or 0,
        "accounts": db.scalar(select(func.count()).select_from(Account)) or 0,
        "contacts": db.scalar(select(func.count()).select_from(Contact)) or 0,
        "opportunities": db.scalar(select(func.count()).select_from(Opportunity)) or 0,
        "quotes": db.scalar(select(func.count()).select_from(Quote)) or 0,
        "quote_line_items": db.scalar(select(func.count()).select_from(QuoteLineItem)) or 0,
        "open_leads": db.scalar(
            select(func.count()).select_from(Lead).where(Lead.status.in_(("New", "Working", "Qualified")))
        )
        or 0,
    }
    grouped = db.execute(
        select(Opportunity.stage, func.count(), func.coalesce(func.sum(Opportunity.amount), 0)).group_by(
            Opportunity.stage
        )
    ).all()
    by_stage = {stage: (count, amount) for stage, count, amount in grouped}
    pipeline = []
    open_amount = Decimal("0.00")
    for stage in OPPORTUNITY_STAGES:
        count, amount = by_stage.get(stage, (0, Decimal("0.00")))
        pipeline.append(StageTotal(stage=stage, count=count, amount=amount))
        if stage not in CLOSED_STAGES:
            open_amount += Decimal(amount)
    accepted = db.scalar(
        select(func.coalesce(func.sum(Quote.grand_total), 0)).where(Quote.status == "Accepted")
    )
    open_quotes = db.scalar(
        select(func.count()).select_from(Quote).where(Quote.status.in_(OPEN_QUOTE_STATUSES))
    )
    recent = list(db.scalars(select(Lead).order_by(Lead.updated_at.desc()).limit(5)).all())
    return DashboardRead(
        counts=counts,
        open_pipeline_amount=open_amount,
        accepted_quote_total=accepted or 0,
        open_quote_count=open_quotes or 0,
        pipeline=pipeline,
        recent_leads=[LeadRead.model_validate(row) for row in recent],
    )


@router.get("/leads", response_model=dict)
def list_leads(
    status: str = Query(default=None),
    q: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(Lead)
    if status:
        statement = statement.where(Lead.status == status)
    pattern = search_pattern(q)
    if pattern:
        statement = statement.where(
            or_(
                Lead.first_name.ilike(pattern, escape="\\"),
                Lead.last_name.ilike(pattern, escape="\\"),
                Lead.company.ilike(pattern, escape="\\"),
                Lead.email.ilike(pattern, escape="\\"),
            )
        )
    statement = statement.order_by(Lead.updated_at.desc())
    total, rows = _page(db, statement, limit, offset)
    return {"items": [LeadRead.model_validate(row) for row in rows], "total": total}


@router.post("/leads", response_model=LeadRead, status_code=201)
def create_lead(payload: LeadWrite, db: Session = Depends(get_db)):
    lead = assign(Lead(), payload.model_dump(exclude_unset=True))
    db.add(lead)
    commit(db)
    db.refresh(lead)
    return lead


@router.get("/leads/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Lead, lead_id)


@router.patch("/leads/{lead_id}", response_model=LeadRead)
def update_lead(lead_id: str, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id)
    if lead.status == "Converted":
        raise_converted()
    assign(lead, payload.model_dump(exclude_unset=True))
    commit(db)
    db.refresh(lead)
    return lead


@router.delete("/leads/{lead_id}", status_code=204)
def remove_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id)
    db.delete(lead)
    commit(db)
    return Response(status_code=204)


@router.post("/leads/{lead_id}/convert", response_model=ConvertResult)
def convert_lead(lead_id: str, payload: ConvertLead, db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id)
    lead, account, contact, opportunity = convert_lead_record(db, lead, payload)
    commit(db)
    db.refresh(lead)
    db.refresh(account)
    db.refresh(contact)
    if opportunity is not None:
        db.refresh(opportunity)
    return ConvertResult(lead=lead, account=account, contact=contact, opportunity=opportunity)


def raise_converted():
    from fastapi import HTTPException

    raise HTTPException(status_code=409, detail="Converted leads are read-only")


@router.get("/accounts", response_model=dict)
def list_accounts(
    q: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(Account)
    pattern = search_pattern(q)
    if pattern:
        statement = statement.where(
            or_(
                Account.name.ilike(pattern, escape="\\"),
                Account.industry.ilike(pattern, escape="\\"),
                Account.website.ilike(pattern, escape="\\"),
            )
        )
    statement = statement.order_by(Account.updated_at.desc())
    total, rows = _page(db, statement, limit, offset)
    return {"items": [AccountRead.model_validate(row) for row in rows], "total": total}


@router.post("/accounts", response_model=AccountRead, status_code=201)
def create_account(payload: AccountWrite, db: Session = Depends(get_db)):
    account = assign(Account(), payload.model_dump(exclude_unset=True))
    db.add(account)
    commit(db)
    db.refresh(account)
    return account


@router.get("/accounts/{account_id}", response_model=AccountRead)
def get_account(account_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Account, account_id)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
def update_account(account_id: str, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = get_or_404(db, Account, account_id)
    assign(account, payload.model_dump(exclude_unset=True))
    commit(db)
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=204)
def remove_account(account_id: str, db: Session = Depends(get_db)):
    account = get_or_404(db, Account, account_id)
    delete_account(db, account)
    commit(db)
    return Response(status_code=204)


@router.get("/contacts", response_model=dict)
def list_contacts(
    account_id: str = Query(default=None),
    q: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(Contact)
    if account_id:
        statement = statement.where(Contact.account_id == account_id)
    pattern = search_pattern(q)
    if pattern:
        statement = statement.where(
            or_(
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
            )
        )
    statement = statement.order_by(Contact.updated_at.desc())
    total, rows = _page(db, statement, limit, offset)
    return {"items": [ContactRead.model_validate(row) for row in rows], "total": total}


@router.post("/contacts", response_model=ContactRead, status_code=201)
def create_contact(payload: ContactWrite, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    require_row(db, Account, data["account_id"], "Account")
    contact = assign(Contact(), data)
    db.add(contact)
    commit(db)
    db.refresh(contact)
    return contact


@router.get("/contacts/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Contact, contact_id)


@router.patch("/contacts/{contact_id}", response_model=ContactRead)
def update_contact(contact_id: str, payload: ContactUpdate, db: Session = Depends(get_db)):
    contact = get_or_404(db, Contact, contact_id)
    data = payload.model_dump(exclude_unset=True)
    if "account_id" in data:
        require_row(db, Account, data["account_id"], "Account")
    assign(contact, data)
    commit(db)
    db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}", status_code=204)
def remove_contact(contact_id: str, db: Session = Depends(get_db)):
    contact = get_or_404(db, Contact, contact_id)
    delete_contact(db, contact)
    commit(db)
    return Response(status_code=204)


@router.get("/opportunities", response_model=dict)
def list_opportunities(
    account_id: str = Query(default=None),
    primary_contact_id: str = Query(default=None),
    stage: str = Query(default=None),
    q: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(Opportunity)
    if account_id:
        statement = statement.where(Opportunity.account_id == account_id)
    if primary_contact_id:
        statement = statement.where(Opportunity.primary_contact_id == primary_contact_id)
    if stage:
        statement = statement.where(Opportunity.stage == stage)
    pattern = search_pattern(q)
    if pattern:
        statement = statement.where(Opportunity.name.ilike(pattern, escape="\\"))
    statement = statement.order_by(Opportunity.updated_at.desc())
    total, rows = _page(db, statement, limit, offset)
    return {"items": [OpportunityRead.model_validate(row) for row in rows], "total": total}


@router.post("/opportunities", response_model=OpportunityRead, status_code=201)
def create_opportunity(payload: OpportunityWrite, db: Session = Depends(get_db)):
    data = prepare_opportunity(db, payload.model_dump(exclude_unset=True))
    opportunity = assign(Opportunity(), data)
    db.add(opportunity)
    commit(db)
    db.refresh(opportunity)
    return opportunity


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Opportunity, opportunity_id)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def update_opportunity(opportunity_id: str, payload: OpportunityUpdate, db: Session = Depends(get_db)):
    opportunity = get_or_404(db, Opportunity, opportunity_id)
    data = prepare_opportunity(db, payload.model_dump(exclude_unset=True), opportunity)
    assign(opportunity, data)
    commit(db)
    db.refresh(opportunity)
    return opportunity


@router.delete("/opportunities/{opportunity_id}", status_code=204)
def remove_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = get_or_404(db, Opportunity, opportunity_id)
    delete_opportunity(db, opportunity)
    commit(db)
    return Response(status_code=204)


@router.get("/quotes", response_model=dict)
def list_quotes(
    opportunity_id: str = Query(default=None),
    account_id: str = Query(default=None),
    contact_id: str = Query(default=None),
    status: str = Query(default=None),
    q: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(Quote)
    if opportunity_id:
        statement = statement.where(Quote.opportunity_id == opportunity_id)
    if account_id:
        statement = statement.where(Quote.account_id == account_id)
    if contact_id:
        statement = statement.where(Quote.contact_id == contact_id)
    if status:
        statement = statement.where(Quote.status == status)
    pattern = search_pattern(q)
    if pattern:
        statement = statement.where(Quote.name.ilike(pattern, escape="\\"))
    statement = statement.order_by(Quote.updated_at.desc())
    total, rows = _page(db, statement, limit, offset)
    return {"items": [QuoteRead.model_validate(row) for row in rows], "total": total}


@router.post("/quotes", response_model=QuoteRead, status_code=201)
def create_quote(payload: QuoteWrite, db: Session = Depends(get_db)):
    data = prepare_quote(db, payload.model_dump(exclude_unset=True))
    quote = assign(Quote(), data)
    db.add(quote)
    db.flush()
    recompute_quote(db, quote)
    commit(db)
    db.refresh(quote)
    return quote


@router.get("/quotes/{quote_id}", response_model=QuoteRead)
def get_quote(quote_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Quote, quote_id)


@router.patch("/quotes/{quote_id}", response_model=QuoteRead)
def update_quote(quote_id: str, payload: QuoteUpdate, db: Session = Depends(get_db)):
    quote = get_or_404(db, Quote, quote_id)
    data = prepare_quote(db, payload.model_dump(exclude_unset=True), quote)
    assign(quote, data)
    recompute_quote(db, quote)
    commit(db)
    db.refresh(quote)
    return quote


@router.delete("/quotes/{quote_id}", status_code=204)
def remove_quote(quote_id: str, db: Session = Depends(get_db)):
    quote = get_or_404(db, Quote, quote_id)
    delete_quote(db, quote)
    commit(db)
    return Response(status_code=204)


@router.get("/quotes/{quote_id}/line-items", response_model=dict)
def list_line_items(quote_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Quote, quote_id)
    rows = list(
        db.scalars(
            select(QuoteLineItem)
            .where(QuoteLineItem.quote_id == quote_id)
            .order_by(QuoteLineItem.sort_order, QuoteLineItem.created_at)
        ).all()
    )
    return {"items": [LineRead.model_validate(row) for row in rows], "total": len(rows)}


@router.post("/quotes/{quote_id}/line-items", response_model=LineWriteResult, status_code=201)
def create_line_item(quote_id: str, payload: LineWrite, db: Session = Depends(get_db)):
    quote = get_or_404(db, Quote, quote_id)
    data = payload.model_dump(exclude_unset=True)
    line = assign(QuoteLineItem(quote_id=quote.id, sort_order=next_sort_order(db, quote.id)), data)
    db.add(line)
    db.flush()
    recompute_quote(db, quote)
    commit(db)
    db.refresh(line)
    db.refresh(quote)
    return LineWriteResult(line_item=line, quote=quote)


@router.patch("/quotes/{quote_id}/line-items/{line_id}", response_model=LineWriteResult)
def update_line_item(quote_id: str, line_id: str, payload: LineUpdate, db: Session = Depends(get_db)):
    quote = get_or_404(db, Quote, quote_id)
    line = get_or_404(db, QuoteLineItem, line_id)
    if line.quote_id != quote.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Record not found")
    assign(line, payload.model_dump(exclude_unset=True))
    recompute_quote(db, quote)
    commit(db)
    db.refresh(line)
    db.refresh(quote)
    return LineWriteResult(line_item=line, quote=quote)


@router.delete("/quotes/{quote_id}/line-items/{line_id}", response_model=QuoteRead)
def remove_line_item(quote_id: str, line_id: str, db: Session = Depends(get_db)):
    quote = get_or_404(db, Quote, quote_id)
    line = get_or_404(db, QuoteLineItem, line_id)
    if line.quote_id != quote.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(line)
    db.flush()
    recompute_quote(db, quote)
    commit(db)
    db.refresh(quote)
    return quote
