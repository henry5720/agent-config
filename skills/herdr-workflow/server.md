# 已配置主機的 herdr server

Linux 已配置主機：`herdr machine add` 或 `--machine` 經 ssh 把遠端 server 拉起來是官方設計，不用處理。
下面只講 Windows。

## Windows 的 server 要從桌面起

使用者的 Windows 帳號在 Administrators 群組。從 OpenSSH 登入的 Administrators 帳號拿到的是完整（elevated）權限、跑在 session 0，
經 ssh 起的 herdr server 和裡面的每個 pane 都繼承這個權限。結果：

- 從桌面開的一般 terminal 連不上，`herdr` 回 elevated server 拒絕 unelevated client（存取被拒）。
- pane 的提示列顯示 Administrator，GUI 程式看不到，junction 無法遍歷（「未受信任的掛接點」）。

## 檢查

用自己的 ssh 跑（AFK 操作）：

```powershell
Get-Process herdr | Select-Object Id, SessionId, StartTime
```

正常是只有一個 server、`SessionId` ≥ 1，在那台 pane 裡的提示列不是 Administrator。`SessionId` 是 0 就照下面修。

## 修法

1. 找出所有存了這台設定的 client（個人電腦、其他已配置主機），各自用 profile **id**（`herdr machine list --json` 看，label 無效）停用：
   `herdr machine disable <id>`。不先停用，停掉的 server 會被重連拉回 session 0。
   改 profile 要使用者同意，先問。
2. 停 server：`herdr server stop` 會殺掉裡面所有 pane，先問使用者，由他執行（人工步驟）。
3. 請使用者在那台登入桌面，開一般 terminal 跑 `herdr`。
4. 各 client `herdr machine enable <id>`。
5. 再跑一次檢查，確認只剩一個 server、`SessionId` ≥ 1。

`[server] allow_unelevated_clients` 不採用：它讓一般權限的 client 操作 elevated server，等於開一條提權的路，而且 pane 仍然是 elevated。
