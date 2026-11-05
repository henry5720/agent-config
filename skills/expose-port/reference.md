# expose-port reference

公網驗證沒過、或連得上但 app 回錯誤時才讀。坑照原因分層：先看經過代理的（每種方式都會遇到），再看 Funnel、quick tunnel 各自專屬的。app 本身的坑看 app 自己的文件（例如 windows-mcp 的 reference.md）。

## 經過本機代理或 tunnel（Funnel、quick tunnel）

- **`Host` 是公開網址**：代理預設把對外網址當成 `Host` 轉進來。app 綁 loopback 又檢查 `Host` 時會回 400（windows-mcp 是 Invalid host header）。解法二選一：app 綁 `0.0.0.0`（Funnel 只能這樣做），或讓代理改寫成 `localhost`（cloudflared 用 `--http-host-header localhost`）。
- **用來源 IP 擋人的設定不能用**：請求是代理從 127.0.0.1 轉進來的。uvicorn 這類 server 預設信任 127.0.0.1 帶的 `X-Forwarded-For`，會把來源 IP 改成真正的外部 IP；allowlist 填 `127.0.0.1` 就會連代理的請求一起擋掉（windows-mcp 的 `--ip-allowlist` 回 `403 … not in the IP allowlist`）。
- **app 綁 `0.0.0.0` 時**，區網直連那個 port 只靠防火牆擋。開之前確認沒有放行它的 inbound 規則。

## Funnel 專屬

- **只能用 443、8443、10000**（[官方文件](https://tailscale.com/docs/features/tailscale-funnel)）。443 常被其他 `tailscale serve` 佔用，所以預設 8443。
- **開不起來**：tailnet 要開 MagicDNS 和 HTTPS 憑證，policy 要有 `funnel` node attribute。細節看 remote-access 的 [Tailscale Funnel](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#tailscale-funnel)。
- **在本機驗不到 Funnel**：在 tailnet 內的機器查 ts.net 名稱會拿到 tailnet IP，連線會逾時。要用公開 DNS 查到的 IP 加 `curl --resolve`，`expose-port-funnel open` 已經這樣做。手動驗（那台沒有腳本時）：

  ```bash
  host=<機器>.<tailnet>.ts.net port=<對外 port>
  ip=$(curl -s "https://cloudflare-dns.com/dns-query?name=$host&type=A" -H 'accept: application/dns-json' \
    | python3 -c 'import sys,json;print([a["data"] for a in json.load(sys.stdin)["Answer"] if a["type"]==1][-1])')
  curl -s -m 30 -o /dev/null -w '%{http_code}\n' --resolve "$host:$port:$ip" <app 要的參數> "https://$host:$port<路徑>"
  # 帶驗證那次加 -H "Authorization: …"
  ```

  完成條件跟腳本一樣：不帶驗證、帶驗證各回 app 給的碼。剛開的前幾秒可能還不通，隔幾秒重打。
- **收掉後還在**：`tailscale funnel status` 還列著那個 port 時，`expose-port-funnel close --https <port>` 會再 `off` 一次。前景開的 Funnel 收到 SIGTERM 就撤，這在 Linux 由 share-shell 實測過（2026-10-02）；從 WSL 叫 Windows 的 tailscale（`TAILSCALE='powershell.exe …'`）時，停掉 WSL 這邊的行程會不會撤掉 Windows 那邊的 Funnel **未實測**，收完一定看 `剩 0 條`。

## quick tunnel 專屬

- **限制**：不支援 SSE、每條 200 個並行請求（超過回 `429`）、網址每次都變、官方只給測試開發用（[官方文件](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)）。SSE 經 quick tunnel 會怎麼壞**未實測**：連得上、一般請求 200，但某個操作卡住或斷線時先懷疑 SSE，改走 Funnel。
- **不帶驗證回 `400`**：Host 沒對好。app 綁 loopback 又檢查 `Host` 時要 `--host-header localhost`（cloudflared 的 `--http-host-header localhost`）。
- **不帶驗證回 `5xx`**：多半是 cloudflared 接到了、app 沒在那個 port 聽（cloudflared 的 log 會有 origin 連不上的錯誤）。回 app 的文件確認 server 起了、port 對。
- **剛印出網址時連不上**：網址要幾秒才生效。腳本用公開 DNS 查到的 IP 加 `--resolve` 重打，避開本機 DNS 把剛查不到的名稱快取起來。手動打時隔幾秒重試。
- **cloudflared 沒印出網址就結束**：腳本會印 cloudflared 最後幾行。照那幾行查；連不到 Cloudflare（網路擋 outbound）時就是在這裡停住。
- **收掉後還有 cloudflared**：`expose-port-quick-tunnel close --port <port>` 停掉這台上轉那個 port 的 quick tunnel，只認命令列是 `cloudflared tunnel … --url http://127.0.0.1:<port>`（或 `localhost`）的行程，別的 tunnel 不動。
