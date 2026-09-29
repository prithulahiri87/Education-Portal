-- Harbor CRM reference schema for Postgres.
-- The API creates the same tables on startup through SQLAlchemy.
-- Apply this file only when you want to inspect or provision the database yourself.

CREATE TABLE accounts (
    id varchar(36) PRIMARY KEY,
    name varchar(160) NOT NULL,
    type varchar(32) NOT NULL DEFAULT 'Prospect',
    industry varchar(120),
    website varchar(300),
    phone varchar(40),
    annual_revenue numeric(12, 2),
    employee_count integer,
    billing_street varchar(200),
    billing_city varchar(80),
    billing_state varchar(80),
    billing_postal_code varchar(20),
    billing_country varchar(80),
    description text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_accounts_type CHECK (type IN ('Prospect', 'Customer', 'Partner', 'Other')),
    CONSTRAINT ck_accounts_revenue CHECK (annual_revenue IS NULL OR annual_revenue >= 0),
    CONSTRAINT ck_accounts_employees CHECK (employee_count IS NULL OR employee_count >= 0)
);

CREATE TABLE contacts (
    id varchar(36) PRIMARY KEY,
    account_id varchar(36) NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    first_name varchar(80) NOT NULL,
    last_name varchar(80) NOT NULL,
    title varchar(120),
    department varchar(120),
    email varchar(254),
    phone varchar(40),
    description text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE opportunities (
    id varchar(36) PRIMARY KEY,
    account_id varchar(36) NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    primary_contact_id varchar(36) REFERENCES contacts (id) ON DELETE SET NULL,
    name varchar(160) NOT NULL,
    stage varchar(32) NOT NULL DEFAULT 'Prospecting',
    amount numeric(12, 2) NOT NULL DEFAULT 0,
    probability integer NOT NULL DEFAULT 10,
    close_date date NOT NULL,
    description text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_opportunities_stage CHECK (stage IN (
        'Prospecting', 'Qualification', 'Needs Analysis', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost'
    )),
    CONSTRAINT ck_opportunities_amount CHECK (amount >= 0),
    CONSTRAINT ck_opportunities_probability CHECK (probability >= 0 AND probability <= 100)
);

CREATE TABLE quotes (
    id varchar(36) PRIMARY KEY,
    opportunity_id varchar(36) NOT NULL REFERENCES opportunities (id) ON DELETE RESTRICT,
    account_id varchar(36) NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    contact_id varchar(36) REFERENCES contacts (id) ON DELETE SET NULL,
    name varchar(160) NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'Draft',
    expiration_date date,
    discount_percent numeric(5, 2) NOT NULL DEFAULT 0,
    tax_percent numeric(5, 2) NOT NULL DEFAULT 0,
    subtotal numeric(12, 2) NOT NULL DEFAULT 0,
    discount_amount numeric(12, 2) NOT NULL DEFAULT 0,
    tax_amount numeric(12, 2) NOT NULL DEFAULT 0,
    grand_total numeric(12, 2) NOT NULL DEFAULT 0,
    description text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_quotes_status CHECK (status IN ('Draft', 'In Review', 'Presented', 'Accepted', 'Rejected', 'Expired')),
    CONSTRAINT ck_quotes_discount CHECK (discount_percent >= 0 AND discount_percent <= 100),
    CONSTRAINT ck_quotes_tax CHECK (tax_percent >= 0 AND tax_percent <= 100),
    CONSTRAINT ck_quotes_subtotal CHECK (subtotal >= 0),
    CONSTRAINT ck_quotes_discount_amount CHECK (discount_amount >= 0),
    CONSTRAINT ck_quotes_tax_amount CHECK (tax_amount >= 0),
    CONSTRAINT ck_quotes_grand_total CHECK (grand_total >= 0)
);

CREATE TABLE quote_line_items (
    id varchar(36) PRIMARY KEY,
    quote_id varchar(36) NOT NULL REFERENCES quotes (id) ON DELETE CASCADE,
    sort_order integer NOT NULL DEFAULT 0,
    product_name varchar(160) NOT NULL,
    description text,
    quantity numeric(12, 2) NOT NULL,
    unit_price numeric(12, 2) NOT NULL,
    discount_percent numeric(5, 2) NOT NULL DEFAULT 0,
    line_total numeric(12, 2) NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_line_quantity CHECK (quantity > 0),
    CONSTRAINT ck_line_price CHECK (unit_price >= 0),
    CONSTRAINT ck_line_discount CHECK (discount_percent >= 0 AND discount_percent <= 100),
    CONSTRAINT ck_line_total CHECK (line_total >= 0),
    CONSTRAINT ck_line_sort CHECK (sort_order >= 0)
);

CREATE TABLE leads (
    id varchar(36) PRIMARY KEY,
    first_name varchar(80) NOT NULL,
    last_name varchar(80) NOT NULL,
    company varchar(160),
    title varchar(120),
    email varchar(254),
    phone varchar(40),
    status varchar(32) NOT NULL DEFAULT 'New',
    source varchar(32),
    rating varchar(16),
    description text,
    converted_account_id varchar(36) REFERENCES accounts (id) ON DELETE SET NULL,
    converted_contact_id varchar(36) REFERENCES contacts (id) ON DELETE SET NULL,
    converted_opportunity_id varchar(36) REFERENCES opportunities (id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_leads_status CHECK (status IN ('New', 'Working', 'Qualified', 'Unqualified', 'Converted')),
    CONSTRAINT ck_leads_source CHECK (source IS NULL OR source IN ('Web', 'Phone', 'Referral', 'Partner', 'Campaign', 'Other')),
    CONSTRAINT ck_leads_rating CHECK (rating IS NULL OR rating IN ('Hot', 'Warm', 'Cold'))
);

CREATE INDEX ix_accounts_name ON accounts (name);
CREATE INDEX ix_contacts_account_id ON contacts (account_id);
CREATE INDEX ix_contacts_email ON contacts (email);
CREATE INDEX ix_opportunities_account_id ON opportunities (account_id);
CREATE INDEX ix_opportunities_primary_contact_id ON opportunities (primary_contact_id);
CREATE INDEX ix_opportunities_stage ON opportunities (stage);
CREATE INDEX ix_quotes_opportunity_id ON quotes (opportunity_id);
CREATE INDEX ix_quotes_account_id ON quotes (account_id);
CREATE INDEX ix_quotes_contact_id ON quotes (contact_id);
CREATE INDEX ix_quotes_status ON quotes (status);
CREATE INDEX ix_quote_line_items_quote_id ON quote_line_items (quote_id);
CREATE INDEX ix_leads_status ON leads (status);
CREATE INDEX ix_leads_email ON leads (email);
