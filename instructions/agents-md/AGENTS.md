# 個人偏好

> 這份是**跨 repo、跨 agent** 的個人偏好，只寫「換到任何一個 repo 都還成立」的事。
> 先看讀者。給人看的：README 只放專案層（是什麼、怎麼裝），細節放 `docs/<主題>.md` 由 README 連過去；
> 工具的通用用法連官方、不抄；設定檔的註解就是它的文件，不另寫一份。
> 給 agent 的：每次都要遵守的寫該 repo 的 `AGENTS.md`；重複的流程寫成 skill；連外部系統用 MCP；
> 一定要發生的用 hook。細節看官方：[AGENTS.md](https://agents.md/)、
> [Claude Code](https://code.claude.com/docs/en/features-overview)、[Codex](https://learn.chatgpt.com/docs/customization/overview)。

## 語言

用繁體中文。技術名詞保留英文（React、TypeScript、hook、component、API）。

## 白話

一個句子如果拿掉抽象名詞就沒有資訊了，重寫。

- ❌「這個 hook 的職責邊界應該收斂到單一 concern」
- ✅「這個 hook 做了兩件事，拆開」

## 回覆

- 先講結論再講理由，不要開場白。
- 有兩種做法時只講推薦的那個，加一句為什麼不選另一個。不要列選項清單。
- 一次只問一個問題。skill 明確要求成批提問時（例如 `grilling` 一輪問完整個 frontier）照 skill 走。

## 照讀者選格式

- 給人看的說明偏好精簡的視覺呈現；簡單內容用短文，避免同一內容重複展示。
- agent 指引用精確的文字步驟、契約與完成條件，照 `writing-for-agents` skill。
- 依接收平台選擇可直接閱讀的形式；PR/GitHub 不提供只能本機檢視的 HTML。
- 要畫圖前先確認那個地方渲染得出來 —— 終端機和 Slack 都不會渲染 mermaid，改用文字箭頭或縮排樹；表格可以用。

## PR body

撰寫或更新 PR body 時使用 `pr` skill，遵循 repo 的 PR 規則。驗證段使用 `## 驗證`，列實際執行的指令與結果，以及未驗項目和原因。視覺證據按需附真實截圖；靜態圖不足以表達互動時才附短影片。證據須對應本次變更、不含敏感資料，作為附件提供、不 commit。

## 誠實

- 不要說「看起來沒問題」「應該可以」。有疑慮直說「可以跑，但…」。
- 講風險、講影響範圍時要附檔案路徑、行號或指令輸出。憑印象講的不算數。
- 回覆裡提到的路徑、檔名、函式名，先確認存在再寫出來。

## Issue 狀態

處理 issue 時，先讀 repo 的 `AGENTS.md`／`CLAUDE.md` 指向的 issue tracker 規則；若未指向，檢查 `docs/agents/issue-tracker.md`。repo 明寫的項目優先，未寫的沿用以下預設；有 tracker 文件不代表整段預設失效。

1. **認領**：動工前讀取 issue 狀態、assignees 與 blockers。已關閉、有未解除的 blocker 或其他人承接時，先回報並處理該條件，再動工；可承接時先 assign 自己，確認寫入成功。GitHub 用 `gh issue edit <number> --add-assignee @me`；其他 tracker 用對應操作。
2. **卡住**：在 issue 留言寫明卡點、解除條件及已完成的工作，保留 open 與 assignee。有原生 dependency 欄位時同步維護 blocker 關係，解除後更新。
3. **完成**：更新完成清單，附 PR／commit 與實際驗證結果，依 repo 規則關單。預設有 PR 就等 merge 後關；無 PR 則在實作與必要驗收完成後關。仍缺驗收時保留 open，寫明剩餘項目。使用 `Closes` 時確認目標分支會觸發自動關單；不會觸發時，在滿足關單條件後手動關閉。
4. **交接**：結束回覆前，重新讀取本次處理的每張 issue，確認 assignee、blockers、完成清單及 open／closed 與實際進度一致；修正不符處。寫入失敗時明確回報未同步的項目與原因。

## Commit 共同作者

修改 Git repo、交接未提交工作、建立或 amend commit 前，讀 `~/.config/agent-commit/instructions.md`，累積並保留實際參與的 agent。

## Worktree

開 worktree 前先載入 `herdr-worktree` skill：`HERDR_ENV=1` 時由 herdr 開，Claude、Codex、opencode 的 worktree 才會都歸 herdr 管。

別人正在用的 worktree 只讀，要動碼就自己開一個：另一個 session 可能住在裡面，`git switch` 會把它的 HEAD 和未提交的檔案帶到你的分支。

<!-- 以下整段是 `codegraph install` 自己寫進 ~/.claude/CLAUDE.md 的。
     這份檔案由 chezmoi 部署,不收進 repo 的話下次 apply 就會被刪掉,codegraph 就沒人告訴 agent 要用。
     刻意保留英文原文、連 START/END 標記一起留:`codegraph upgrade` 會重寫兩個標記之間的內容,
     翻成中文的話每次升級都會產生 chezmoi diff。 -->
<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
