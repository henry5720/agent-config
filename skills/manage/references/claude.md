# Claude Code 原生操作

派工前讀本 reference，操作依當下 CLI `--help`、工具 schema 與實際模式核對；共用 brief、worktree、review、驗收規則以 [manage](../SKILL.md) 為準。

## Subagent

用原生 `Agent` 工具，角色與任務寫在 brief；依實際 schema 選背景執行，manager 可做不相依工作，完成通知帶回最終報告。
後續聯繫用原生 `SendMessage`，依 schema 使用既有 agent 識別碼。權限提示浮到 manager，executor 有問題則回報 manager，由 manager 問使用者。

reviewer 必須明確建立 **non-fork** subagent；互動 session 的 fork 預設不能當 context 隔離。
檢查 `Agent` schema 的隔離選項，確認可以不繼承父對話後才派 reviewer；缺這項能力按主流程停止 review。
Claude 原生 worktree isolation 不能繞過 herdr-worktree：操作對準 brief 指定的專用 worktree，避免再建立未受管理的臨時 worktree。

## 可接手背景 session

先核對 `claude --help`，沿用原生背景啟動與既有權限模式：

```bash
claude --bg --permission-mode auto -n "<票號或任務短名>" "<開頭指令與完整 brief>"
```

在 brief 指定的 worktree 啟動，將路徑與 branch 核對列為首項。
需要手動 skill 時，prompt 開頭使用使用者指定的 slash command，例如 `/implement <issue URL>`、`/diagnosing-bugs`、`/resolving-merge-conflicts`、`/research`；先確認相應 skill 存在且符合任務。
讀輸出確認 skill 載入與執行，不能僅憑 prompt 中出現名稱判定。
`--permission-mode auto` 沿用既有設定，不承諾完全無權限提示；背景 session 需要人處理時提供 attach 方式。

記錄啟動回傳的 ID，再以 `claude agents --json --all` 核對相同 ID 與狀態。
觀察到 `working` 或日誌證明已工作才算派出；工作快速完成時仍讀日誌確認，ID 不存在時先診斷。

## 等待、讀取與接手

背景 Bash 可用 `run_in_background` 等離開 `working`，主 session 不被占住；用實際 schema 啟動。
以下輪詢只提供喚醒訊號；消失或非 working 後仍須按主流程查狀態與輸出：

```bash
while true; do
  agents_json=$(claude agents --json --all) || exit 1
  state=$(printf '%s' "$agents_json" | jq -er --arg id "<session-id>" \
    'map(select(.id == $id)) | .[0].state // "gone"') || exit 1
  [ "$state" = "working" ] || break
  sleep 5
done
```

`claude agents --json --all` 的指令錯誤、JSON 解析錯誤與 timeout 要回報；不能把輪詢未查到有效狀態解讀為仍在工作或已完成。缺背景 Bash 能力時，以短原生狀態查詢配合不相依工作；任務必要能力不足依主流程停止。

用 `claude logs <session-id>` 讀進度、blocker、最終回報與手動 skill 啟動證據。
`claude agents` 讓使用者找到背景 session；`claude attach <session-id>` 進入回答問題、改方向或討論 findings。
後續背景訊息依原生 attach／輸入方式，不假設 `SendMessage` 可寄給 CLI 背景 session；處理後核對原 ID，繼續等原任務。
reviewer 背景 session 也用相同操作，但 prompt 明確唯讀、固定 SHA 與 axis，讀回 findings 後交 manager 彙整。

## 模式與限制

`claude -p` 若有任務必要原生工具即可執行；需要接手、手動 skill 或 non-fork review 而工具缺失，就指出缺項並請切換 Claude Code 互動 session。
容量暫滿先等可用名額；工具缺失是停止原因。兩者都不授權跨 provider。
