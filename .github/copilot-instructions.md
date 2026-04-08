# TWSE 開發指示

你正在維護一個以 TWSE OpenAPI 為來源的資料抓取與 SQLite 匯入專案。
首要目標是讓資料流穩定、命名一致、設定集中、操作可預期。
除非使用者明確要求重構，否則優先做最小改動並維持現有架構。

## 架構原則

- 不要把原始資料、程式碼、schema、log 混放在同一層。
- 原始 JSON 一律放在 Source/。
- schema SQL 一律放在 database/。
- 共用設定一律放在 config.toml。
- 共用初始化與設定解析放在 init.py。
- 共用 API 抓取能力放在 OpenData/twse_fetcher.py。
- 共用 SQLite 匯入能力放在 OpenData/twse_importer.py。
- dataset 專屬邏輯集中在 OpenData/company.py 與 OpenData/fund.py。
- Makefile 是主要操作入口，新增功能時優先思考是否需要對應的 make target。

## 命名規範

- dataset 名稱維持 company 與 fund，不要再引入重複別名。
- schema 檔名使用 init_<dataset>.sql 格式。
- 不要再引入 basic、service、process、importer 的重複變體來表示同一層責任，除非責任真的不同。
- 共用模組名稱維持 twse_fetcher.py 與 twse_importer.py。

## 設定規範

- 所有可調整路徑都應優先從 config.toml 讀取。
- 不要把專案路徑硬編碼在 company.py 或 fund.py。
- [opendata] 只放共用設定，例如 db_path、source_dir、log_path、log_retention_days。
- dataset 專屬設定只放在 [company] 或 [fund]。

## Python 實作規範

- 優先使用標準函式庫，除非真的有必要再引入第三方套件。
- 設定檔解析使用 tomllib，請延續這個做法。
- 盡量維持函式小而明確，不要把抓取、解析、寫檔、匯入全部塞進同一個函式。
- 發生錯誤時應保留原本例外拋出，不要只吃掉錯誤不處理。
- 若新增 log，預設走現有 setup_logging()，不要各模組自行建立另一套 logging 規則。
- 若修改 argparse 參數，需同步檢查 Makefile 是否也需要更新。
- 若一個功能已經可以由共用模組處理，不要在 dataset module 再複製一次類似實作。

## Makefile 規範

- 優先使用顯式 target，不要回到 make fetch TARGET=company 這種模式。
- help 內容必須與實際 target 保持一致。
- 若新增 target，請補上簡短用途說明。
- 若某個 Python 參數會被頻繁使用，優先考慮是否暴露為 Makefile 變數。
- 既有 target 名稱若非必要不要改，避免破壞使用習慣。

## Log 規範

- log 檔案統一寫到 log/。
- log 檔名統一使用 YYYYMMDD.log。
- 目前 log 主要記錄錯誤，不要先加入大量 info/debug 造成噪音。
- log 清理由 make clean-log 顯式執行，不要在 setup_logging 時自動刪檔。
- log 清理以 mtime 為準，並由 log_retention_days 控制。
- log_retention_days = 0 代表不清理任何 log。

## 修改規範

- 優先做最小改動，不要重排整個檔案。
- 不要順手修 unrelated 的命名或格式，除非它直接阻礙目前功能。
- 新增檔案前先確認是否已有同責任檔案存在，避免重複。
- 刪除舊檔前先確認沒有引用殘留。

## 回應與協作規範

- 回答功能說明時，先講目前行為，再講例外與邊界。
- 若發現使用者要求和現有架構衝突，先指出衝突點，再提出最小改法。
- 若某個行為是暫時設計，不要包裝成永久最佳做法。
- 說明指令時，優先給可直接執行的 make 指令。
- 若修改影響使用方式，務必同步更新 README。
