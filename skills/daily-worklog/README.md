# daily-worklog

從 git commit 產生給主管看的每日／每週工作日誌。

方法論全部在 [`SKILL.md`](./SKILL.md)，兩種用法都吃同一份檔案：

## 用法 A：裝成 Claude Code skill（推薦，之後只要說「寫日誌」）

這支放在 agent-config 的 `skills/`，由 skillshare sync 到 `~/.claude/skills/` 與
`~/.agents/skills/`。換一台機器跑一次 `skillshare pull` 就有，不用手動拉線。

裝好之後開新 session，說「幫我寫今天的工作日誌」就會自動觸發。

## 用法 B：當純 context 貼給任何 agent

Codex / Cursor / ChatGPT 沒有 skill 機制，直接把 `SKILL.md` 全文貼進去，
再補一句「今天是 2026-08-11，author 是 henry」即可。
最上面那段 `---` frontmatter 留著不影響閱讀，不用刪。

## 產出放哪

哪裡都不放。日誌直接輸出在對話裡讓你複製貼進公司表單，使用者明講要存檔才落檔，
理由（兩個 repo 都是 public）見 [`SKILL.md`](./SKILL.md) 的「產出放哪」。
唯一固定會寫的檔案是跨日進度清單 `~/.claude/worklog-backlog.md`。
