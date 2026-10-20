---
name: remote-chrome
description: 開一個 CDP 9222 可連的 Chrome（桌機 Chrome 經 ssh 轉發，或遠端 headless），給 chrome-devtools MCP、playwright-cli（attach --cdp）等 CDP 工具連。用 chrome-devtools MCP 查前端問題的原因（慢、記憶體、minify 過的錯誤）前，或使用者要看著 agent 在他的 Chrome 上操作時使用；CDP 工具（MCP 或 playwright-cli）連不上 127.0.0.1:9222（Failed、Target closed、逾時）時也用。
---

# remote-chrome

9222 上的 Chrome 誰接都行：
- **chrome-devtools MCP** 查原因：performance trace、lighthouse、heap snapshot、minify 過的 code 下斷點。
- **`playwright-cli attach --cdp=http://127.0.0.1:9222`** 操作、截圖、錄影；接桌機 Chrome 時使用者看得到視窗。

驗收流程照 `verify-in-browser` skill 走。

CDP client 一律連 `127.0.0.1:9222`（chrome-devtools MCP 的設定就指向它），後面接的 Chrome 有兩種。平常是使用者的 Windows 桌機，封包這樣走：

```
company-ec2 的 CDP client  →  127.0.0.1:9222
                                │  ssh 轉發（remote-chrome 前景跑的 `ssh -N company-ec2-chrome`，帶 RemoteForward）
                                ▼
桌機 WSL                   →  127.0.0.1:9222
                                │  WSL mirrored 網路，WSL 和 Windows 共用 localhost
                                ▼
Windows Chrome             ←  在 9222 監聽（由 scripts/remote-chrome 啟動，profile ChromeDevToolsMCP）
```

`remote-chrome` 像 server 一樣停在前景：開 Chrome、起轉發，之後一直佔著那個終端機。
Ctrl+C 會把轉發和 MCP Chrome 一起關掉 —— 開著就是在用，用完就關。
只有 `Host company-ec2-chrome` 帶 RemoteForward；一般的 `ssh company-ec2` 和 herdr 都不帶
—— EC2 的 9222 只有一個位子，誰的 `remote-chrome` 開著就是誰的。

另一種是遠端主機自己開 headless Chrome 佔 9222（`scripts/remote-chrome-headless`，見步驟 2）。
兩種隨時都能用、CDP client 的設定不變，但同時只能開一個：誰開著 9222 就是誰的。
- **headless**：不用使用者動手，看不到畫面（要看就截圖）。不需要看畫面時用這個。
- **桌機 Chrome**：使用者看得到視窗、用的是他在桌機登入過的 profile，但要他在桌機跑 `remote-chrome`。

## 步驟

1. **驗證**：`curl -s --max-time 3 127.0.0.1:9222/json/version | grep User-Agent`
   （在 company-ec2 上驗就在那邊跑；桌機那邊的 Chrome 好了但 EC2 不通，看 `remote-chrome` 印的轉發訊息）
   - 看到 `Windows NT` → 通了（桌機的 Chrome），跳到 3。
   - 看到 `HeadlessChrome` → 通了（遠端主機自己的 headless，見 2），跳到 3。
   - 看到 `X11; Linux` → 連到本機別的 Chrome（例如 Playwright 起的）。`ss -ltnp | grep 9222`
     找出來，請使用者決定要不要關。
   - 沒回應 → 做 2。
2. **開 Chrome**，看這台是哪一種：
   - **桌機 WSL**（`command -v cmd.exe` 找得到）→ 自己跑 `~/.claude/skills/remote-chrome/scripts/remote-chrome`。
     它不會自己結束：放背景跑（Claude Code 的 Bash `run_in_background`）或開一個 herdr pane，
     等到印出「按 Ctrl+C」那行再回到 1。用完要關就對它送 Ctrl+C，不要直接殺 pane ——
     herdr 關 pane 會把整棵 process 砍掉，轉發會斷但 Chrome 留著（下次跑會沿用、結束時一起關）。
   - **遠端主機**（找不到 `cmd.exe`）而且有 `google-chrome` → 自己跑
     `~/.claude/skills/remote-chrome/scripts/remote-chrome-headless`（放背景，等到印出「按 Ctrl+C」）。
     預設走這條，使用者不用動手。使用者要看著瀏覽器操作、或要用桌機登入過的網站，就改走下一條。用完對它送 Ctrl+C，
     不然 9222 一直被佔著，桌機的 `remote-chrome` 會轉發失敗。
   - **遠端主機**，沒有 `google-chrome` 或使用者要用桌機的 Chrome → 請使用者在眼前那台的
     WSL 跑 `remote-chrome`，並讓那個終端機開著。它說「轉發斷了」「9222 被別台占著」時，
     另一台的 `remote-chrome` 還開著：去那台 Ctrl+C 再重跑；那台已經關機就等 EC2 清掉死連線（約 90 秒）。

   做完回到 1。
3. **接上 CDP client**：
   - chrome-devtools MCP：Claude Code 用 `/mcp` 重連；其他 client 用它自己的 reconnect。
   - playwright-cli：`playwright-cli -s=<S> attach --cdp=http://127.0.0.1:9222`，之後 `goto`、`screenshot`、`video-start` 照常用（`<S>` 是 session 名，驗收時照 `verify-in-browser` 的命名）。
     用完 `playwright-cli -s=<S> detach`：只斷開 session，Chrome 留給下一個 client。

## 開 Chrome 一律走 `remote-chrome`

它會先確認 9222 沒被占、使用專用 profile、等 endpoint 起來才回報。遠端主機的 headless
同理走 `remote-chrome-headless`。手拼的
`chrome.exe --remote-debugging-port=9222 --user-data-dir=...` 會開出另一個 profile：既有的
MCP Chrome 還開著時搶不到 9222 而且不報錯，登入狀態也不共用。遠端主機只裝官方 `.deb` 的
Chrome（dotfiles chezmoi 選裝工具的 `headless-chrome`，`playwright-cli` 用的也是這支），不要另外裝 Playwright／puppeteer 的。

背景與完整排錯表：agent-config 的
[docs/skills/remote-chrome.md](https://github.com/henry5720/agent-config/blob/main/docs/skills/remote-chrome.md)。
