---
name: remote-access
description: 連線：agent 跟服務不在同一台時怎麼連過去（同一台、tailnet 內、tailnet 外）。要連別台的服務、把這台的 port 借給別台、開給 tailnet 外、挑本機轉發的 port、收掉公開網址時使用。
---

# remote-access

服務和連線分兩層。服務（瀏覽器、Windows-MCP、ttyd…）的安裝、驗證由各自的 skill 管；這支管連過去。寫在 `services.yaml` 的服務例外，由這支的 CLI 在別台起、收、驗證。給人看的情境和理由在 dotfiles 的 [remote-access](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md)。

## 判準

先看連的那一方（人或 agent）跟服務的位置，照順序第一個符合的就是：

1. 跟服務在同一台 → [同一台](#同一台)
2. 在使用者的 tailnet 內，服務在 `services.yaml` 裡 → [服務定義（up／ps／down）](#服務定義uppsdown)
3. 在使用者的 tailnet 內，其他服務 → [tailnet 內](#tailnet-內)，不開公網
4. 在 tailnet 外 → [tailnet 外](tailnet-outside.md)：開出去的那台**跑得到登入使用者 tailnet 的 tailscale** → [Funnel](tailnet-outside.md#funnel)；那台不加進使用者的 tailnet（別人的機器、臨時借用）→ [quick tunnel](tailnet-outside.md#quick-tunnel)。差異看 [比較表](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md#比較表)。

你自己就跑在服務那台 Windows（原生 Windows，不經 WSL）時，選完照 [agent 在原生 Windows](tailnet-outside.md#agent-在原生-windows) 做。

## 本機 port 總表

挑轉發的本機 port 照這張，不另外挑；要新的 port 先加進這張。

| port | 服務 | 起、收照哪裡 | 開到 tailnet 外 |
|---|---|---|---|
| 9222 | Chrome 的 CDP（agent 的 headless 或使用者的獨立 profile），chrome-devtools MCP 寫死連它 | `browser-access` skill | 不行，沒有驗證 |
| 9377 | `playwright-cli show` 的畫面（看 agent 的瀏覽器、接手） | `browser-access` skill | 不行，沒有驗證 |
| 9555 | Playwright 插件的 relay（接使用者日常的 Chrome） | `browser-access` skill（`playwright-extension-attach`） | 只經 `playwright-extension-attach --tunnel` |
| 1080 | 反向 SOCKS（`ssh -R`，借使用者的網路） | `browser-access` skill | 不行，沒有驗證 |
| 7681 | ttyd 網頁 shell | dotfiles 的 [ttyd-serve](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/ttyd-serve.md) | 可以，ttyd 帶隨機密碼 |
| `services.yaml` 的 `local_port` | 服務定義走 forward 模式時 agent 這台接的 port（windows-mcp、browser）；serve 模式不佔本機 port | `remote-access up` | 照服務 |

服務定義的 port 以 `services.yaml` 為準，這張不抄數字。agent 那台在 WSL mirrored networking 下跟 Windows 共用 port，`local_port` 要跟服務本身的 `port` 錯開。兩台都走 forward 時，第二台在 `hosts.<host>` 另給 `local_port`。browser 的 `local_port` 跟 `port` 相同（chrome-devtools MCP 寫死 9222），同時只接一台。

**port 被佔就回報，不換 port。** 換了會接到錯的 server，或跟寫死 port 的 MCP 設定對不上。用 `ss -ltnp | grep <port>` 找出是誰（Windows 用 `Get-NetTCPConnection -State Listen -LocalPort <port> -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_.OwningProcess }`，沒印東西就是沒人在聽），告訴使用者，由他決定。

## 同一台

直接連 `127.0.0.1:<port>`，不開轉發、不開公網。WSL 開 mirrored networking 時跟它的 Windows 共用 port，也算同一台。服務有不用網路的接法（例如 Windows-MCP 的 stdio）時照服務的 skill 用那條。

完成條件：在連的那一端 `curl -sI http://127.0.0.1:<port>` 有回應（或服務 skill 寫的驗證通過）。

## 服務定義（up／ps／down）

服務寫在這支 skill 的 `services.yaml`（現在有 windows-mcp、browser）時，一律用 CLI `~/.claude/skills/remote-access/scripts/remote-access`，不手動開 ssh、serve，參數看 `remote-access <子命令> --help`。`<host>` 是 ssh config 的 Host。CLI 經 ssh 送 PowerShell 到那台做事，那台不用有 skill 目錄（沒勾 agent-config 的 Windows 也行）。服務自己要的前置（安裝、key、MCP 設定）看服務的 skill。

1. **先問使用者**，說好才跑：
   - 那台第一次 `up` 要加 `--create-task`：常駐 task 會一直留在那台。browser 的 task 由 browser-access 建：`up` 回報沒有 task 時照 browser-access 問。
   - 客戶的機器：`up`、`down`、`ps <服務> <host>` 都會在那台跑 PowerShell，每次都先問。客戶機器在 `services.yaml` 的 `hosts.<host>` 設 `keep: false`（範例在檔案註解），task 由 `up` 建、`down` 刪。
2. **起**：`remote-access up <服務> <host>`。已經起好而且驗證過時只回報，重跑安全。
   完成條件：印出 `網址：…`（或 `已經起好：…`）和 `MCP：<名稱>`。
3. **查**：`remote-access ps` 列出這台 `up` 過、還沒 `down` 的機器，各自的網址或本機 port、MCP 名稱、驗證過沒；連不上、沒在跑也列。別台 agent 機器 `up` 的不在裡面，要查就 `ps <服務> <host>`。
4. **收**：`remote-access down <服務> <host>`。
   完成條件：印 `已收乾淨` 或 `本來就沒開`。
5. **換 key**：`remote-access key init` 第一次產生，`remote-access key rotate` 換新並重起已接上的機器；兩個都要重開 session 才讀得到。
   完成條件：`rotate` 沒有印 `這幾台沒同步到`；有的話照它印的 `up` 在新 session 重跑。

`up` 失敗時已經收掉起了一半的東西，照 [reference.md〈`up` 的錯誤訊息〉](reference.md#up-的錯誤訊息) 處理。

## tailnet 內

一行指令，照打，不包 script。`<host>` 是 ssh config 裡那台的 Host（例如 `company-ec2`）：

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:<本機 port>:127.0.0.1:<那台 port> <host>   # 把那台的服務拉到這台
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:<那台 port>:127.0.0.1:<這台 port> <host>   # 把這台的服務借給那台
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:1080 <host>                                # 反向 SOCKS：那台借這台的網路
tailscale serve --bg --https=443 <port>                                                    # tailnet 內帶憑證的 https://<機器>.<tailnet>.ts.net
```

- **ssh 轉發是預設。** 服務在 `services.yaml` 裡的照[服務定義](#服務定義uppsdown)，不手動開。
- **兩端都綁 `127.0.0.1`。** 被轉發的服務多半沒有驗證，綁 `0.0.0.0` 等於開給整個網路。
- **你自己跑 ssh 時背景跑**（Claude Code 的 Bash `run_in_background`），用完停掉它。要使用者在他那台跑時，把指令交給他，請他開著別關。
- **tailscale serve** 在 ssh 不到那台時用。它不改寫 `Host`，服務綁 loopback 又檢查 `Host` 時要改綁 `0.0.0.0`，並確認防火牆沒放行那個 port 的 inbound。listener 不能跟服務同一個 port（WSL mirrored 下會互搶）。收：`tailscale serve --https=443 off`，`tailscale serve status` 沒有那個 port 才算收掉。

完成條件：ssh 停著沒印錯誤，在連的那一端 `curl -sI http://127.0.0.1:<port>`（serve 是那個 ts.net 網址）有回應，或服務 skill 寫的驗證通過。`Address already in use`、`remote port forwarding failed` 是 port 被佔，照[本機 port 總表](#本機-port-總表)回報；其他連不上照 dotfiles 的 [ssh 轉發連不上](https://github.com/henry5720/dotfiles/blob/main/docs/how-to/remote-access/README.md#ssh-轉發連不上) 查。

## script 規則

改這支或替別的服務寫 script 時照這三條：

- **只包碰 key 或密碼、或收尾檢查會騙人的操作。** 例如 Funnel 收掉後 `tailscale funnel status` 照樣印 `No serve config`，所以收的判準包進 `remote-access funnel`。一行講完的指令（上面的 ssh、`tailscale serve`）寫在 skill 裡，不包。
- **名字名詞在前。** 服務或連線的名字放前面，多個動作用子命令（`remote-access funnel open`），只有一個動作就接在名字後面（`ttyd-serve`）。
- **每支都有 `--help`。**
