PYTHON ?= python3
TWSE_DIR := $(CURDIR)
TWSE_MODULE_DIR := $(TWSE_DIR)/TWSE
CONFIG_FILE := $(TWSE_DIR)/config.toml

CONFIG ?= $(CONFIG_FILE)
TIMEOUT ?=
OUTPUT ?=
API_URL ?=
DATASET ?=

FETCH_ARGS := --config $(CONFIG)
FETCH_ARGS += $(if $(TIMEOUT),--timeout $(TIMEOUT),)
FETCH_ARGS += $(if $(OUTPUT),--output $(OUTPUT),)
FETCH_ARGS += $(if $(API_URL),--api-url $(API_URL),)

define dataset_json_path
$(shell $(PYTHON) $(TWSE_DIR)/init.py --config $(CONFIG) --print-dataset-json-path $(1))
endef

COMPANY_JSON_PATH := $(call dataset_json_path,company)
FUND_JSON_PATH := $(call dataset_json_path,fund)
DAY_REPORT_JSON_PATH := $(call dataset_json_path,day_report)
MONTH_REPORT_JSON_PATH := $(call dataset_json_path,month_report)
YEAR_REPORT_JSON_PATH := $(call dataset_json_path,year_report)

.PHONY: help validate-config init-db init-company-schema init-fund-schema \
	init-day-reports-schema init-month-reports-schema init-year-reports-schema \
	fetch-company fetch-fund fetch-day-reports fetch-month-reports fetch-year-reports \
	import-company import-fund import-day-reports import-month-reports import-year-reports \
	sync-company sync-fund sync-day-reports sync-month-reports sync-year-reports \
	clean-company-json clean-fund-json clean-day-reports-json \
	clean-month-reports-json clean-year-reports-json clean-log
.SILENT:

help:
	@echo "make validate-config # 驗證 config，可帶 CONFIG 與 DATASET"
	@echo "make init-db    # 依 config 建立空的 SQLite db 檔案"
	@echo "make init-company-schema # 在既有 db 上建立公司 table/schema"
	@echo "make init-fund-schema # 在既有 db 上建立基金 table/schema"
	@echo "make init-day-reports-schema # 在既有 db 上建立日報 table/schema"
	@echo "make init-month-reports-schema # 在既有 db 上建立月報 table/schema"
	@echo "make init-year-reports-schema # 在既有 db 上建立年報 table/schema"
	@echo "make fetch-company # 抓公司 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make fetch-fund # 抓基金基本資料 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make fetch-day-reports # 抓日報 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make fetch-month-reports # 抓月報 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make fetch-year-reports # 抓年報 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make import-company # 從本地公司 JSON 匯入 SQLite"
	@echo "make import-fund # 從本地基金 JSON 匯入 SQLite"
	@echo "make import-day-reports # 從本地日報 JSON 匯入 SQLite"
	@echo "make import-month-reports # 從本地月報 JSON 匯入 SQLite"
	@echo "make import-year-reports # 從本地年報 JSON 匯入 SQLite"
	@echo "make sync-company # 直接抓公司 API 並匯入 SQLite"
	@echo "make sync-fund  # 直接抓基金 API 並匯入 SQLite"
	@echo "make sync-day-reports # 直接抓日報 API 並匯入 SQLite"
	@echo "make sync-month-reports # 直接抓月報 API 並匯入 SQLite"
	@echo "make sync-year-reports # 直接抓年報 API 並匯入 SQLite"
	@echo "make clean-company-json # 刪除公司 JSON"
	@echo "make clean-fund-json # 刪除基金 JSON"
	@echo "make clean-day-reports-json # 刪除日報 JSON"
	@echo "make clean-month-reports-json # 刪除月報 JSON"
	@echo "make clean-year-reports-json # 刪除年報 JSON"
	@echo "make clean-log # 依 log_retention_days 清理過期 log"
	@echo "example: make fetch-company TIMEOUT=60 OUTPUT=Source/company_custom.json"
	@echo "example: make fetch-day-reports OUTPUT=Source/day_report_custom.json"
	@echo "example: make sync-year-reports"
	@echo "example: make validate-config DATASET=company"

