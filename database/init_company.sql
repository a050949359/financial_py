CREATE TABLE IF NOT EXISTS companies (
    company_code TEXT PRIMARY KEY,
    data_date TEXT NOT NULL,
    company_name TEXT,
    company_short_name TEXT,
    foreign_registration_country TEXT,
    industry_category TEXT,
    address TEXT,
    business_registration_number TEXT,
    chairman TEXT,
    general_manager TEXT,
    spokesperson TEXT,
    spokesperson_title TEXT,
    acting_spokesperson TEXT,
    switchboard_phone TEXT,
    establishment_date TEXT,
    listed_date TEXT,
    par_value_per_share TEXT,
    paid_in_capital TEXT,
    private_placement_shares TEXT,
    preferred_shares TEXT,
    financial_statement_type TEXT,
    stock_transfer_agent TEXT,
    transfer_phone TEXT,
    transfer_address TEXT,
    certified_accounting_firm TEXT,
    certified_accountant_1 TEXT,
    certified_accountant_2 TEXT,
    english_short_name TEXT,
    english_address TEXT,
    fax_number TEXT,
    email TEXT,
    website TEXT,
    issued_common_shares_or_tdr_shares TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_name
ON companies (company_name);

CREATE INDEX IF NOT EXISTS idx_companies_industry
ON companies (industry_category);