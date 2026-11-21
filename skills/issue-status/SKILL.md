---
name: issue-status
description: 認領、卡住、完成、交接 issue 時同步 tracker 狀態（assignee、blocker、完成清單、open／closed）。動手處理任何 issue 或 ticket 前載入。
---

# Issue 狀態

先讀 repo 的 `AGENTS.md`／`CLAUDE.md` 指向的 issue tracker 規則；若未指向，檢查 `docs/agents/issue-tracker.md`。repo 明寫的項目優先，未寫的沿用以下預設；有 tracker 文件不代表整段預設失效。

1. **認領**：動工前讀取 issue 狀態、assignees 與 blockers。已關閉、有未解除的 blocker 或其他人承接時，先回報並處理該條件，再動工；可承接時先 assign 自己，確認寫入成功。GitHub 用 `gh issue edit <number> --add-assignee @me`；其他 tracker 用對應操作。
2. **卡住**：在 issue 留言寫明卡點、解除條件及已完成的工作，保留 open 與 assignee。有原生 dependency 欄位時同步維護 blocker 關係，解除後更新。
3. **完成**：更新完成清單，附 PR／commit 與實際驗證結果。有 PR 就寫 `Closes`，merge 時關（目標分支不會自動關單時，merge 後手動關）；無 PR 則實作完成就關。只差實機驗收照樣關；沒做完的部分另開 issue。issue 要解決的事本身只有實機驗得到時，PR 改寫 `Refs`、保留 open、寫明剩餘項目，驗過才關。
   例外是 spec 拆成多張 ticket、各 ticket 先併進 integration 分支（`/implement-spec`）時：ticket 併進 integration、這邊驗得到的都驗過就關，留言附 commit 與驗證結果，不等 PR merge；否則跨 ticket、跨 repo 的 blocker 要等 PR merge 才解除，會互相卡住。實機這類這邊驗不到的，寫進 PR 的驗證清單。spec 本身等 PR merge 才關。
4. **交接**：結束回覆前，重新讀取本次處理的每張 issue，確認 assignee、blockers、完成清單及 open／closed 與實際進度一致；修正不符處。寫入失敗時明確回報未同步的項目與原因。
