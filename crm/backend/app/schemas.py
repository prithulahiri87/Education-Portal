"""Request and response contracts. Clients cannot set server-owned totals or conversion links."""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, field_validator

from app.domain import (
    ACCOUNT_TYPES,
    EDITABLE_LEAD_STATUSES,
    LEAD_RATINGS,
    LEAD_SOURCES,
    OPPORTUNITY_STAGES,
    QUOTE_STATUSES,
)

TWOPLACES = Decimal("0.01")


def parse_decimal(value):
    if isinstance(value, str) and not value.strip():
        raise ValueError("Enter a number")
    try:
        return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a number")


def parse_optional_decimal(value):
    if value is None or value == "":
        return None
    return parse_decimal(value)


JsonDecimal = Annotated[
    Decimal,
    BeforeValidator(parse_decimal),
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]
OptionalJsonDecimal = Annotated[
    Optional[Decimal],
    BeforeValidator(parse_optional_decimal),
    PlainSerializer(
        lambda value: None if value is None else float(value),
        return_type=float,
        when_used="json",
    ),
]


def clean_required(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("This field is required")
    return value.strip()


def clean_optional(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Enter text")
    text = value.strip()
    return text or None


def clean_email(value):
    value = clean_optional(value)
    if value is None:
        return None
    if len(value) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("Enter a valid email address")
    return value


def clean_phone(value):
    value = clean_optional(value)
    if value is None:
        return None
    if not re.fullmatch(r"[0-9+\-().\s]{3,40}", value):
        raise ValueError("Enter a phone number using digits and + - ( )")
    return value


def clean_website(value):
    value = clean_optional(value)
    if value is None:
        return None
    if len(value) > 300 or not value.startswith(("http://", "https://")):
        raise ValueError("Website must start with http:// or https://")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Website must be an http(s) URL")
    return value


def clean_id(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("Record id is not valid")


RequiredName = Annotated[str, BeforeValidator(clean_required), Field(max_length=160)]
RequiredShort = Annotated[str, BeforeValidator(clean_required), Field(max_length=80)]
OptionalName = Annotated[Optional[str], BeforeValidator(clean_optional), Field(max_length=160)]
OptionalShort = Annotated[Optional[str], BeforeValidator(clean_optional), Field(max_length=120)]
OptionalMedium = Annotated[Optional[str], BeforeValidator(clean_optional), Field(max_length=80)]
OptionalPostal = Annotated[Optional[str], BeforeValidator(clean_optional), Field(max_length=20)]
OptionalText = Annotated[Optional[str], BeforeValidator(clean_optional), Field(max_length=8000)]
OptionalEmail = Annotated[Optional[str], BeforeValidator(clean_email)]
OptionalPhone = Annotated[Optional[str], BeforeValidator(clean_phone)]
OptionalWebsite = Annotated[Optional[str], BeforeValidator(clean_website)]
RecordId = Annotated[str, BeforeValidator(clean_id)]
OptionalRecordId = Annotated[Optional[str], BeforeValidator(lambda value: None if value in (None, "") else clean_id(value))]


class WriteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    items: list
    total: int


class LeadWrite(WriteModel):
    first_name: RequiredShort
    last_name: RequiredShort
    company: OptionalName = None
    title: OptionalShort = None
    email: OptionalEmail = None
    phone: OptionalPhone = None
    status: str = "New"
    source: Optional[str] = None
    rating: Optional[str] = None
    description: OptionalText = None

    @field_validator("status")
    @classmethod
    def status_is_editable(cls, value):
        if value not in EDITABLE_LEAD_STATUSES:
            raise ValueError("Use the convert action to convert a lead")
        return value

    @field_validator("source")
    @classmethod
    def source_is_known(cls, value):
        value = clean_optional(value)
        if value is not None and value not in LEAD_SOURCES:
            raise ValueError("Unsupported lead source")
        return value

    @field_validator("rating")
    @classmethod
    def rating_is_known(cls, value):
        value = clean_optional(value)
        if value is not None and value not in LEAD_RATINGS:
            raise ValueError("Unsupported lead rating")
        return value


class LeadUpdate(WriteModel):
    first_name: Optional[RequiredShort] = None
    last_name: Optional[RequiredShort] = None
    company: OptionalName = None
    title: OptionalShort = None
    email: OptionalEmail = None
    phone: OptionalPhone = None
    status: Optional[str] = None
    source: Optional[str] = None
    rating: Optional[str] = None
    description: OptionalText = None

    @field_validator("status")
    @classmethod
    def status_is_editable(cls, value):
        if value is None:
            return value
        if value not in EDITABLE_LEAD_STATUSES:
            raise ValueError("Use the convert action to convert a lead")
        return value

    @field_validator("source")
    @classmethod
    def source_is_known(cls, value):
        value = clean_optional(value)
        if value is not None and value not in LEAD_SOURCES:
            raise ValueError("Unsupported lead source")
        return value

    @field_validator("rating")
    @classmethod
    def rating_is_known(cls, value):
        value = clean_optional(value)
        if value is not None and value not in LEAD_RATINGS:
            raise ValueError("Unsupported lead rating")
        return value


class LeadRead(ReadModel):
    id: str
    first_name: str
    last_name: str
    company: Optional[str]
    title: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    status: str
    source: Optional[str]
    rating: Optional[str]
    description: Optional[str]
    converted_account_id: Optional[str]
    converted_contact_id: Optional[str]
    converted_opportunity_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class ConvertLead(WriteModel):
    account_name: OptionalName = None
    create_opportunity: bool = True
    opportunity_name: OptionalName = None
    close_date: Optional[date] = None


class AccountWrite(WriteModel):
    name: RequiredName
    type: str = "Prospect"
    industry: OptionalShort = None
    website: OptionalWebsite = None
    phone: OptionalPhone = None
    annual_revenue: OptionalJsonDecimal = None
    employee_count: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    billing_street: OptionalName = None
    billing_city: OptionalMedium = None
    billing_state: OptionalMedium = None
    billing_postal_code: OptionalPostal = None
    billing_country: OptionalMedium = None
    description: OptionalText = None

    @field_validator("type")
    @classmethod
    def type_is_known(cls, value):
        if value not in ACCOUNT_TYPES:
            raise ValueError("Unsupported account type")
        return value

    @field_validator("annual_revenue")
    @classmethod
    def revenue_is_positive(cls, value):
        if value is not None and value < 0:
            raise ValueError("Annual revenue cannot be negative")
        return value


class AccountUpdate(WriteModel):
    name: Optional[RequiredName] = None
    type: Optional[str] = None
    industry: OptionalShort = None
    website: OptionalWebsite = None
    phone: OptionalPhone = None
    annual_revenue: OptionalJsonDecimal = None
    employee_count: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    billing_street: OptionalName = None
    billing_city: OptionalMedium = None
    billing_state: OptionalMedium = None
    billing_postal_code: OptionalPostal = None
    billing_country: OptionalMedium = None
    description: OptionalText = None

    @field_validator("type")
    @classmethod
    def type_is_known(cls, value):
        if value is None:
            return value
        if value not in ACCOUNT_TYPES:
            raise ValueError("Unsupported account type")
        return value

    @field_validator("annual_revenue")
    @classmethod
    def revenue_is_positive(cls, value):
        if value is not None and value < 0:
            raise ValueError("Annual revenue cannot be negative")
        return value


class AccountRead(ReadModel):
    id: str
    name: str
    type: str
    industry: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    annual_revenue: OptionalJsonDecimal
    employee_count: Optional[int]
    billing_street: Optional[str]
    billing_city: Optional[str]
    billing_state: Optional[str]
    billing_postal_code: Optional[str]
    billing_country: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class ContactWrite(WriteModel):
    account_id: RecordId
    first_name: RequiredShort
    last_name: RequiredShort
    title: OptionalShort = None
    department: OptionalShort = None
    email: OptionalEmail = None
    phone: OptionalPhone = None
    description: OptionalText = None


class ContactUpdate(WriteModel):
    account_id: Optional[RecordId] = None
    first_name: Optional[RequiredShort] = None
    last_name: Optional[RequiredShort] = None
    title: OptionalShort = None
    department: OptionalShort = None
    email: OptionalEmail = None
    phone: OptionalPhone = None
    description: OptionalText = None


class ContactRead(ReadModel):
    id: str
    account_id: str
    first_name: str
    last_name: str
    title: Optional[str]
    department: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class OpportunityWrite(WriteModel):
    account_id: RecordId
    primary_contact_id: OptionalRecordId = None
    name: RequiredName
    stage: str = "Prospecting"
    amount: JsonDecimal = Decimal("0.00")
    probability: Optional[int] = Field(default=None, ge=0, le=100)
    close_date: date
    description: OptionalText = None

    @field_validator("stage")
    @classmethod
    def stage_is_known(cls, value):
        if value not in OPPORTUNITY_STAGES:
            raise ValueError("Unsupported opportunity stage")
        return value

    @field_validator("amount")
    @classmethod
    def amount_is_positive(cls, value):
        if value < 0:
            raise ValueError("Amount cannot be negative")
        return value


class OpportunityUpdate(WriteModel):
    account_id: Optional[RecordId] = None
    primary_contact_id: OptionalRecordId = None
    name: Optional[RequiredName] = None
    stage: Optional[str] = None
    amount: Optional[JsonDecimal] = None
    probability: Optional[int] = Field(default=None, ge=0, le=100)
    close_date: Optional[date] = None
    description: OptionalText = None

    @field_validator("stage")
    @classmethod
    def stage_is_known(cls, value):
        if value is not None and value not in OPPORTUNITY_STAGES:
            raise ValueError("Unsupported opportunity stage")
        return value

    @field_validator("amount")
    @classmethod
    def amount_is_positive(cls, value):
        if value is not None and value < 0:
            raise ValueError("Amount cannot be negative")
        return value


class OpportunityRead(ReadModel):
    id: str
    account_id: str
    primary_contact_id: Optional[str]
    name: str
    stage: str
    amount: JsonDecimal
    probability: int
    close_date: date
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class QuoteWrite(WriteModel):
    opportunity_id: RecordId
    contact_id: OptionalRecordId = None
    name: RequiredName
    status: str = "Draft"
    expiration_date: Optional[date] = None
    discount_percent: JsonDecimal = Decimal("0.00")
    tax_percent: JsonDecimal = Decimal("0.00")
    description: OptionalText = None

    @field_validator("status")
    @classmethod
    def status_is_known(cls, value):
        if value not in QUOTE_STATUSES:
            raise ValueError("Unsupported quote status")
        return value

    @field_validator("discount_percent", "tax_percent")
    @classmethod
    def percent_in_range(cls, value):
        if value < 0 or value > 100:
            raise ValueError("Percent must be between 0 and 100")
        return value


class QuoteUpdate(WriteModel):
    opportunity_id: Optional[RecordId] = None
    contact_id: OptionalRecordId = None
    name: Optional[RequiredName] = None
    status: Optional[str] = None
    expiration_date: Optional[date] = None
    discount_percent: Optional[JsonDecimal] = None
    tax_percent: Optional[JsonDecimal] = None
    description: OptionalText = None

    @field_validator("status")
    @classmethod
    def status_is_known(cls, value):
        if value is not None and value not in QUOTE_STATUSES:
            raise ValueError("Unsupported quote status")
        return value

    @field_validator("discount_percent", "tax_percent")
    @classmethod
    def percent_in_range(cls, value):
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Percent must be between 0 and 100")
        return value


class QuoteRead(ReadModel):
    id: str
    opportunity_id: str
    account_id: str
    contact_id: Optional[str]
    name: str
    status: str
    expiration_date: Optional[date]
    discount_percent: JsonDecimal
    tax_percent: JsonDecimal
    subtotal: JsonDecimal
    discount_amount: JsonDecimal
    tax_amount: JsonDecimal
    grand_total: JsonDecimal
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class LineWrite(WriteModel):
    product_name: RequiredName
    description: OptionalText = None
    quantity: JsonDecimal
    unit_price: JsonDecimal
    discount_percent: JsonDecimal = Decimal("0.00")

    @field_validator("quantity")
    @classmethod
    def quantity_is_positive(cls, value):
        if value <= 0:
            raise ValueError("Quantity must be greater than zero")
        return value

    @field_validator("unit_price")
    @classmethod
    def price_is_positive(cls, value):
        if value < 0:
            raise ValueError("Unit price cannot be negative")
        return value

    @field_validator("discount_percent")
    @classmethod
    def percent_in_range(cls, value):
        if value < 0 or value > 100:
            raise ValueError("Percent must be between 0 and 100")
        return value


class LineUpdate(WriteModel):
    product_name: Optional[RequiredName] = None
    description: OptionalText = None
    quantity: Optional[JsonDecimal] = None
    unit_price: Optional[JsonDecimal] = None
    discount_percent: Optional[JsonDecimal] = None

    @field_validator("quantity")
    @classmethod
    def quantity_is_positive(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Quantity must be greater than zero")
        return value

    @field_validator("unit_price")
    @classmethod
    def price_is_positive(cls, value):
        if value is not None and value < 0:
            raise ValueError("Unit price cannot be negative")
        return value

    @field_validator("discount_percent")
    @classmethod
    def percent_in_range(cls, value):
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Percent must be between 0 and 100")
        return value


class LineRead(ReadModel):
    id: str
    quote_id: str
    sort_order: int
    product_name: str
    description: Optional[str]
    quantity: JsonDecimal
    unit_price: JsonDecimal
    discount_percent: JsonDecimal
    line_total: JsonDecimal
    created_at: datetime
    updated_at: datetime


class LineWriteResult(BaseModel):
    line_item: LineRead
    quote: QuoteRead


class ConvertResult(BaseModel):
    lead: LeadRead
    account: AccountRead
    contact: ContactRead
    opportunity: Optional[OpportunityRead]


class StageTotal(BaseModel):
    stage: str
    count: int
    amount: JsonDecimal


class DashboardRead(BaseModel):
    counts: dict
    open_pipeline_amount: JsonDecimal
    accepted_quote_total: JsonDecimal
    open_quote_count: int
    pipeline: list
    recent_leads: list
