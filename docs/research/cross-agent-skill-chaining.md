# 跨 agent 串接 skill 的機制

> 對應 issue：[henry5720/agent-config#14](https://github.com/henry5720/agent-config/issues/14)（map：#12）
> 調查日期：2026-10-09。本機版本：Claude Code 2.1.295、codex-cli 0.161.0、opencode 1.18.35、gh 2.102.0。
> 標 **〔未驗〕** 的是官方文件沒寫清楚、或我沒實際跑過的推論。

## 結論

PR 開出來之後要讓 agent 自己往下接（`pr-review` → 修 → 瀏覽器驗 → 回 comment），三家**都能用**的只有兩條：

1. **一支 skill 在自己的步驟裡寫「做完接著讀下一支 skill」**（skill 串 skill）。三家都把 skill 當成 agent 可自行載入的指令，同一個 session 裡就能接下去，人要在場啟動第一步，之後不用。
2. **外部 script 用各家的 headless 模式逐步呼叫**（`claude -p` / `codex exec` / `opencode run`），步驟之間用 `gh` 讀 PR 狀態與 comment。這條可以放在本機（herdr、cron、shell）或放進 GitHub Actions。

各家獨有的 Stop hook、`/loop`、`/goal`、cloud routine、plugin event 都能做「自動接下一步」，但寫法互不相容，流程不能依賴它們。

---

## 1. Claude Code

### 1.1 Hooks（`Stop` / `SubagentStop` / `PostToolUse`）

- 有 33 個 hook event，其中 `Stop`、`SubagentStop` 可以回 `decision: "block"` + `reason`，效果是「不讓 Claude 停，繼續對話」；也可用 `hookSpecificOutput.additionalContext` 塞非錯誤的接續提示。
  來源：<https://code.claude.com/docs/en/hooks>（decision control 表格）
- 防無限迴圈：Stop hook 輸入有 `stop_hook_active`（已因 stop hook 繼續過時為 `true`）；另有「連續 8 次 continuation 上限」，超過就強制結束，`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` 可調。同頁 Stop 段。
- Hook handler 除了 `command`，還有 `type: "prompt"`（單輪 model 判斷）與 `type: "agent"`（可用 Read/Grep 的 subagent，標示 experimental）。
- 用在串接：Stop hook 判斷「PR 已建立但還沒跑 review」→ block 並在 `reason` 寫「接著執行 /pr-review <N>」。
- 要人在場嗎：不用回答，但要有一個 session 在跑（hook 掛在 session 上）。
- 能讀 PR comment 嗎：hook 是 shell script，可以自己呼 `gh`；Claude 本身也能用 Bash 跑 `gh`。
- 權限：hook 以使用者身分執行，不受 permission mode 管。`-p` 模式不加 `--bare` 時會執行專案 `.claude/settings.json` 的 hooks，且沒有 workspace trust 對話框（<https://code.claude.com/docs/en/headless>）。
- 成本：只吃該 session 的 token。

### 1.2 `/loop`、cron 工具、`/goal`

- `/loop [interval] <prompt>`：session 內定時重跑 prompt，可以把 skill 當 prompt（`/loop 20m /review-pr 1234`）；不給 interval 時 Claude 自選 1 分鐘～1 小時的間隔。官方範例正好是「`/loop check whether CI passed and address any review comments`」。
  來源：<https://code.claude.com/docs/en/scheduled-tasks>
- 限制（同頁）：session-scoped，關掉 terminal 就停；一個 session 最多 50 個排程；recurring task 7 天後自動過期；`disable-model-invocation: true` 的 skill 在排程觸發時不會執行（會變成純文字）。
- 不帶 prompt 的 `/loop` 有內建 maintenance prompt：繼續未完成的工作 → 處理當前分支 PR 的 review comment、失敗的 CI、merge conflict。可用 `.claude/loop.md` 或 `~/.claude/loop.md` 覆寫。
- `/goal <條件>`：每輪結束後另一個 model 判斷條件是否達成，沒達成就自動再跑一輪。適合「把所有 review comment 處理完」這種有終點的事。
  來源：<https://code.claude.com/docs/en/goal>
- 要人在場：session 要開著，但不用人回應。

### 1.3 Skill 叫 skill

- Skill 預設 Claude 可以自行叫用（Skill tool），除非 frontmatter 設 `disable-model-invocation: true`。`context: fork` 讓 skill 跑在獨立 subagent。
  來源：<https://code.claude.com/docs/en/skills>（frontmatter reference）
- 所以「pr-review 最後一步寫：修完後叫 verify-in-browser」在同一個 session 裡就會接上。被串的 skill 不能設 `disable-model-invocation: true`。

### 1.4 Headless（`claude -p`）

- `claude -p "<prompt>"`；`--output-format json` 回傳 `session_id` 與 `total_cost_usd`；`--resume <id>` / `--continue` 接著同一段對話；`--allowedTools`、`--permission-mode`（`auto`／`dontAsk`／`acceptEdits`）、`--permission-prompts none`（無人值守時把會問人的請求一律拒絕）。
- `-p` 裡可以直接寫 `/skill-name`，會展開成 skill。
- `--bare` 不讀 hooks／skills／CLAUDE.md，且**不用訂閱登入**，要 `ANTHROPIC_API_KEY`。
  來源：<https://code.claude.com/docs/en/headless>
- 用在串接：script 依序 `claude -p "/pr-review 123" --output-format json` → 取 `session_id` → `claude -p --resume $id "/verify-in-browser ..."`。

### 1.5 GitHub Actions（`anthropics/claude-code-action@v1`）

- 兩種模式：沒給 `prompt` 時等 `@claude` 提及（`issue_comment`、`pull_request_review_comment`、review）；給 `prompt` 時任何 GitHub event（含 `pull_request`、`schedule`）都直接跑。`prompt` 可以是 `/skill-name`（需先 `actions/checkout`）。
- 認證：`ANTHROPIC_API_KEY`，或 `CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` 產生，吃個人訂閱額度）；也支援 OIDC federation、Bedrock/Vertex/Foundry。
- 觸發者檢查：issue/PR event 的觸發者要有 write 權限；bot 觸發一律拒絕，除非列在 `allowed_bots`（防止 bot 互相觸發成迴圈）。
- 成本：GitHub Actions 分鐘數 + token；建議 `--max-turns`、workflow timeout、concurrency 控制。
  來源：<https://code.claude.com/docs/en/github-actions>
- runner 上沒有本機瀏覽器環境、測試機帳號，`verify-in-browser` 要另外在 workflow 裝 Playwright 與 secrets 〔未驗：沒試過在 Action 裡跑我們的 verify-in-browser〕。

### 1.6 Routines（cloud，`/schedule`）

- 在 Anthropic 雲端跑，可用 schedule、API POST、GitHub event 觸發；GitHub event 只支援 **Pull request** 與 **Release** 兩類（沒有 issue comment）。每次 event 開新 session，不重用。
- 全自動，沒有 permission prompt；以你的 GitHub 身分 commit／留言；fresh clone，讀不到本機檔案。
- 限制：research preview；scheduled run 每帳號每小時 100 次、API／Run now 每 routine 每小時 30 次；GitHub event 有每 routine／每帳號的每小時上限，超過直接丟棄；吃訂閱額度。
  來源：<https://code.claude.com/docs/en/routines>

---

## 2. OpenAI Codex CLI

### 2.1 Hooks

- 事件：`PreToolUse`、`PermissionRequest`、`PostToolUse`、`PreCompact`、`PostCompact`、`UserPromptSubmit`、`SubagentStart`、`SubagentStop`、`Stop`、`Interrupt`、`SessionStart`、`SessionEnd`。預設啟用（`[features].hooks`）。
- `Stop` 回 `{"decision":"block","reason":"..."}`（或 exit 2 + stderr）時，Codex **把 `reason` 當成新的 user prompt 繼續跑**；有 `stop_hook_active` 可防迴圈。
- 非 managed 的 hook 要先 review 並 trust（以 hash 記錄，改了要重新 trust）；`--dangerously-bypass-hook-trust` 可略過。專案 `.codex/` 的 hook 只在專案被 trust 時載入。
- 有 MCP tool hook 與 background hook（background 不能 block 或控制接續）。
  來源：<https://learn.chatgpt.com/docs/hooks.md>（`developers.openai.com/codex/llms.txt` 導向此處）
- 和 Claude Code 的 Stop hook 輸出格式幾乎一樣，但設定檔位置與 trust 流程不同，要各寫一份。

### 2.2 `/goal`、排程

- CLI 有 `/goal <objective>`（`edit`／`pause`／`resume`／`clear`），讓目標跟著 chat 持續追蹤。
  來源：<https://learn.chatgpt.com/docs/developer-commands.md?surface=cli>
  〔未驗：文件只說「keeps the goal attached」，沒寫清楚會不會像 Claude 的 `/goal` 一樣每輪自動評估並自動續跑〕
- **Codex CLI 本身沒有 `/loop` 類排程**。Scheduled tasks 在 ChatGPT desktop app（本機，要開著電腦和 app）與 web；「GitHub PR 活動觸發」只在 ChatGPT web/mobile，**明寫 CLI 與 IDE extension 不支援**。GitHub trigger 可選 reviews、comments、commit updates 或 merge。排程以 `approval_policy = "never"` 跑。
  來源：<https://learn.chatgpt.com/docs/automations.md>

### 2.3 Skill 叫 skill

- 顯式：prompt 裡寫 `$skill-name` 或 `/skills`；隱式：任務符合 skill `description` 時 Codex 自選。
  來源：<https://learn.chatgpt.com/docs/build-skills.md>
- 所以 skill 內寫「接著用 `$verify-in-browser`」可接上。〔未驗：沒找到文件明說 skill 內文提到另一支 skill 會被當作顯式叫用〕

### 2.4 Headless（`codex exec`）

- 預設 read-only sandbox；`--sandbox workspace-write` 允許改檔；`--json` 輸出 JSONL 事件；`--output-schema` 結構化輸出；`codex exec resume --last` / `resume <SESSION_ID>` 接續上一段；還有 `codex exec review` 子命令。需要在 git repo 內。
- 認證：預設沿用 CLI 登入；CI 用 `CODEX_API_KEY`（文件警告不要設成 job-level env）；也可用 ChatGPT 管理的 `auth.json`（進階）。
  來源：<https://learn.chatgpt.com/docs/non-interactive-mode.md>；本機 `codex exec --help` 確認 `resume`／`fork`／`review` 子命令存在。

### 2.5 GitHub Action（`openai/codex-action@v1`）與 `@codex`

- Action 安裝 CLI、啟動 Responses API proxy、跑 `codex exec`；輸入 `prompt` 或 `prompt-file`、`sandbox`、`codex-args`、`safety-strategy`（預設 `drop-sudo`）、`allow-users`／`allow-bots`（預設只有 write 權限者可觸發）。輸出 `final-message`，**官方範例是另開一個 job 用 `actions/github-script` 把結果貼回 PR**，Action 本身不直接留言。認證是 `OPENAI_API_KEY`（API 計費）。
  來源：<https://learn.chatgpt.com/docs/github-action.md>
- Codex cloud 的 GitHub 整合：PR 留言 `@codex review`、可開 Automatic review；`@codex fix the P1 issue` 會開 cloud chat 並可推 fix。這條跑在 OpenAI 雲端、不讀本機 skill 〔未驗：cloud 是否載入 repo 內 `.agents/skills`〕。
  來源：<https://learn.chatgpt.com/docs/third-party/github.md>

---

## 3. OpenCode

### 3.1 Plugins（相當於 hooks）

- JS/TS plugin 訂閱事件：`session.idle`、`session.created`、`session.error`、`tool.execute.before/after`、`permission.*`、`command.*`、`tui.prompt.append`…；plugin 拿到 `client`（SDK client）與 `$`（shell）。
  來源：<https://opencode.ai/docs/plugins/>
- SDK 有 `session.prompt({ path, body })`（送 prompt，`noReply: true` 只塞 context）與 `session.command(...)`（送 slash command）。
  來源：<https://opencode.ai/docs/sdk/>
- 用在串接：plugin 聽 `session.idle` → 用 `gh` 判斷狀態 → `client.session.prompt` 送「接著跑下一步」。〔未驗：文件沒有在 `session.idle` 裡回送 prompt 的範例，也沒寫防迴圈機制，要自己做〕

### 3.2 排程

- OpenCode 本身沒有 `/loop` 或排程功能（在 CLI、commands、plugins 文件中都找不到 schedule／cron／loop）。排程只有透過 GitHub Actions 的 `schedule` event。〔未驗：可能有第三方 plugin〕

### 3.3 Slash command 與 skill

- 自訂 command（`.opencode/commands/*.md`），支援 `$ARGUMENTS`、指定 `agent`／`model`、`subtask: true` 強制以 subagent 執行。
  來源：<https://opencode.ai/docs/commands/>
- Skill 透過原生 `skill` tool 按需載入；搜尋路徑包含 `.opencode/skills`、`~/.config/opencode/skills`、`.claude/skills`、`~/.claude/skills`、`.agents/skills`、`~/.agents/skills`。權限可對 `skill` 設 allow/ask/deny。
  來源：<https://opencode.ai/docs/skills/>、<https://opencode.ai/docs/permissions/>
- 所以 skill 內寫「接著載入 verify-in-browser」agent 可自己用 skill tool 接上。

### 3.4 Headless（`opencode run`）

- `opencode run [message]`、`--command <name>`（跑自訂 command）、`-c/--continue`、`-s/--session <id>`、`--fork`、`--format json`、`--attach http://localhost:4096`（接到 `opencode serve` 的常駐 server）、`--auto`（自動核准沒被明確 deny 的權限，help 標示 dangerous）。
  來源：<https://opencode.ai/docs/cli/>；本機 `opencode run --help` 確認。
- 〔未驗：沒有 `--auto` 時，`opencode run` 遇到 `ask` 權限是卡住還是拒絕〕

### 3.5 GitHub（`anomalyco/opencode/github@latest`）

- `opencode github install` 一鍵設定；留言 `/opencode` 或 `/oc` 觸發。支援 `issue_comment`、`pull_request_review_comment`（帶檔案路徑、行號、diff）、`issues`、`pull_request`、`schedule`、`workflow_dispatch`（後四個需要 `prompt` input）。
- 認證：模型 provider 的 key（例 `ANTHROPIC_API_KEY`）放 env；GitHub 端預設用 OIDC 換 OpenCode App installation token，或 `use_github_token: true` 改用自己的 `GITHUB_TOKEN`（要自己給 `contents/pull-requests/issues: write`）。
  來源：<https://opencode.ai/docs/github/>

---

## 4. 不綁 agent 的做法

### 4.1 Skill 串 skill（寫在 SKILL.md 裡）

三家都支援 agent 自行載入 skill（Claude 的 Skill tool、Codex 的隱式／`$` 叫用、OpenCode 的 skill tool），而且同一份 skill 三家都讀得到：Claude 讀 `~/.claude/skills`，Codex 讀 `$HOME/.agents/skills`（<https://learn.chatgpt.com/docs/build-skills.md>），OpenCode 兩個都讀（3.3 節），skillshare 再負責同步。在 `pr-review` 結尾寫「下一步：載入 `verify-in-browser`」是成本最低、三家通用的串法。

- 人在場：要人觸發第一支；中間如果遇到權限詢問還是要人。
- 讀 PR comment：靠 skill 內寫好的 `gh` 指令。
- 限制：串接靠 model 遵守指示，不是硬保證；context 會越疊越長。Claude 端被串的 skill 不能設 `disable-model-invocation: true`。

### 4.2 `gh` CLI script + headless agent

```
gh pr create … → claude -p / codex exec / opencode run "<下一支 skill>"
             → gh pr checks <N> --watch --fail-fast
             → gh api …/pulls/<N>/comments（讀 inline review comment）
             → 再呼叫 agent 修 → gh pr comment <N> --body-file …
```

- `gh pr checks --watch`、`gh pr view --comments` 本機確認存在（gh 2.102.0）。`gh pr view --comments` 不含 inline review thread，要用 `gh api repos/{owner}/{repo}/pulls/{n}/comments` 或 GraphQL `reviewThreads`（後者才看得到 resolved 狀態）。〔未驗：`gh pr view --comments` 是否包含 inline comment，我是依經驗判斷〕
  REST 文件：<https://docs.github.com/en/rest/pulls/comments>
- 人在場：不用。權限：本機 `gh auth` 的身分，各家 agent 自己的登入。成本：本機跑，只有 token。
- 換 agent 只換一行命令，這是三家最一致的介面。

### 4.3 GitHub Actions 裡跑 agent

三家都有官方 action（第 1.5、2.5、3.5 節），觸發與權限模型類似：

- 能讀 PR comment：都能（`issue_comment`／`pull_request_review_comment` event payload，或 agent 內用 `gh`）。
- 不用人在場，但要把 API key 放進 repo secrets；Claude 可用訂閱 OAuth token，Codex action 只寫了 `OPENAI_API_KEY`，OpenCode 用模型 provider 的 key。
- **串接陷阱**：用預設 `GITHUB_TOKEN` 產生的 event（留言、push）**不會觸發新的 workflow run**，只有 `workflow_dispatch`、`repository_dispatch` 例外。所以「agent A 留言 → 觸發 agent B 的 workflow」用 `GITHUB_TOKEN` 接不起來，要用 GitHub App token／PAT 或 `workflow_dispatch`。
  來源：<https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow>
- 另外 Claude action 預設拒絕 bot 觸發（`allowed_bots`），Codex 有 `allow-bots`，也會擋掉 bot 串 bot。
- 成本：Actions 分鐘數 + API token。瀏覽器驗收要在 runner 裝瀏覽器、放測試帳號 secrets，比本機麻煩。

### 4.4 herdr（terminal multiplexer）

- 本機 `herdr agent` 支援 `start <name> --kind claude|codex|opencode|…`、`prompt <target> <text> --wait --timeout`、`wait --until idle|done|blocked`、`read`。`prompt --wait` 會等 agent 進入 `idle`／`done`／`blocked`。
  來源：本機 `herdr agent` 輸出與 `~/.claude/skills/herdr/SKILL.md`（沒有找到公開的官方文件網址〔未驗〕）。
- 用在串接：orchestrator（script 或另一個 agent）在 PR 建立後 `herdr agent prompt reviewer "/pr-review 123" --wait` → 讀結果 → 再 prompt 下一個 agent。三家 agent 都在 kind 清單內，是本機最直接的跨 agent 編排。
- 人在場：herdr server 要在跑（`HERDR_ENV=1`）；遇到 `blocked`（權限詢問）時 skill 規定要問人，不能代答。
- 讀 PR comment：靠 pane 裡的 agent 或 orchestrator 自己跑 `gh`。
- 成本：本機，只有各 agent 的 token。

---

## 比較表

| 機制 | Claude Code | Codex CLI | OpenCode | 要人在場 | 讀 PR comment | 主要限制 |
| --- | --- | --- | --- | --- | --- | --- |
| Skill 串 skill | ✅ Skill tool | ✅ `$skill`／隱式 | ✅ skill tool | 啟動第一步 | 靠 skill 內 `gh` | 靠 model 遵守，非硬保證 |
| Stop hook 接續 | ✅ `decision: block` | ✅ `reason` 變新 prompt | ⚠️ plugin `session.idle` + SDK（未驗） | session 開著 | hook 跑 `gh` | 三家設定格式不同 |
| session 內輪詢 | ✅ `/loop`、`/goal` | ⚠️ `/goal`（自動續跑未驗） | ❌ | session 開著 | ✅ | Claude `/loop` 7 天過期、50 個上限 |
| 雲端 / app 排程 | ✅ Routines（PR／Release event） | ⚠️ ChatGPT app/web，CLI 不支援 event | ❌ | 不用 | ✅ | 讀不到本機檔案、吃訂閱額度 |
| Headless CLI | ✅ `claude -p` | ✅ `codex exec` | ✅ `opencode run` | 不用 | 搭 `gh` | 權限要事先給好 |
| GitHub Action | ✅ `claude-code-action` | ✅ `codex-action` | ✅ `opencode/github` | 不用 | ✅ event payload | `GITHUB_TOKEN` 不觸發下一個 workflow；要 API key |
| `gh` script | ✅ | ✅ | ✅ | 不用 | ✅ `gh api` | 自己寫狀態判斷 |
| herdr | ✅ | ✅ | ✅ | herdr 要開著；blocked 要人 | 靠 agent 跑 `gh` | 只在本機 |

## 建議

三家都能用、又不依賴某家獨有機制的組合是：**skill 結尾寫明「下一步載入哪支 skill」做預設串接，再用 `gh` + headless CLI（`claude -p`／`codex exec`／`opencode run`）的 script 做需要硬保證的段落**（例如等 CI 綠、等 review comment 出現）；要在本機同時看著多個 agent 時，把同一支 script 換成 `herdr agent prompt --wait` 驅動。Stop hook、`/loop`、Routines、Codex app 排程都可以當個人加速，但不寫進流程 spec，因為換 agent 就失效。GitHub Actions 版本適合「review 機器人」這種不需要本機瀏覽器的步驟；要串多個 workflow 時改用 GitHub App token 或 `workflow_dispatch`，不要靠 `GITHUB_TOKEN` 的留言觸發。
