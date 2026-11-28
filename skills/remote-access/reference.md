# remote-access reference

`remote-access up` 失敗、公網驗證沒過、或連得上但 app 回錯誤時才讀。坑照原因分層：先看經過代理的（每種方式都會遇到），再看 Funnel、quick tunnel 各自專屬的。app 本身的坑看 app 自己的文件（例如 windows-access 的 reference.md）。

## 經過本機代理或 tunnel（Funnel、quick tunnel）

- **`Host` 是公開網址**：代理預設把對外網址當成 `Host` 轉進來。app 綁 loopback 又檢查 `Host` 時會回 400（windows-mcp 是 Invalid host header）。解法二選一：app 綁 `0.0.0.0`（Funnel 只能這樣做），或讓代理改寫成 `localhost`（cloudflared 用 `--http-host-header localhost`）。
- **用來源 IP 擋人的設定不能用**：請求是代理從 127.0.0.1 轉進來的。uvicorn 這類 server 預設信任 127.0.0.1 帶的 `X-Forwarded-For`，會把來源 IP 改成真正的外部 IP；allowlist 填 `127.0.0.1` 就會連代理的請求一起擋掉（windows-mcp 的 `--ip-allowlist` 回 `403 … not in the IP allowlist`）。
- **app 綁 `0.0.0.0` 時**，區網直連那個 port 只靠防火牆擋。開之前確認沒有放行它的 inbound 規則。

## `up` 的錯誤訊息

起了一半的東西 `up` 已經收掉，照訊息處理：

