CREATE TABLE IF NOT EXISTS day_reports (
    company_code TEXT NOT NULL,
    company_name TEXT,
    report_period TEXT NOT NULL,
    trade_volume TEXT,
    trade_value TEXT,
    transaction_count TEXT,
    opening_price TEXT,
    highest_price TEXT,
    lowest_price TEXT,
    closing_price TEXT,
    price_change TEXT,
    payload_json TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_day_reports_period
ON day_reports (report_period);

CREATE INDEX IF NOT EXISTS idx_day_reports_company
ON day_reports (company_code);