validate-config:
	$(PYTHON) $(TWSE_DIR)/init.py --config $(CONFIG) --validate-config $(if $(DATASET),--dataset $(DATASET),)

init-db:
	$(PYTHON) $(TWSE_DIR)/init.py --config $(CONFIG)

fetch-company:
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --fetch-json $(FETCH_ARGS)

fetch-fund:
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --fetch-json $(FETCH_ARGS)

fetch-day-reports:
	$(PYTHON) $(TWSE_MODULE_DIR)/day_reports.py --fetch-json $(FETCH_ARGS)

fetch-month-reports:
	$(PYTHON) $(TWSE_MODULE_DIR)/month_reports.py --fetch-json $(FETCH_ARGS)

fetch-year-reports:
	$(PYTHON) $(TWSE_MODULE_DIR)/year_reports.py --fetch-json $(FETCH_ARGS)

init-company-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --config $(CONFIG) --init-schema

init-fund-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --config $(CONFIG) --init-schema

init-day-reports-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/day_reports.py --config $(CONFIG) --init-schema

init-month-reports-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/month_reports.py --config $(CONFIG) --init-schema

init-year-reports-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/year_reports.py --config $(CONFIG) --init-schema

import-company:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=company
	@if [ ! -f "$(COMPANY_JSON_PATH)" ]; then \
		echo "$(COMPANY_JSON_PATH) not found, running fetch-company first"; \
		$(MAKE) fetch-company CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --config $(CONFIG)

import-fund:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=fund
	@if [ ! -f "$(FUND_JSON_PATH)" ]; then \
		echo "$(FUND_JSON_PATH) not found, running fetch-fund first"; \
		$(MAKE) fetch-fund CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --config $(CONFIG)

import-day-reports:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=day_report
	@if [ ! -f "$(DAY_REPORT_JSON_PATH)" ]; then \
		echo "$(DAY_REPORT_JSON_PATH) not found, running fetch-day-reports first"; \
		$(MAKE) fetch-day-reports CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/day_reports.py --config $(CONFIG)

import-month-reports:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=month_report
	@if [ ! -f "$(MONTH_REPORT_JSON_PATH)" ]; then \
		echo "$(MONTH_REPORT_JSON_PATH) not found, running fetch-month-reports first"; \
		$(MAKE) fetch-month-reports CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/month_reports.py --config $(CONFIG)

import-year-reports:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=year_report
	@if [ ! -f "$(YEAR_REPORT_JSON_PATH)" ]; then \
		echo "$(YEAR_REPORT_JSON_PATH) not found, running fetch-year-reports first"; \
		$(MAKE) fetch-year-reports CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/year_reports.py --config $(CONFIG)

sync-company:
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --config $(CONFIG) --fetch

sync-fund:
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --config $(CONFIG) --fetch

sync-day-reports:
	$(PYTHON) $(TWSE_MODULE_DIR)/day_reports.py --config $(CONFIG) --fetch $(if $(TIMEOUT),--timeout $(TIMEOUT),)

sync-month-reports:
	$(PYTHON) $(TWSE_MODULE_DIR)/month_reports.py --config $(CONFIG) --fetch $(if $(TIMEOUT),--timeout $(TIMEOUT),)

sync-year-reports:
	$(PYTHON) $(TWSE_MODULE_DIR)/year_reports.py --config $(CONFIG) --fetch $(if $(TIMEOUT),--timeout $(TIMEOUT),)

clean-company-json:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=company
	rm -f $(COMPANY_JSON_PATH)

clean-fund-json:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=fund
	rm -f $(FUND_JSON_PATH)

clean-day-reports-json:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=day_report
	rm -f $(DAY_REPORT_JSON_PATH)

clean-month-reports-json:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=month_report
	rm -f $(MONTH_REPORT_JSON_PATH)

clean-year-reports-json:
	$(MAKE) validate-config CONFIG=$(CONFIG) DATASET=year_report
	rm -f $(YEAR_REPORT_JSON_PATH)

clean-log:
	$(PYTHON) $(TWSE_DIR)/init.py --config $(CONFIG) --clean-log