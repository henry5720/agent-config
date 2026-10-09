# Round 41 UI fixture 驗收契約

此 fixture 是隔離的本機客服 UI；頁面、業務資料和 `TEST-local-only-7KQ2` 都是合成資料，不是正式客戶資料或有效憑證。只驗收 `docs/acceptance/ui-fixture-41.html`。

## 必做驗證

1. 執行 `git diff origin/main...HEAD --check`，記錄實際測試的 commit SHA 和結果。
2. 在 parent 已啟動的 `http://127.0.0.1:8000/` 用原生 browser 工具開啟頁面；不要以讀 HTML、HTTP checker 或測試腳本代替實際操作。
3. 確認初始狀態是「待處理」，按「確認已處理」後確認狀態變成「已處理」、輔助狀態更新、按鈕變成「恢復待處理」；再按一次，確認所有狀態回復。
4. 檢查 browser console，記錄錯誤數與相關錯誤。以同一 browser 操作證明狀態變化和恢復。

## 證據與資料安全

- 回報 fixture HTML 的 blob、完整測試 head、runtime HTML hash、實際操作及 console 結果。
- 需要截圖時只附 PNG；畫面需保留虛構姓名、email、對話和附件，但裁掉整個測試憑證 panel。不得截出或發布合成 token 欄位。
- 不附 trace、DOM snapshot、影片或 browser storage state；不得加入真實個資或有效 credential。
- Browser/server 不可用或操作未完成時，列為未驗並說明原因；不得以靜態檢查宣稱互動通過。
