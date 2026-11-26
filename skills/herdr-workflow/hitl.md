# HITL 操作走 herdr

官方 `herdr` skill 寫的是 "Use only when the user explicitly mentions Herdr" 和
"Do not create a workspace, tab, worktree, or different cwd unless the user explicitly requests that topology"。
使用者已經明確要求：**HITL 操作**一律在已配置主機的 herdr、有標籤的 workspace 裡跑。這是那兩條本身允許的情況，不用每次再提。

## 判準

- **HITL 操作**：改已配置主機狀態的（apply、安裝、重啟服務、git reset）、跑很久的、含**人工步驟**的。人可能會看、review、喊停或接手，所以要跑在 workspace 裡讓人看得到。
- **AFK 操作**：唯讀的查詢與檢查。照常在自己的 shell 或 ssh 跑，不開 workspace。

拿不準就當 HITL。

## 開在哪

- 一個任務、一台已配置主機，開**一個**有標籤的 workspace，側欄找得到：
  ```
  herdr --machine <label> workspace create --label <任務名> --no-focus   # 回傳 .result.root_pane
  ```
- 同一個任務在同一台要平行跑，在那個 workspace 裡開 tab，不另開 workspace。
- 已配置主機就是這台、使用者就在旁邊時，用旁邊的 pane（官方 skill 的 `pane split`）。
- 已配置主機沒有 herdr、或 `--machine` 連不上：把要跑的指令和完成後的檢查指令直接交給使用者，等他回報。

## 跑

安全的步驟自己用 `pane run` 跑，用 `pane wait-output` 等、`pane read` 看結果。

PowerShell 的指令避免巢狀雙引號，否則會卡在 `∙` 續行提示（要送 `ctrl+c` 才出得來）。
複雜的唯讀檢查不必塞進 pane，改用自己的 ssh 跑，那是 AFK 操作。

## 人工步驟

被權限擋下、或本來就要人親手做的那一步（例如別台的 `git reset --hard`、`herdr server stop`）：

1. 前面安全的步驟自己跑完。
2. 用 `pane send-text` 把指令打好、**不送出**，指令後面接上完成標記。標記用字串拼接印，
   免得 `wait-output` 比對到提示列上那行指令本身：
   ```
   herdr --machine <label> pane send-text <pane> 'git reset --hard origin/main; echo ("X" + "_DONE")'
   ```
   bash 外框改用雙引號：`"git reset --hard origin/main; echo X''_DONE"`（單引號外框會讓本機 shell 先把 `''` 吃掉）。
3. 告訴使用者哪台、哪個 workspace，請他到那個 pane 按 Enter。
4. 背景等：`pane wait-output <pane> --regex '(?m)^X_DONE'`。標記只代表跑完、不代表成功，到了先 `pane read` 看結果，再接手後面的步驟。

只把真正要人做的那一步交出去，前後能自己跑的都自己跑。

## 收

做完不關 workspace。回報時列出開過的 workspace（機器、標籤、id），等使用者說 review 完再 `workspace close`。
