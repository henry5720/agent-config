# 查待辦、開 GitHub issue

[SKILL.md](SKILL.md) 的分支：被派去查一件待辦，或要把一列待辦開成 GitHub issue。

## 🔍 被派去查一件待辦時

**草稿／issue body 的格式照你所在 repo 的 `CLAUDE.md` 觸發表指的那份規範**，這裡只有那份規範不可能知道的 Slack 端。
怎麼查由你自己決定，但動手前先照 [SKILL.md](SKILL.md) 紅線第 1 條讀完那列的留言串。

## 🔑 開 issue 一定要先埋指紋

先跑 `slack-list env` 看 `ISSUE_MODE`：

- `agent`：照本節流程，用 `gh` 查重並開 issue。
- `manual`：**這個環境沒有 GitHub credential，`gh` 和要 token 都不碰。** 偵察寫完草稿後，用
  `slack-list draft` 把 Markdown、指紋搜尋頁與 New issue 頁交回原生 item 留言串，然後停。
  只有既有待辦列能走這條發布流程；DM 或一般 channel 的口述需求要先用 `add`（見 [add.md](add.md)）對應到待辦列。

```bash
~/.claude/skills/slack-list/scripts/slack-list draft Rec0B… \
  --md drafts/<日期>/<短名>.md \
  --repo ShuChenAI/<repo> \
  --summary "<一句定位結論>" \
  --requested-by <openab.sender.v1 的 sender_id>
```

`manual` mode 的核准動作是人從 GitHub 網頁提交，或把附件交給有 `gh` 權限的 local agent。
回報時講清楚你只提供了搜尋連結，GitHub 查重由核准者確認。

**開 issue 前必做，不是加分項。** 待辦從 Slack 進 GitHub 的流程裡，開 issue 的是 agent
不是人，沒有人在那個位置擋重複，所以這步漏掉就一定會開出重複的任務。

```bash
# 1. 先比對，任何一筆命中就去那張既有的 issue 上留言，不開新的
gh issue list --search "Rec0B…" --state all

# 2. 沒命中才開。body 第一行放這個，然後才是簡報
> Slack 來源：[Rec0B…](<WORKSPACE>/lists/<TEAM_ID>/<LIST_ID>?record_id=Rec0B…)
```

**開完不用另外記。** 那行指紋就是正本，`--search` 立刻查得到，工具不留副本。

`Rec0B…` 就是 `rows` / `mine` 每列開頭印的那串。`<WORKSPACE>`、`<TEAM_ID>`、`<LIST_ID>`
從 `slack-list env` 印出來的那三行拿。`progress`、`ready` 等指令最後印的就是這條連結，有的話直接抄。

⚠️ **指紋放成看得見的引言行。** GitHub 搜尋會不會索引 HTML 註解（`<!-- -->`）沒有定論，
而整套去重就靠這個查詢，賭不起。可見的引言行還有兩個好處：你點得回 Slack 那列，
別人看 issue 也知道來源。

⚠️ **查重只靠上面那個指紋搜尋。** GitHub 自己的重複偵測只在網頁表單被證實，
`gh issue create` 走不走得到官方沒講，當它不存在。

### 一列預設一張 issue

拆成多個任務是**例外**（顆粒度還沒定案，見 [SKILL.md](SKILL.md) 紅線第 2 條）。真的拆了，每一個都各自埋同一個指紋，
再用 `slack-list progress` 在該列的留言串貼一則「拆成 #1801 #1802 #1803」讓後面的人看得到。

### 只有正本，沒有快取

「這一列對到哪幾張 issue」的唯一答案是 `gh issue list --search "Rec0B…" --state all`。
工具不存副本 —— 存了就是養一份會過期的東西。

### issue 格式

走 runtime 明確提供的目標 repo（例如 mounted 的 `teamsync-frontend`）的
`docs/guides/workflow/github-issue-standards.md`
與 `docs/agents/issue-tracker.md`（`gh issue create --type` 是必要的），
規格不足的掛 `needs-triage`。
