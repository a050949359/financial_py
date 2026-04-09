# API 串接

這個目錄用來管理臺灣證券交易所 OpenAPI 的抓取、原始 JSON 落地、SQLite schema 初始化、資料匯入與 log 管理。

目前程式固定讀專案根目錄的 config.toml；讀不到就直接報錯，不再支援覆寫設定檔路徑。

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

- 資料集支援
	- company：上市公司基本資料
	- fund：基金基本資料
	- day_report：上市個股日成交資訊
	- month_report：上市個股月成交資訊
	- year_report：上市個股年成交資訊

- 資料流程
	- 抓取 TWSE OpenAPI 資料
	- 將原始回應落地為 Source/ JSON
	- 初始化 SQLite schema
	- 從本地 JSON 匯入 SQLite
	- 直接執行 fetch + import 同步流程

- 設定與註冊
	- config.toml 管理 system 與 dataset 覆寫設定
	- registry.d 管理 dataset 預設值與支援清單
	- validate-config 可檢查設定與 schema 是否可用

- 操作入口
	- Makefile 統一提供 fetch、import、sync、clean、validate-config 指令
	- init.py 提供 config 驗證、JSON 路徑查詢、db 初始化與 log 清理入口

- 錯誤與維運
	- API 呼叫與匯入失敗會寫入每日 log
	- 可依 log_retention_days 清理過期 log

## 主要指令

```bash
make validate-config
make init-schema DATASET=company
make fetch DATASET=company
make import DATASET=company
make sync DATASET=company
make clean-json DATASET=company
make init-db
make clean-log
```

也可以直接呼叫共用 fetcher：

```bash
python3 core/fetcher.py --dataset company
python3 core/fetcher.py --api-path /opendata/t187ap03_L
python3 core/fetcher.py --api-path /exchangeReport/STOCK_DAY_ALL --output Source/day_report.json
```

## 可用參數

通用入口與顯式 target 都可帶對應參數：

```bash
make fetch DATASET=company TIMEOUT=60
make fetch DATASET=day_report OUTPUT=Source/day_report_custom.json
make import DATASET=month_report
make sync DATASET=year_report TIMEOUT=60
make clean-json DATASET=fund
make validate-config DATASET=company
make fetch DATASET=fund API_URL=https://openapi.twse.com.tw/v1/opendata/t187ap47_L
```

若直接使用共用 fetcher：

```bash
python3 core/fetcher.py --dataset fund
python3 core/fetcher.py --api-path /opendata/t187ap47_L
python3 core/fetcher.py --api-url https://openapi.twse.com.tw/v1/exchangeReport/FMNPTK_ALL --output Source/year_report.json
```

共用 fetcher 也支援自訂 request 參數。

下列是非 TWSE JSON API 的語法範例；TWSE OpenAPI 目前仍以 GET 為主：

```bash
python3 core/fetcher.py --api-url <API_URL> --method POST
python3 core/fetcher.py --api-url <API_URL> --header 'X-Token: abc123' --header 'Accept: application/json'
python3 core/fetcher.py --api-url <API_URL> --query page=1 --query limit=100
python3 core/fetcher.py --api-url <API_URL> --method POST --body-json '{"hello":"world"}'
```

## 設定檔

設定檔位於 config.toml。

dataset 預設註冊表位於 registry.d/，採一個 dataset 一個 TOML 檔的形式。

可以先用下列指令驗證設定是否可用：

```bash
make validate-config
make validate-config DATASET=company
python3 init.py --validate-config
python3 init.py --print-dataset-json-path company
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
