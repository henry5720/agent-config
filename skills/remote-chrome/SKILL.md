---
name: remote-chrome
description: 查原因前在本機開 headless Chrome 佔 9222 給 chrome-devtools MCP。要用 chrome-devtools MCP 查前端問題的原因（慢、記憶體、minify 過的錯誤、斷點）前使用；chrome-devtools MCP 連不上 127.0.0.1:9222（Failed、Target closed、逾時）時也用。
---

# remote-chrome

chrome-devtools MCP 的設定寫死連 `127.0.0.1:9222`，自己不開 Chrome。這個 skill 用
`remote-chrome-headless` 在 agent 跑的這台開一個 headless Chrome 佔 9222，給 MCP 查原因：
performance trace、lighthouse、heap snapshot、minify 過的 code 下斷點。

操作、驗收不用這個 skill：用 `playwright-cli open`（自己開瀏覽器、不佔 9222），流程照 `verify-in-browser` skill。

背景、排錯、設定放在哪：[reference.md](reference.md)。

## 步驟

1. **驗證**：`curl -s --max-time 3 127.0.0.1:9222/json/version | grep User-Agent`
   - 看到 `HeadlessChrome` → 通了，跳到 3。
   - 看到別的 User-Agent → 9222 被別的 Chrome 佔著（例如別人手動開的）。`ss -ltnp | grep 9222`
     找出是誰，請使用者決定要不要關，不要自己殺。
   - 沒回應 → 做 2。
2. **開 Chrome**：沒有 `google-chrome` 就停下來回報，請使用者在 dotfiles 的選裝工具勾 `headless-chrome`
   （WSL 不提供這一項：WSL 上 chrome-devtools MCP 沒有 Chrome 可接，查原因改到有 `headless-chrome` 的機器做）。
   有就跑 `~/.claude/skills/remote-chrome/scripts/remote-chrome-headless`（`~/.local/bin/remote-chrome-headless` 是同一支）。
   它停在前景不會自己結束：放背景跑（Claude Code 的 Bash `run_in_background`）或開一個 herdr pane，
   等到印出「按 Ctrl+C」那行再回到 1。它說 9222 有別的服務時，會印出佔著的 process，照那行回報使用者。
3. **接上 MCP**：Claude Code 用 `/mcp` 重連；其他 client 用它自己的 reconnect。
4. **收尾**：查完對 `remote-chrome-headless` 送 Ctrl+C（或停掉那個背景工作），不要留著佔 9222。

## 不要手拼 Chrome 指令

開 Chrome 一律走 `remote-chrome-headless`：它會先確認 9222 沒被佔、用固定的 profile
（`~/.local/state/chrome-mcp-profile`，登入狀態關掉再開還在）、等 endpoint 起來才回報。
只用 dotfiles 選裝工具 `headless-chrome` 裝的官方 `.deb` Chrome，不要另外裝 Playwright／puppeteer 的 Chrome。
