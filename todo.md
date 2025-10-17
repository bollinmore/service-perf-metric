- [ ] 把 View 的部分跟 Logic 分開放
- [ ] Average Loading Time (Grouped Bar) 改名為 Loading Time
  - [ ] 可選擇顯示平均、最大、最小、中位數
- [x] 產生績效報表，如果指定版本跟比較對象發現效能降低超過 30%，要特別註記
  ```prompt
  1. 在 sidebar 新增一個按鈕 - Compare
  2. 在 Compare 頁面中主要呈現的方式是一個表格：
    - 每個服務名稱當成列
    - 共有三個欄位：第一個與第二個欄位為版本，第三個欄位為比較結果
      - 版本呈現為下拉選單，可以改變比較對象
      - 第三個欄位的比較呈現為百分比格式，資料為為第二欄跟第一欄的內容比較結果
    - 第一欄與第二欄的每個資料為服務的平均時間
  ```
- [ ] 修改首頁，使 Analytics Dashboard 就是網站的首頁，並加入側邊攔提供原始查看 csv 的功能
  ```prompt
  1. 把 Analytics Dashboard 變成預設首頁
  2. 仿造 vscode 增加左側 sidebar, 預設就是 Analytics Dashboard
  3. 把原始的 CSV 預覽功能放在 sidebar 第二個 button, 所有的報表連結做在同一個網頁內
  ```
- [ ] Per-Service Evolution
  ```prompt
  在 Analytics Dashboard 畫面新增一個 Card - "Per-Service Evolution"
  - 裡面呈現一個 Table:
    - Row 包含所有 Services
    - Column 包含三個版本
  - 右上角提供 Expand button 可以展開 Card
  - Expand button 左邊提供下拉選單包含: Average, Max, Min, Median
  - 在沒有展開 Card 的情況下，允許透過滑鼠捲動來查看表格內容
  ```