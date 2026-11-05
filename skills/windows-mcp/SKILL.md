---
name: windows-mcp
description: 把一台 Windows 桌面的 Windows-MCP 開給別台的 agent 操作（截圖、點擊、打字）：起 server、換 key、交 key，用完收掉並換 key。別台的 agent 要操作某台 Windows 的 GUI app，或說測完要收掉時使用。
---

# windows-mcp

Windows-MCP 要跑在 Windows 的使用者 session 裡，才操作得到眼前這個桌面。

- **同一台的 agent**（WSL 裡的 Claude Code、Codex）：不用這個 skill，直接用 skillshare `mcp.yaml` 裡的 `windows-mcp` server（stdio，client 用時才帶起來）。
- **別台的 agent**：照下面「別台的 agent」起 HTTP server、換 key，讓對方連 `/mcp`、帶 Bearer key，用完收掉並換 key。對方在使用者的 tailnet 內就直接連，不叫 `expose-port`；在 tailnet 外才交給 `expose-port` skill 開公開網址。

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

### 選連法

照 [remote-access 的判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)，先看對方 agent 在哪：

- **對方 agent 在使用者的 tailnet 內** → [tailnet 內](#tailnet-內)：ssh 轉發或 tailscale serve，不開公網、不叫 `expose-port`。
- **在 tailnet 外，那台 Windows 加進使用者的 tailnet**（WSL 裡的 tailscale、Windows 原生 tailscale 都算）→ [Funnel](#funnel)。
- **在 tailnet 外，那台不加進使用者的 tailnet**（別人的機器、臨時借用）→ [quick tunnel](#quick-tunnel)。

有沒有 WSL 不影響選哪條，只決定 server 由誰起：有 WSL 時 agent 在那台 WSL 跑 `~/.claude/skills/windows-mcp/scripts/` 的腳本（靠 `powershell.exe` 操作 Windows）；沒有 WSL（或那台沒有 skillshare）時請使用者照[〈使用者在那台 PowerShell 貼〉](#使用者在那台-powershell-貼)貼。公開網址的開、驗、收都交給 `expose-port`，這裡只寫 server 那半和要給 `expose-port` 的輸入。

### 交 key 和交代 agent（每條都一樣）

- **交 key**：key 會先複製到那台的剪貼簿。請使用者交給對方 agent，最好設成它的環境變數 `WINDOWS_MCP_AUTH_KEY`。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要收掉並換 key。
- **交代 agent**：endpoint 是各條給的網址（結尾 `/mcp`）；先跑 `tools/list` 和 `Screenshot`。`PowerShell`、`Registry`、`FileSystem` 寫入，要使用者同意才用。

### 使用者在那台 PowerShell 貼

那台沒有 WSL 或沒有 skillshare 時，server 由使用者起、收。`<綁的位址>` 照各條：要讓代理改寫 `Host` 或走 ssh 轉發時 `127.0.0.1`；Funnel、tailscale serve 不能改寫 `Host`，用 `0.0.0.0`。

- **起 server、換 key**：`auth --force` 換一把新 key，最後一行把 key 複製到剪貼簿、不會印出來。取 key 都用最後一行；`config.toml` 開在畫面上時 key 會被 `Screenshot` 拍進去，真的用記事本開過就立刻關掉。綁 `0.0.0.0` 時，先請使用者確認防火牆沒放行 windows-mcp 的 inbound（不然區網能直連 8000，只剩 key 擋）。

  ```powershell
  windows-mcp auth --transport streamable-http --host <綁的位址> --port 8000 --force
  Start-Process -WindowStyle Minimized windows-mcp -ArgumentList 'serve','--host','<綁的位址>'
  (Select-String "$HOME\.windows-mcp\config.toml" -Pattern 'auth_key\s*=\s*"([^"]+)"').Matches.Groups[1].Value | Set-Clipboard
  ```

  完成條件：使用者說貼完了，並照上面交 key。
- **收掉**：第一行停掉聽 8000 的程式（server 的最小化視窗會跟著關），第二行換 key、設定改回 loopback，交出去的那把就作廢了，第三行確認。

  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
  windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
  (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count
  ```

  完成條件：最後一行印出 `0`。這段收尾**還沒實測**：`Stop-Process` 停得掉 server、`auth --force` 換 key 後舊 key 被拒（用舊 key 再打一次要 `401`）。

### tailnet 內

對方 agent 直接連那台，照 remote-access 的 [tailnet 內](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#tailnet-內)。這條**未實測**。

1. **挑做法、起 server**：
   - **ssh 轉發**（預設；對方那台 ssh 得到一個接得到那台 Windows `127.0.0.1:8000` 的端點，例如 Windows 的 OpenSSH、或 mirrored networking 的 WSL）：server 綁 loopback，`Host` 是 `127.0.0.1`，過得了檢查，也不用放行防火牆。server 照[〈使用者在那台 PowerShell 貼〉](#使用者在那台-powershell-貼)起，`<綁的位址>` 填 `127.0.0.1`。
   - **tailscale serve**（ssh 不到那台時）：serve 跟 Funnel 一樣不改寫 `Host`，server 要綁 `0.0.0.0`。有 WSL 跑 `windows-mcp-serve`；沒有就照上面那節貼，`<綁的位址>` 填 `0.0.0.0`。

   直接連 `<tailnet IP>:8000` 要另外在防火牆放行 inbound，不走這種。
   完成條件：server 起好，key 在使用者手上。
2. **接上**：
   - ssh 轉發：在對方 agent 那台背景跑 `ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8000:127.0.0.1:8000 <那台>`。網址是 `http://127.0.0.1:8000/mcp`。
   - tailscale serve：在那台 Windows 前景跑 `tailscale serve --https=8443 8000`（不加 `--bg`；有 WSL 時用 `powershell.exe -NoProfile -Command tailscale serve --https=8443 8000` 背景跑）。網址是 `https://<機器>.<tailnet>.ts.net:8443/mcp`。8443 被佔就換 `10000`。

   完成條件：從對方那台打網址，不帶 key 回 `401`，帶 key 的 POST `initialize`（[Funnel](#funnel) 第 2 步 `--` 後面那串）回 `200`。
3. 照上面交 key、交代 agent。
4. **收掉**：先停掉第 2 步那支（ssh 轉發或 tailscale serve），再收 server：有 WSL 跑 `windows-mcp-stop`，沒有照上面那節貼。
   完成條件：tailscale serve 那條在那台跑 `tailscale serve status` 沒有 8443；server 收尾的完成條件照各自那段。

### Funnel

Funnel 不能改寫 `Host`，所以這條 server 綁 `0.0.0.0:8000`。從 WSL 叫 Windows 原生 tailscale 開 Funnel **未實測**（跟 remote-access〈Tailscale Funnel〉那句一致）：開完照 `expose-port` 的完成條件驗、收完一定看收尾檢查是 0。

**那台沒有 WSL** 時下面的腳本用不了：server 照[〈使用者在那台 PowerShell 貼〉](#使用者在那台-powershell-貼)起（`<綁的位址>` 填 `0.0.0.0`），公開網址照 `expose-port` 的 Funnel 分支〈那台沒有這支腳本〉請使用者在那台 PowerShell 開，驗證用的 header 照 [quick tunnel](#quick-tunnel) 表裡的 `--auth-header-cmd`。收掉時先照 `expose-port` 收公開網址，再照上面那節收 server。下面 1–4 是有 WSL 的做法。

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
3. 照上面交 key、交代 agent，網址是 `公開網址`。
4. **收掉**：先照 `expose-port` 收掉公開網址，再跑 `windows-mcp-stop`：停 server、換掉 key，交出去的那把就作廢了。
   完成條件：`expose-port` 的收尾檢查是 0，`windows-mcp-stop` 印出 `還在聽 8000 的程式：0` 和 `已收掉，key 已換新`。

### quick tunnel

server 留在 loopback，`Host` 由 quick tunnel 改寫成 `localhost`，不用放行防火牆 inbound。那台通常沒有 skillshare。

1. **起 server、換 key**：照[〈使用者在那台 PowerShell 貼〉](#使用者在那台-powershell-貼)起，`<綁的位址>` 填 `127.0.0.1`。
   完成條件：同那節。
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
3. 照上面交代 agent，網址是 `公開網址`。
4. **收掉**：先照 `expose-port` 收掉公開網址，再照[〈使用者在那台 PowerShell 貼〉](#使用者在那台-powershell-貼)收 server。
   完成條件：`expose-port` 的收尾檢查是 0，加上那節的完成條件。

## 操作時

- **登入、輸入帳密或驗證碼**：帳密不經過 agent，交給使用者自己在那台輸入。
- **測試開的視窗**：使用者說要關才關，裡面可能有沒存的東西。

使用者在那台旁邊、或用遠端桌面看著 agent 操作時，再加：

- **輸入輪流**：同一時間只有一方動滑鼠鍵盤。使用者要動手時先停下，等使用者說好再繼續。
- **RPA 類程式在跑時**，agent 只截圖，不點擊、不打字。
- **每次都要使用者同意**：寫入外部系統（例如存檔、送單）、`PowerShell`、`FileSystem` 寫入。同意一次只算那一次。
