# 打卡：實測紀錄與雷

- **`accuracy` 500 的門檻是自己加的。** 伺服器收到 100 km 都接受，只在畫面標「粗略位置」；
  但超過 500 的多半是 Windows 退回 IP 推估，PMS 不允許拿 IP 座標打卡。
- **ssh 過去跑 `gps.ps1` 拿到的是 IP 推估。** 2026-11-27 從 henry-laptop ssh 到 henry-desktop 跑，
  回 `accuracy` 50000、座標落在台中，但 desktop 不在台中。ssh 的程式不在桌面登入階段，
  Windows 不給 Wi‑Fi 定位（跟 herdr server 要從桌面起是同一類限制）。
- **筆電本機的精確度**：2026-11-19、11-26、11-27 在辦公室（台北松山）66–73 m，
  地址解析成「台北市松山區敦化北路2號附近」，跟網頁打卡的紀錄一致。
- **定位抓完要立刻送**：伺服器只收 `capturedAt` 在 30 秒內的未來時間到 2 分鐘前的定位，超出回「裝置定位已過期」。
- **`gps.ps1` 只能有 ASCII 字元。** Windows PowerShell 5.1 把沒有 BOM 的 UTF-8 當系統編碼讀，
  2026-11-26 加了中文註解就整支解析失敗（`MissingEndParenthesisInMethodCall`）。
- **WSL 寫 `powershell.exe` 全路徑**：有些 shell 的 PATH 沒有 Windows 目錄，直接打 `powershell.exe` 會 command not found。
- **「會議」不是下班匯總的固定選項。** 每一筆時數都要掛在任務、子任務或問題上，所以借用
  「TeamSync 系統開發 › 會議」這個持續進行的任務（建立者不是本人，參與即可填時數）。
- **macOS、Linux 還沒有腳本。** macOS 有 Homebrew cask `corelocationcli` 可讀 CoreLocation，未實測；
  Linux 的 GeoClue 原本靠已關閉的 Mozilla Location Service，不建議。
