---
name: browser-access
description: 接瀏覽器：自己的 headless、使用者的獨立 profile（9222）、使用者的 Chrome 經插件（tailnet 內走 ssh，tailnet 外走一次性 tunnel）。要開瀏覽器操作或查原因（chrome-devtools MCP 連不上 9222）、使用者要你在他看得到的 Chrome 裡做事、一定要他日常的 Chrome（passkey、硬體金鑰、裝置 SSO）、使用者不在 tailnet、使用者跟你在同一台 Windows、網站擋機房 IP 時使用。
---

# browser-access

指令、怎麼確認成功、踩過的坑都在 dotfiles 的〈瀏覽器〉服務卡：

- 本機有 dotfiles：`~/.local/share/chezmoi/docs/how-to/remote-access/browser.md`
- 沒有：<https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/browser.md>

## 先看使用者在哪

使用者跟你在同一台、tailnet 內還是 tailnet 外，照 `remote-access` skill 的〈判準〉判斷；ssh 轉發的寫法和本機 port 也照它。判完照這裡接：

- **同一台**（你跑在使用者面前那台 Windows，`uname -s` 印 `MINGW*`／`MSYS*`；他可能是 ssh 進來的，不確定就問他）→ 照下面〈同一台 Windows〉。
- **你跑在 Windows、使用者在別台** → tailnet 內用獨立 profile（照下一條）。一定要插件或使用者在 tailnet 外時，跟使用者說這台接不了，請他從 Linux／macOS 的已配置主機開 session。
- **tailnet 內** → 讀服務卡〈先挑哪支 Chrome〉決定用哪支，再照那一節做到它寫的「怎麼確認」成立。轉發由使用者在他的個人電腦開；ssh 指令照抄服務卡給他。例外：獨立 profile 在 Windows、你 ssh 得進那台時，照 `remote-access`〈服務定義〉跑 `remote-access up browser <host>`：它叫起那台的 `chrome-agent` task、開 `-L` 到這台的 9222，並確認接到的是那台的 Chrome。`up` 說那台還沒有 `chrome-agent` task 時，問使用者要不要建（建了會一直留在他那台），他說好再照服務卡〈獨立 profile〉那段建，再重跑 `up`。
- **tailnet 外** → 照下面〈接插件〉跑 `--tunnel`，把輸出交給他。插件的 relay 由這支 script 自己開 tunnel，不走 `remote-access` 的 Funnel、quick tunnel。

## 只有你要守的

- **9222、9377、1080 沒有驗證，只走 tailnet 內**（`remote-access`〈本機 port 總表〉）。開到 tailnet 外的只有插件的 relay，而且只經 `playwright-extension-attach --tunnel` 開。
- **port 被佔照 `remote-access`〈本機 port 總表〉回報**，由使用者決定怎麼處理。例外：9222 上是使用者的獨立 profile（`/json/version` 不是 `HeadlessChrome`）時直接用它，不另開 headless。
- **使用者的 Chrome 開新分頁再操作。** 接上他的獨立 profile 或插件後，用 `tab-new <網址>`；他正在看的分頁留給他。插件接上後一樣能開多個分頁（收在同一個分頁群組），用 `tab-list` 確認看得到。
- **用完收。** 自己開的 headless、`show` 收掉；接使用者的 Chrome 用 `detach`（Chrome 和分頁留給他），tailnet 內再請他關 ssh；`up browser` 開的由你 `remote-access down browser <host>` 收（只關轉發，Chrome 留著）。

## 同一台 Windows

`scripts/playwright-extension-attach` 只在 Linux／macOS 跑，同一台時也用不到：它做的是把 relay 轉到使用者那台，同一台時 relay 本來就在使用者的 `127.0.0.1`。

1. 背景跑 `playwright-cli -s=<S> attach --extension=chrome`，它停住等使用者接上。它自己用這台的 Chrome 開插件的 connect 分頁，網址不印出來。
2. 請使用者在那個分頁的插件畫面選分頁、按允許。沒跳出分頁，或插件畫面說沒裝插件，就請他在那支 Chrome 裝 Playwright Extension（<https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm>）再重跑。
3. 沒有 `playwright-extension-attach` 的逾時，你自己計時：300 秒沒接上，或使用者說不接了，就把背景的 attach 收掉，不留著。

完成條件和收尾同下面〈接插件〉：`playwright-cli -s=<S> tab-list` 看得到使用者的分頁；用完 `playwright-cli -s=<S> detach`。

## 接插件：`scripts/playwright-extension-attach`

tailnet 內只在獨立 profile 也登不進去時用；tailnet 外一律加 `--tunnel`。

script 在這份 SKILL.md 所在資料夾的 `scripts/playwright-extension-attach`，用絕對路徑叫它：先 `ls` 確認你讀這份 SKILL.md 的那個資料夾底下有 `scripts/playwright-extension-attach`，再用 `<那個資料夾>/scripts/playwright-extension-attach` 跑，不要從目前工作目錄找。裝了 dotfiles 的機器另外有 `~/.local/bin/playwright-extension-attach`，是同一支。要 `playwright-cli` ≥ 0.1.23，`--tunnel` 另要 `cloudflared`；`command -v` 找得到就是裝好了，找不到才回報缺工具。

背景跑 `<那個資料夾>/scripts/playwright-extension-attach -s=<S> [--tunnel]`，它停在前景直到 session 結束；`--timeout=<秒>` 改等待時間（預設 300，`--tunnel` 預設 600）。`--tunnel` 印出的步驟裡已經建議使用者用獨立 profile、附各 OS 的開法；使用者選日常 profile 也照做。

- 印出「tunnel 開好了」（`--tunnel`）→ 把它印出的步驟原樣轉交使用者。connect 網址就是鑰匙，只交給使用者本人。
  轉交到聊天（Discord 等）時，步驟編號和說明照抄，格式照這樣，使用者才複製得乾淨、點得開：
  - 終端機指令和 `chrome-extension://` 開頭的 connect 網址：各放一個 code block，裡面只放那一行本身（OS 名稱寫在 code block 外面）。connect 網址在聊天裡點不開，一定要複製。
  - `https://` 連結（cloudflared 下載頁、插件商店頁）：直接寫在句子裡，不放進 code block，使用者點了就開。
- 印出 `chrome-extension://…connect.html?…`（tailnet 內，沒設 token）→ 原樣交給使用者，請他貼進日常 Chrome 的**新分頁**，再在插件畫面選這個分頁、按允許。
- 印出「connect 網址含 token,不印在這裡」（tailnet 內，有設 token）→ 轉述它列的兩步：新分頁開 `http://127.0.0.1:9555/connect`、按「複製」、貼進同一個分頁。那一頁只給使用者的瀏覽器開，你只轉述步驟。
- 逾時、attach 失敗、cloudflared 起不來 → 它已經收乾淨（`--tunnel` 印「cloudflared 剩 0 個」）、exit 1。問使用者卡在哪一步再重跑（網址每次不同）。

完成條件：輸出「已接上,session:<S>」，`playwright-cli -s=<S> tab-list` 看得到使用者的分頁。收尾 `playwright-cli -s=<S> detach`，等它印「session <S> 結束了」並 exit 0。

**token 只在使用者那邊流動。** tailnet 內使用者想只貼網址，請他自己把插件狀態頁的 token 設成你這台的環境變數 `PLAYWRIGHT_MCP_EXTENSION_TOKEN`；token 和帶 token 的網址都留在他的 ssh 轉發和他的瀏覽器裡，不經過對話、輸出或檔案。`--tunnel` 不帶 token，每次由使用者在插件畫面按允許。
