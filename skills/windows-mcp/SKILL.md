---
name: windows-mcp
description: 把一台 Windows 桌面的 Windows-MCP 開給別台的 agent 操作（截圖、點擊、打字）：起 server、換 key、交 key，用完收掉並換 key。別台的 agent 要操作某台 Windows 的 GUI app，或說測完要收掉時使用。
---

# windows-mcp

Windows-MCP 要跑在 Windows 的使用者 session 裡，才操作得到眼前這個桌面。

- **同一台的 agent**（WSL 裡的 Claude Code、Codex）：不用這個 skill，直接用 skillshare `mcp.yaml` 裡的 `windows-mcp` server（stdio，client 用時才帶起來）。
- **別台的 agent**（tailnet 內的也算）：照下面「別台的 agent」起 HTTP server、換 key，開到外面交給 `expose-port` skill；對方連 `/mcp`，帶 Bearer key，用完收掉並換 key。

server 本身的坑（400、307、session）看 [reference.md](reference.md)；經過 Funnel、quick tunnel 的坑看 `expose-port` 的 reference.md。給人看的版本（要在那台貼什麼、怎麼收）在 agent-config 的 `docs/skills/windows-mcp.md`。

## 第一次安裝

在 Windows PowerShell 跑：

```powershell
winget install --exact --id Python.Python.3.14 --scope user
winget install --exact --id astral-sh.uv
# 重開 PowerShell
uv tool install --python 3.14 windows-mcp
uv tool update-shell
```

完成條件：重開的 PowerShell 跑 `windows-mcp --help` 有輸出。

只用需要時才開的方式。`windows-mcp install` 會建登入時自動啟動的 scheduled task，這裡用不到。

## 別台的 agent

### 連線要求

- endpoint 是 `/mcp`，不帶結尾斜線；每個請求都要帶 `Authorization: Bearer <key>`，不帶回 `401`。
- server 綁 loopback（`127.0.0.1`）時只接受 `localhost`、`127.0.0.1`、`[::1]` 當 `Host`，其他回 `400`；綁 `0.0.0.0` 時不檢查。
- MCP streamable HTTP 可能用 SSE 回應。quick tunnel 不支援 SSE，走 quick tunnel 時這是風險：一般請求通、某個操作卡住或斷線時先懷疑它。

### 選對外方式

