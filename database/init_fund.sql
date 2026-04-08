CREATE TABLE IF NOT EXISTS funds (
    fund_code TEXT PRIMARY KEY,
    data_date TEXT NOT NULL,
    fund_short_name TEXT,
    fund_type TEXT,
    fund_name_zh TEXT,
    fund_name_en TEXT,
    benchmark_index_name TEXT,
    benchmark_index_disclosure_flag TEXT,
    stock_bond_allocation_note TEXT,
    has_performance_benchmark TEXT,
    performance_benchmark_name_zh TEXT,
    performance_benchmark_name_en TEXT,
    includes_foreign_constituents TEXT,
    fund_registration_number TEXT,
    establishment_date TEXT,
    listed_date TEXT,
    fund_manager TEXT,
    manager_company_phone TEXT,
    manager_company_address TEXT,
    manager_company_chairman TEXT,
    manager_company_spokesperson TEXT,
    manager_company_general_manager TEXT,
    manager_company_acting_spokesperson TEXT,
    master_agent TEXT,
    issued_units_or_conversion_units TEXT,
    custodian_institution TEXT,
    custodian_phone TEXT,
    custodian_address TEXT,
    remarks TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_funds_name_zh
ON funds (fund_name_zh);

CREATE INDEX IF NOT EXISTS idx_funds_type
ON funds (fund_type);