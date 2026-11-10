## 瀏覽器驗收

驗收 commit：`abc123`

| 環境 | |
|---|---|
| 前端 | 本機 dev server @ abc123 |
| 後端 | staging |
| 瀏覽器 | Chromium 1440×900、zh-TW、淺色 |
| 資料 | 真實 API |

| # | 驗收項目 | 操作 | 看到 | 資料 | 結果 | 證據 |
|---|---|---|---|---|---|---|
| 1 | 顯示 A &#124; B | 1. 開 /demo<br>2. 看 &lt;標題&gt; | 看到 &lt;A&gt;<br>B | 真實 | ✅ 通過 | ![after.png](./after.png) |

判定 model：claude-sonnet-4-6（與實作同一個 model）