照 [remote-access 的判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)：那台 Windows 跑得到登入使用者 tailnet 的 tailscale → [Funnel](#funnel)；不加進使用者的 tailnet → [quick tunnel](#quick-tunnel)。開、驗、收都交給 `expose-port` skill，這裡只寫 server 那半和要給 `expose-port` 的輸入。

### 交 key 和交代 agent（兩種都一樣）

- **交 key**：key 會先複製到那台的剪貼簿。請使用者交給對方 agent，最好設成它的環境變數 `WINDOWS_MCP_AUTH_KEY`。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要收掉並換 key。
- **交代 agent**：endpoint 是 `expose-port` 印出的 `公開網址`（結尾 `/mcp`）；先跑 `tools/list` 和 `Screenshot`。`PowerShell`、`Registry`、`FileSystem` 寫入，要使用者同意才用。

### Funnel

Funnel 不能改寫 `Host`，所以這條 server 綁 `0.0.0.0:8000`。腳本都在 `~/.claude/skills/windows-mcp/scripts/`，靠 `powershell.exe` 操作 Windows，要在那台的 WSL 跑；那台沒有 WSL 時停下來回報使用者。

1. **起 server、換 key**：跑 `windows-mcp-serve`。它先確認防火牆沒放行 windows-mcp 的 inbound（區網直連 8000 只靠防火牆擋），換新 key，在 `0.0.0.0:8000` 起 server，再把 key 複製到 Windows 剪貼簿。
   完成條件：印出 `server 在 0.0.0.0:8000，key 已複製到 Windows 剪貼簿`。
2. **開到 tailnet 外**：照 `expose-port` 的 Funnel 分支開，輸入如下。`TAILSCALE` 讓它叫 Windows 那邊的 tailscale。

   ```bash
   TAILSCALE='powershell.exe -NoProfile -Command tailscale' \
   ~/.claude/skills/expose-port/scripts/expose-port-funnel open --port 8000 --https 8443 --path /mcp \
     --expect-without 401 --expect-with 200 \
     --auth-header-cmd ~/.claude/skills/windows-mcp/scripts/windows-mcp-auth-header \
     -- -X POST -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
   ```

   完成條件：`expose-port` 印出 `公開網址`。驗證沒過時 `expose-port` 已經撤掉 Funnel；跑 `windows-mcp-stop` 收掉 server，再看 [reference.md](reference.md) 和 `expose-port` 的 reference.md。
3. 照上面交 key、交代 agent。
4. **收掉**：先照 `expose-port` 收掉公開網址，再跑 `windows-mcp-stop`：停 server、換掉 key，交出去的那把就作廢了。
   完成條件：`expose-port` 的收尾檢查是 0，`windows-mcp-stop` 印出 `還在聽 8000 的程式：0` 和 `已收掉，key 已換新`。

### quick tunnel

server 留在 loopback，`Host` 由 quick tunnel 改寫成 `localhost`，不用放行防火牆 inbound。那台通常沒有 skillshare，server 由使用者在那台 PowerShell 起。

1. **起 server、換 key**：請使用者在那台 PowerShell 依序貼上。`auth --force` 換一把新 key，最後一行把 key 複製到剪貼簿、不會印出來。取 key 都用最後一行；`config.toml` 開在畫面上時 key 會被 `Screenshot` 拍進去，真的用記事本開過就立刻關掉。

   ```powershell
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   Start-Process -WindowStyle Minimized windows-mcp -ArgumentList 'serve'
   (Select-String "$HOME\.windows-mcp\config.toml" -Pattern 'auth_key\s*=\s*"([^"]+)"').Matches.Groups[1].Value | Set-Clipboard
   ```

   完成條件：使用者說貼完了，並照上面交 key。
2. **開到 tailnet 外**：照 `expose-port` 的 quick tunnel 分支開（那台沒有腳本，照「那台沒有這支腳本」那條請使用者貼），輸入：

   | 輸入 | 值 |
   |---|---|
   | 本機 port | `8000` |
   | `--host-header` | `localhost` |
   | `--path` | `/mcp` |
   | 不帶／帶驗證 | `401`／`200` |
   | `--auth-header-cmd` | `printf 'Authorization: Bearer %s\n' "$WINDOWS_MCP_AUTH_KEY"`（key 設在環境變數，不印出來） |
   | curl 參數 | 跟 Funnel 第 2 步 `--` 後面那串一樣（POST `initialize`） |

   完成條件：`expose-port` 印出 `公開網址`。2026-11-05 實測過這條：不帶 key `401`；帶 key 時 `initialize`、`tools/list`、`Snapshot` 都 `200`。手動打 `tools/list` 前先看 reference.md 的 session 那條。
3. 照上面交代 agent。
4. **收掉**：先照 `expose-port` 收掉公開網址，再請使用者在那台 PowerShell 貼上：第一行停掉聽 8000 的程式（server 的最小化視窗會跟著關），第二行換 key，交出去的那把就作廢了，第三行確認。

   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count
   ```

   完成條件：`expose-port` 的收尾檢查是 0，最後一行印出 `0`。這兩條收尾在 quick tunnel 這條**還沒實測**：`Stop-Process` 停得掉 server、`auth --force` 換 key 後舊 key 被拒（用舊 key 再打一次要 `401`）。

## 操作時

- **登入、輸入帳密或驗證碼**：帳密不經過 agent，交給使用者自己在那台輸入。
- **測試開的視窗**：使用者說要關才關，裡面可能有沒存的東西。

使用者在那台旁邊、或用遠端桌面看著 agent 操作時，再加：

- **輸入輪流**：同一時間只有一方動滑鼠鍵盤。使用者要動手時先停下，等使用者說好再繼續。
- **RPA 類程式在跑時**，agent 只截圖，不點擊、不打字。
- **每次都要使用者同意**：寫入外部系統（例如存檔、送單）、`PowerShell`、`FileSystem` 寫入。同意一次只算那一次。
