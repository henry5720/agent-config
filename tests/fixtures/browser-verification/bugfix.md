## 瀏覽器驗收

驗收 commit：`abc123`

| 環境 | |
|---|---|
| 前端 | 本機 dev server @ abc123 |
| 後端 | staging |
| 瀏覽器 | Chromium 1440×900、zh-TW、淺色 |
| 資料 | 真實 API |
| 改前 | 線上部署 https://dev.example.com（部署 commit def456） |

| # | 驗收項目 | 操作 | 看到 | 資料 | 結果 | 帳號 | 改前 | 改後 |
|---|---|---|---|---|---|---|---|---|
| 1 | 移除唯一管理者：提示要保留一位管理者 | 1. 開成員設定<br>2. 移除唯一的管理者 | 顯示「至少保留一位管理者」，名單仍可編輯；改前整個視窗鎖住 | 真實 | ✅ 通過 | E2E_ADMIN | ![before-remove.png](./before-remove.png) | ![after-remove.png](./after-remove.png) |
| 2 | 後端缺管理者 409：不鎖視窗 | 1. 儲存時讓後端回 409 | 顯示管理者失效提示 | mock | ✅ 通過 | E2E_ADMIN | 只有改後：base 部署關了這個模組 | ![after-409.png](./after-409.png) |
| 3 | 版本衝突仍鎖視窗 | 1. 兩個分頁同時編輯<br>2. 後存的那頁按儲存 | 與改前相同，視窗鎖住 | 真實 | ✅ 通過 | E2E_ADMIN | 不變 | ![after-conflict.png](./after-conflict.png) |
| 4 | 按鈕文案改成「儲存」 | 1. 開成員設定 | 按鈕顯示「儲存」 | 真實 | ✅ 通過 | — | — | ![after-button.png](./after-button.png) |

判定 model：claude-sonnet-4-6（與實作同一個 model）
