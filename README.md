# TWSE OpenData

這個目錄用來管理臺灣證券交易所 OpenAPI 的抓取、原始 JSON 落地、SQLite schema 初始化、資料匯入與 log 管理。

## 目錄說明

- OpenData/: Python 腳本與共用抓取、匯入模組
- Source/: 下載回來的原始 JSON
- database/: SQLite schema SQL
- log/: 執行過程中的錯誤 log
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
- 直接從 API 抓資料後匯入 SQLite
- API 呼叫失敗時寫入每日 log
- SQL schema 或匯入失敗時寫入每日 log
- 透過 mtime 清理過期 log

## 主要指令

```bash
make init-db
make init-company-schema
make init-fund-schema
make fetch-company
make fetch-fund
make import-company
make import-fund
make sync-company
make sync-fund
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
```

## 設定檔

設定檔位於 config.toml。

```toml
[system]
db_driver = "sqlite"
db_path = "OpenData/database/twse.db"
source_dir = "Source"
log_path = "log"
log_retention_days = 30

[company]
api_endpoint = "/opendata/t187ap03_L"
schema_path = "database/init_company.sql"
table_name = "listed_company_basic"
json_name = "listed_company.json"

[fund]
api_endpoint = "/opendata/t187ap47_L"
schema_path = "database/init_fund.sql"
table_name = "fund_basic"
json_name = "fund.json"
```

## Log 規則

- log 檔名格式為 YYYYMMDD.log
- 所有錯誤寫入同一天的同一份 log
- 目前只記錄 error 等級
- `make clean-log` 依檔案 mtime 與 `log_retention_days` 清理過期 log
- `log_retention_days = 0` 代表不清理任何 log
