# windows-access reference

出問題時才讀。server 本身的坑所有 HTTP 模式都會遇到；經過 Funnel、quick tunnel 的坑和 `remote-access up` 的 serve 模式在 `remote-access` skill 的 reference.md。

## server 本身

- **從 ssh 起的 server 一啟動就結束**：ssh 進 Windows（或 ssh 進去再叫 `wsl.exe`、`powershell.exe`）是沒有互動桌面的 session，`serve` 在 lifespan 丟 `RuntimeError: No active interactive desktop for physical input control` 就結束（2026-11-05 在 henry-laptop 實測）。所以 `remote-access up` 用 Interactive scheduled task 起，要有人登入著桌面；沒人登入時它先報 `沒有人登入桌面`，不會起到一半。2026-11-05 在 henry-laptop、2026-11-22 在一台客戶的 Windows 主機（PowerShell 5.1，windows-mcp 用 uv tool 裝、經 PATH 找到）用 Interactive task 起成功。
- **server 跑著時換 key 不生效**：`auth --force` 只改 `config.toml`，跑著的 server 繼續收舊 key（2026-11-05 在 henry-laptop 實測舊 key 仍回 `200`）。換 key 一律先停 server；`remote-access key rotate` 重起 server，`windows-mcp-http.ps1` 的 `start`（有 server 在聽就拒絕）和 `rotate` 都是先停再換。
- **`/mcp/` 會 307 轉到 `/mcp`**：有些 client 不跟 POST redirect，所以直接給 `/mcp`。
- **log 在 server 的最小化視窗**：手動 `serve` 不寫檔；`~\.windows-mcp\server.log` 只有 scheduled task 會寫。
- **`serve` 沒帶 `--transport` 時**，會照 `config.toml` 的 transport 起 server。`auth` 會把它寫成 HTTP，所以 stdio 一定要明寫 `--transport stdio`。
- **綁 loopback 時會檢查 `Host` header**：只接受 `localhost`、`127.0.0.1`、`[::1]`。這版沒有可以加 allowed hosts 的選項（`windows_mcp/__main__.py` 的 DNS rebinding 段），綁 `0.0.0.0` 時不檢查。其他值一律回 400，訊息是 Invalid host header。
- **要先建 session**：streamable HTTP 直接打 `tools/list` 不會成功。順序是 POST `initialize` → 從回應 header 取 `Mcp-Session-Id` → 送 `notifications/initialized` → 之後每個請求都帶 `Mcp-Session-Id` header。MCP client 會自己做，手動用 curl 打才要照這個順序。
- **MCP streamable HTTP 用 SSE 回應**（`initialize`、`tools/list` 回 `text/event-stream`）。走 quick tunnel 時某個操作卡住或斷線先懷疑它（`remote-access` 的 reference.md〈quick tunnel 專屬〉）。
- **`Snapshot` 有時讀不到視窗**（回 `No windows found`），截圖仍然正常。讀不到就靠截圖加座標點擊。

## 機器的狀態

- **henry-laptop 走不了 serve（2026-11-27）**：這台 agent 機器 ssh config 裡 henry-laptop 的 HostName 不是 ts.net 名稱，`up` 會報 `HostName 要是 ts.net 名稱`。ssh config 由 dotfiles 管，請使用者改 dotfiles，不在這裡繞。

## ssh 不到那台：手動起 server

agent 在 tailnet 外、ssh 不到那台 Windows，要經 Funnel、quick tunnel 開出去時才用。server 用 `scripts/windows-mcp-http.ps1` 在那台的桌面 PowerShell 起（5.1 或 7，不經 WSL），`--help` 看參數。它保證先停 server 再換 key、key 不印出來。

誰跑：你就在那台 Windows（原生 Windows 的 Claude Code，從使用者桌面開的）時用 PowerShell tool 自己跑；其他情況把指令交給使用者，請他在那台桌面開 PowerShell 貼。動 PowerShell 前先問使用者，客戶的機器每次都問。

那台有 skillshare 時 script 在 `$HOME\.claude\skills\windows-access\scripts\windows-mcp-http.ps1`。沒有的話先下載（指 `main`：這個 repo 由使用者自己維護；`-UseBasicParsing` 給 5.1 用）：

```powershell
Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/henry5720/agent-config/main/skills/windows-access/scripts/windows-mcp-http.ps1 -OutFile "$env:TEMP\windows-mcp-http.ps1"
```

下面 `<script>` 是那個路徑。`-ExecutionPolicy Bypass` 是因為下載的檔案會被預設的執行原則擋掉。

1. **起**：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File <script> start --host <綁的位址>
   ```

   `<綁的位址>`：quick tunnel 用 `127.0.0.1`；Funnel 不改寫 `Host`，用 `0.0.0.0`（預設）。綁 `0.0.0.0` 時它先確認防火牆沒有讓區網連到 8000 的 inbound 規則，有就拒絕。
   完成條件：印出 `server 在 <綁的位址>:8000，key 已複製到剪貼簿（沒有印出來）`。印 `8000 已經有程式在聽` 時看它列的程式：是 windows-mcp 就先跑 `stop` 再起；不是就停下來回報使用者，不要自己停它。
2. **連線**：照 `remote-access`〈tailnet 外〉，輸入照下面的表。
3. **交 key**：key 在那台的剪貼簿。請使用者交給對方 agent 的使用者，設成啟動 agent 的 shell 的環境變數 `WINDOWS_MCP_AUTH_KEY`，再開 session。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要 `rotate`。`config.toml` 開在畫面上時 key 會被 `Screenshot` 拍進去，真的用記事本開過就立刻關掉。
4. **收**：先照 `remote-access` 收掉公開網址，再跑 `powershell -NoProfile -ExecutionPolicy Bypass -File <script> stop`（key 不換）；key 要作廢時改跑 `rotate`（先停，再換 key、設定改回 `127.0.0.1`）。聽 8000 的不是 windows-mcp 時它不停那支，列出 PID 和程式名後 exit 1：照轉達給使用者。
   完成條件：印出 `還在聽 8000 的程式：0（要 0）` 和 `已收掉（key 沒換）`；`rotate` 是 `已收掉，key 已換新`。

### 給 remote-access 的輸入

| 輸入 | 值 |
|---|---|
| app port | 那台聽 `8000` |
| `Host` 規則 | 綁 `127.0.0.1` 時只接受 `localhost`、`127.0.0.1`、`[::1]`，其他回 `400`；綁 `0.0.0.0` 不檢查 |
| quick tunnel | 帶 `--host-header localhost`，server 留在 `127.0.0.1` |
| 驗證路徑、請求 | `/mcp`（不帶結尾斜線），POST MCP `initialize`；curl 參數：`-X POST -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'` |
| 不帶／帶驗證 | `401`／`200` |
| auth header | 從 agent 這台驗：`--auth-header-cmd 'printf "Authorization: Bearer %s\n" "$WINDOWS_MCP_AUTH_KEY"'`（key 在環境變數，不印出來）。你就在那台 Windows：`<印出 header 的 PowerShell>` 填 `powershell -NoProfile -ExecutionPolicy Bypass -File <script> auth-header` |

你就在那台 Windows 時，`remote-access`〈agent 就在那台 Windows〉第 3 步那段的輸入：`<curl 參數>` 填 `'-X', 'POST', '-H', 'Accept: application/json, text/event-stream', '-H', 'Content-Type: application/json'`，`$json` 填上面 `-d` 後面那串 JSON。
