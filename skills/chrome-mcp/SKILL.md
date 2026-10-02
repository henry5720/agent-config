---
name: chrome-mcp
description: chrome-devtools MCP 連不上 127.0.0.1:9222（Failed、Target closed、逾時）時使用；要讓 agent 用瀏覽器偵錯前、或在 company-ec2 等遠端主機要用瀏覽器時也用。
---

# chrome-mcp

Chrome 跑在使用者的 Windows 桌機。chrome-devtools MCP 連 `127.0.0.1:9222`，封包這樣走：

```
company-ec2 的 MCP  →  127.0.0.1:9222
                         │  ssh 轉發（chrome-mcp 前景跑的 `ssh -N company-ec2-chrome`，帶 RemoteForward）
                         ▼
桌機 WSL            →  127.0.0.1:9222
                         │  WSL mirrored 網路，WSL 和 Windows 共用 localhost
                         ▼
Windows Chrome      ←  在 9222 監聽（由 scripts/chrome-mcp 啟動，profile ChromeDevToolsMCP）
```

`chrome-mcp` 像 server 一樣停在前景：開 Chrome、起轉發，之後一直佔著那個終端機。
Ctrl+C 會把轉發和 MCP Chrome 一起關掉 —— 開著就是在用，用完就關。
只有 `Host company-ec2-chrome` 帶 RemoteForward；一般的 `ssh company-ec2` 和 herdr 都不帶
—— EC2 的 9222 只有一個位子，誰的 `chrome-mcp` 開著就是誰的。

## 步驟

1. **驗證**：`curl -s --max-time 3 127.0.0.1:9222/json/version | grep User-Agent`
   （在 company-ec2 上驗就在那邊跑；桌機那邊的 Chrome 好了但 EC2 不通，看 `chrome-mcp` 印的轉發訊息）
   - 看到 `Windows NT` → 通了，跳到 3。
   - 看到 `X11; Linux` → 連到本機別的 Chrome（例如 Playwright 起的）。`ss -ltnp | grep 9222`
     找出來，請使用者決定要不要關。
   - 沒回應 → 做 2。
2. **開 Chrome**，看這台是哪一種：
   - **桌機 WSL**（`command -v cmd.exe` 找得到）→ 自己跑 `~/.claude/skills/chrome-mcp/scripts/chrome-mcp`。
     它不會自己結束：放背景跑（Claude Code 的 Bash `run_in_background`）或開一個 herdr pane，
     等到印出「按 Ctrl+C」那行再回到 1。用完要關就對它送 Ctrl+C，不要直接殺 pane ——
     herdr 關 pane 會把整棵 process 砍掉，轉發會斷但 Chrome 留著（下次跑會沿用、結束時一起關）。
   - **遠端主機**（找不到 `cmd.exe`）→ Chrome 在使用者那台，這台開不了。請使用者在眼前那台的
     WSL 跑 `chrome-mcp`，並讓那個終端機開著。它說「轉發斷了」「9222 被別台占著」時，
     另一台的 `chrome-mcp` 還開著：去那台 Ctrl+C 再重跑；那台已經關機就等 EC2 清掉死連線（約 90 秒）。

   做完回到 1。
3. **重連 MCP**：Claude Code 用 `/mcp`；其他 client 用它自己的 reconnect。

## 開 Chrome 一律走 `chrome-mcp`

它會先確認 9222 沒被占、使用專用 profile、等 endpoint 起來才回報。手拼的
`chrome.exe --remote-debugging-port=9222 --user-data-dir=...` 會開出另一個 profile：既有的
MCP Chrome 還開著時搶不到 9222 而且不報錯，登入狀態也不共用。遠端主機保持不裝 Chrome。

背景與完整排錯表：dotfiles 的
[docs/chrome-devtools-mcp.md](https://github.com/henry5720/dotfiles/blob/main/docs/chrome-devtools-mcp.md)。
