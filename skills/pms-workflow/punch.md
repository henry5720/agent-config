# 打卡

規則以 `pms` MCP 的工具說明為準；這裡只寫使用者的偏好和 MCP 做不到的定位。

## 步驟

1. **讀狀態**：`get_my_attendance` operation=current，照 `allowedActions` 決定上班卡或下班匯總。
2. **給使用者確認**：上班卡列出可勾的工作；下班匯總列出每項時數（參考 `clockOutSuggestion` 和當天實際做的事）。
   會議掛在「TeamSync 系統開發 › 會議」（持續進行的任務）。
   **完成條件**：使用者確認了要勾的工作或每項時數。
3. **抓定位**：確認完緊接著跑，跑完就送。遠端日伺服器不收定位，沒有定位來源時先不帶 `gps` 送；回「需要裝置定位」才請使用者改用網頁打卡頁。

   | agent 跑在哪 | 指令 |
   |---|---|
   | WSL | `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w <skill 目錄>/scripts/gps.ps1)"` |
   | Windows 桌面 | `powershell -NoProfile -ExecutionPolicy Bypass -File <skill 目錄>\scripts\gps.ps1` |
   | 其他（macOS、Linux、EC2、ssh 進 Windows） | 沒有定位來源 |

   `accuracy` 超過 500 也請使用者改用網頁打卡頁，停。
4. **送出並回讀**：`record_my_attendance`，再用 `get_my_attendance` operation=roster（`date`=今天）讀回。
   **完成條件**：回報打卡時間、地址、精確度和各項時數。

實測紀錄和踩過的雷：[reference.md](reference.md)。
