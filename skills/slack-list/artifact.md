# 交付 prototype／artifact

[SKILL.md](SKILL.md) 的分支：要把 prototype、截圖或其他交付物附到某列的留言串給 PM。

backlog agent 要把 container `/home/node/drafts` 下的 prototype 或其他交付物交給 PM 時，使用
專用的 `artifact` 指令，交付到該列**既有的原生 item 留言串**。這不是任意 channel 的檔案
上傳器：`record_id` 必須來自原 Slack item/runtime context，工具會自己查回正確的 thread 與
channel。

```bash
~/.claude/skills/slack-list/scripts/slack-list artifact Rec0B… \
  --file /home/node/drafts/<日期>/<檔名> \
  --kind prototype \
  --summary "可操作的庫存匯出 prototype"
```

**prototype／artifact 只用 `artifact`，issue body 只用 `draft`**，兩者不是彼此的別名：
`draft` 保留「完整 Markdown issue body + GitHub 查重／建立連結」的人工發布流程（見 [issue.md](issue.md)）。

**只交到原 item 留言串。** DM、一般 channel 或新開的 thread 都不是交付點。若 runtime 沒有原 Slack item 的
`record_id`/thread context，就不能保證回到原 thread；先回報這項 deployment 限制，channel 不用猜的。

## 腳本強制的安全限制

`--file` resolve 後必須仍在 `/home/node/drafts` 底下，原路徑是 symlink、directory
或其他非 regular file 都會拒絕；副檔名白名單是 `.html`、`.md`、`.css`、`.js`、`.json`、`.png`、`.zip`
（不分大小寫）。單檔上限是 10 MiB；工具會先對安全 fd 做 `fstat`，再以 stream 讀取並再次
檢查上限。成功只在原 item 留言串附檔並發一則不含 `@` 的簡短訊息，不改狀態，也不寫 List
的「檔案」欄。

成功完成 upload 與 thread 訊息後，工具會刪除來源 regular file；upload、complete 或 post 任一步失敗都保留來源，避免無法重試或查證。

## local（沒有 `/home/node/drafts` 的主機）

在呼叫的 process 環境設 `SLACK_LIST_ARTIFACT_ROOT` 指向一個專用目錄，把要交付的檔案（例如驗收截圖）
先複製進去再跑 `artifact`；根目錄限制、白名單、刪除來源、`cleanup` 都改以那個目錄為準。
這個值只讀 process 環境，寫在 `~/.config/slack-list/.env` 不會生效。
**它要指向只放交付物的專用目錄**，home 或 repo 這種大目錄不行 —— 交付成功會刪來源，
`cleanup` 也會清掉裡面 24 小時以上的檔案。

```bash
mkdir -p ~/.local/share/slack-list/drafts && cp <截圖>.png ~/.local/share/slack-list/drafts/
SLACK_LIST_ARTIFACT_ROOT=~/.local/share/slack-list/drafts \
  ~/.claude/skills/slack-list/scripts/slack-list artifact Rec0B… \
  --file ~/.local/share/slack-list/drafts/<截圖>.png --kind artifact --summary "<這張圖在證明什麼>"
```

## cleanup

container cron／entrypoint 可呼叫：

```bash
~/.claude/skills/slack-list/scripts/slack-list cleanup
```

它只刪除 `/home/node/drafts` 內超過或正好 24 小時的 regular artifact，不追 symlink，也不會
掃描 root 以外的檔案。

## 失敗時

上傳或 complete 失敗時不會發訊息。若訊息發送失敗，附件可能已經上傳；**先檢查 item 留言串再決定要不要重試**，
避免重複附件。

## scopes

這條流程的 external dependency scopes 是 `files:write`、`chat:write`，以及查找既有 item 留言串沿用的讀取
scopes（目前私有 channel 使用 `groups:history`；程式只呼叫 `conversations.history`、`conversations.replies`，不需要 `groups:read`）。
新增或調整 scope 後必須重新 Install app，並改用 rotation 後的新 token 重試，舊 token 已經失效。
