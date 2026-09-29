"""Sample desk. Idempotent: if any account exists, it leaves the database alone."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.database import get_session_factory, init_db
from app.domain import STAGE_PROBABILITY
from app.models import Account, Contact, Lead, Opportunity, Quote, QuoteLineItem, utcnow
from app.services import recompute_quote

ACCOUNT_NORTHWIND = "11111111-1111-4111-8111-111111111111"
ACCOUNT_LUMEN = "22222222-2222-4222-8222-222222222222"
CONTACT_ADA = "33333333-3333-4333-8333-333333333333"
CONTACT_EVAN = "44444444-4444-4444-8444-444444444444"
CONTACT_MINA = "55555555-5555-4555-8555-555555555555"
OPP_RACKING = "66666666-6666-4666-8666-666666666666"
OPP_RETAINER = "77777777-7777-4777-8777-777777777777"
OPP_KIOSK = "88888888-8888-4888-8888-888888888888"
QUOTE_RACKING = "99999999-9999-4999-8999-999999999999"
QUOTE_KIOSK = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LEAD_JONAH = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
LEAD_ADELE = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
LEAD_ADA = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def seed():
    init_db()
    db = get_session_factory()()
    try:
        if db.scalar(select(Account.id).limit(1)):
            return False
        today = utcnow().date()
        northwind = Account(
            id=ACCOUNT_NORTHWIND,
            name="Northwind Goods",
            type="Customer",
            industry="Wholesale",
            website="https://northwind.example",
            phone="555-0100",
            annual_revenue=Decimal("4200000.00"),
            employee_count=86,
            billing_city="Oakland",
            billing_state="CA",
            billing_country="USA",
            description="Regional wholesaler replacing warehouse racking.",
        )
        lumen = Account(
            id=ACCOUNT_LUMEN,
            name="Lumen Field Clinics",
            type="Prospect",
            industry="Healthcare",
            website="https://lumenfield.example",
            phone="555-0142",
            annual_revenue=Decimal("9100000.00"),
            employee_count=140,
            billing_city="Austin",
            billing_state="TX",
            billing_country="USA",
            description="Clinic group evaluating intake kiosks.",
        )
        ada = Contact(
            id=CONTACT_ADA,
            account_id=northwind.id,
            first_name="Ada",
            last_name="Brooks",
            title="Director of Operations",
            department="Operations",
            email="ada.brooks@example.com",
            phone="555-0101",
        )
        evan = Contact(
            id=CONTACT_EVAN,
            account_id=northwind.id,
            first_name="Evan",
            last_name="Cole",
            title="CFO",
            department="Finance",
            email="evan.cole@example.com",
            phone="555-0108",
        )
        mina = Contact(
            id=CONTACT_MINA,
            account_id=lumen.id,
            first_name="Mina",
            last_name="Ortiz",
            title="VP of Operations",
            department="Operations",
            email="mina.ortiz@example.com",
            phone="555-0148",
        )
        racking = Opportunity(
            id=OPP_RACKING,
            account_id=northwind.id,
            primary_contact_id=ada.id,
            name="Warehouse racking refresh",
            stage="Proposal",
            amount=Decimal("0.00"),
            probability=STAGE_PROBABILITY["Proposal"],
            close_date=today + timedelta(days=28),
            description="Replace aisle racking and install the new rows.",
        )
        retainer = Opportunity(
            id=OPP_RETAINER,
            account_id=northwind.id,
            primary_contact_id=evan.id,
            name="Support retainer",
            stage="Qualification",
            amount=Decimal("12000.00"),
            probability=STAGE_PROBABILITY["Qualification"],
            close_date=today + timedelta(days=45),
            description="Annual support after the racking project.",
        )
        kiosk = Opportunity(
            id=OPP_KIOSK,
            account_id=lumen.id,
            primary_contact_id=mina.id,
            name="Intake kiosks",
            stage="Negotiation",
            amount=Decimal("0.00"),
            probability=STAGE_PROBABILITY["Negotiation"],
            close_date=today + timedelta(days=18),
            description="Eight lobby kiosks plus a first-year service plan.",
        )
        quote_racking = Quote(
            id=QUOTE_RACKING,
            opportunity_id=racking.id,
            account_id=northwind.id,
            contact_id=ada.id,
            name="Q-1042 Warehouse racking",
            status="Draft",
            expiration_date=today + timedelta(days=21),
            discount_percent=Decimal("0.00"),
            tax_percent=Decimal("0.00"),
        )
        quote_kiosk = Quote(
            id=QUOTE_KIOSK,
            opportunity_id=kiosk.id,
            account_id=lumen.id,
            contact_id=mina.id,
            name="Q-1048 Intake kiosks",
            status="Presented",
            expiration_date=today + timedelta(days=14),
            discount_percent=Decimal("5.00"),
            tax_percent=Decimal("8.25"),
        )
        db.add_all([northwind, lumen, ada, evan, mina, racking, retainer, kiosk, quote_racking, quote_kiosk])
        db.flush()
        db.add_all(
            [
                QuoteLineItem(
                    id="e1111111-1111-4111-8111-111111111111",
                    quote_id=quote_racking.id,
                    sort_order=1,
                    product_name="Pallet racking",
                    quantity=Decimal("12.00"),
                    unit_price=Decimal("1800.00"),
                    discount_percent=Decimal("5.00"),
                ),
                QuoteLineItem(
                    id="e2222222-2222-4222-8222-222222222222",
                    quote_id=quote_racking.id,
                    sort_order=2,
                    product_name="Installation",
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("6400.00"),
                    discount_percent=Decimal("0.00"),
                ),
                QuoteLineItem(
                    id="e3333333-3333-4333-8333-333333333333",
                    quote_id=quote_kiosk.id,
                    sort_order=1,
                    product_name="Intake kiosk",
                    quantity=Decimal("8.00"),
                    unit_price=Decimal("7200.00"),
                    discount_percent=Decimal("0.00"),
                ),
                QuoteLineItem(
                    id="e4444444-4444-4444-8444-444444444444",
                    quote_id=quote_kiosk.id,
                    sort_order=2,
                    product_name="Service plan",
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("4800.00"),
                    discount_percent=Decimal("10.00"),
                ),
            ]
        )
        db.flush()
        recompute_quote(db, quote_racking)
        recompute_quote(db, quote_kiosk)
        racking.amount = quote_racking.grand_total
        kiosk.amount = quote_kiosk.grand_total
        db.add_all(
            [
                Lead(
                    id=LEAD_ADA,
                    first_name="Ada",
                    last_name="Brooks",
                    company="Northwind Goods",
                    title="Director of Operations",
                    email="ada.brooks@example.com",
                    phone="555-0101",
                    status="Converted",
                    source="Campaign",
                    rating="Hot",
                    description="Converted from the spring facilities campaign.",
                    converted_account_id=northwind.id,
                    converted_contact_id=ada.id,
                    converted_opportunity_id=racking.id,
                ),
                Lead(
                    id=LEAD_JONAH,
                    first_name="Jonah",
                    last_name="Hale",
                    company="Bright Parcel Co",
                    title="Logistics Manager",
                    email="jonah.hale@example.com",
                    phone="555-0177",
                    status="New",
                    source="Web",
                    rating="Warm",
                    description="Asked for a racking estimate after the site form.",
                ),
                Lead(
                    id=LEAD_ADELE,
                    first_name="Adele",
                    last_name="Frost",
                    company="Paper & Pine",
                    title="Owner",
                    email="adele.frost@example.com",
                    phone="555-0194",
                    status="Working",
                    source="Referral",
                    rating="Hot",
                    description="Referred by Evan Cole. Wants a showroom quote.",
                ),
            ]
        )
        db.commit()
        return True
    finally:
        db.close()
