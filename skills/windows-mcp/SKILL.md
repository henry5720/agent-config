---
name: windows-mcp
description: 把這台 Windows 桌面的 Windows-MCP 經 Tailscale Funnel 開給 tailnet 外的 agent 操作（截圖、點擊、打字），用完收掉並換 key。別台的 agent 要操作這台 Windows 的 GUI app，或說測完要收掉時使用。
---

# windows-mcp

Windows-MCP 要跑在 Windows 的使用者 session 裡，才操作得到眼前這個桌面。

- **同一台的 agent**（WSL 裡的 Claude Code、Codex）：不用這個 skill，直接用 skillshare `mcp.yaml` 裡的 `windows-mcp` server（stdio，client 用時才帶起來）。
- **別台的 agent**：照下面「tailnet 外的 agent」把 server 經 Funnel 開到外面，經 HTTPS 入口連到 `/mcp`，帶 Bearer key，用完收掉並換 key。tailnet 內的 agent 目前沒有自己的開法，也走這條。

連不上、出現 400／403／逾時，或要改用 Funnel 以外的對外方式時，看 [reference.md](reference.md)。

## 第一次安裝

在 Windows PowerShell 跑：

```powershell
winget install --exact --id Python.Python.3.14 --scope user
winget install --exact --id astral-sh.uv
# 重開 PowerShell
uv tool install --python 3.14 windows-mcp
uv tool update-shell
```

完成條件：PowerShell 跑 `windows-mcp --help` 有輸出。

只用需要時才開的方式。`windows-mcp install` 會建登入時自動啟動的 scheduled task，這裡用不到。

## tailnet 外的 agent（經 Funnel + key）

1. 在這台 Windows 的 WSL 跑 `~/.claude/skills/windows-mcp/scripts/windows-mcp-funnel-open`。它會換新 key、在 0.0.0.0:8000 起 server、開 Funnel :8443，再從公開 IP 驗證，最後印出 endpoint，並把 key 複製到 Windows 剪貼簿。
   完成條件：印出 `不帶 key=401` `帶 key=200` 和 endpoint。驗證沒過就跑 funnel-close，再看 reference.md。
2. **交 key**：請使用者把剪貼簿裡的 key 交給對方 agent，最好設成它的環境變數 `WINDOWS_MCP_AUTH_KEY`。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要 funnel-close 換 key。
3. 交代對方 agent：endpoint 用 `/mcp`，不帶結尾斜線；先跑 `tools/list` 和 `Screenshot`。`PowerShell`、`Registry`、`FileSystem` 寫入，要使用者同意才用。
4. 用完跑 `~/.claude/skills/windows-mcp/scripts/windows-mcp-funnel-close`：關 Funnel、停 server、換掉 key，交出去的那把就作廢了。
   完成條件：印出 `還在聽 8000 的程式：0，Funnel :8443 剩 0 條` 和 `已收掉`。

## 操作時

- **登入、輸入密碼**：交給使用者在桌機上自己做，不要跟他要密碼。
- **測試開的視窗**：使用者說要關才關，裡面可能有沒存的東西。
