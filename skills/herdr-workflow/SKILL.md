---
name: herdr-workflow
description: herdr 的個人用法：開或收 git worktree（EnterWorktree、git worktree add、平行改碼），決定子分支要不要 push；HITL 操作（人會看或介入的操作，在已配置主機上跑）；起或重起已配置主機的 herdr server。
---

# herdr 的個人用法

官方 `herdr` skill 管 CLI 怎麼用；這份只寫使用者的偏好和實際踩過的雷。

- 要在已配置主機上跑 **HITL 操作**（改狀態、跑很久、含人工步驟）：讀 [hitl.md](hitl.md)。
- Windows 已配置主機的 herdr server：要在 pane 裡操作桌面（GUI、截圖）、桌面 terminal 連 herdr 回「存取被拒」、要起或重起 server：讀 [server.md](server.md)。

## Worktree：什麼時候開

一次做一件就在目前分支 commit。要平行改碼、AFK 跑、或手上改到一半要插急件時才開 worktree。
`--bg` session 會被 harness 要求先進 worktree，照下面開。

## Worktree：怎麼開

`HERDR_ENV=1` 時由 herdr 開，再進去：

```
herdr worktree create --cwd <repo> --branch <name> --base <ref> --no-focus   # 回傳 .worktree.path
EnterWorktree --path <那個 path>
```

進去後先初始化開發環境：worktree 是全新 checkout，沒有 `node_modules` 這類被 ignore 的目錄，
git hook、lint、formatter 的 plugin 都載不到。repo 有 lockfile 就照它裝（`pnpm install --frozen-lockfile`、
`npm ci`、`uv sync`…），裝完才開始改。

- `--cwd` 給**主 checkout**；給 linked worktree 會回 `linked_worktree_source`。
- `--base` 不給就用預設分支。要疊在別人剛做好的那顆 commit 上時指定它。
- 使用 Herdr 預設位置 `~/.herdr/worktrees/<repo>/<branch>`；建立指令省略 `--path`。
  在 repo 外面，IDE、檔案搜尋、watcher 掃不到；代價是順便開一個 herdr workspace。
- 若 sandbox 或檔案權限阻擋預設位置，先回報被拒的路徑與錯誤，再處理權限；不得自行改放 `~/code` 或其他位置。
- 改用非預設位置前，先說明原因與完整目標路徑，取得使用者對該位置的明確同意後才加 `--path`。本次對話已取得的同意可沿用；同意開 worktree 不等於同意改位置。
- Claude Code 進了一個 worktree 之後，`EnterWorktree --path` 只認 `<repo>/.claude/worktrees/` 底下的，
  換不到第二個 herdr worktree。要換基底就在**現在這個** worktree 裡 `git switch`。
- `EnterWorktree` 不接受 session 啟動目錄以外的 repo（例如從 `~/code` 開、要改 `~/.config/skillshare`）。
  這時不進去，直接用 herdr 回傳的絕對路徑讀寫檔、在那裡跑 git。

沒有 herdr 就用內建的 `EnterWorktree`，它開在 `<repo>/.claude/worktrees/`。

## Worktree：什麼時候收

合併完、在**目標分支那份 checkout** 上驗過、確定不用回去改，就 `herdr worktree remove --workspace <id>`。
一做完就收，worktree 和分支才不會越積越多。

收掉不會弄丟東西：分支 ref 住在主 checkout 的 `.git/refs/heads/`，`worktree remove` 不刪分支也不刪 commit。
本機分支另外刪：一般 merge 用 `git branch -d`；squash merge 後 `-d` 認不出已合併，先確認
`git diff --stat <分支 head> <merge commit> -- <PR 改到的路徑>` 是空的，再用 `git branch -D`。
所以子分支只在換裝置、換人接手、過夜離開機器時才 push，合併後當天 `git push origin --delete`。
