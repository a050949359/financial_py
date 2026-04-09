# TWSE OpenData

這個目錄用來管理臺灣證券交易所 OpenAPI 的抓取、原始 JSON 落地、SQLite schema 初始化、資料匯入與 log 管理。

## 目錄說明

- TWSE/: dataset 專屬流程腳本
- core/fetcher.py / core/importer.py: 共用抓取與匯入模組
- registry.d/: dataset 註冊表，每個 dataset 一個 TOML 檔
- Source/: 下載回來的原始 JSON
- database/: SQLite schema SQL
- log/: 執行過程中的錯誤 log
- utils/: 共用工具模組（例如 log 處理）
- init.py: 共用設定讀取、SQLite db 檔初始化、log 清理入口
- config.toml: 專案設定
- Makefile: 常用操作指令入口

## 目前功能

- 抓取上市公司基本資料 OpenAPI
- 抓取基金基本資料 OpenAPI
- 將 API 原始資料輸出成 JSON 到 Source/
- 依設定建立 SQLite db 檔案
- 初始化公司資料表 schema
- 初始化基金資料表 schema
- 從本地 JSON 匯入公司資料到 SQLite
- 從本地 JSON 匯入基金資料到 SQLite
- 抓取全市場日報並儲存 JSON
- 抓取全市場月報並儲存 JSON
- 抓取全年報並儲存 JSON
- 從本地日報/月報/年報 JSON 匯入 SQLite
- 初始化日報/月報/年報各自的 schema
- 日報/月報/年報分別匯入 day_reports、month_reports、year_reports
- 直接從日報/月報/年報 API 抓資料後匯入 SQLite
- 直接從 API 抓資料後匯入 SQLite
- API 呼叫失敗時寫入每日 log
- SQL schema 或匯入失敗時寫入每日 log
- 透過 mtime 清理過期 log

## 主要指令

```bash
make validate-config
make init-db
make init-company-schema
make init-fund-schema
make init-day-reports-schema
make init-month-reports-schema
make init-year-reports-schema
make fetch-company
make fetch-fund
make fetch-day-reports
make fetch-month-reports
make fetch-year-reports
make import-company
make import-fund
make import-day-reports
make import-month-reports
make import-year-reports
make sync-company
make sync-fund
make sync-day-reports
make sync-month-reports
make sync-year-reports
make clean-company-json
make clean-fund-json
make clean-log
```

## 可用參數

`fetch-company` 與 `fetch-fund` 可帶以下參數：

```bash
make fetch-company TIMEOUT=60
make fetch-company OUTPUT=Source/company_custom.json
make fetch-fund API_URL=https://openapi.twse.com.tw/v1/opendata/t187ap47_L
make fetch-fund CONFIG=/path/to/config.toml
make validate-config DATASET=company
make fetch-day-reports OUTPUT=Source/day_report_custom.json
make fetch-month-reports
make fetch-year-reports
make import-day-reports
make sync-day-reports
```

## 設定檔

設定檔位於 config.toml。

dataset 預設註冊表位於 registry.d/，採一個 dataset 一個 TOML 檔的形式。

可以先用下列指令驗證設定是否可用：

```bash
make validate-config
make validate-config DATASET=company
python3 init.py --config config.toml --validate-config
python3 init.py --config config.toml --print-dataset-json-path company
```

```toml
[system]
db_driver = "sqlite"
db_path = "database/twse.db"
source_dir = "Source"
log_path = "log"
log_retention_days = 30
debug = false

[company]
api_endpoint = "/opendata/t187ap03_L"
schema_path = "database/init_company.sql"
table_name = "companies"
json_name = "listed_company.json"

[fund]
api_endpoint = "/opendata/t187ap47_L"
schema_path = "database/init_fund.sql"
table_name = "funds"
json_name = "fund.json"

[day_report]
api_endpoint = "/exchangeReport/STOCK_DAY_ALL"
schema_path = "database/init_day_report.sql"
table_name = "day_reports"
json_name = "day_report.json"

[month_report]
api_endpoint = "/exchangeReport/FMSRFK_ALL"
schema_path = "database/init_month_report.sql"
table_name = "month_reports"
json_name = "month_report.json"

[year_report]
api_endpoint = "/exchangeReport/FMNPTK_ALL"
schema_path = "database/init_year_report.sql"
table_name = "year_reports"
json_name = "year_report.json"
```

## Log 規則

- log 檔名格式為 YYYYMMDD.log
- 所有錯誤寫入同一天的同一份 log
- 目前只記錄 error 等級
- 當 `debug = true` 時，會額外記錄抓取/匯入的耗時與結果摘要
- `make clean-log` 依檔案 mtime 與 `log_retention_days` 清理過期 log
- `log_retention_days = 0` 代表不清理任何 log
