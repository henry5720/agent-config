# windows-mcp reference

出問題、或要改用 SKILL.md 那兩條以外的對外方式時才讀。這份只寫 server 本身的坑；經過代理或 tunnel、Funnel 專屬的坑在 `expose-port` skill 的 reference.md。

## 對外入口要滿足的條件

不管用哪種對外方式，入口都要做到：
- 對外是 HTTPS，外面只連得到 `/mcp` 這個 endpoint。
- server 要求 Bearer key（`windows-mcp auth` 產生，存在 `~/.windows-mcp/config.toml`）。
- 用完能完整收掉：關入口、停 server、跑 `windows-mcp auth --force` 換 key。

| 方式 | server 綁哪裡 | 狀態 |
|------|--------------|------|
| Tailscale Funnel | `0.0.0.0` | 步驟在 SKILL.md：`windows-mcp-serve`／`windows-mcp-stop` 起停 server、換 key，Funnel 由 `expose-port` 開關 |
| Cloudflare quick tunnel | 可以留在 `127.0.0.1` | 步驟在 SKILL.md。2026-11-05 實測過：不帶 key 401；帶 key 時 `initialize`、`tools/list`、`Snapshot` 都 200 |
| 防火牆 inbound 直連 | `0.0.0.0` | 未實測 |

用表上第三種方式時，照上面的條件和下面的坑自己組指令。

## server 本身（所有 HTTP 模式都會遇到）

- **`/mcp/` 會 307 轉到 `/mcp`**：有些 client 不跟 POST redirect，所以直接給 `/mcp`。
- **log 在 server 的最小化視窗**：手動 `serve` 不寫檔；`~\.windows-mcp\server.log` 只有 scheduled task 會寫。
- **`serve` 沒帶 `--transport` 時**，會照 `config.toml` 的 transport 起 server。`auth` 會把它寫成 HTTP，所以 stdio 一定要明寫 `--transport stdio`。
- **綁 loopback 時會檢查 `Host` header**：只接受 `localhost`、`127.0.0.1`、`[::1]`。這版沒有可以加 allowed hosts 的選項（`windows_mcp/__main__.py` 的 DNS rebinding 段），綁 `0.0.0.0` 時不檢查。其他值一律回 400，訊息是 Invalid host header。
- **要先建 session**：streamable HTTP 直接打 `tools/list` 不會成功。順序是 POST `initialize` → 從回應 header 取 `Mcp-Session-Id` → 送 `notifications/initialized` → 之後每個請求都帶 `Mcp-Session-Id` header。MCP client 會自己做，手動用 curl 打才要照這個順序。
- **`Snapshot` 有時讀不到視窗**（回 `No windows found`），截圖仍然正常。讀不到就靠截圖加座標點擊。

## 防火牆直連專屬（未實測）

- 要有公開 IP 或 port forward。
- TLS 只有 `windows-mcp auth --with-tls` 產的自簽憑證，client 要另外信任。
- 沒有代理改寫來源 IP，所以 `--ip-allowlist` 可以用。防火牆規則也可以只放行對方 IP。
