---
name: personal-pc-tunnel
description: 要使用者在個人電腦開一條 ssh 轉發才做得到的瀏覽器工作：控使用者的 remote browser（他要一邊看、多分頁）、接他日常的 Chrome（passkey、硬體金鑰、裝置 SSO），或借他那台的對外 IP。使用者說「remote browser 開好了」、要你在他的瀏覽器裡做事、一定要他日常的 Chrome、或網站擋機房 IP（headless 瀏覽器被擋、對方要驗證你不是機器人）時使用。
---

# personal-pc-tunnel

你在已配置主機（例如 company-ec2）上，瀏覽器預設用這台自己的 headless 瀏覽器（`playwright-cli open`，流程照 `verify-in-browser` skill）。這個 skill 只處理那條走不通、要借使用者個人電腦的情況，共同點是使用者要開一條 ssh 轉發，而且只綁 127.0.0.1：轉過來的東西都沒有驗證。

這幾條都是 tailnet 內的 ssh 轉發，不開公網：使用者的個人電腦要連得到你這台的 ssh。他連不到（不在 tailnet、沒有 ssh key）就停下來回報，不要改開公開網址。其他開法給人看的全貌在 dotfiles 的 [remote-access](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#tailnet-內)。

## 控使用者的 remote browser

使用者坐在個人電腦前、要你在他看得到的瀏覽器裡做事時用。remote browser 是他個人電腦上一支**獨立 profile** 的 Chrome，CDP port 經 `ssh -R` 帶到你這台的 127.0.0.1:9222：你用 `playwright-cli attach --cdp` 操作、可以開多個分頁，chrome-devtools MCP 也直接接得上（`mcp.yaml` 寫死 9222）。登入狀態留在那個 profile，要登入的網站請他在視窗裡自己登。

跟下一節的日常 Chrome 是兩個入口、兩支 Chrome：日常 profile 從 Chrome 136 起開不了 debug port，只能靠插件交出一個分頁。只有網站一定要日常 profile 裡的東西（passkey、硬體金鑰、裝置 SSO）時才走下一節。

1. **確認 9222 是他的 remote browser**：`curl -s --max-time 3 127.0.0.1:9222/json/version`。
   - 沒回應 → 請使用者開：Windows 在 PowerShell 跑 `remote-browser`（dotfiles 部署的指令，開 Chrome 加轉發一起做）；其他系統自己開帶 `--remote-debugging-port=9222 --user-data-dir=<另一個資料夾>` 的 Chrome，再開 `ssh -N company-ec2-chrome`。等他說好再查一次。
   - `User-Agent` 有 `HeadlessChrome` → 那是這台自己的 headless（`remote-chrome-headless` 還開著）。他的轉發會因此失敗；問他要不要先收掉 headless，不要自己殺。
   完成條件：回應裡有 `webSocketDebuggerUrl`，`User-Agent` 不是 `HeadlessChrome`（Windows 的會帶 `"File-Path-Style": "windows"`）。
2. **接上**：`playwright-cli -s=<S> attach --cdp=http://127.0.0.1:9222`，之後照常用 `playwright-cli -s=<S> <指令>`。要新分頁用 `tab-new <網址>`，別 `goto` 蓋掉他正在看的分頁。
   完成條件：`playwright-cli -s=<S> tab-list` 列得出他開著的分頁。
3. **收尾**：`playwright-cli -s=<S> detach`。Chrome 和分頁留給他繼續用；轉發由他按 Ctrl+C 關（Chrome 留著）。
   完成條件：輸出 `Browser '<S>' detached`，並告訴使用者可以關轉發了。

## 接使用者日常的 Chrome

只在**一定要使用者日常的 profile** 時用：passkey、硬體金鑰、裝置 SSO，也就是 headless 瀏覽器和 remote browser 都登不進去的網站。使用者要看畫面、要替你登入，走 headless 瀏覽器 + `playwright-cli show`（`verify-in-browser` 的 hitl.md〈讓使用者看畫面、接手〉），不用打擾他的 Chrome。

接上之後你只看得到使用者貼網址的那一個分頁，`goto` 會直接換掉那個分頁的內容，所以一定請他貼在**新分頁**。

1. **確認有工具**：`command -v personal-chrome-attach`（`~/.claude/skills/personal-pc-tunnel/scripts/personal-chrome-attach` 是同一支）。它要 `playwright-cli` ≥ 0.1.23（dotfiles 選裝工具 `playwright-cli` 裝的）。沒有就停下來回報。
2. **請使用者做準備**（一次講完，等他說好）：
   - 第一次用：日常 Chrome 裝 [Playwright Extension](https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm)。
   - 在個人電腦開 ssh 轉發，開著別關：`ssh -N company-ec2-attach`（dotfiles 的 ssh config 有這個別名；沒有就用 `ssh -N -L 127.0.0.1:9555:127.0.0.1:9555 <你這台的 ssh host>`）。這條說 port 被佔而失敗，就是他另一台還開著。
3. **跑腳本**：背景跑 `personal-chrome-attach -s=<S>`（Claude Code 的 Bash `run_in_background`），它會停在前景直到 session 結束。不帶 `-s` 時 session 名是 `personal-chrome`。等使用者的時間預設 300 秒，`--timeout=<秒>` 可改。
   - 印出 `chrome-extension://…connect.html?…` 網址（沒設 token）→ 原樣交給使用者，請他貼進日常 Chrome 的新分頁網址列，貼完還要在 extension 畫面選這個分頁、按允許。
   - 印出「connect 網址含 token,不印在這裡」（有設 token）→ 把它列的兩步轉給使用者：新分頁開 `http://127.0.0.1:9555/connect`、按「複製」、貼進同一個分頁的網址列。那一頁有 token，你不要自己開、不要 curl。
   - 說 9555 已經有人在聽 → 照它印出的 process 回報使用者，請他決定；不要自己殺。
   - 逾時或 attach 失敗 → 它已經收乾淨、exit 1。問使用者卡在哪一步，再重跑（網址每次不同）。
   完成條件：輸出出現「已接上,session:<S>」。
4. **操作**：跟 headless 瀏覽器一樣用 `playwright-cli -s=<S> <指令>`。先 `tab-list`，應該只有一個分頁。
5. **收尾**：`playwright-cli -s=<S> detach`（dotfiles #248 實測過：Chrome 和分頁留著）。
   完成條件：背景的 `personal-chrome-attach` 印出「session <S> 結束了」並 exit 0。最後請使用者關掉那條 ssh。

使用者想每次只貼網址、不用選分頁：請他把 extension 狀態頁上的 token 設成**你這邊**的環境變數 `PLAYWRIGHT_MCP_EXTENSION_TOKEN`（他自己設在你跑的 shell 看得到的地方）。token 不進任何 repo，也不要叫他貼進對話；你也不要印出、存檔或轉述它。所以有 token 時腳本不印網址，網址只經他的 ssh 轉發到他的瀏覽器。

## 借使用者的對外 IP（網站擋機房 IP）

只在 headless 瀏覽器**因為 IP 被擋**時用：同一頁在使用者那台正常，這台卻是 403、驗證碼迴圈、「unusual traffic」、影片不能播。這時還是用 headless 瀏覽器，只是讓流量從使用者那台出去，不用改接他的 Chrome。平常不開：開著的時候你所有走 proxy 的流量都經過他的網路。

1. **請使用者開反向 SOCKS**，開著別關：`ssh -N company-ec2-socks`（dotfiles 的 ssh config 有這個別名；沒有就用 `ssh -N -R 127.0.0.1:1080 <你這台的 ssh host>`）。說 port 被佔而失敗，就是他另一台還開著。
   完成條件：`ss -ltn 'sport = :1080'` 看得到 `127.0.0.1:1080` 在聽。
2. **開帶 proxy 的 headless 瀏覽器**：proxy 只在瀏覽器啟動時讀，session 已經開著就先 `playwright-cli -s=<S> close`，再
   `PLAYWRIGHT_MCP_PROXY_SERVER=socks5://127.0.0.1:1080 playwright-cli -s=<S> open <網址>`。之後照常用 `playwright-cli -s=<S>` 指令。
   完成條件：在這個 session 開 `https://api64.ipify.org`，印出來的 IP 跟沒帶 proxy 時不同，而且使用者認得是他那台的。
   - Chrome 的 SOCKS5 在使用者那端解析 DNS，看到的是他那邊的 DNS 結果；他那台有 IPv6 時，對外 IP 常是 IPv6，跟他核對時兩種都要看。
3. **收尾**：`playwright-cli -s=<S> close`，請使用者在那個視窗按 Ctrl-C 關掉 ssh。
   完成條件：`ss -ltn 'sport = :1080'` 沒有東西在聽。
