# windows-mcp

別台的 agent 要操作某台 Windows 的 GUI app（截圖、點擊、打字）時，它會照這個 skill 請你在那台
起 Windows-MCP 的 server、交 key，再讓它連進來：在你的 tailnet 內就直接連，在外面才開成公開網址。agent 怎麼做寫在
[`skills/windows-mcp/SKILL.md`](../../skills/windows-mcp/SKILL.md)，這份只寫你要在那台做的事。
同一台的 agent（那台 WSL 裡的 Claude Code、Codex）不走這條，直接用 `mcp.yaml` 的 `windows-mcp`。

## 開哪一種

照 dotfiles 的 [remote-access 判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)：

```
對方 agent 在你的 tailnet 內？
├─ 是 → tailnet 內：ssh 轉發或 tailscale serve，不開公網
└─ 否 → 那台 Windows 加進你的 tailnet？（WSL 裡的、Windows 原生的 tailscale 都算）
        ├─ 是 → Funnel
        └─ 否（別人的機器、臨時借用）→ quick tunnel：你在那台 PowerShell 貼幾行
```

有沒有 WSL 不影響走哪條，只影響誰動手：那台有 WSL 時 agent 在 WSL 跑腳本起 server，你只要交 key；
沒有 WSL 時你在那台 PowerShell 貼——起 server、收掉跟下面 quick tunnel 那兩段一樣，只是 Funnel、
tailscale serve 要把第一、二行的 `127.0.0.1` 換成 `0.0.0.0`（agent 會講），再貼 agent 給你的那行開網址的指令。

