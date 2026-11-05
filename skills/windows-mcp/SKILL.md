---
name: windows-mcp
description: 把一台 Windows 桌面的 Windows-MCP 開給別台的 agent 操作（截圖、點擊、打字）：起 server、換 key、交 key，用完收掉並換 key。別台的 agent 要操作某台 Windows 的 GUI app，或說測完要收掉時使用。
---

# windows-mcp

Windows-MCP 要跑在 Windows 的使用者 session 裡，才操作得到眼前這個桌面。

- **同一台的 agent**（WSL 裡的 Claude Code、Codex）：不用這個 skill，直接用 skillshare `mcp.yaml` 裡的 `windows-mcp` server（stdio，client 用時才帶起來）。
- **別台的 agent**（tailnet 內的也算）：照下面「別台的 agent」起 HTTP server、換 key，開到外面交給 `expose-port` skill；對方連 `/mcp`，帶 Bearer key，用完收掉並換 key。

server 本身的坑（400、307、session）看 [reference.md](reference.md)；經過 Funnel 或代理的坑看 `expose-port` 的 reference.md。

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

照 [remote-access 的判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)：那台 Windows 跑得到登入使用者 tailnet 的 tailscale → Funnel；不加進使用者的 tailnet → quick tunnel。Funnel 這邊的腳本要在那台的 WSL 跑（靠 `powershell.exe` 操作 Windows），沒有 WSL 時停下來回報使用者。

### 交 key 和交代 agent（兩種都一樣）

- **交 key**：key 會先複製到那台的剪貼簿。請使用者交給對方 agent，最好設成它的環境變數 `WINDOWS_MCP_AUTH_KEY`。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要收掉並換 key。
- **交代 agent**：endpoint 用 `/mcp`，不帶結尾斜線；先跑 `tools/list` 和 `Screenshot`。`PowerShell`、`Registry`、`FileSystem` 寫入，要使用者同意才用。

### Funnel

Funnel 不能改寫 `Host`，而 server 綁 loopback 時只接受 `localhost`，所以這條 server 綁 `0.0.0.0:8000`。腳本都在 `~/.claude/skills/windows-mcp/scripts/`，在那台的 WSL 跑。

1. **起 server、換 key**：跑 `windows-mcp-serve`。它先確認防火牆沒放行 windows-mcp 的 inbound（區網直連 8000 只靠防火牆擋），換新 key，在 `0.0.0.0:8000` 起 server，再把 key 複製到 Windows 剪貼簿。
   完成條件：印出 `server 在 0.0.0.0:8000，key 已複製到 Windows 剪貼簿`。
2. **開到 tailnet 外**：照 `expose-port` skill 的 Funnel 分支開，輸入如下。`TAILSCALE` 讓它叫 Windows 那邊的 tailscale。

   ```bash
   TAILSCALE='powershell.exe -NoProfile -Command tailscale' \
   ~/.claude/skills/expose-port/scripts/expose-port-funnel open --port 8000 --https 8443 --path /mcp \
     --expect-without 401 --expect-with 200 \
     --auth-header-cmd ~/.claude/skills/windows-mcp/scripts/windows-mcp-auth-header \
     -- -X POST -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
   ```

   完成條件：`expose-port` 印出 `公開網址`，endpoint 就是那個網址（結尾 `/mcp`）。驗證沒過時 `expose-port` 已經撤掉 Funnel；跑 `windows-mcp-stop` 收掉 server，再看兩份 reference.md。
3. 照上面交 key、交代 agent。
4. **收掉**：先照 `expose-port` 收掉 Funnel，再跑 `windows-mcp-stop`：停 server、換掉 key，交出去的那把就作廢了。
   完成條件：`expose-port` 印出 `Funnel :8443 剩 0 條`，`windows-mcp-stop` 印出 `還在聽 8000 的程式：0` 和 `已收掉，key 已換新`。

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
