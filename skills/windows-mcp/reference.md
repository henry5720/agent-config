# windows-mcp reference

出問題時才讀。這份只寫 server 本身的坑，所有 HTTP 模式都會遇到；經過 Funnel、quick tunnel 的坑在 `expose-port` skill 的 reference.md。

## server 本身

- **`/mcp/` 會 307 轉到 `/mcp`**：有些 client 不跟 POST redirect，所以直接給 `/mcp`。
- **log 在 server 的最小化視窗**：手動 `serve` 不寫檔；`~\.windows-mcp\server.log` 只有 scheduled task 會寫。
- **`serve` 沒帶 `--transport` 時**，會照 `config.toml` 的 transport 起 server。`auth` 會把它寫成 HTTP，所以 stdio 一定要明寫 `--transport stdio`。
- **綁 loopback 時會檢查 `Host` header**：只接受 `localhost`、`127.0.0.1`、`[::1]`。這版沒有可以加 allowed hosts 的選項（`windows_mcp/__main__.py` 的 DNS rebinding 段），綁 `0.0.0.0` 時不檢查。其他值一律回 400，訊息是 Invalid host header。
- **要先建 session**：streamable HTTP 直接打 `tools/list` 不會成功。順序是 POST `initialize` → 從回應 header 取 `Mcp-Session-Id` → 送 `notifications/initialized` → 之後每個請求都帶 `Mcp-Session-Id` header。MCP client 會自己做，手動用 curl 打才要照這個順序。
- **`Snapshot` 有時讀不到視窗**（回 `No windows found`），截圖仍然正常。讀不到就靠截圖加座標點擊。
