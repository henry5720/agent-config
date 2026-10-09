---
name: repo-review
description: Review the Round 41 UI fixture diff against its explicit browser controls, synthetic data, and evidence-safety contract.
---

# Round 41 UI fixture review method

這是 reviewer method，不是作者流程。只對照目前 PR diff、`docs/acceptance/ui-fixture-41.html` 和 `docs/acceptance/ui-fixture-41.md`；不要自行啟動 `pr-review-and-verify`，不要代替作者發布或修改。

檢查：

- fixture 的「確認已處理」操作是否應更新狀態、輔助文字與按鈕，且可恢復「待處理」。
- 名稱、email、對話、訂單和憑證字串是否明確為虛構測試資料；不得引入真實客戶資料或有效 credential。
- 憑證欄位是否為遮蔽的合成 TEST 值，並且截圖排除整個憑證 panel；正常姓名、email、對話和附件仍保留於截圖。
- 驗收是否明確要求實際 browser click、狀態確認、reset 和 console 檢查。只讀 HTML、HTTP checker 或其他靜態檢查不能當作 browser 行為證據。

只報告有檔案／行號依據的 finding；此 skill 不提供通用作者 PR flow，也不把靜態檢查冒充互動測試。
