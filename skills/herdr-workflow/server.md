# 已配置主機的 herdr server

Linux 已配置主機：`herdr machine add` 或 `--machine` 經 ssh 把遠端 server 拉起來是官方設計，不用處理。
下面只講 Windows。

## Windows：預設由登入排程起，session 0 的是例外

使用者的 Windows 帳號在 Administrators 群組。從 OpenSSH 登入的 Administrators 帳號拿到的是完整（elevated）權限、跑在 session 0。
重開機後沒有 server，第一個開 herdr 的決定它的權限：

- **預設**：勾了 herdr 的 Windows 由 dotfiles 註冊排程 `herdr-server`，使用者登入時以一般權限把 server 起在登入的 session。
  pane 能用桌面：GUI、定位、剪貼簿。要管理員權限的操作改走自己的 ssh。
- **例外**：重開機後還沒登入，就有人從別台 `--machine` 或 TUI 點那台：server 和每個 pane 都是 elevated、session 0。

session 0 的 server 看得出來的症狀：

- 使用者在那台桌面用一般 terminal 連 herdr：elevated server 拒絕 unelevated client（存取被拒）
- pane 裡開的 GUI 程式桌面上看不到、windows-mcp 從 pane 起抓不到畫面、剪貼簿是分開的
- pane 裡跑定位（PMS 打卡的 `gps.ps1`）只拿到 IP 推估，沒有 Wi‑Fi 定位
- pane 裡走 junction 回「未受信任的掛接點」

看到這些就照下一節換回來；要在 pane 用桌面、server 卻是 session 0 時，先跟使用者說，不在 session 0 的 pane 裡繞路。

檢查（自己的 ssh，AFK 操作）：

```powershell
Get-CimInstance Win32_Process | Where-Object Name -like herdr* | Select-Object ProcessId, SessionId, CommandLine
```

`server` 那行的 `SessionId` 是 0 就是 elevated；在 pane 裡跑
`([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole('Administrators')` 是最終判準
（session 1 也可能是使用者用系統管理員身分開的 terminal 起的）。

## 換回登入的 session（使用者同意後做）

順序不能換：停用 profile 之後 `--machine` 就連不到那台。

1. 用 `--machine <label>` 在那台開 workspace，把 `herdr server stop` 用 `pane send-text` 打好、不送出。
2. 找出所有存了這台的 client（這台和其他已配置主機的 `herdr machine list`），各自用 profile **id** 停用：
   `herdr machine disable <id>`（label 無效）。不先停用，停掉的 server 會被重連拉回 session 0。
3. 請使用者到那個 pane 按 Enter（人工步驟：會關掉那台所有 pane，先講）。
4. 那台有人登入時（ssh 跑 `query user` 看得到 console），用自己的 ssh 註冊排程、以一般權限把 server 起在登入的 session：

   有 dotfiles 註冊的 `herdr-server` 排程（`Get-ScheduledTask herdr-server`）就直接 `Start-ScheduledTask herdr-server`；沒有才註冊一個：

   ```powershell
   $u = [Security.Principal.WindowsIdentity]::GetCurrent().Name   # ssh 的 USERDOMAIN 是 WORKGROUP，不能拿來拼
   $a = New-ScheduledTaskAction -Execute conhost.exe -Argument ('--headless "{0}" server' -f (Join-Path $env:LOCALAPPDATA 'mise\shims\herdr.exe'))
   $p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited
   $s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero)
   Register-ScheduledTask herdr-server -Action $a -Principal $p -Settings $s -Force | Out-Null
   Start-ScheduledTask herdr-server
   ```

   這個排程沒有觸發條件，只在 `Start-ScheduledTask` 時跑；留著下次重用，不刪（刪掉正在跑的排程會不會連 server 一起停，沒驗過）。
   `ExecutionTimeLimit` 一定要設 0，預設 72 小時後會停掉 server。沒人登入就等使用者登入，或請他在桌面一般 terminal 跑 `herdr`。
5. 各 client `herdr machine enable <id>`，再檢查：只剩一個 server、`SessionId` ≥ 1、pane 的 `IsInRole` 是 `False`。

之後那台重開機，要使用者先登入，排程才會在別台連進來前起好 server。

`[server] allow_unelevated_clients` 不採用：它只讓一般權限的 client 連得上，pane 仍是 elevated、session 0。