| 訊息 | 代表什麼、怎麼做 |
|---|---|
| `沒有人登入桌面` | 服務要桌面 session。請使用者登入那台桌面（ssh 的那個帳號）再跑 |
| `HostName 要是 ts.net 名稱` | serve 網址從 ssh config 的 HostName 來。ssh config 由 dotfiles 管，回報使用者改；serve 真的連不到才在 `hosts.<host>` 改 `mode: forward` |
| `還沒有常駐 task` | 照 SKILL.md〈服務定義〉第 1 步問，說好再加 `--create-task` |
| `task 由服務的 skill 建` | 沒有 key 的服務（browser）不建 task。照服務的 skill 問使用者、建好再跑 `up` |
| `被別的程式佔著` | 照[本機 port 總表](SKILL.md#本機-port-總表)回報，不換 port、不停別人的程式。browser 會附上佔著的那支 Chrome 回的 User-Agent（常是別台的 `ssh -R`），一起回報 |
| `接到的不是 <host> 那支` | 轉發開了，但這台 `local_port` 接到的跟那台自己的 `same_as_host` 欄位不一樣，也就是接到別支 Chrome。轉發已收掉；把印出的 User-Agent 回報使用者，不換 port |
| `比對不了` | 那台查不到自己的值（ssh 斷、逾時），不代表接錯。轉發留著；確認 `ssh <host>` 正常後重跑 `up`，不用了就 `down` |
| `開著但沒開 9222` | 那台 `chrome-agent` profile 的 Chrome 開著但沒帶 debug port，`schtasks /run` 會被轉給它。請使用者關掉那個視窗再 `up` |
| `已經有別的 tailscale serve 設定` | 那台的 serve 有別人的設定，回報使用者，不要蓋掉 |
| `ssh … 跑 PowerShell 沒有回應` | 先確認 `ssh <host>` 連得上、那台是 Windows |
| `驗證沒過`、`起不來` | 看下面〈serve 模式〉和服務 skill 的 reference.md |

## serve 模式（`remote-access up`／`down`）

查證日期 2026-11-27，看的是 Windows-MCP `main`（commit `ccbe664`，鎖 fastmcp 4.2.5、uvicorn 0.54.0）的原始碼。

- **windows-mcp 只在直接連線來自 `127.0.0.1`／`::1` 時才信 `X-Forwarded-For`**：
  - windows-mcp 的 `IPAllowlistMiddleware` 看的是 ASGI 的 `request.client`（[security.py](https://github.com/CursorTouch/Windows-MCP/blob/ccbe664616e3ce62dc65b3bf98fd0a6b2e12c63e/src/windows_mcp/infrastructure/security.py#L266-L293)）。
  - fastmcp 建 `uvicorn.Config` 時沒改 proxy 設定（fastmcp-slim 4.2.5 的 `server/mixins/transport.py`）。
  - 所以用 uvicorn 的預設：`proxy_headers=True`，`forwarded_allow_ips` 取環境變數 `FORWARDED_ALLOW_IPS`，沒設時是 `127.0.0.1,::1`（uvicorn 0.54.0 的 `config.py`、`middleware/proxy_headers.py`）。只有直接連線來自這兩個位址時，才用 `X-Forwarded-For` 改寫 `request.client`。
  - 影響：`tailscale serve` 從 127.0.0.1 轉進來，帶呼叫端的 tailnet IP，所以 allowlist 要填 agent 機器的 tailnet IP（#137 prototype 看到的 `100.100.7.68` 就是這樣來的）。區網直連 8000 的人來源不是 loopback，偽造 `X-Forwarded-For` 沒用，繞不過 allowlist。
  - 前提：那台沒把 `FORWARDED_ALLOW_IPS` 設成 `*`。那台本機的程式本來就能從 127.0.0.1 偽造，allowlist 擋不了它們，只能靠 key 擋。
- **`--config FILE` 可以放 key**：
  - `serve --config <檔案>` 讀 TOML，支援 `[server]` 的 `transport`、`host`、`port`、`auth_key`，和 `[security]` 的 `ip_allowlist`（[config.py](https://github.com/CursorTouch/Windows-MCP/blob/ccbe664616e3ce62dc65b3bf98fd0a6b2e12c63e/src/windows_mcp/infrastructure/config.py)）。
  - 指令列參數和環境變數優先，都沒給才用設定檔（`__main__.py` 的 `_choose_value`、`_param_explicit`）。所以那台的使用者環境變數裡有 `WINDOWS_MCP_AUTH_KEY` 或 `WINDOWS_MCP_IP_ALLOWLIST` 時，會蓋過設定檔：key 不對時 `up` 驗證會失敗並收掉；allowlist 被蓋掉驗證不一定看得出來，那台不要設這兩個變數。
  - 所以不用包裝腳本：`up` 經 sftp 把 key 放到那台的 `~\.windows-mcp\remote-access.key`，PowerShell 讀完就刪、寫進 `~\.windows-mcp\remote-access.toml`，task 的參數只有 `serve --config <那個檔>`；`down` 會刪掉這個檔。
- **不加 `--allow-insecure-remote`**：
  - prototype 有加。照 `__main__.py`，有 `auth_key` 時綁 `0.0.0.0` 本來就不會被拒絕。
  - `0.0.0.0` 也不做 Host 檢查，加不加行為一樣。
  - 只在實機驗收時確認。
- **key 走 sftp，不走 PowerShell 的 stdin**（2026-11-27 henry-desktop 實測）：
  - `ssh <host> powershell -EncodedCommand …` 讀 `[Console]::In.ReadLine()`，8 次裡有 2 次一直收不到、卡到逾時，長短腳本都會。
  - 改成 `sftp -b -` 把 key 放到那台的 `~\.windows-mcp\remote-access.key`，同一台連傳 5 次都成功。那台的 sshd 要開 sftp subsystem（Windows OpenSSH 預設有）。
- **mise shim 起的 windows-mcp 有 4 層行程**（shim → python → python → 聽 port 的 python）：只殺聽 port 的那個，port 可能還被佔著。`down` 會把命令列帶 `remote-access.toml` 的行程都收掉。
- **常駐 task 不再用時手動刪**：`keep: true` 的 task 在 `down` 之後也留著（在那台的「工作排程器」根目錄看得到 `remote-access-windows-mcp`）。
  先 `remote-access down`，再在那台跑 `Unregister-ScheduledTask -TaskName remote-access-windows-mcp -Confirm:$false`；之後要再用就重新 `up --create-task`。

## Funnel 專屬

- **只能用 443、8443、10000**（[官方文件](https://tailscale.com/docs/features/tailscale-funnel)）。443 常被其他 `tailscale serve` 佔用，所以預設 8443。
- **開不起來**：tailnet 要開 MagicDNS 和 HTTPS 憑證，policy 要有 `funnel` node attribute。細節看 dotfiles remote-access 的 [Tailscale Funnel](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md#tailscale-funnel)。
- **剛開時公開 DNS 查不到 ts.net 名稱**：2026-11-05 在 henry-laptop 實測，開 Funnel 後立刻查公開 DNS 是查無此名，之後才查得到。`remote-access funnel open` 會每隔幾秒重查，最多約 60 秒；一直查不到就撤掉 Funnel、exit 1。
- **在本機驗不到 Funnel**：在 tailnet 內的機器查 ts.net 名稱會拿到 tailnet IP，連線會逾時。要用公開 DNS 查到的 IP 加 `curl --resolve`，`remote-access funnel open` 已經這樣做。手動驗（那台沒有腳本時）：

  ```bash
  host=<機器>.<tailnet>.ts.net port=<對外 port>
  ip=$(curl -s "https://cloudflare-dns.com/dns-query?name=$host&type=A" -H 'accept: application/dns-json' \
    | python3 -c 'import sys,json;print([a["data"] for a in json.load(sys.stdin)["Answer"] if a["type"]==1][-1])')
  curl -s -m 30 -o /dev/null -w '%{http_code}\n' --resolve "$host:$port:$ip" <app 要的參數> "https://$host:$port<路徑>"
  # 帶驗證那次加 -H "Authorization: …"
  ```

  完成條件跟腳本一樣：不帶驗證、帶驗證各回 app 給的碼。剛開的前幾秒可能還不通，隔幾秒重打。
- **收掉後還在**（`remote-access funnel` 印 `還沒收乾淨`，或手動收完公網還回 `401`）：2026-11-05 在 henry-laptop 實測，Windows 原生 tailscale 從 ssh 前景跑 `tailscale funnel --https=8443 8000`，停掉 ssh 那端後：
  - Windows 上的 `tailscale.exe`（`C:\Program Files\Tailscale\tailscale.exe`）還在跑，公網照樣回 `401`。
  - 同時 `tailscale funnel status` 印 `# Funnel on:` 後接 `No serve config`：前景 Funnel 不會列成 serve config，數 status 的條數會誤判成 0 條。
  - `Get-Process tailscale | Stop-Process` 後公網變 `000`，status 仍是 `No serve config`。

  所以收的判準看行程數和公網，不看 status。腳本收的時候會停掉那個 port 的 `tailscale funnel` 行程（`TAILSCALE` 是 `powershell.exe …` 或 `.exe` 時從 PowerShell 用 `Get-CimInstance Win32_Process` 對命令列停），停不掉就印 `還沒收乾淨`、exit 1。這時在那台手動停：Windows 跑 `Get-Process tailscale | Stop-Process -Force`，Linux 跑 `pkill -f 'tailscale funnel --https=<port>'`（沒設 operator 加 sudo），再跑 `remote-access funnel check-closed --url https://<機器>.<tailnet>.ts.net:<port>`。`--bg` 留下的設定才會列在 status，`close` 會再 `off` 一次。
  從 WSL 用 `TAILSCALE='powershell.exe … tailscale'` 跑腳本整條（開、驗、SIGTERM 收）**未實測**：2026-11-05 那輪是直接在 Windows 跑 tailscale；腳本從 PowerShell 停 `tailscale.exe` 這段只在假指令的測試裡驗過。

## quick tunnel 專屬

- **連得上、一般請求 200，但某個操作卡住或斷線**：先懷疑 SSE（quick tunnel 的四項限制在 [SKILL.md〈quick tunnel〉](SKILL.md#quick-tunnel)）。2026-11-05 在 henry-laptop 實測，單次請求用 SSE 回的收得到（MCP `initialize` 回 `text/event-stream`、`tools/list` 23615 bytes 都完整）；長時間開著的 SSE stream 會怎麼壞**未實測**。卡住的是這種時改走 Funnel。
- **不帶驗證回 `400`**：Host 沒對好。app 綁 loopback 又檢查 `Host` 時要 `--host-header localhost`（cloudflared 的 `--http-host-header localhost`）。
- **不帶驗證回 `5xx`**：多半是 cloudflared 接到了、app 沒在那個 port 聽（cloudflared 的 log 會有 origin 連不上的錯誤）。回 app 的文件確認 server 起了、port 對。
- **剛印出網址時連不上**：網址要幾秒才生效。腳本用公開 DNS 查到的 IP 加 `--resolve` 重打，避開本機 DNS 把剛查不到的名稱快取起來。手動打時隔幾秒重試。
- **cloudflared 沒印出網址就結束**：腳本會印 cloudflared 最後幾行。照那幾行查；連不到 Cloudflare（網路擋 outbound）時就是在這裡停住。
- **收掉後還有 cloudflared**：2026-11-05 在 henry-laptop 實測，停掉叫 cloudflared 的那一端（ssh）後，Windows 上的 `cloudflared.exe` 還在、公網照樣通；`Stop-Process` 後公網回 `530`。`remote-access quick-tunnel close --port <port> [--url <網址>]` 停掉轉那個 port 的 quick tunnel，只認命令列是 `cloudflared tunnel … --url http://127.0.0.1:<port>`（或 `localhost`）的行程，別的 tunnel 不動；`CLOUDFLARED` 叫 Windows 的時候也從 PowerShell 停 `cloudflared.exe`。開在別台的，請使用者在那台 `Get-Process cloudflared | Stop-Process -Force`，再從這邊 `check-closed --url`。
- **winget 裝完找不到 `cloudflared`**：當下那個 PowerShell 的 PATH 不會更新。用完整路徑 `C:\Program Files (x86)\cloudflared\cloudflared.exe`，或重開 PowerShell。
