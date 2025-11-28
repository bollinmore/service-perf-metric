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

## clarify

## plan

## checklist

## tasks

## analyze

## implement
