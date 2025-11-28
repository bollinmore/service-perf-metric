# 001-dev-prod-toggle

## specify

增加選項，可以維持目前的開發版本，以可以切換為 Prodcution 模式準備部署。

## clarify

## plan

使用 .env 檔案來增加欄位用來切換模式，切換模式只有對在本地使用 `python spm.py serve` 啟動有用，在部署到 Docker 環境下一律設定為 Production 模式。調整好之後也一併更新 README.md

## checklist

## tasks

## analyze

## implement

---

# 002-user-version-compare

## specify

修改目前測試資料的檔案結構，不再使用指定 data folder 固定讀取其中三個資料夾的測試紀錄，而是交由使用者決定要比較的版本。

## clarify

## plan

spm.py 啟動的時候要指定 data folder, 也可以另外指定要比較的版本例如： --versions 2.0.1.0,2.0.1.2,2.0.1.3
每一個版本的測試資料必須要符合以下目錄結構：
<tool-version>
  - PerformanceLog
    - *.log
3. 修改上傳檔案的邏輯，使其一次指定一個 zip 並且其中要符合上述目錄結構。

## checklist

## tasks

## analyze

## implement

---

# 003-

## specify

- 改為「資料池 + 即選即算」模式：data folder 只當版本池，使用者可從中自由挑選 3 個版本進行比較。
- 讀取資料時僅生成各版本的單版 summary.csv；不再預先生成跨版 summary.csv / summary_stats.csv / service_stats.csv。
- 當使用者指定要比較的 3 個版本時，才即時生成「暫時」的跨版 summary.csv、summary_stats.csv、service_stats.csv，內容僅涵蓋本次選取的版本。
- 選取版本數固定為 3（原本 2–4 的邏輯需更新），若不足或超過則阻擋並提示。
- CLI/API/UI 的比較流程需讀取池中版本、讓使用者選 3 個並觸發上述暫時報表生成；其他非比較操作不應生成跨版報表。
- 報表輸出位置與存留策略需明確：暫時報表可放在 result/<data-folder>/temp 或同層命名隔離，避免覆蓋池中其他版本的單版 summary。
- 既有下載/視覺化路徑需改用暫時報表（若存在），否則提示尚未選擇版本進行比較。

## clarify

## plan

1. 需求對齊與邊界確認：定義「暫時報表」的路徑/覆蓋策略、TTL 或清理時機，以及 UI/CLI 如何觸發比較（指令或前端操作）。
2. 資料流程調整：重構 generate 路徑，讓預設僅產生單版 summary；新增「比較」步驟只針對選取 3 版生成跨版 summary/service_stats/
summary_stats。
3. 選版驗證更新：將選取規則改為必須且只能 3 個版本；錯誤訊息與測試覆蓋。
4. Web/UI 整合：前端選版介面與 API 改讀「池」中的版本清單，提交 3 版後重新載入暫時報表，並處理未選版時的提示。
5. CLI 工作流程：新增/調整 compare 命令以符合新邏輯，避免 generate 預先合併；更新日誌與路徑設定。
6. 測試與文件：補充單元/整合測試（含缺少 PerformanceLog、版本不足/過多、重覆選取）並更新 README/docs/quickstart。

## checklist

## tasks

## analyze

## implement
