---
name: windows-mcp
description: 把一台 Windows 桌面的 Windows-MCP 經 Tailscale Funnel 或 Cloudflare quick tunnel 開給別台的 agent 操作（截圖、點擊、打字），用完收掉並換 key。別台的 agent 要操作某台 Windows 的 GUI app，或說測完要收掉時使用。
---

# windows-mcp

Windows-MCP 要跑在 Windows 的使用者 session 裡，才操作得到眼前這個桌面。

- **同一台的 agent**（WSL 裡的 Claude Code、Codex）：不用這個 skill，直接用 skillshare `mcp.yaml` 裡的 `windows-mcp` server（stdio，client 用時才帶起來）。
- **別台的 agent**（tailnet 內的也算）：照下面「別台的 agent」把 server 經 HTTPS 入口開到外面，連 `/mcp`，帶 Bearer key，用完收掉並換 key。

連不上、出現 400／403／逾時，或要改用其他對外方式時，看 [reference.md](reference.md)。

## 第一次安裝

在 Windows PowerShell 跑：

```powershell
winget install --exact --id Python.Python.3.14 --scope user
winget install --exact --id astral-sh.uv
# 重開 PowerShell
uv tool install --python 3.14 windows-mcp
uv tool update-shell
```

要走 quick tunnel 的話，在第一次重開 PowerShell 之前多裝 cloudflared：

```powershell
winget install --exact --id Cloudflare.cloudflared
```

完成條件：重開的 PowerShell 跑 `windows-mcp --help` 有輸出；走 quick tunnel 的再加 `cloudflared --version` 有輸出。

只用需要時才開的方式。`windows-mcp install` 會建登入時自動啟動的 scheduled task，這裡用不到。

## 別台的 agent

### 選對外方式

兩種並列，看那台 Windows 的條件選：

|  | Funnel | quick tunnel |
|---|---|---|
| 那台要有 | WSL，且登入 Tailscale | cloudflared，不用帳號 |
| 怎麼開 | WSL 跑 funnel-open／funnel-close 腳本 | 沒有腳本，指令請使用者貼進那台 PowerShell |
| server 綁 | `0.0.0.0:8000` | `127.0.0.1:8000`，不用開防火牆 inbound |
| 網址 | 腳本印出 | 每次開都不同，要重新交給 agent |

只符合一邊的條件就走那邊；兩邊都符合時兩者皆可。

### 交 key 和交代 agent（兩種都一樣）

- **交 key**：key 會先複製到那台的剪貼簿。請使用者交給對方 agent，最好設成它的環境變數 `WINDOWS_MCP_AUTH_KEY`。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要收掉並換 key。
- **交代 agent**：endpoint 用 `/mcp`，不帶結尾斜線；先跑 `tools/list` 和 `Screenshot`。`PowerShell`、`Registry`、`FileSystem` 寫入，要使用者同意才用。

### Funnel

1. **開**：在那台 Windows 的 WSL 跑 `~/.claude/skills/windows-mcp/scripts/windows-mcp-funnel-open`。它會換新 key、在 0.0.0.0:8000 起 server、開 Funnel :8443，再從公開 IP 驗證，最後印出 endpoint，並把 key 複製到 Windows 剪貼簿。
   完成條件：印出 `不帶 key=401` `帶 key=200` 和 endpoint。驗證沒過就跑 funnel-close，再看 reference.md。
2. 照上面交 key、交代 agent。
3. **收掉**：用完跑 `~/.claude/skills/windows-mcp/scripts/windows-mcp-funnel-close`：關 Funnel、停 server、換掉 key，交出去的那把就作廢了。
   完成條件：印出 `還在聽 8000 的程式：0，Funnel :8443 剩 0 條` 和 `已收掉`。

### quick tunnel

由 cloudflared 開一個 `trycloudflare.com` 的 HTTPS 網址，轉進留在 loopback 的 server。

1. **開**：請使用者在那台 PowerShell 依序貼上。`auth --force` 會換一把新 key。

   ```powershell
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   Start-Process -WindowStyle Minimized windows-mcp -ArgumentList 'serve'
   cloudflared tunnel --url http://127.0.0.1:8000 --http-host-header localhost
   ```

   cloudflared 會佔住這個視窗，輸出裡有一行 `https://<隨機名稱>.trycloudflare.com`。endpoint 是這個網址加 `/mcp`。
   完成條件：使用者把 cloudflared 印出的網址給你。
2. **取 key**：請使用者另開一個 PowerShell 貼上下面這行，key 會複製到剪貼簿、不會印出來，再照上面交 key、交代 agent。取 key 都用這行；`config.toml` 開在畫面上時 key 會被 `Screenshot` 拍進去，所以真的用記事本開過就立刻關掉。

   ```powershell
   (Select-String "$HOME\.windows-mcp\config.toml" -Pattern 'auth_key\s*=\s*"([^"]+)"').Matches.Groups[1].Value | Set-Clipboard
   ```

3. **驗證**：從 agent 這邊 POST endpoint 兩次，一次不帶 key、一次帶 `Authorization: Bearer <key>`。

   ```bash
   curl -s -m 30 -o /dev/null -w '%{http_code}' -X POST "<endpoint>" \
     -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
   # 帶 key 那次加 -H "Authorization: Bearer $WINDOWS_MCP_AUTH_KEY"
   ```

   完成條件：不帶 key 回 `401`、帶 key 回 `200`（2026-11-05 實測過兩條）。之後要手動打 `tools/list` 等方法，先看 reference.md 的 session 那條。驗證沒過就照第 4 步收掉，再看 reference.md。
4. **收掉**：請使用者在 cloudflared 視窗按 Ctrl+C，關掉 windows-mcp 的最小化視窗（找不到就用下面第一行停掉聽 8000 的程式），最後用第二行換 key，交出去的那把就作廢了。這兩行還沒實測過，跑完照完成條件確認。

   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   ```

   完成條件：`(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count` 印出 `0`，cloudflared 視窗已結束，且 key 已換。

## 操作時

- **登入、輸入帳密或驗證碼**：帳密不經過 agent，交給使用者自己在那台輸入。
- **測試開的視窗**：使用者說要關才關，裡面可能有沒存的東西。

使用者在那台旁邊、或用遠端桌面看著 agent 操作時，再加：

- **輸入輪流**：同一時間只有一方動滑鼠鍵盤。使用者要動手時先停下，等使用者說好再繼續。
- **RPA 類程式在跑時**，agent 只截圖，不點擊、不打字。
- **每次都要使用者同意**：寫入外部系統（例如存檔、送單）、`PowerShell`、`FileSystem` 寫入。同意一次只算那一次。
