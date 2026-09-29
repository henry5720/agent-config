---
name: chrome-mcp
description: chrome-devtools MCP 連不上 127.0.0.1:9222（Failed、Target closed、逾時）時使用；要讓 agent 用瀏覽器偵錯前、或在 company-ec2 等遠端主機要用瀏覽器時也用。
---

# chrome-mcp

Chrome 跑在使用者的 Windows 桌機。chrome-devtools MCP 連 `127.0.0.1:9222`，封包這樣走：

```
company-ec2 的 MCP  →  127.0.0.1:9222
                         │  ssh 轉發（桌機 `ssh company-ec2` 的 RemoteForward）
                         ▼
桌機 WSL            →  127.0.0.1:9222
                         │  WSL mirrored 網路，WSL 和 Windows 共用 localhost
                         ▼
Windows Chrome      ←  在 9222 監聽（由 scripts/chrome-mcp 啟動，profile ChromeDevToolsMCP）
```

在桌機 WSL 用只需要 Chrome 開著；在 company-ec2 用還要那條 ssh 連線沒斷。

## 步驟

1. **驗證**：`curl -s --max-time 3 127.0.0.1:9222/json/version | grep User-Agent`
   - 看到 `Windows NT` → 通了，跳到 3。
   - 看到 `X11; Linux` → 連到本機別的 Chrome（例如 Playwright 起的）。`ss -ltnp | grep 9222`
     找出來，請使用者決定要不要關。
   - 沒回應 → 做 2。
2. **開 Chrome**，看這台是哪一種：
   - **桌機 WSL**（`command -v cmd.exe` 找得到）→ 自己跑 `~/.claude/skills/chrome-mcp/scripts/chrome-mcp`。
   - **遠端主機**（找不到 `cmd.exe`）→ Chrome 在使用者那台，這台開不了。請使用者在桌機 WSL 跑
     `chrome-mcp`，並確認桌機有一條 `ssh company-ec2` 連線開著。

   做完回到 1。
3. **重連 MCP**：Claude Code 用 `/mcp`；其他 client 用它自己的 reconnect。

## 開 Chrome 一律走 `chrome-mcp`

它會先確認 9222 沒被占、使用專用 profile、等 endpoint 起來才回報。手拼的
`chrome.exe --remote-debugging-port=9222 --user-data-dir=...` 會開出另一個 profile：既有的
MCP Chrome 還開著時搶不到 9222 而且不報錯，登入狀態也不共用。遠端主機保持不裝 Chrome。

背景與完整排錯表：dotfiles 的
[docs/chrome-devtools-mcp.md](https://github.com/henry5720/dotfiles/blob/main/docs/chrome-devtools-mcp.md)。
