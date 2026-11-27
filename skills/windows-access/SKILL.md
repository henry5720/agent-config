---
name: windows-access
description: 讓 agent 操作一台 Windows 桌面（截圖、點擊、打字）：同一台用 stdio 的 windows-mcp；別台用 `remote-access up windows-mcp <host>` 起 server、接 MCP，用完 `down`，key 要作廢時 `remote-access key rotate`。要操作某台 Windows 的 GUI app、在那台起或收 windows-mcp server、設定接別台 Windows 的 MCP 時使用。
---

# windows-access

Windows-MCP 要跑在 Windows 使用者登入的桌面 session 裡，才操作得到眼前這個桌面。

先看 agent 在哪：

- **同一台**（那台 WSL 裡的 Claude Code、Codex）→ 直接用 skillshare `mcp.yaml` 裡的 `windows-mcp`（stdio，client 用時才帶起來）。不起 HTTP server、不用 key、不用連線。
- **別台，ssh 得到那台**（tailnet 內）→ [別台的 agent](#別台的-agent)。
- **別台，ssh 不到**（agent 在 tailnet 外，要開 Funnel、quick tunnel）→ 照 [reference.md〈ssh 不到那台：手動起 server〉](reference.md#ssh-不到那台手動起-server)。

server 本身的坑（400、307、session）看 [reference.md](reference.md)；連線的坑看 `remote-access` 的 reference.md。

## 第一次安裝

Windows-MCP 是第三方開源專案（[CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP)），工具清單和選項以它的 README 為準。安裝交給使用者：裝了 dotfiles 的 Windows 主機在 PowerShell 打 `tools` 勾 windows-mcp 再 apply（mise 裝）；沒裝 dotfiles 的照 Windows-MCP 的 README 裝。CLI 先找 mise 的 shim `%LOCALAPPDATA%\mise\shims\windows-mcp.exe`、再找 PATH。

完成條件：使用者在新開的 PowerShell 跑 `windows-mcp --help` 有輸出。

只用需要時才開的方式。`windows-mcp install` 會建登入時自動啟動的 scheduled task，這裡用不到。

## 別台的 agent

在 agent 這台照 `remote-access`〈服務定義（up／ps／down）〉跑 CLI。那台 Windows 只要有 windows-mcp、ssh、tailscale，不用有 skill 目錄。服務名是 `windows-mcp`；先問使用者的情況（第一次 `--create-task`、客戶機器）和報錯怎麼處理都在那裡。這支只補 windows-mcp 自己的：

- **key**：agent 這台第一次用先跑 `remote-access key init`，再開新的 session（key 在 `~/.config/windows-mcp/auth.env`，shell 啟動時讀進環境變數）。key 由 CLI 產生、經 sftp 送過去，你和使用者都不用看到或搬它。客戶機器用另一個變數（`--key-env`），不跟自己的機器共用。
- **起好之後**：在 session 裡打 `/mcp` 重連 `up` 印的 MCP 名稱，先跑 `tools/list` 和 `Screenshot`。印的是 `mcp.yaml 沒有網址是 … 的條目` 時，照它說的用 `skillshare mcp add` 加一筆（以機器命名，例如 `windows-mcp-laptop`），sync 後重開 session。
- **同時接幾台都可以**，每台一筆 MCP，`remote-access ps` 看接著哪幾台。
- **key 要作廢**（用聊天訊息交過、懷疑外洩）：`remote-access key rotate`。
- **`找不到 windows-mcp`**：照〈第一次安裝〉。

### 客戶端設定

- **MCP 設定每台一筆**，在 `mcp.yaml`（例如 `windows-mcp-desktop`、`windows-mcp-laptop`），網址是那台的 ts.net、key 用 `fromEnv`。session 開始時就要有這筆設定和環境變數；session 中途只跑 `up`，起好後 `/mcp` 重連。
- **換 key 要重開 session**：client 只在啟動時讀環境變數。
- **收舊設定**：之前用 `claude mcp add` 加過的 local scope 設定（key 原文在裡面），等新的那筆驗證過（`/mcp` 看得到 tools）後，用 `claude mcp remove <名字> -s local` 收掉，再 `remote-access key rotate`。

## 操作時

- **登入、輸入帳密或驗證碼**：帳密不經過 agent，交給使用者自己在那台輸入。
- **測試開的視窗**：使用者說要關才關，裡面可能有沒存的東西。
- **`PowerShell`、`Registry`、`FileSystem` 寫入**：要使用者同意才用。

使用者在那台旁邊、或用遠端桌面看著 agent 操作時，再加：

- **輸入輪流**：同一時間只有一方動滑鼠鍵盤。使用者要動手時先停下，等使用者說好再繼續。
- **RPA 類程式在跑時**，agent 只截圖，不點擊、不打字。
- **每次都要使用者同意**：寫入外部系統（例如存檔、送單）、`PowerShell`、`FileSystem` 寫入。同意一次只算那一次。
