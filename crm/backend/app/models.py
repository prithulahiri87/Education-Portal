"""Sales objects: Lead, Account, Contact, Opportunity, Quote, QuoteLineItem."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.database import Base
from app.domain import (
    ACCOUNT_TYPES,
    LEAD_RATINGS,
    LEAD_SOURCES,
    LEAD_STATUSES,
    OPPORTUNITY_STAGES,
    QUOTE_STATUSES,
    in_list,
    percent_check,
)


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(in_list("type", ACCOUNT_TYPES), name="ck_accounts_type"),
        CheckConstraint(
            "annual_revenue IS NULL OR annual_revenue >= 0",
            name="ck_accounts_revenue",
        ),
        CheckConstraint(
            "employee_count IS NULL OR employee_count >= 0",
            name="ck_accounts_employees",
        ),
        Index("ix_accounts_name", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="Prospect")
    industry: Mapped[str] = mapped_column(String(120), nullable=True)
    website: Mapped[str] = mapped_column(String(300), nullable=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)
    annual_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=True)
    billing_street: Mapped[str] = mapped_column(String(200), nullable=True)
    billing_city: Mapped[str] = mapped_column(String(80), nullable=True)
    billing_state: Mapped[str] = mapped_column(String(80), nullable=True)
    billing_postal_code: Mapped[str] = mapped_column(String(20), nullable=True)
    billing_country: Mapped[str] = mapped_column(String(80), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_email", "email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=True)
    department: Mapped[str] = mapped_column(String(120), nullable=True)
    email: Mapped[str] = mapped_column(String(254), nullable=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(in_list("stage", OPPORTUNITY_STAGES), name="ck_opportunities_stage"),
        CheckConstraint("amount >= 0", name="ck_opportunities_amount"),
        CheckConstraint(percent_check("probability"), name="ck_opportunities_probability"),
        Index("ix_opportunities_stage", "stage"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    primary_contact_id: Mapped[str] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="Prospecting")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    close_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Quote(TimestampMixin, Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint(in_list("status", QUOTE_STATUSES), name="ck_quotes_status"),
        CheckConstraint(percent_check("discount_percent"), name="ck_quotes_discount"),
        CheckConstraint(percent_check("tax_percent"), name="ck_quotes_tax"),
        CheckConstraint("subtotal >= 0", name="ck_quotes_subtotal"),
        CheckConstraint("discount_amount >= 0", name="ck_quotes_discount_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_quotes_tax_amount"),
        CheckConstraint("grand_total >= 0", name="ck_quotes_grand_total"),
        Index("ix_quotes_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")
    expiration_date: Mapped[date] = mapped_column(Date, nullable=True)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    line_items: Mapped[list] = relationship(
        "QuoteLineItem",
        back_populates="quote",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class QuoteLineItem(TimestampMixin, Base):
    __tablename__ = "quote_line_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_line_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_line_price"),
        CheckConstraint(percent_check("discount_percent"), name="ck_line_discount"),
        CheckConstraint("line_total >= 0", name="ck_line_total"),
        CheckConstraint("sort_order >= 0", name="ck_line_sort"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    quote: Mapped[Quote] = relationship(back_populates="line_items")


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(in_list("status", LEAD_STATUSES), name="ck_leads_status"),
        CheckConstraint(in_list("source", LEAD_SOURCES, allow_null=True), name="ck_leads_source"),
        CheckConstraint(in_list("rating", LEAD_RATINGS, allow_null=True), name="ck_leads_rating"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_email", "email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=True)
    title: Mapped[str] = mapped_column(String(120), nullable=True)
    email: Mapped[str] = mapped_column(String(254), nullable=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="New")
    source: Mapped[str] = mapped_column(String(32), nullable=True)
    rating: Mapped[str] = mapped_column(String(16), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    converted_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    converted_contact_id: Mapped[str] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    converted_opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )


@event.listens_for(Session, "before_flush")
def touch_updated_at(session, _flush_context, _instances):
    now = utcnow()
    for obj in session.dirty:
        if isinstance(obj, Base) and hasattr(obj, "updated_at"):
            obj.updated_at = now
