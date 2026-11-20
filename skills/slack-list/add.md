# 建立待辦、設定回報對象

[SKILL.md](SKILL.md) 的分支：要在 Bug/需求總表新增一列，或改某列驗收時 `@` 誰。

## ➕ 建立待辦

`add` 由 OpenAB backlog agent 與 local agent 都可以跑。

**只有使用者明確要求「新增／建立待辦」才寫入。** 使用者明確給標題時直接建立；若要從一大段話
濃縮標題或敘述，先把準備寫入的內容貼出來確認。到期日按 `Asia/Taipei` 換成實際
`YYYY-MM-DD`，回覆時也顯示該日期；沒把握就問。

**建之前一定要先查重**（`rows <關鍵字>`；0 列時再加 `--all` 查一次），這是唯一真正管用的防線。

⚠️ `add` 的同名去重是 read-then-write，而 `add_lock()` 那把鎖只在單一 runtime 內有效：
它鎖的是 `/tmp/slack-list-add-<list_id>.lock`，container 的 `/tmp` 與 host 的 `/tmp` 是兩個檔案，
所以**跨 runtime 同時建同名列會各建一列**，Slack 那邊也沒有 unique 約束擋。窗口很窄
（要同一個標題、落在同幾秒內），代價是多一列、請使用者去 UI 刪（沒有刪除指令）。
撞到才修鎖；在那之前，防線就是上面的查重。

`--assignee` 與 `--requested-by` 必須是同一個 ID（腳本會擋），差別只在那個 ID 從哪來：

| 跑在哪 | ID 來源 | 來源對話 |
|---|---|---|
| OpenAB | `openab.sender.v1.sender_id` | 帶 `--source-channel` / `--source-thread` |
| local（終端機） | `~/.config/slack-list/.env` 的 `SLACK_MY_USER_ID` | **兩個都省略** |

```bash
# OpenAB
~/.claude/skills/slack-list/scripts/slack-list add \
  --title "<使用者明確給出或已確認的標題>" \
  --description "<選填>" \
  --due YYYY-MM-DD \
  --assignee <openab.sender.v1.sender_id> \
  --requested-by <openab.sender.v1.sender_id> \
  --source-channel <openab.sender.v1.channel_id> \
  --source-thread <openab.sender.v1.thread_id>

# local
~/.claude/skills/slack-list/scripts/slack-list add \
  --title "<使用者明確給出或已確認的標題>" \
  --description "<選填>" \
  --assignee "$SLACK_MY_USER_ID" \
  --requested-by "$SLACK_MY_USER_ID"
```

local 省略來源對話時那一列只是少一行「來源對話」—— `--requested-by` 仍會寫進發起者註記，
所以 `reporter --default` 之後找得到 fallback 對象。**來源 flag 只傳真實的 channel／ts**；
`chat.getPermalink` 取不到就會中止建立，為了填滿欄位隨便塞一組只會讓 `add` 失敗。

**回報對象**：沒特別說時預設回報給 sender。使用者明確說「回報給 @某人」時，從 Slack mention
取可靠的 `U…` ID，加 `--report-to U…`；說「不要通知任何人」才加 `--no-reporter`。
可靠的 ID 來源只有 mention 和 `slack-list users <關鍵字>`，後者回超過一個人時要先問是哪一位；
顯示名稱不算。

**精確同名**由 `add` 自行處理：active 列存在時不建第二列，而是把 sender 追加到 assignees，
並補一則再次回報的來源；原本就有 sender 時只補來源。既有列在「PM確認中」時不改指派，
只回既有連結。使用者確認是復發或另一件事後，才用同一組參數加 `--force`。
命中既有列時保留原回報對象，`add` 的 `--report-to` / `--no-reporter` 不套用；使用者看過合併結果後
仍要改，才另跑 `reporter`。

**從既有 item 留言串要求新增時，即使標題不同也先顯示目前待辦與準備新增的內容，確認是另一件事。**
腳本也會擋下第一次呼叫；使用者確認後才加 `--force`，這一次對話省不得。

**成功後**只回新增／合併結果、實際到期日及 deep link。若工具說列已建立但來源／回報設定失敗，
照實回報，不重跑 `add`（重跑可能建出重複列）。若是「建立結果不明」，先到 List 搜尋同名列再決定。
這支工具不修改標題、敘述、日期，也不刪列。

## 設定既有列的回報對象

任何授權使用者都能在 item 留言串明確要求變更；用 `context` 取得 record ID 後執行：

```bash
~/.claude/skills/slack-list/scripts/slack-list reporter Rec0B… --user U0B…  # 回報給被 mention 的一人
~/.claude/skills/slack-list/scripts/slack-list reporter Rec0B… --default    # 真人建立者／bot 建列發起者
~/.claude/skills/slack-list/scripts/slack-list reporter Rec0B… --none       # 驗收時不 @ 人
```

一列可以有多位指派對象，但回報對象至多一位。該通知誰以明確設定為準，assignee 不是回報對象。
