---
name: browser-access
description: 接瀏覽器：自己的 headless、使用者的獨立 profile（9222）、使用者日常的 Chrome（插件）。要開瀏覽器操作或查原因（chrome-devtools MCP 連不上 9222）、使用者要你在他看得到的 Chrome 裡做事、一定要他日常的 Chrome（passkey、硬體金鑰、裝置 SSO）、網站擋機房 IP 時使用。
---

# browser-access

指令、怎麼確認成功、踩過的坑都在 dotfiles 的〈瀏覽器〉服務卡，照它做：

- 本機有 dotfiles：`~/.local/share/chezmoi/docs/remote-access/browser.md`
- 沒有：<https://github.com/henry5720/dotfiles/blob/main/docs/remote-access/browser.md>

先讀〈先挑哪支 Chrome〉決定用哪支，再照那一節做到它寫的「怎麼確認」成立。轉發要使用者在他的個人電腦開；ssh 指令照抄那份給他。

## 只有你要守的

- **轉發只走 tailnet 內的 ssh、只綁 127.0.0.1。** 9222、9377、9555、1080 都沒有驗證。使用者連不到你這台的 ssh（不在 tailnet、沒有 key）就停下來回報。
- **port 被佔就回報。** 9222、9555、1080 已經有程式在聽：用 `ss -ltnp | grep <port>` 找出是誰，告訴使用者，由他決定怎麼處理。9222 上是使用者的獨立 profile（`/json/version` 不是 `HeadlessChrome`）時直接用它，不另開 headless。
- **使用者的 Chrome 開新分頁再操作。** 接上他的獨立 profile 或日常 profile 後，用 `tab-new <網址>`；他正在看的分頁留給他。
- **用完收。** 自己開的 headless、`show` 收掉；接使用者的 Chrome 用 `detach`（Chrome 和分頁留給他），再請他關 ssh。

## 接日常 profile：`scripts/personal-chrome-attach`

只在獨立 profile 也登不進去時用。背景跑 `scripts/personal-chrome-attach -s=<S>`（`~/.local/bin/personal-chrome-attach` 是同一支，要 `playwright-cli` ≥ 0.1.23），它停在前景直到 session 結束；`--timeout=<秒>` 改等待時間（預設 300）。

- 印出 `chrome-extension://…connect.html?…`（沒設 token）→ 原樣交給使用者，請他貼進日常 Chrome 的**新分頁**，再在插件畫面選這個分頁、按允許。
- 印出「connect 網址含 token,不印在這裡」（有設 token）→ 轉述它列的兩步：新分頁開 `http://127.0.0.1:9555/connect`、按「複製」、貼進同一個分頁。那一頁只給使用者的瀏覽器開，你只轉述步驟。
- 逾時或 attach 失敗 → 它已經收乾淨、exit 1。問使用者卡在哪一步再重跑（網址每次不同）。

完成條件：輸出「已接上,session:<S>」。收尾 `playwright-cli -s=<S> detach`，等它印「session <S> 結束了」並 exit 0。

**token 只在使用者那邊流動。** 使用者想只貼網址，請他自己把插件狀態頁的 token 設成你這台的環境變數 `PLAYWRIGHT_MCP_EXTENSION_TOKEN`；token 和帶 token 的網址都留在他的 ssh 轉發和他的瀏覽器裡，不經過對話、輸出或檔案。
