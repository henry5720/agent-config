# windows-mcp reference

出問題、或要改用 Funnel 以外的對外方式時才讀。坑照原因分層：先看 server 本身，再看經過代理的，最後看各方式專屬的。

## 對外入口要滿足的條件

不管用哪種對外方式，入口都要做到：
- 對外是 HTTPS，外面只連得到 `/mcp` 這個 endpoint。
- server 要求 Bearer key（`windows-mcp auth` 產生，存在 `~/.windows-mcp/config.toml`）。
- 用完能完整收掉：關入口、停 server、跑 `windows-mcp auth --force` 換 key。

| 方式 | server 綁哪裡 | 狀態 |
|------|--------------|------|
| Tailscale Funnel | `0.0.0.0` | 預設，有 funnel-open / funnel-close 腳本 |
| Cloudflare quick tunnel | 可以留在 `127.0.0.1` | 未實測，這台還沒裝 cloudflared |
| 防火牆 inbound 直連 | `0.0.0.0` | 未實測 |

不用 Funnel 時，照上面的條件和下面對應那層的坑自己組指令。

## server 本身（所有 HTTP 模式都會遇到）

- **`/mcp/` 會 307 轉到 `/mcp`**：有些 client 不跟 POST redirect，所以直接給 `/mcp`。
- **log 在 server 的最小化視窗**：手動 `serve` 不寫檔；`~\.windows-mcp\server.log` 只有 scheduled task 會寫。
- **`serve` 沒帶 `--transport` 時**，會照 `config.toml` 的 transport 起 server。`auth` 會把它寫成 HTTP，所以 stdio 一定要明寫 `--transport stdio`。
- **綁 loopback 時會檢查 `Host` header**：只接受 `localhost`、`127.0.0.1`、`[::1]`。這版沒有可以加 allowed hosts 的選項（`windows_mcp/__main__.py` 的 DNS rebinding 段），綁 `0.0.0.0` 時不檢查。其他值一律回 400，訊息是 Invalid host header。
- **`Snapshot` 有時讀不到視窗**（回 `No windows found`），截圖仍然正常。讀不到就靠截圖加座標點擊。

## 經過本機代理或 tunnel（Funnel、quick tunnel）

- **`Host` 是公開網址**：代理預設把對外網址當成 `Host` 轉進來，會撞到上面的 loopback 檢查。解法二選一：server 綁 `0.0.0.0`（Funnel 只能這樣做），或讓代理改寫成 `localhost`（cloudflared 用 `--http-host-header localhost`）。
- **`--ip-allowlist` 不能用**：請求是代理從 127.0.0.1 轉進來的，uvicorn 預設信任 127.0.0.1 帶的 `X-Forwarded-For`，會把來源 IP 改成真正的外部 IP。allowlist 填 `127.0.0.1` 就會連代理的請求一起擋掉，回 `403 … not in the IP allowlist`。
- **綁 `0.0.0.0` 時**，區網直連 8000 只靠 Windows 防火牆擋。funnel-open 會先確認沒有放行 windows-mcp 的 inbound 規則。

## Funnel 專屬

- **只能用 443、8443、10000**：443 常被其他 `tailscale serve` 佔用，所以腳本用 8443。
- **在本機驗不到 Funnel**：本機查 ts.net 名稱會拿到 tailnet IP，連線會逾時。要用公開 DNS 查到的 IP 加 `curl --resolve`，funnel-open 已經這樣做。

## Cloudflare quick tunnel 專屬（未實測）

- `cloudflared tunnel --url http://127.0.0.1:8000 --http-host-header localhost`，server 可以留在 loopback。
- 不用帳號，但每次網址都會變，要重新交給對方。

## 防火牆直連專屬（未實測）

- 要有公開 IP 或 port forward。
- TLS 只有 `windows-mcp auth --with-tls` 產的自簽憑證，client 要另外信任。
- 沒有代理改寫來源 IP，所以 `--ip-allowlist` 可以用。防火牆規則也可以只放行對方 IP。
