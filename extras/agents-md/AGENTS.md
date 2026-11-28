# 個人偏好

寫給人看的文件（README、`docs/`）時載入 `writing-for-humans`。
寫給 agent 的文件（skill、`AGENTS.md`、`CLAUDE.md`）時載入 `writing-for-agents`。

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

- 給人看的說明：流程、前後比較、目錄關係用表格或縮排樹；一句話講得完的不畫圖，同一內容不重複展示。
- 依接收平台選擇可直接閱讀的形式；PR/GitHub 不提供只能本機檢視的 HTML。
- 要畫圖前先確認那個地方渲染得出來 —— 終端機和 Discord 都不會渲染 mermaid，改用文字箭頭或縮排樹；表格可以用。

## 誠實

- 不要說「看起來沒問題」「應該可以」。有疑慮直說「可以跑，但…」。
- 講風險、講影響範圍時要附檔案路徑、行號或指令輸出。憑印象講的不算數。
- 回覆裡提到的路徑、檔名、函式名，先確認存在再寫出來。
- 截圖、影片等證據作為附件提供，不 commit、不含敏感資料。

## Issue 狀態

處理 issue 前先載入 `issue-status` skill（認領、卡住、完成、交接）。

## Commit 共同作者

建立或 amend commit 前，讀 `~/.config/agent-commit/instructions.md`：誰改的誰 commit，每顆 commit 標自己。

## Herdr

開 worktree 前先載入 `herdr-workflow` skill：`HERDR_ENV=1` 時由 herdr 開，Claude、Codex、opencode 的 worktree 才會都歸 herdr 管。

別人正在用的 worktree 只讀，要動碼就自己開一個：另一個 session 可能住在裡面，`git switch` 會把它的 HEAD 和未提交的檔案帶到你的分支。

`HERDR_ENV=1` 時，要跑改到自己工作目錄以外、跑很久、或要人親手做的指令之前，先載入 `herdr-workflow`：這些指令開 herdr workspace 跑給使用者看，判準在它的 `hitl.md`。

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.

OpenCode puts the MCP server's key in front of each tool's name, so it lists this tool as `codegraph_codegraph_explore` where other agents list `codegraph_explore`; if the server is registered under another key, that key replaces the first `codegraph_`.
<!-- CODEGRAPH_END -->

## Graphify

Graphify Cloud 的圖只從 GitHub 預設分支建，本機改動和其他分支都不在裡面。查程式碼預設用 CodeGraph（上一段），只有這三種情況才用 Graphify：

- 不知道在哪個 repo：某個 symbol、API 有哪些 repo 在用（`search`，或 `teamsync-core` 這類合併 workspace）。幾個 repo 都在本機且有 `.codegraph/` 時，用 CodeGraph 的 `projectPath` 各查一次。
- 本機沒 checkout、或沒有 `.codegraph/` 的 repo。
- 讀寫 workspace 共用的 memory（`recall`／`remember`）。
