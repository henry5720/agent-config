# 拿改前畫面

[SKILL.md](SKILL.md) 步驟 3 的細節：有 `fixed` 條件時一定要拿，`changed` 順手拿得到就拿。

照順序取，拿到就停。截圖都存 `<E>/before-<狀態>.png`，另開一個瀏覽器 session（`playwright-cli` 用 `-s=<S>-before`），每條的操作與它的改後相同，viewport 也相同；一張改前只能放進操作相同的那條 `before`。

1. **base 的線上部署**：該 repo 的 `AGENTS.md`／docs 寫了網址與查部署 commit 的方法，且下面三條都成立才用：
   - 部署 commit 與 merge-base 在這次改到的路徑上沒有差異（`git diff --name-only <merge-base> <部署 commit> -- <改到的路徑>` 輸出為空）；
   - 這張 PR 依賴的後端改動還沒部署；
   - 部署端開得到改到的頁面（模組開關、feature flag）。

   共用環境只截唯讀畫面。改前與改後的環境不同，寫進 `environment.before`：網址、部署 commit、資料來源。
2. **本機 base**：`git worktree add <tmp>/before <merge-base>`，另一個 port 起 dev server。後端用 base 時期的版本：這張 PR 沒改後端契約就用改後那台；改了就用不含那些改動的舊版後端。`environment.before` 寫 `本機 base @ <merge-base>` 與後端來源。收尾時 `git worktree remove <tmp>/before`。
3. **都拿不到**：`fixed` 那幾條的 `beforeReason` 寫原因，報告會顯示「只有改後：<原因>」。

**完成條件**：每條 `fixed` 都有 `before` 或 `beforeReason`；拿到改前時 `environment.before` 已填。
