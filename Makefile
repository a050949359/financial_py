PYTHON ?= python3
TWSE_DIR := $(CURDIR)
TWSE_MODULE_DIR := $(TWSE_DIR)/TWSE
CONFIG_FILE := $(TWSE_DIR)/config.toml

CONFIG ?= $(CONFIG_FILE)
TIMEOUT ?=
OUTPUT ?=
API_URL ?=

FETCH_ARGS := --config $(CONFIG)
FETCH_ARGS += $(if $(TIMEOUT),--timeout $(TIMEOUT),)
FETCH_ARGS += $(if $(OUTPUT),--output $(OUTPUT),)
FETCH_ARGS += $(if $(API_URL),--api-url $(API_URL),)

.PHONY: help init-db init-company-schema init-fund-schema fetch-company fetch-fund import-company import-fund sync-company sync-fund clean-company-json clean-fund-json clean-log
.SILENT:

help:
	@echo "make init-db    # 依 config 建立空的 SQLite db 檔案"
	@echo "make init-company-schema # 在既有 db 上建立公司 table/schema"
	@echo "make init-fund-schema # 在既有 db 上建立基金 table/schema"
	@echo "make fetch-company # 抓公司 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make fetch-fund # 抓基金基本資料 JSON，可帶 TIMEOUT/OUTPUT/API_URL/CONFIG"
	@echo "make import-company # 從本地公司 JSON 匯入 SQLite"
	@echo "make import-fund # 從本地基金 JSON 匯入 SQLite"
	@echo "make sync-company # 直接抓公司 API 並匯入 SQLite"
	@echo "make sync-fund  # 直接抓基金 API 並匯入 SQLite"
	@echo "make clean-company-json # 刪除公司 JSON"
	@echo "make clean-fund-json # 刪除基金 JSON"
	@echo "make clean-log # 依 log_retention_days 清理過期 log"
	@echo "example: make fetch-company TIMEOUT=60 OUTPUT=Source/company_custom.json"
	@echo "example: make fetch-fund OUTPUT=Source/fund_custom.json"
	@echo "example: make fetch-fund API_URL=https://openapi.twse.com.tw/v1/opendata/t187ap47_L"

init-db:
	$(PYTHON) $(TWSE_DIR)/init.py --config $(CONFIG)

fetch-company:
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --fetch-json $(FETCH_ARGS)

fetch-fund:
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --fetch-json $(FETCH_ARGS)

init-company-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --config $(CONFIG) --init-schema

init-fund-schema:
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --config $(CONFIG) --init-schema

import-company:
	@if [ ! -f "$(TWSE_DIR)/Source/listed_company.json" ]; then \
		echo "Source/listed_company.json not found, running fetch-company first"; \
		$(MAKE) fetch-company CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --config $(CONFIG)

import-fund:
	@if [ ! -f "$(TWSE_DIR)/Source/fund.json" ]; then \
		echo "Source/fund.json not found, running fetch-fund first"; \
		$(MAKE) fetch-fund CONFIG=$(CONFIG); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --config $(CONFIG)

sync-company:
	$(PYTHON) $(TWSE_MODULE_DIR)/company.py --config $(CONFIG) --fetch

sync-fund:
	$(PYTHON) $(TWSE_MODULE_DIR)/fund.py --config $(CONFIG) --fetch

clean-company-json:
	rm -f $(TWSE_DIR)/Source/listed_company.json

clean-fund-json:
	rm -f $(TWSE_DIR)/Source/fund.json

clean-log:
	$(PYTHON) $(TWSE_DIR)/init.py --config $(CONFIG) --clean-log