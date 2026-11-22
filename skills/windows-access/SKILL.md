---
name: windows-access
description: 讓 agent 操作一台 Windows 桌面（截圖、點擊、打字）：同一台用 stdio 的 windows-mcp；別台起 Windows-MCP 的 HTTP server、換 key、交 key，用完收掉並換 key。要操作某台 Windows 的 GUI app、在那台起或收 windows-mcp server、設定接別台 Windows 的 MCP 時使用。
---

# windows-access

Windows-MCP 要跑在 Windows 使用者登入的桌面 session 裡，才操作得到眼前這個桌面。從 ssh 起的沒有桌面，server 一啟動就結束（做法和例外看 [reference.md](reference.md)〈從 ssh 起的 server 一啟動就結束〉）。

先看 agent 在哪：

- **同一台**（那台 WSL 裡的 Claude Code、Codex）→ 直接用 skillshare `mcp.yaml` 裡的 `windows-mcp`（stdio，client 用時才帶起來）。不起 HTTP server、不用 key、不用連線。
- **別台** → [別台的 agent](#別台的-agent)：在那台起 HTTP server，連線交給 `remote-access` skill。

server 本身的坑（400、307、session）看 [reference.md](reference.md)；連線的坑看 `remote-access` 的 reference.md。

## 第一次安裝

Windows-MCP 是第三方開源專案（[CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP)），工具清單和選項以它的 README 為準。安裝交給使用者：裝了 dotfiles 的 Windows 主機在 PowerShell 打 `tools` 勾 windows-mcp 再 apply（mise 裝）；沒裝 dotfiles 的照 Windows-MCP 的 README 裝。stdio 那支只找 mise 的 shim `%LOCALAPPDATA%\mise\shims\windows-mcp.exe`，`windows-mcp-http.ps1` 先找 shim、再找 PATH；找不到都會印出要使用者做什麼，照轉達。

完成條件：使用者在新開的 PowerShell 跑 `windows-mcp --help` 有輸出。

只用需要時才開的方式。`windows-mcp install` 會建登入時自動啟動的 scheduled task，這裡用不到。

## 別台的 agent

### 起、收 server

一律用 `scripts/windows-mcp-http.ps1`，在那台 Windows 的 PowerShell 跑（5.1 或 7，不經 WSL）。它保證先停 server 再換 key、key 不印出來；`--help` 看參數。誰跑：

- **你就在那台 Windows**（原生 Windows 的 Claude Code，從使用者桌面開的）：用 PowerShell tool 自己跑。
- **其他情況**：把指令交給使用者，請他在那台桌面開 PowerShell 貼。

那台有 skillshare 時 script 在 `$HOME\.claude\skills\windows-access\scripts\windows-mcp-http.ps1`。沒有的話先下載（指 `main`：這個 repo 由使用者自己維護，script 改了不用再改這行；`-UseBasicParsing` 給 5.1 用）：

```powershell
Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/henry5720/agent-config/main/skills/windows-access/scripts/windows-mcp-http.ps1 -OutFile "$env:TEMP\windows-mcp-http.ps1"
```

下面 `<script>` 是那個路徑。`-ExecutionPolicy Bypass` 是因為下載的檔案會被預設的執行原則擋掉。

1. **起**：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File <script> start --host <綁的位址>
   ```

   `<綁的位址>` 照連線選：ssh 轉發、quick tunnel 用 `127.0.0.1`；Funnel、tailscale serve 不改寫 `Host`，用 `0.0.0.0`（預設）。綁 `0.0.0.0` 時它先確認防火牆沒放行 windows-mcp 的 inbound，有就拒絕。
   完成條件：印出 `server 在 <綁的位址>:8000，key 已複製到剪貼簿（沒有印出來）`。印 `8000 已經有程式在聽` 時先跑下面的 `stop` 再起。
2. **連線**：照 `remote-access` 的判準選，輸入照[〈給 remote-access 的輸入〉](#給-remote-access-的輸入)。
3. **交 key、交代 agent**：照[〈交 key 和交代 agent〉](#交-key-和交代-agent)。
4. **收**：先照 `remote-access` 收掉連線，再跑：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File <script> stop
   ```

   它停掉聽 8000 的程式，再換 key、設定改回 `127.0.0.1`，交出去的那把就作廢了。
   完成條件：印出 `還在聽 8000 的程式：0（要 0）` 和 `已收掉，key 已換新`。

實測紀錄（2026-11-05，henry-laptop，當時是手動貼同樣的指令）：server 跑著時 `auth --force` 換的 key 不生效、舊 key 仍回 `200`，所以 script 一定先停再換；`Stop-Process` 停得掉 server，聽 8000 的數變 `0`。用新 key 重起的 server 拒絕舊 key（要 `401`）**未實測**；這支 script 本身在真的 Windows 上也還沒跑過。

### 給 remote-access 的輸入

| 輸入 | 值 |
|---|---|
| 本機 port | 那台聽 `8000`；agent 這台轉發用 `18000`（照 `remote-access` 的 port 總表） |
| `Host` 規則 | 綁 `127.0.0.1` 時只接受 `localhost`、`127.0.0.1`、`[::1]`，其他回 `400`；綁 `0.0.0.0` 不檢查 |
| quick tunnel | 帶 `--host-header localhost`，server 留在 `127.0.0.1` |
| 驗證路徑、請求 | `/mcp`（不帶結尾斜線），POST MCP `initialize`；curl 參數：`-X POST -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'` |
| 不帶／帶驗證 | `401`／`200` |
| auth header | 從 agent 這台驗：`--auth-header-cmd 'printf "Authorization: Bearer %s\n" "$WINDOWS_MCP_AUTH_KEY"'`（key 在環境變數，不印出來）。你就在那台 Windows：`<印出 header 的 PowerShell>` 填 `powershell -NoProfile -ExecutionPolicy Bypass -File <script> auth-header` |

MCP streamable HTTP 用 SSE 回應（`initialize`、`tools/list` 回 `text/event-stream`）。走 quick tunnel 時某個操作卡住或斷線先懷疑它（`remote-access` 的 quick tunnel 那節有實測紀錄）。

你就在那台 Windows 時，`remote-access`〈agent 就在那台 Windows〉第 3 步的 JSON 要寫進檔案用 `-d "@檔案"` 帶：寫檔那行 `$body = New-TemporaryFile; '<上面 -d 後面那串 JSON>' | Set-Content $body -Encoding ascii -NoNewline` 跟那段放在同一次 PowerShell 呼叫（tool 不一定在兩次呼叫間保留變數），插在 `$hdr = New-TemporaryFile` 前一行，並把那段的 `finally` 改成 `finally { Remove-Item $hdr, $body }`。

### 交 key 和交代 agent

- **交 key**：`start` 已經把 key 複製到那台的剪貼簿。請使用者交給對方 agent 的使用者，設成啟動 agent 的 shell 的環境變數 `WINDOWS_MCP_AUTH_KEY`（見下面〈客戶端設定〉）。agent 自己讀 key、或把 key 傳到別的服務，都要先取得使用者明說同意。用聊天訊息交的話，用完一定要 `stop` 換 key。`config.toml` 開在畫面上時 key 會被 `Screenshot` 拍進去，真的用記事本開過就立刻關掉。
- **交代 agent**：endpoint 是連線給的網址（結尾 `/mcp`）；先跑 `tools/list` 和 `Screenshot`。`PowerShell`、`Registry`、`FileSystem` 寫入，要使用者同意才用。

### 客戶端設定

對方 agent 那端（例如 company-ec2）用 `mcp.yaml` 裡固定的 `windows-mcp-remote`：`http://127.0.0.1:18000/mcp`，Bearer key 讀環境變數 `WINDOWS_MCP_AUTH_KEY`。連哪台只由 ssh 轉發的目標決定（`ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:18000:127.0.0.1:8000 <那台>`，照 `remote-access` 的 tailnet 內），換一台不改設定。

- **開 session 前**：使用者在啟動 agent 的 shell 裡 `export WINDOWS_MCP_AUTH_KEY=<key>`，再開 session。MCP 設定在 session 開始時就要存在；session 中途只做 ssh 轉發，轉發起來後用 `/mcp` 重連 `windows-mcp-remote`。
- **換 key 要重開 session**：client 只在啟動時讀環境變數。
- **本機 18000 被佔**（ssh 報 `Address already in use`、或 `ExitOnForwardFailure` 直接結束）：回報使用者是哪支程式佔著，port 維持 18000。換 port 會跟 MCP 設定對不上，可能連到錯的 server。
- **同一時間只接一台**：要接另一台，先收掉現在這條轉發。
- **收舊設定**：之前用 `claude mcp add` 自己加過的 local scope 設定（key 原文在裡面），等 `windows-mcp-remote` 驗證過（`/mcp` 看得到 tools）後，用 `claude mcp remove <名字> -s local` 收掉，再在那台跑 `stop` 換 key，讓舊設定裡那把作廢。

## 操作時

- **登入、輸入帳密或驗證碼**：帳密不經過 agent，交給使用者自己在那台輸入。
- **測試開的視窗**：使用者說要關才關，裡面可能有沒存的東西。

使用者在那台旁邊、或用遠端桌面看著 agent 操作時，再加：

- **輸入輪流**：同一時間只有一方動滑鼠鍵盤。使用者要動手時先停下，等使用者說好再繼續。
- **RPA 類程式在跑時**，agent 只截圖，不點擊、不打字。
- **每次都要使用者同意**：寫入外部系統（例如存檔、送單）、`PowerShell`、`FileSystem` 寫入。同意一次只算那一次。