兩種差在哪（網址固不固定、SSE、並行上限）見 [比較表](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#比較表)。
Windows-MCP 回應可能用 SSE，quick tunnel 不支援 SSE：走 quick tunnel 時某個操作卡住或斷線，先懷疑這個。

server 一定要在你登入的桌面起：你在那台桌面開 PowerShell（或 WSL）跑；agent 只連得到 ssh 時，
它會請你核准用一個暫時的 scheduled task 在你的桌面起，用完刪掉。從 ssh 直接起的沒有桌面，一啟動就結束。

## 第一次：在那台裝 Windows-MCP

```powershell
winget install --exact --id Python.Python.3.14 --scope user
winget install --exact --id astral-sh.uv
# 重開 PowerShell
uv tool install --python 3.14 windows-mcp
uv tool update-shell
```

重開的 PowerShell 跑 `windows-mcp --help` 有輸出就好。走 quick tunnel 的再裝 cloudflared
（[remote-access 的 Cloudflare quick tunnel](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#cloudflare-quick-tunnel)）。
winget 裝完，當下的 PowerShell 找不到 `cloudflared`：重開 PowerShell，或用完整路徑
`& 'C:\Program Files (x86)\cloudflared\cloudflared.exe'`。

## quick tunnel：你要貼的

1. **起 server、換 key**：那台 PowerShell 依序貼上。最後一行把 key 複製到剪貼簿，不會印在畫面上。
   上一輪的 server 還開著的話先照〈用完收掉〉收：server 跑著時換 key 不生效，舊 key 照樣能用。

   ```powershell
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   Start-Process -WindowStyle Minimized windows-mcp -ArgumentList 'serve'
   (Select-String "$HOME\.windows-mcp\config.toml" -Pattern 'auth_key\s*=\s*"([^"]+)"').Matches.Groups[1].Value | Set-Clipboard
   ```

2. **交 key**：把剪貼簿的 key 交給對方 agent，最好設成它的環境變數 `WINDOWS_MCP_AUTH_KEY`。
   別用記事本開 `config.toml` 看 key：開在畫面上會被 agent 的截圖拍進去。
3. **開公開網址**：另開一個 PowerShell，貼 agent 給你的那行 quick tunnel 指令（轉 `127.0.0.1:8000`、
   `Host` 改寫成 `localhost`，server 就不用開防火牆 inbound）。開著別關，把輸出裡
   `https://<隨機>.trycloudflare.com` 那行給 agent。agent 從它那邊驗：不帶 key 要 `401`、帶 key 要 `200`。

## quick tunnel：用完收掉

1. 在 quick tunnel 那個視窗按 Ctrl+C。
2. 同一個視窗貼上：停掉還在的 cloudflared、停 server、換 key、確認。先停 server 再換 key：
   server 跑著時換的 key 不生效，交出去的那把照樣能用。

   ```powershell
   Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count
   (Get-Process cloudflared -ErrorAction SilentlyContinue | Measure-Object).Count
   ```

   最後兩行都印 `0` 才算收乾淨（第一行會停掉所有 cloudflared，有開別的先跟 agent 說）。
   agent 會再從它那邊確認網址連不上（Cloudflare 回 `530`）。只按 Ctrl+C 不夠保險：
   叫 cloudflared 的那一端斷掉時，`cloudflared.exe` 可能還在跑，網址照樣通。

## Funnel、tailnet 內：你要做的

那台有 WSL 時，agent 在那台 WSL 跑腳本起 server、開網址、驗證，key 會複製到那台的剪貼簿。你只要：

1. 把剪貼簿的 key 交給對方 agent（同上）。
2. 用完跟 agent 說收掉。它會撤掉網址、停 server、換 key，並從公網確認網址連不上。

沒有 WSL、Funnel 是你在 PowerShell 開的：用完在那個視窗按 Ctrl+C，再貼
`Get-Process tailscale -ErrorAction SilentlyContinue | Stop-Process -Force`（只停 `tailscale` 指令本身，
不會斷你的 tailscale 連線）。實測過只按 Ctrl+C、或斷掉 ssh 時 `tailscale.exe` 還在，網址照樣通，
`tailscale funnel status` 卻顯示 `No serve config`。

沒有 WSL 時照上面〈開哪一種〉最後那段自己貼。tailnet 內走 ssh 轉發時，server 留在 `127.0.0.1`，
由對方 agent 那台開 ssh 轉發，不用開任何網址。

## 測過什麼

| 項目 | 狀態 |
|---|---|
| quick tunnel：不帶 key `401`；帶 key 時 `initialize` `200`（`text/event-stream`、回 `mcp-session-id`）、`notifications/initialized` `202`、`tools/list` `200`（SSE，21 個 tool，23615 bytes）、`Snapshot` `200` | 2026-11-05 在 henry-laptop 實測（cloudflared 2026.10.7，server 綁 `127.0.0.1`、`--http-host-header localhost`） |
| quick tunnel 收掉：停掉呼叫端後 `cloudflared.exe` 還在，要 `Stop-Process`；停後公網回 `530` | 2026-11-05 在 henry-laptop 實測 |
| 長時間開著的 SSE stream 經 quick tunnel | 未實測（單次請求的 SSE 回應收得到） |
| Windows 原生 tailscale 開 Funnel：不帶 key `401`、帶 key `200` | 2026-11-05 在 henry-laptop 實測（server 綁 `0.0.0.0`，用 Interactive scheduled task 在桌面起；從 ssh 前景跑 `tailscale funnel --https=8443 8000`；用公開 DNS 查到的 IP 加 `--resolve` 打） |
| Funnel 收掉：停掉呼叫端後 `tailscale.exe` 還在、公網仍 `401`，`funnel status` 卻是 `No serve config`；`Get-Process tailscale \| Stop-Process` 後公網 `000` | 2026-11-05 在 henry-laptop 實測 |
| 從 WSL 跑 `expose-port-funnel` 整條（`TAILSCALE='powershell.exe …'`） | 未實測（上面是直接在 Windows 跑 tailscale） |
| server 跑著時 `auth --force` 換 key | 2026-11-05 實測：舊 key 仍回 `200`，要先停 server 再換 |
| 收掉時 `Stop-Process` 停得掉 server | 2026-11-05 在 henry-laptop 實測：聽 8000 的數變 `0` |
| 用新 key 重起的 server 拒絕舊 key | 未實測 |
| server 從 ssh session 起 | 2026-11-05 實測起不來：`No active interactive desktop`，要在桌面起（終端機或 Interactive scheduled task） |
| `auth --force` 每次寫入新 key | 2026-11-05 實測：config 的 key 雜湊每跑一次就不同 |
| tailnet 內（ssh 轉發、tailscale serve） | 未實測 |

server 本身的坑（`/mcp/` 307、log 在哪、`Host` 檢查、session 順序）見
[`skills/windows-mcp/reference.md`](../../skills/windows-mcp/reference.md)。
