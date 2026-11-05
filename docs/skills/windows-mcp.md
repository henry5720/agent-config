# windows-mcp

別台的 agent 要操作某台 Windows 的 GUI app（截圖、點擊、打字）時，它會照這個 skill 請你在那台
起 Windows-MCP 的 server、交 key，再把 server 開成一個公開網址給它連。agent 怎麼做寫在
[`skills/windows-mcp/SKILL.md`](../../skills/windows-mcp/SKILL.md)，這份只寫你要在那台做的事。
同一台的 agent（那台 WSL 裡的 Claude Code、Codex）不走這條，直接用 `mcp.yaml` 的 `windows-mcp`。

## 開哪一種

照 dotfiles 的 [remote-access 判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)：

```
那台 Windows 跑得到登入你 tailnet 的 tailscale，而且有 WSL？
├─ 是 → Funnel：agent 在那台 WSL 跑腳本，你只要交 key
└─ 否（別人的機器、臨時借用）→ quick tunnel：你在那台 PowerShell 貼幾行
```

兩種差在哪（網址固不固定、SSE、並行上限）見 [比較表](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#比較表)。
Windows-MCP 回應可能用 SSE，quick tunnel 不支援 SSE：走 quick tunnel 時某個操作卡住或斷線，先懷疑這個。

## 第一次：在那台裝 Windows-MCP

```powershell
winget install --exact --id Python.Python.3.14 --scope user
winget install --exact --id astral-sh.uv
# 重開 PowerShell
uv tool install --python 3.14 windows-mcp
uv tool update-shell
```

重開的 PowerShell 跑 `windows-mcp --help` 有輸出就好。走 quick tunnel 的再裝 cloudflared
（[remote-access 的 Cloudflare quick tunnel](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#cloudflare-quick-tunnel)），
裝完重開 PowerShell。

## quick tunnel：你要貼的

1. **起 server、換 key**：那台 PowerShell 依序貼上。最後一行把 key 複製到剪貼簿，不會印在畫面上。

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
2. 同一個視窗貼上：停 server、換 key（交出去的那把作廢）、確認。

   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   windows-mcp auth --transport streamable-http --host 127.0.0.1 --port 8000 --force
   (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count
   (Get-Process cloudflared -ErrorAction SilentlyContinue | Measure-Object).Count
   ```

   最後兩行都印 `0` 才算收乾淨（第二個 `0` 假設你沒有開別的 cloudflared）。

## Funnel：你要做的

agent 在那台 WSL 跑腳本起 server、開 Funnel、驗證，key 會複製到那台的剪貼簿。你只要：

1. 把剪貼簿的 key 交給對方 agent（同上）。
2. 用完跟 agent 說收掉。它會撤掉 Funnel、停 server、換 key。

## 測過什麼

| 項目 | 狀態 |
|---|---|
| quick tunnel：不帶 key `401`；帶 key 時 `initialize`、`tools/list`、`Snapshot` 都 `200` | 2026-11-05 實測 |
| quick tunnel 收掉時 `Stop-Process` 停得掉 server | 未實測 |
| `auth --force` 換 key 後舊 key 被拒 | 未實測 |
| SSE 經 quick tunnel | 未實測 |
| Windows 原生 tailscale 開 Funnel | 未實測 |

server 本身的坑（`/mcp/` 307、log 在哪、`Host` 檢查、session 順序）見
[`skills/windows-mcp/reference.md`](../../skills/windows-mcp/reference.md)。
