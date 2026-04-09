PYTHON ?= python3
TWSE_DIR := $(CURDIR)
TWSE_MODULE_DIR := $(TWSE_DIR)/TWSE

TIMEOUT ?=
OUTPUT ?=
API_URL ?=
DATASET ?=

FETCH_ARGS :=
FETCH_ARGS += $(if $(TIMEOUT),--timeout $(TIMEOUT),)
FETCH_ARGS += $(if $(OUTPUT),--output $(OUTPUT),)
FETCH_ARGS += $(if $(API_URL),--api-url $(API_URL),)

define dataset_module_name
$(strip $(if $(filter company,$(1)),company,$(if $(filter fund,$(1)),fund,$(if $(filter day_report,$(1)),day_reports,$(if $(filter month_report,$(1)),month_reports,$(if $(filter year_report,$(1)),year_reports,))))))
endef

DATASET_MODULE = $(call dataset_module_name,$(DATASET))

.PHONY: help validate-config init-db init-schema fetch import sync clean-json clean-log ensure-dataset

define dataset_json_path
$(shell $(PYTHON) $(TWSE_DIR)/init.py --print-dataset-json-path $(1))
endef
.SILENT:

help:
	@echo "make validate-config # 驗證固定的 config.toml，可帶 DATASET"
	@echo "make init-schema DATASET=company # 通用 schema 初始化入口"
	@echo "make fetch DATASET=company # 通用 JSON 抓取入口，可帶 TIMEOUT/OUTPUT/API_URL"
	@echo "make import DATASET=company # 通用 JSON 匯入入口"
	@echo "make sync DATASET=company # 通用抓取並匯入入口"
	@echo "make clean-json DATASET=company # 通用 JSON 清理入口"
	@echo "make init-db    # 依固定 config.toml 建立空的 SQLite db 檔案"
	@echo "make clean-log # 依 log_retention_days 清理過期 log"
	@echo "example: make fetch DATASET=company TIMEOUT=60 OUTPUT=Source/company_custom.json"
	@echo "example: make fetch DATASET=day_report TIMEOUT=60"
	@echo "example: make fetch DATASET=day_report OUTPUT=Source/day_report_custom.json"
	@echo "example: make sync DATASET=year_report"
	@echo "example: make validate-config DATASET=company"

ensure-dataset:
	@if [ -z "$(DATASET)" ]; then \
		echo "DATASET is required"; \
		exit 1; \
	fi
	@if [ -z "$(DATASET_MODULE)" ]; then \
		echo "unsupported DATASET: $(DATASET)"; \
		exit 1; \
	fi

validate-config:
	$(PYTHON) $(TWSE_DIR)/init.py --validate-config $(if $(DATASET),--dataset $(DATASET),)

init-schema: ensure-dataset
	$(MAKE) validate-config DATASET=$(DATASET)
	$(PYTHON) $(TWSE_MODULE_DIR)/$(DATASET_MODULE).py --init-schema

fetch: ensure-dataset
	$(MAKE) validate-config DATASET=$(DATASET)
	$(PYTHON) $(TWSE_DIR)/core/fetcher.py --dataset $(DATASET) $(FETCH_ARGS)

import: ensure-dataset
	$(MAKE) validate-config DATASET=$(DATASET)
	@if [ ! -f "$(call dataset_json_path,$(DATASET))" ]; then \
		echo "$(call dataset_json_path,$(DATASET)) not found, running fetch first"; \
		$(MAKE) fetch DATASET=$(DATASET); \
	fi
	$(PYTHON) $(TWSE_MODULE_DIR)/$(DATASET_MODULE).py

sync: ensure-dataset
	$(MAKE) validate-config DATASET=$(DATASET)
	$(PYTHON) $(TWSE_MODULE_DIR)/$(DATASET_MODULE).py --fetch $(if $(TIMEOUT),--timeout $(TIMEOUT),)

clean-json: ensure-dataset
	$(MAKE) validate-config DATASET=$(DATASET)
	rm -f $(call dataset_json_path,$(DATASET))

init-db:
	$(PYTHON) $(TWSE_DIR)/init.py

clean-log:
	$(PYTHON) $(TWSE_DIR)/init.py --clean-log