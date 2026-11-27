# windows-access reference

出問題時才讀。這份只寫 server 本身的坑，所有 HTTP 模式都會遇到；經過 Funnel、quick tunnel 的坑在 `remote-access` skill 的 reference.md。

## server 本身

- **從 ssh 起的 server 一啟動就結束**：ssh 進 Windows（或 ssh 進去再叫 `wsl.exe`、`powershell.exe`）是沒有互動桌面的 session，`serve` 在 lifespan 丟 `RuntimeError: No active interactive desktop for physical input control` 就結束，`windows-mcp-http.ps1 start` 會等滿 30 秒後報「server 30 秒內沒在 8000 起來」（2026-11-05 在 henry-laptop 實測）。server 要從使用者登入的桌面 session 起，兩種：
  - 使用者在那台桌面開 PowerShell 跑。
  - agent 只連得到 ssh 時，經使用者核准，用暫時的 Interactive scheduled task 跑 `windows-mcp-http.ps1 start`（2026-11-05 在 henry-laptop、2026-11-22 在一台客戶的 Windows 主機這樣起成功）。task 跑 script 而不是直接 `serve`：script 的 8000 檢查、換 key、防火牆檢查、key 不印出都照樣做，exe 也由它找。使用者要登入著桌面。`<script>` 照 SKILL.md〈起、收 server〉；8000 已經有 windows-mcp 在聽時先從 ssh 跑 `stop`。收掉 server 後一定刪掉 task：

    ```powershell
    $log = "$env:TEMP\windows-mcp-start.log"
    # 經 cmd 導出：script 的錯誤用 [Console]::Error 印，PowerShell 的 *> 收不到
    $a = New-ScheduledTaskAction -Execute cmd.exe -Argument "/c powershell -NoProfile -ExecutionPolicy Bypass -File `"<script>`" start --host <綁的位址> > `"$log`" 2>&1"
    $p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
    Register-ScheduledTask -TaskName windows-mcp-temp -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName windows-mcp-temp
    # 等 30 秒內 log 出現完成訊息
    Get-Content $log
    # 收掉 server 後
    Unregister-ScheduledTask -TaskName windows-mcp-temp -Confirm:$false
    ```

    完成條件跟 SKILL.md 的 `start` 一樣，看 `$log`。**剪貼簿會被蓋掉**：script 在桌面 session 跑，key 直接複製到使用者桌面的剪貼簿，他原本剪貼簿裡的東西就沒了。註冊 task 前先跟使用者講，等他說好再起；之後 `rotate` 換 key，剪貼簿裡那把就作廢。這跟 `windows-mcp install` 建的登入自動啟動 task 不同，用完不留。
- **server 跑著時換 key 不生效**：`auth --force` 只改 `config.toml`，跑著的 server 繼續收舊 key（2026-11-05 在 henry-laptop 實測舊 key 仍回 `200`）。換 key 一律先停 server；`windows-mcp-http.ps1` 的 `start`（有 server 在聽就拒絕）和 `rotate` 都是這個順序。
- **`/mcp/` 會 307 轉到 `/mcp`**：有些 client 不跟 POST redirect，所以直接給 `/mcp`。
- **log 在 server 的最小化視窗**：手動 `serve` 不寫檔；`~\.windows-mcp\server.log` 只有 scheduled task 會寫。
- **`serve` 沒帶 `--transport` 時**，會照 `config.toml` 的 transport 起 server。`auth` 會把它寫成 HTTP，所以 stdio 一定要明寫 `--transport stdio`。
- **綁 loopback 時會檢查 `Host` header**：只接受 `localhost`、`127.0.0.1`、`[::1]`。這版沒有可以加 allowed hosts 的選項（`windows_mcp/__main__.py` 的 DNS rebinding 段），綁 `0.0.0.0` 時不檢查。其他值一律回 400，訊息是 Invalid host header。
- **要先建 session**：streamable HTTP 直接打 `tools/list` 不會成功。順序是 POST `initialize` → 從回應 header 取 `Mcp-Session-Id` → 送 `notifications/initialized` → 之後每個請求都帶 `Mcp-Session-Id` header。MCP client 會自己做，手動用 curl 打才要照這個順序。
- **`Snapshot` 有時讀不到視窗**（回 `No windows found`），截圖仍然正常。讀不到就靠截圖加座標點擊。
