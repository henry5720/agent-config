---
name: remote-access
description: 連線：agent 跟服務不在同一台時怎麼連過去。同一台直接連；tailnet 內用 ssh `-L`／`-R`、tailscale serve；tailnet 外用 Funnel、quick tunnel 開公開網址（開、從公網驗證、收）。要連別台的服務、把這台的 port 借給別台、開給 tailnet 外、挑本機轉發的 port、收掉公開網址時使用。
---

# remote-access

服務和連線分兩層。服務（瀏覽器、Windows-MCP、ttyd…）由各自的 skill 起、收、帶驗證；這支只管連過去，跟服務是什麼無關。給人看的情境和理由在 dotfiles 的 [remote-access](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md)。

## 判準

先看連的那一方（人或 agent）跟服務的位置，照順序第一個符合的就是：

1. 跟服務在同一台 → [同一台](#同一台)
2. 在使用者的 tailnet 內 → [tailnet 內](#tailnet-內)，不開公網
3. 在 tailnet 外 → [tailnet 外](#tailnet-外)：開出去的那台**跑得到登入使用者 tailnet 的 tailscale** → [Funnel](#funnel)；那台不加進使用者的 tailnet（別人的機器、臨時借用）→ [quick tunnel](#quick-tunnel)。差異看 [比較表](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md#比較表)。

你自己就跑在服務那台 Windows（原生 Windows，不經 WSL）時，選完照 [agent 就在那台 Windows](#agent-就在那台-windows) 做。

## 本機 port 總表

挑轉發的本機 port 照這張，不另外挑；要新的 port 先加進這張。

| port | 服務 | 起、收照哪裡 | 開到 tailnet 外 |
|---|---|---|---|
| 9222 | Chrome 的 CDP（agent 的 headless 或使用者的獨立 profile），chrome-devtools MCP 寫死連它 | `browser-access` skill | 不行，沒有驗證 |
| 9377 | `playwright-cli show` 的畫面（看 agent 的瀏覽器、接手） | `browser-access` skill | 不行，沒有驗證 |
| 9555 | Playwright 插件的 relay（接使用者日常的 Chrome） | `browser-access` skill（`playwright-extension-attach`） | 只經 `playwright-extension-attach --tunnel` |
| 1080 | 反向 SOCKS（`ssh -R`，借使用者的網路） | `browser-access` skill | 不行，沒有驗證 |
| 7681 | ttyd 網頁 shell | dotfiles 的 [ttyd-serve](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/ttyd-serve.md) | 可以，ttyd 帶隨機密碼 |
| 8000→18000 | Windows-MCP 的 HTTP server：那台 Windows 聽 8000，agent 這台用 18000 接 | `windows-access` skill | 可以，帶 Bearer key |

8000→18000：agent 那台在 WSL mirrored networking 下，自己的 8000 可能被自己的 windows-mcp 佔走，所以本機用 18000。要同時接第二台時用 18001。

**port 被佔就回報，不換 port。** 換了會接到錯的 server，或跟寫死 port 的 MCP 設定對不上。用 `ss -ltnp | grep <port>` 找出是誰（Windows 用 `Get-NetTCPConnection -State Listen -LocalPort <port> -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_.OwningProcess }`，沒印東西就是沒人在聽），告訴使用者，由他決定。

## 同一台

直接連 `127.0.0.1:<port>`，不開轉發、不開公網。WSL 開 mirrored networking 時跟它的 Windows 共用 port，也算同一台。服務有不用網路的接法（例如 Windows-MCP 的 stdio）時照服務的 skill 用那條。

完成條件：在連的那一端 `curl -sI http://127.0.0.1:<port>` 有回應（或服務 skill 寫的驗證通過）。

## tailnet 內

一行指令，照打，不包 script。`<host>` 是 ssh config 裡那台的 Host（例如 `company-ec2`）：

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:<本機 port>:127.0.0.1:<那台 port> <host>   # 把那台的服務拉到這台
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:<那台 port>:127.0.0.1:<這台 port> <host>   # 把這台的服務借給那台
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:1080 <host>                                # 反向 SOCKS：那台借這台的網路
tailscale serve --bg --https=443 <port>                                                    # tailnet 內帶憑證的 https://<機器>.<tailnet>.ts.net
```

- **ssh 轉發是預設。** 2026-11-11 起 company-ec2 的 agent 用 `ssh -L` 接別台 Windows 的 Windows-MCP（本機 18000 → 那台 8000），是最常用的一條。
- **兩端都綁 `127.0.0.1`。** 被轉發的服務多半沒有驗證，綁 `0.0.0.0` 等於開給整個網路。
- **你自己跑 ssh 時背景跑**（Claude Code 的 Bash `run_in_background`），用完停掉它。要使用者在他那台跑時，把指令交給他，請他開著別關。
- **tailscale serve** 在 ssh 不到那台時用。它不改寫 `Host`，服務綁 loopback 又檢查 `Host` 時要改綁 `0.0.0.0`，並確認防火牆沒放行那個 port 的 inbound。listener 不能跟服務同一個 port（WSL mirrored 下會互搶）。收：`tailscale serve --https=443 off`，`tailscale serve status` 沒有那個 port 才算收掉。

完成條件：ssh 停著沒印錯誤，在連的那一端 `curl -sI http://127.0.0.1:<port>`（serve 是那個 ts.net 網址）有回應，或服務 skill 寫的驗證通過。`Address already in use`、`remote port forwarding failed` 是 port 被佔，照[本機 port 總表](#本機-port-總表)回報；其他連不上照 dotfiles 的 [ssh 轉發連不上](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md#ssh-轉發連不上) 查。

## tailnet 外

公開網址誰拿到都能連，擋陌生人的只剩 app 自己的驗證。所以只開**有驗證的 app**（[本機 port 總表](#本機-port-總表)最後一欄），交出網址前從公網確認「不帶驗證被拒、帶了通過」，用完一定收掉。

### 跟 app 要的輸入

叫這支的 app skill（例如 windows-access）要給齊，缺一項就回去問 app 的文件或使用者：

| 輸入 | 例子（windows-access） |
|---|---|
| 本機 port | `8000` |
| app 對 `Host` 的要求 | 綁 loopback 時只接受 `localhost` |
| 驗證打哪個路徑、帶什麼請求 | `/mcp`，POST MCP `initialize` |
| 不帶驗證、帶驗證各要回什麼 | `401`、`200` |
| 怎麼拿驗證 header | 一支印出 `Authorization: Bearer <key>` 的指令（[agent 就在那台 Windows](#agent-就在那台-windows) 時是一段 PowerShell） |

驗證 header 由指令印出、腳本自己讀，你不用也不要看到 key。

### Funnel

腳本：`~/.claude/skills/remote-access/scripts/remote-access funnel`（`remote-access funnel --help` 看參數）。它照[共通規則](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md#共通規則)前景跑：不加 `--bg`，停著直到收到 Ctrl+C／SIGTERM 才撤掉 Funnel。

**收乾淨的判準**（這支和下面手動的做法都一樣）：那個對外 port 的 tailscale CLI 行程剩 0 個，**而且**從公網打公開網址連不上（`000`，或公開 DNS 查不到）。`tailscale funnel status` 不算數：前景 Funnel 不會列成 serve config，印 `No serve config` 時公網照樣回 `401`（2026-11-05 在 henry-laptop 實測）。停掉叫 tailscale 的那一端（ssh、WSL 的 `powershell.exe`）也不會停掉 Windows 上的 `tailscale.exe`，口子會一直開著。

1. **對好 `Host`**：Funnel 不能改寫 `Host`，轉進來的 `Host` 是公開網址。app 綁 loopback 又檢查 `Host` 時，請 app 改綁 `0.0.0.0`，並確認防火牆沒放行那個 port 的 inbound（不然區網能直連）。
   完成條件：app 綁的位址接受公開網址當 `Host`。
2. **挑對外 port**：只能用 `443`、`8443`、`10000`，預設 `8443`。`tailscale funnel status` 只看得到 `--bg` 留下的設定，看不到別人前景開著的；腳本開之前會再查那個 port 的 tailscale 行程和公網，有人在用就拒絕。
3. **開**：背景跑（Claude Code 的 Bash `run_in_background`）：

   ```bash
   ~/.claude/skills/remote-access/scripts/remote-access funnel open --port <app port> --https <對外 port> --path <路徑> \
     --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' \
     -- <兩次驗證都帶的 curl 參數，例如 -X POST -H … -d …>
   ```

   tailscale 不在這台的 PATH 上、或要叫別台的（例如 WSL 叫 Windows 那邊的），用環境變數 `TAILSCALE` 給整條指令。沒設時腳本自己判斷要不要 sudo。
   完成條件：輸出出現 `公網驗證：不帶驗證=<碼>（要 <碼>），帶驗證=<碼>（要 <碼>）` 兩邊相符，接著 `公開網址：https://…`。驗證沒過時腳本已經撤掉 Funnel、exit 1；照 [reference.md](reference.md) 查原因。
4. **交網址**：把 `公開網址` 那行交給 app skill 或使用者。驗證用的 key 由 app 自己的規則交。
5. **收掉**：用完對背景那支送 SIGTERM（`TaskStop`、`kill -TERM <pid>`）。它停掉 tailscale CLI（`TAILSCALE` 叫 Windows 的時候從 PowerShell 停 `tailscale.exe`），再從公網確認連不上。
   完成條件：輸出有 `tailscale funnel :<port> 的行程剩 0 個（要 0）`、`公網 https://…：000`，最後是 `Funnel :<port> 已收乾淨`。印 `還沒收乾淨` 時照 [reference.md](reference.md)〈收掉後還在〉處理。接著由 app 停掉它的 server（app 的文件寫怎麼確認沒有程式在聽那個 port）。背景那支已經不在（session 斷過、被 SIGKILL）時，跑 `~/.claude/skills/remote-access/scripts/remote-access funnel close --https <對外 port>`，完成條件相同。

#### 那台沒有這支腳本

開出去的那台沒有 skillshare（或沒有 WSL 的 Windows）時，第 1、2 步照上面做，第 3 步改成請使用者在那台開一個終端機（Windows 用 PowerShell）貼上，開著別關：

```bash
tailscale funnel --https=<對外 port> <app port>    # Linux 沒設 operator 要加 sudo；不加 --bg
```

1. **開**：完成條件：使用者說貼了、視窗停著沒有回到提示字元（印出網址或要你開權限的 admin console 連結都算開著；後者先請使用者開好權限再貼一次）。
2. **驗**：從你這邊跑：

   ```bash
   ~/.claude/skills/remote-access/scripts/remote-access funnel verify --url https://<那台的機器名>.<tailnet>.ts.net:<對外 port> --path <路徑> \
     --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' -- <curl 參數>
   ```

   完成條件：輸出出現 `公網驗證：…` 兩邊相符，接著 `公開網址：https://…`。沒過就照第 3 步收掉，再照 reference.md 查原因。
3. **交網址、收掉**：交網址同上面第 4 步。用完請使用者在那個視窗按 Ctrl+C，再貼下面這行（Windows PowerShell；Linux 用 `pgrep -fc 'tailscale funnel'`）：

   ```powershell
   Get-Process tailscale -ErrorAction SilentlyContinue | Stop-Process -Force; (Get-Process tailscale -ErrorAction SilentlyContinue | Measure-Object).Count
   ```

   `tailscale` 這個名字只對到 CLI 的 `tailscale.exe`，不會停掉 tailscale 本身（`tailscaled`、`tailscale-ipn`）。接著從你這邊跑 `remote-access funnel check-closed --url https://<機器名>.<tailnet>.ts.net:<對外 port>`。
   完成條件：使用者那行印 `0`，`check-closed` exit 0（印出 `000` 或公開 DNS 查不到）。再由 app 停掉它的 server。

### quick tunnel

腳本：`~/.claude/skills/remote-access/scripts/remote-access quick-tunnel`（`remote-access quick-tunnel --help` 看參數）。cloudflared 給一個 `https://<隨機>.trycloudflare.com`，不用 Cloudflare 帳號，轉進 app 的 `127.0.0.1:<port>`。

開之前對一次 app 的需求和這四項限制（[Cloudflare 官方文件](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)），app 撐不住就停下來回報使用者：

- **不支援 SSE**：app 靠 SSE 推資料時可能會壞。2026-11-05 在 henry-laptop 實測，單次請求用 SSE 回的（MCP `initialize`、`tools/list`）收得到；長時間開著的 SSE stream **未實測**。
- **每條最多 200 個並行請求**，超過的回 `429`。
- **網址每次都變**：每開一次是新網址，重開就要重交。
- **官方只給測試、開發用**：用完就收，不長駐。

1. **對好 `Host`**：app 綁 loopback 又檢查 `Host` 時，帶 `--host-header localhost`（cloudflared 的 `--http-host-header`）。app 留在 loopback，不用放行防火牆 inbound。
   完成條件：決定好帶不帶 `--host-header`、帶什麼值。
2. **開**：看 cloudflared 跑在哪台。
   - **這台**（`cloudflared --version` 有輸出）：背景跑（Claude Code 的 Bash `run_in_background`）：

     ```bash
     ~/.claude/skills/remote-access/scripts/remote-access quick-tunnel open --port <app port> [--host-header localhost] --path <路徑> \
       --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' \
       -- <兩次驗證都帶的 curl 參數>
     ```

   - **那台沒有這支腳本**（例如別人的 Windows）：請使用者在那台 PowerShell 貼上，開著別關。沒裝 cloudflared 先跑 `winget install --exact --id Cloudflare.cloudflared`。裝完當下的 PowerShell 找不到 `cloudflared`（PATH 要重開才更新），所以直接給完整路徑：

     ```powershell
     & 'C:\Program Files (x86)\cloudflared\cloudflared.exe' tunnel --url http://127.0.0.1:<app port> --http-host-header localhost   # app 不檢查 Host 就拿掉最後兩個字
     ```

     請使用者把輸出裡 `https://<隨機>.trycloudflare.com` 那行給你，從這邊驗：

     ```bash
     ~/.claude/skills/remote-access/scripts/remote-access quick-tunnel verify --url <那個網址> --path <路徑> \
       --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' -- <curl 參數>
     ```

   完成條件：輸出出現 `公網驗證：不帶驗證=<碼>（要 <碼>），帶驗證=<碼>（要 <碼>）` 兩邊相符，接著 `公開網址：https://…`。驗證沒過時 `open` 已經停掉 cloudflared、exit 1；`verify` 沒過就照第 4 步請使用者收掉。原因照 [reference.md](reference.md) 查。
3. **交網址**：把 `公開網址` 那行交給 app skill 或使用者。
4. **收掉**：
   收乾淨的判準：轉那個 port 的 cloudflared 剩 0 個，**而且**從公網打網址連不上（Cloudflare 回 `530`，或公開 DNS 查不到）。停掉叫 cloudflared 的那一端（ssh、WSL）不會停掉 Windows 上的 `cloudflared.exe`（2026-11-05 在 henry-laptop 實測），要另外停。
   - **這台**：對背景那支送 SIGTERM。它停掉 cloudflared（`CLOUDFLARED` 叫 Windows 的時候也從 PowerShell 停 `cloudflared.exe`），再從公網確認。完成條件：輸出有 `cloudflared → :<port> 剩 0 個（要 0）` 和 `公網 https://…：530`（或公開 DNS 查不到），exit 0。背景那支已經不在時，跑 `remote-access quick-tunnel close --port <app port> --url <公開網址>`，完成條件相同（沒有網址時不帶 `--url`，只確認行程數）。
   - **那台**：請使用者在 cloudflared 視窗按 Ctrl+C，再貼下面這行；接著從你這邊跑 `remote-access quick-tunnel check-closed --url <公開網址>`。

     ```powershell
     Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force; (Get-Process cloudflared -ErrorAction SilentlyContinue | Measure-Object).Count
     ```

     完成條件：印出 `0`（假設那台沒有別的 cloudflared），`check-closed` exit 0。

   接著由 app 停掉它的 server（app 的文件寫怎麼確認沒有程式在聽那個 port）。

## agent 就在那台 Windows

agent 直接跑在要開出去的那台 Windows（原生 Windows 的 Claude Code，不經 WSL）時，兩支腳本都跑不了：它們是 python3，靠 `pgrep`／`pkill`、`SIGHUP`，dotfiles 在 Windows 也不裝 Python。分支照[判準](#判準)選，各步改成 agent 用 PowerShell tool 自己跑（tailnet 內的 ssh、`tailscale serve` 在 PowerShell 照打，不用這段）。下面的 `<程式>` 是 `tailscale`（Funnel）或 `cloudflared`（quick tunnel）；日誌路徑每次都寫完整，因為 PowerShell tool 不一定在兩次呼叫間保留變數。

1. **對好 `Host`**：同各分支第 1 步。
2. **開**：先確認 `(Get-Process <程式> -ErrorAction SilentlyContinue | Measure-Object).Count` 是 `0`。不是 `0` 就是有人開著（腳本遇到這種情況會拒絕開），停下問使用者，不要硬開，第 5 步也會一起停掉它。接著背景起、輸出寫進暫存檔：

   ```powershell
   # Funnel：對外 port 照 Funnel 第 2 步挑
   Start-Process tailscale -ArgumentList 'funnel','--https=<對外 port>','<app port>' -WindowStyle Hidden -RedirectStandardOutput "$env:TEMP\remote-access.log" -RedirectStandardError "$env:TEMP\remote-access.err"
   # quick tunnel：沒裝 cloudflared 先 winget 裝（同〈那台沒有這支腳本〉那條）；app 不檢查 Host 就拿掉最後兩個參數
   Start-Process 'C:\Program Files (x86)\cloudflared\cloudflared.exe' -ArgumentList 'tunnel','--url','http://127.0.0.1:<app port>','--http-host-header','localhost' -WindowStyle Hidden -RedirectStandardOutput "$env:TEMP\remote-access.log" -RedirectStandardError "$env:TEMP\remote-access.err"
   ```

   過幾秒讀 `$env:TEMP\remote-access.log`、`$env:TEMP\remote-access.err` 找網址：Funnel 是 `https://<機器名>.<tailnet>.ts.net:<對外 port>`（印的是 admin console 連結時，請使用者開好 Funnel 權限，照第 5 步收掉再開一次），quick tunnel 是 `https://<隨機>.trycloudflare.com`。
   完成條件：拿到網址，`<程式>` 的行程數是 `1`。
3. **驗**：取代 `verify`。照腳本的做法用公開 DNS 查 IP 再 `--resolve` 過去（這台自己查 ts.net 會拿到 tailnet IP），header 寫進暫存檔用 `-H @檔案` 帶，key 不印出來、不進 curl 參數。`<印出 header 的 PowerShell>` 由 app skill 給；curl 參數裡的 JSON 寫進檔案用 `-d "@檔案"` 帶（Windows PowerShell 5.1 傳給外部程式時會吃掉參數裡的雙引號）。

   ```powershell
   $base = '<網址>'; $path = '<路徑>'
   $u = [uri]$base
   $ip = ((Invoke-RestMethod "https://cloudflare-dns.com/dns-query?name=$($u.Host)&type=A" -Headers @{accept = 'application/dns-json'} -TimeoutSec 10).Answer | Where-Object type -eq 1 | Select-Object -Last 1).data
   if (-not $ip) { 'ip=空：公開 DNS 查不到'; return }
   $probe = { param([string[]]$more) curl.exe -s -m 30 -o NUL -w '%{http_code}' --resolve "$($u.Host):$($u.Port):$ip" @more "$base$path" }
   $hdr = New-TemporaryFile
   try {
     <印出 header 的 PowerShell> | Set-Content $hdr -Encoding ascii -NoNewline
     "ip=$ip 不帶驗證=$(& $probe @(<curl 參數>)) 帶驗證=$(& $probe @(<curl 參數>, '-H', "@$hdr"))"
   } finally { Remove-Item $hdr }
   ```

   完成條件：印出 `ip=<IP>`，兩個碼都跟 app 要的一樣。印 `ip=空` 或不帶驗證的碼不對時，等幾秒重跑（剛開的網址要幾秒才通，Funnel 的公開 DNS 也會晚一點才查得到）；重跑一分鐘還不對就照第 5 步收掉，再照 [reference.md](reference.md) 查。
4. **交網址**：同各分支。
5. **收掉**：停掉 `<程式>` 再確認。`tailscale` 只對到 CLI 的 `tailscale.exe`，不會停掉 tailscale 本身；兩種都會停掉這台所有同名行程（第 2 步確認過開之前是 `0`）。

   ```powershell
   Get-Process <程式> -ErrorAction SilentlyContinue | Stop-Process -Force; (Get-Process <程式> -ErrorAction SilentlyContinue | Measure-Object).Count
   ```

   完成條件：印出 `0`，再跑一次第 3 步那段：印 `ip=空`，或不帶驗證的碼是 `000`（Funnel）／`530`（quick tunnel）。剛停掉時可能還通一下，等幾秒重跑。接著由 app 停掉它的 server。

## script 規則

改這支或替別的服務寫 script 時照這三條：

- **只包碰 key 或密碼、或收尾檢查會騙人的操作。** 例如 Funnel 收掉後 `tailscale funnel status` 照樣印 `No serve config`，所以收的判準包進 `remote-access funnel`。一行講完的指令（上面的 ssh、`tailscale serve`）寫在 skill 裡，不包。
- **名字名詞在前。** 服務或連線的名字放前面，多個動作用子命令（`remote-access funnel open`），只有一個動作就接在名字後面（`ttyd-serve`）。
- **每支都有 `--help`。**
