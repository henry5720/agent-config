# 跨 agent 串接 skill：研究

研究日期：2026-10-09。對應決策票：[跨 agent 串接 skill 的機制](https://github.com/henry5720/agent-config/issues/14)。這份文件提供事實與研究建議，流程採用哪個觸發方式仍由後續決策票決定。

| 要接著做的事 | 三家可共用的部分 | 需要個別適配的部分 | 能否在人離開後啟動 |
| --- | --- | --- | --- |
| 建 PR 後，在同一 session 讀下一支 skill | 在上一支 skill 寫明下一步、傳 PR URL；共用 SKILL.md 工作指引 | Claude `/skill-name`、Codex `$skill-name`、OpenCode `skill` tool／custom command | 活躍 turn 可以繼續；指引本身不會監聽 GitHub |
| agent 回答完成後再續跑 | 共用「讀取 PR 狀態」script 與 skill | Claude／Codex Stop hook；OpenCode plugin event | 需 client/session 存活；各家的 continuation 語義不同 |
| PR、review、comment 到來才啟動 | GitHub Actions events、gh/API 資料讀取、固定 prompt／skill 路徑 | 啟動 CLI、認證、權限與輸出轉接器 | 可以，但 approval、runner、憑證仍可能擋住 |
| 定時查 PR | cron／Actions schedule 與固定 prompt | client 內建排程、local app 存活條件 | 外部 runner 可以；local 排程依產品而定 |
| 把下一步送給現有 terminal agent | Herdr agent prompt/wait 支援三種 kind | 各 client 的 readiness／approval UI | Herdr session 與 agent 必須仍活著 |

## 必須先分開的兩件事

**skill 告訴 agent 做什麼；hook、排程或外部程式決定什麼時候啟動。** Claude 的明確 slash invocation、Codex 的 `$skill`、OpenCode 的 skill tool 都能載入工作指引，但三家沒有共用的「上一支 skill 完成」事件。把「建 PR 後呼叫下一支 skill」寫進 SKILL.md，可以要求目前 agent 接著做；這仍是模型遵循文字指令，不是具備重試、去重與狀態轉移保證的 workflow engine。[C1][O1][P1]

真正要保證先 A 後 B，外部 script 必須等 A 的 process 完成、檢查 PR 與輸出，再啟動 B。這可以把觸發與錯誤處理做成程式；B 是否正確解讀 review、採用哪個修改仍由 agent 決定。退出碼／「idle」只代表 process 或 UI 狀態，不能代替 PR checks／review 結果。[O2][H1]

## Codex：目前已有 hooks，不應沿用「沒有 hooks」的舊結論

官方文件列出 `SessionStart`、`PreToolUse`、`PostToolUse`、`UserPromptSubmit`、`Stop` 等事件；hooks 預設開啟，`[features].hooks = false` 可停用。非 managed hooks 必須 review/trust 精確內容，修改後重新審查；project hooks 還需要 trusted project。可以放在 `.codex/hooks.json` 或 config.toml，但這不是三家共用設定。[O3]

同步 `Stop` hook 回傳 `{"decision":"block","reason":"…"}`，會建立 continuation prompt 繼續目前 Codex。這是「回答結束時接著做」，不是「GitHub PR 建立／新留言事件」；reason 可以指示載入下一支 skill，但 hook 本身沒有直接執行 skill 的跨 client API。`stop_hook_active` 表示此 turn 已經被 Stop 續跑過，可讓自訂 script 防止反覆要求同一步。[O3]

`async: true` command hook 只在下一個安全點送回資訊：idle 時會等下一個 user turn，**完成 background hook 不會啟動新 turn**。它不能 block／approve／rewrite／控制原操作；session 結束會取消未完成 hook。要 continuation 必須使用同步 hook。[O3]

`codex exec` 可在 scripts／CI 執行，支援 JSONL、output schema 與 resume；不是一定要有人守著 TUI。外部 orchestration 必須先提供適合的 sandbox／approval 設定，不能把互動確認當作無人值守的流程步驟。`--dangerously-bypass-hook-trust` 是官方為已在外部驗證 hooks 的 automation 提供的特殊旗標，不應當作預設設定。[O2][O3]

目前 `skills` 文件也區分 explicit `$skill` 與 implicit description matching；`agents/openai.yaml` 的 `policy.allow_implicit_invocation: false` 禁止 implicit invocation，explicit 仍可使用。不要把 Claude 的 frontmatter 開關當作 Codex 同名保證。[O1]

官方開源 `core/src/hook_runtime.rs` 有 Stop／SubagentStop dispatch；`exec/tests/suite/hooks.rs` 有 noninteractive SessionStart hook 測試。這驗證目前 main source 有 headless hook 路徑，**本研究沒有在本機執行這些測試**；main 不等於每個已發行版本。[O4][O5]

## Claude Code 與 OpenCode

| 能力 | Claude Code | OpenCode |
| --- | --- | --- |
| headless skill／command | `claude -p "/skill-name args"` 先展開 user-invoked skill；舊的「headless 不支援 slash」說法已過期 [C2] | `opencode run --command <name> <args>` 執行 custom command；skill 另外由 `skill` tool 載入 [P2][P1] |
| 已存對話續跑 | `--resume SESSION_ID`／`--continue`；live background resume 有下述限制 [C2][C6] | `--session`／`--continue`／`--fork` [P2] |
| 完整 background session | `--bg`／`--background` 由 supervisor 管理，關 terminal 仍跑、shutdown 停；不能與 `-p` 組合 [C3][C7] | `serve` + `run --attach`，server 提供 session API [P2][P4] |
| lifecycle 入口 | `Stop`、`PostToolUse` 等 hooks [C4] | plugin `session.idle`、`command.executed`、`tool.execute.after` [P3] |
| 指定 session 的程式入口 | live background `--resume` 是 attach，不是任意 queue [C6] | SDK `session.prompt`／`session.command`；HTTP `POST /session/:id/command`、`prompt_async`（nonblocking 204）[P4][P5] |

Claude `Stop` 是每次 main agent 回應完成；OpenCode `session.idle` 是 idle，兩者都不是「PR 已建立」。`PostToolUse`／`tool.execute.after` 只表示 tool 執行後，若要辨識建 PR 必須自訂判斷，不能只看工具名稱。[C4][P3]

Claude 同步 Stop `decision: block`／`additionalContext` 可續跑，但需注意 `stop_hook_active` 與連續 continuation cap（官方列八次）。`async: true` command hook 不能控制原流程；Claude 另有 `asyncRewake` exit 2 喚醒 idle，這與 Codex background hook 不啟新 turn 的語義不同。`-p` 結束會 kill 未完成 async hooks；完整 background session、async hook、background shell job 必須分開討論。[C4][C3]

Claude `disable-model-invocation: true` 禁止 model 自主 invoke；`context: fork` 不繼承 conversation history。OpenCode 只辨識 `name`、`description`、`license`、`compatibility`、`metadata`，其他 frontmatter ignored。因此不能把 Claude 的 disable／fork／background 開關當跨 client 契約。[C1][P1]

Claude `/loop 20m /review-pr 1234` 能排程 skill，但遇 `disable-model-invocation: true` 只傳 plain text，不執行 skill；最多五十個 tasks、recurring 七天到期、busy 時錯過的 fires 只補一次，且有 jitter。新版本 background session 可接手 loop，因此不能說 terminal 關掉就一定停；獨立 unattended schedule 還有 Routines／desktop schedule／Actions 等不同入口。[C5][C7] 本研究查閱的 OpenCode CLI／plugins／SDK／server 文件沒有找到內建 scheduler，不能據此宣稱所有版本都沒有。

Claude v2.1.285+ `--resume` 正在跑的 background session 會 attach 同一 process，連 terminal 上 `-p --resume` 也會 attach。有 pipe／redirect、JSON output 或部分設定 flags 會不送訊息且 exit 1；prompt 以 `/` 或 `!` 開頭不送。因此它不能直接代替「送下一支 skill 到 live session」的通用 headless queue。[C6]

## GitHub Actions、gh script 與留言讀取

Actions 的 `pull_request`、`pull_request_review`、`pull_request_review_comment`、`issue_comment` 可分別對應 PR、review、inline comment 與一般留言；`issue_comment` 包含 issue 和 PR，需檢查 payload 是否有 `issue.pull_request`。這些事件啟動的是 runner 上的新 job，不是本機原 session 繼續。若要精確銜接建 PR 的 command，也可在 command 得到 PR URL 後呼叫下一個 script／`workflow_dispatch`。[G1]

**最新官方文件有新的 GITHUB_TOKEN 例外，不能只寫「bot 建 PR 不會觸發」。** `workflow_dispatch`／`repository_dispatch` 會啟動；用 repository GITHUB_TOKEN 造成的 PR `opened`／`synchronize`／`reopened` 會產生 **approval-required** runs，要有 write access 的人批准才開始。其他事件仍受避免 recursive workflow 的規則限制。使用者的 gh 認證與 workflow 的 GITHUB_TOKEN 也不應混為一談。[G2]

Actions `schedule` 最短五分鐘、跑 default branch，繁忙時可能延遲甚至丟棄排隊 job；public repo 60 天沒有活動會停用。因此適合定期補查，不能保證 review 到來後立即接手。[G1]

官方 `openai/codex-action` 會安裝 Codex 並跑 `codex exec`；需要認證、checkout、prompt 與明確 permissions。三家可共用的其實是 GitHub event + gh/API script + skill 內容，agent 啟動與認證仍要分別適配。[O6][G1]

讀 review 至少要分三層：

| 資料 | 讀取入口 | 可用來回答什麼 |
| --- | --- | --- |
| PR 的一般討論留言 | `gh pr view <PR> --comments`；REST issues comments | 有沒有人在 conversation 說話 |
| 整體 review 與狀態 | gh `reviews` JSON／REST pulls reviews | APPROVED／CHANGES_REQUESTED，以及 review 摘要 |
| inline code comments／thread 狀態 | `gh api repos/{owner}/{repo}/pulls/{pull_number}/comments`；GraphQL `reviewThreads` | 哪一行被指正、thread 是否已 resolved |

`--comments` 的描述只是「View pull request comments」，不能因此聲稱已讀完所有 inline threads；要依 review 決策需要額外取資料並處理分頁。來源：[G3][G4][G5]。事件 payload 只是一個新事件，不能代替重新查目前 PR／最新 head／thread 狀態；這是避免用過期資料做下一步的研究建議。

## Herdr：共用 terminal 協調，不是 PR scheduler

已安裝 skill 與 CLI 都提供 `herdr agent start … --kind claude|codex|opencode`、`agent prompt … --wait`、`agent wait`。它可把下一支 skill 的 prompt 送到已存在、準備好的 agent，因此三家可共用 terminal transport。[H1]

`prompt --wait` 等的是首個 settled `idle`／`done`／`blocked` 狀態，不是某支 skill 的機械式 completion；agent 已在 working 時，正在跑的 turn 完成也可能滿足等待。`blocked` 表示 approval／question UI；skill 明確要求查看 UI 並詢問人，不能偷偷答 approval。 timeout／stalled 不證明沒送達，不能盲目重送。Herdr 沒有在這份官方 skill 中提供 GitHub PR webhook 或 review 排程；要等 comment 仍須外部事件／查詢。[H1]

## 排程不能跨產品名稱直接套用

2026-10-09 查證 OpenAI `/codex/automations` 會導向 `https://learn.chatgpt.com/docs/automations`（ChatGPT desktop scheduled tasks 文件）：CLI 沒有 Scheduled 管理介面。local project 需要電腦開著、desktop app 運行；web/mobile 的 supported GitHub app event tasks 則受方案、workspace 權限與 connector repository access 限制，並不提供本機 folder。既有 chat 排程可以回到同一 chat，standalone 每次新 chat。這些都不是三個 CLI 共用的 scheduler。[O7]

## 研究建議與尚待決定的事

建議後續流程把「建 PR 後立刻續跑」與「未來 review 到來後再跑」寫成不同觸發需求：前者可以同一 turn 明確讀下一支 skill，後者需要 GitHub event／外部定時程式。若三家共用是硬需求，把 PR 資料讀取、狀態判斷與去重放在共用 script，client adapter 只負責載入指定 skill 與回傳結果；不把 native hook 設定當共用格式。

這只是研究建議，尚未決定採用 Actions、本機 runner、Herdr 或產品排程，也沒有新增這些實作。選擇前仍要在人機討論確認：離開電腦多久還要運作、哪些寫入可無人批准、何時停止等待 review，以及是否必須保留原 session context。

## 驗證與缺口

本機只做 read-only discovery：`claude --version` → `2.1.295 (Claude Code)`；`codex --version` → `codex-cli 0.161.0`（PATH alias read-only warning、exit 0）；`opencode --version` → `1.18.35`；`herdr --version` → `0.9.3`；父 session `gh --version` → `2.102.0`。`codex exec --help` 查到 resume／fork／JSON／output-schema／hook trust 旗標；`herdr --help`、`herdr agent` 查到三家 kind 與 prompt/wait；command group discovery `herdr agent` 是 help output、exit 2，沒有啟動 agent。父 session `codex features list` 查到 `hooks stable true`。

官方文件與 main source 是文件／source 查證，不是本機 end-to-end 實測。**未驗：**真正建 PR 後 skill 串接、hook continuation／trust、headless skill loading、review webhook、Actions／bot approval、Herdr prompt／blocked、排程運行與跨機器復原。研究子 agent 沒有執行 PR agent、workflow、pane control、skill 修改或寫入 GitHub。各機器的版本、認證及 managed policy 也未盤點。文件靜態檢查已確認二十五個來源代號都有定義、無殘留 placeholder；`git diff --no-index --check /dev/null docs/skills/cross-agent-skill-chaining-research.md` 無 whitespace error（exit 1 表示新檔 diff 存在）。

## 一手來源

- [O1] [OpenAI：Build skills](https://developers.openai.com/codex/skills)
- [O2] [OpenAI：Non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [O3] [OpenAI：Hooks](https://developers.openai.com/codex/hooks)
- [O4] [Codex source：hook_runtime.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/hook_runtime.rs)
- [O5] [Codex source：exec hooks test](https://github.com/openai/codex/blob/main/codex-rs/exec/tests/suite/hooks.rs)
- [O6] [OpenAI：GitHub Action](https://developers.openai.com/codex/github-action)
- [O7] [OpenAI：Scheduled tasks](https://learn.chatgpt.com/docs/automations)（`https://developers.openai.com/codex/automations` 在 2026-10-09 redirect 至此）
- [G1] [GitHub：Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [G2] [GitHub：Triggering a workflow from a workflow](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow)
- [G3] [GitHub CLI：gh pr view](https://cli.github.com/manual/gh_pr_view)
- [G4] [GitHub REST：Pull request review comments](https://docs.github.com/en/rest/pulls/comments)
- [G5] [GitHub GraphQL：PullRequest.reviewThreads](https://docs.github.com/en/graphql/reference/objects#pullrequest)
- [H1] [Herdr first-party skill](https://github.com/henry5720/agent-config/blob/main/skills/herdr/SKILL.md)，本機實際讀取 `/home/ubuntu/.config/skillshare/skills/herdr/SKILL.md` 與 `herdr --help`／`herdr agent`。

- [C1] [Claude Code：Skills](https://code.claude.com/docs/en/skills)
- [C2] [Claude Code：Headless](https://code.claude.com/docs/en/headless)
- [C3] [Claude Code：CLI reference](https://code.claude.com/docs/en/cli-reference)
- [C4] [Claude Code：Hooks](https://code.claude.com/docs/en/hooks)
- [C5] [Claude Code：Scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)
- [C6] [Claude Code：Resume a running background session](https://code.claude.com/docs/en/sessions#resume-a-running-background-session)
- [C7] [Claude Code：Agent view](https://code.claude.com/docs/en/agent-view)
- [P1] [OpenCode：Skills](https://opencode.ai/docs/skills/)
- [P2] [OpenCode：CLI](https://opencode.ai/docs/cli/)
- [P3] [OpenCode：Plugins](https://opencode.ai/docs/plugins/)
- [P4] [OpenCode：Server](https://opencode.ai/docs/server/)
- [P5] [OpenCode：SDK](https://opencode.ai/docs/sdk/)
