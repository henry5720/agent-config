## 瀏覽器驗收

驗收 commit：`abc123`

| 環境 | |
|---|---|
| 前端 | 本機 dev server @ abc123 |
| 後端 | staging（版本：openapi 有新欄位，用欄位推斷） |
| 瀏覽器 | Chromium 1440×900、zh-TW、淺色 |
| 資料 | 讀取走真實 API；寫入以 route 攔截回 mock |

| # | 驗收項目 | 操作 | 看到 | 資料 | 結果 | 帳號 | 證據 |
|---|---|---|---|---|---|---|---|
| 1 | 儲存後出現 toast | 1. 開編輯頁<br>2. 改名稱<br>3. 按儲存 | 顯示「儲存成功」 | mock | ✅ 通過 | E2E_ADMIN | ![after-toast.png](./after-toast.png) |
| 2 | 取消後關閉對話框 | 1. 開刪除對話框<br>2. 按取消 | 對話框仍開著<br>**原因**：對話框未關閉 | 真實 | ❌ 失敗 | E2E_ADMIN | ![after-cancel.png](./after-cancel.png) |
| 3 | viewer 不能刪除 | — | 無 viewer 帳號可登入<br>**原因**：缺少 E2E_VIEWER_EMAIL、E2E_VIEWER_PASSWORD | — | ⏭ 略過 | E2E_VIEWER | — |

console error：
- Error: save failed
- TypeError: cannot read x
另有 1 則判定與本次 diff 無關

判定 model：claude-sonnet-4-6（與實作同一個 model）

在 staging 建了 2 筆資料

issue 沒有 ## Acceptance criteria，以下條件由 agent 從內文推出
