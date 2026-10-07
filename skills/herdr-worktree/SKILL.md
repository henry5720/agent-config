---
name: herdr-worktree
description: 開 git worktree 前使用（EnterWorktree、git worktree add、平行改碼）；HERDR_ENV=1 時改由 herdr 開，讓 Claude、Codex、opencode 的 worktree 都歸 herdr 管。收 worktree、決定子分支要不要 push 時也用。
---

# Worktree 走 herdr

## 什麼時候開

一次做一件就在目前分支 commit。要平行改碼、AFK 跑、或手上改到一半要插急件時才開 worktree。
`--bg` session 會被 harness 要求先進 worktree，照下面開。

## 怎麼開

`HERDR_ENV=1` 時由 herdr 開，再進去：

```
herdr worktree create --cwd <repo> --branch <name> --base <ref> --no-focus   # 回傳 .worktree.path
EnterWorktree --path <那個 path>
```

- `--cwd` 給**主 checkout**；給 linked worktree 會回 `linked_worktree_source`。
- `--base` 不給就用預設分支。要疊在別人剛做好的那顆 commit 上時指定它。
- 開在 `~/.herdr/worktrees/<repo>/<branch>`，在 repo 外面，IDE、檔案搜尋、watcher 掃不到。
  代價是順便開一個 herdr workspace。
- Claude Code 進了一個 worktree 之後，`EnterWorktree --path` 只認 `<repo>/.claude/worktrees/` 底下的，
  換不到第二個 herdr worktree。要換基底就在**現在這個** worktree 裡 `git switch`。

沒有 herdr 就用內建的 `EnterWorktree`，它開在 `<repo>/.claude/worktrees/`。

## 什麼時候收

合併完、在**目標分支那份 checkout** 上驗過、確定不用回去改，就 `herdr worktree remove --workspace <id>`。
一做完就收，worktree 和分支才不會越積越多。

收掉不會弄丟東西：分支 ref 住在主 checkout 的 `.git/refs/heads/`，`worktree remove` 不刪分支也不刪 commit。
所以子分支只在換裝置、換人接手、過夜離開機器時才 push，合併後當天 `git push origin --delete`。
