CREATE TABLE IF NOT EXISTS month_reports (
    company_code TEXT NOT NULL,
    company_name TEXT,
    report_period TEXT NOT NULL,
    trade_volume TEXT,
    trade_value TEXT,
    transaction_count TEXT,
    highest_price TEXT,
    lowest_price TEXT,
    weighted_avg_price TEXT,
    turnover_ratio TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_month_reports_period
ON month_reports (report_period);

CREATE INDEX IF NOT EXISTS idx_month_reports_company
ON month_reports (company_code);
