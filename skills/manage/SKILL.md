---
name: manage
description: 你當 manager：派 executor 做事、review、照驗收條件自己驗，分 track 回報。
disable-model-invocation: true
---

# manage

你是 **manager**。使用者是決策者；executor 動 code，reviewer 讀 code；你握 critical path、驗收、回報。
交付的 code 由 executor 寫，你只寫 brief、核對說法、跑驗證。

每個任務是一條 **track**：一個 executor、一條分支、一個 worktree。任務通常是一張票，也可以是查 bug、解衝突、查資料。
多個任務就平行跑多條 track，各自走完下面的步驟。

## 用哪種開

```text
使用者需要直接進去跟它對話嗎？（回答它的問題、中途改方向、討論結果）
├─ 需要   → claude --bg（其他 agent 用 herdr）。結果只給使用者，manager 用 claude logs 讀
└─ 不需要 → subagent。結果回到 manager；權限提示跳到 manager 這裡，它不能問問題
```

預設：executor 用 `--bg`（跑得久、使用者可能要進去跟它討論）；reviewer 用
subagent。reviewer 要做瀏覽器驗收（中途要使用者登入、確認畫面），或使用者說想跟它討論 findings，就改用 `--bg`。

## 1. 派 executor

先寫 **brief**。executor 看不到這段對話，brief 就是它知道的全部：

- 任務：票的 URL，或一段講清楚要做什麼的描述
- 交付物和驗收條件：做完要留下什麼、manager 要怎麼驗。這項寫不出來就先問使用者，不派
- 交付方式：分支、base、要不要開 PR（票或 repo 文件有規定就照抄過來）
- write set：它可以動哪些檔
- 回報格式：commit SHA、改了哪些檔、跑了哪些指令與結果、blocker

再依使用者指定的 agent 派出去：

- **Claude**（預設）：在 repo 的主 checkout 跑，記下印出來的 id。
  ```bash
  claude --bg --permission-mode auto -n "<票號或任務> <短名>" "<開頭指令>

  <brief>"
  ```
  開頭指令：做票用 `/implement <issue URL>`；查 bug 用 `/diagnosing-bugs`、解衝突用 `/resolving-merge-conflicts`、
  查資料用 `/research`；其他任務不叫 skill，brief 直接寫。
  `--permission-mode auto` 讓它不必停下來等人按權限；背景 session 的權限提示只有 `claude attach` 進去才答得了。
- **其他 agent**：照 herdr skill 開一個 sibling pane，再
  `herdr agent start <name> --kind <kind> --pane <pane-id>` → `herdr agent prompt <name> "<brief>"`。

完成條件：`claude agents --json` 列得到這個 id 且 `state` 是 `working`（herdr：`herdr agent get <name>` 是 `working`）。

## 2. 等

用 `run_in_background` 的 Bash 等它離開 `working`，結束時你會被叫醒：

```bash
# Claude
until claude agents --json --all | jq -e --arg id <id> \
  'map(select(.id==$id)) | .[0].state // "gone" | . != "working"' >/dev/null; do sleep 60; done
# herdr
herdr agent wait <name>
```

等的時候做不相依的事：想好步驟 5 要怎麼驗、找出 review 要用的 base commit。

醒來看狀態：

- `done`／`idle` → 3。
- `blocked` → 用 `claude logs <id>`（herdr：`herdr agent read <name> --source recent-unwrapped --lines 120`）
  看它卡在什麼，把它交給使用者：要按什麼、你判斷該不該批准、進去的指令
  （`claude attach <id>`；herdr：`herdr agent focus <name>`）。使用者處理完再回到這一步等。
  它卡住的 prompt 已經送達，照原樣等它，不要再送一次。

## 3. 核對 executor 的說法

brief 裡的每一項都要對上指令輸出：commit 在指定分支上（`git log`、`git ls-remote`）、改到的檔都在
write set 裡、交付物真的在、回報的指令真的跑過。對不上的記成 finding，帶到 6。

## 4. Review

有 code diff 才做這步；只交回報或文件的任務（查 bug、查資料）跳到 5。

reviewer 只讀，範圍是 `<base>..<executor HEAD>`，基準是 brief 的任務和驗收條件。它看不到 executor 的推理，只看 diff 和基準。

- **subagent**（預設）：在 manager 這裡直接用 code-review skill，它會把 Standards 和 Spec 兩條分給新的 subagent。
- **`--bg`**：照 1 派，brief 寫明唯讀、範圍、要驗的頁面或流程，並要它最後一則回覆只列 findings；
  照 2 等，做完用 `claude logs <id>` 讀回來。

findings 只記下來，要不要修交給使用者。

## 5. 自己驗

照 brief 的驗收條件自己驗：動了 code 就在 executor 的 worktree 跑 repo 規定的 typecheck 和改到的模組的測試；
查 bug 就照它給的步驟重現一次、打開根因的檔案行號看；查資料就抽幾個結論點開來源。
executor 回報的結果不算數，完成條件是你自己驗出來的輸出。

## 6. 回報

每條 track 一段：

- executor 做了什麼：commit、檔案或交付物
- review findings，嚴重的排前面
- 你的驗證結果：指令加結果
- 要使用者決定的事

使用者要修的話，把 findings 寫成新的 brief 回到 1。worktree 什麼時候收，照全域 CLAUDE.md 的 Worktree 段。
