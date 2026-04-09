CREATE TABLE IF NOT EXISTS year_reports (
    company_code TEXT NOT NULL,
    company_name TEXT,
    report_period TEXT NOT NULL,
    trade_volume TEXT,
    trade_value TEXT,
    transaction_count TEXT,
    highest_price TEXT,
    lowest_price TEXT,
    avg_closing_price TEXT,
    high_date TEXT,
    low_date TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_year_reports_period
ON year_reports (report_period);

CREATE INDEX IF NOT EXISTS idx_year_reports_company
ON year_reports (company_code);
