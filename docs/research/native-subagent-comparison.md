# Claude 與 Codex 原生 subagent 當 `manage` executor／reviewer 的差異

- Issue：[agent-config#22](https://github.com/henry5720/agent-config/issues/22)（map：[#20](https://github.com/henry5720/agent-config/issues/20)）
- 查證日期：2026-10-09；版本：Claude Code 2.1.295、codex-cli 0.161.0
- 來源標記：**實測**（本機跑過）／**文件**（官方文件）／**原始碼**（`openai/codex` tag `rust-v0.161.0`）
- 不重查、直接引用的既定事實：[dotfiles#140](https://github.com/henry5720/dotfiles/issues/140)（Codex 角色只吃 prompt／model／effort，子 agent 沿用父 agent 權限與 MCP；Codex 只有在使用者／AGENTS.md／skill 明確要求時才派 subagent）、[dotfiles#138](https://github.com/henry5720/dotfiles/issues/138)／[#142](https://github.com/henry5720/dotfiles/issues/142)（Codex 權限釘 `on-request` + `workspace-write` + `approvals_reviewer = "auto_review"`，`.git` 唯讀、網路關）、[dotfiles#144](https://github.com/henry5720/dotfiles/issues/144)（不加原生角色）。

## 結論

1. **兩家都能當 executor／reviewer 平行派、非阻塞等**，但結果回來的方式不同：Claude 是背景 subagent 做完後在下一輪收到完成通知；Codex 是 `spawn_agent` 立刻回 id，要等就呼叫 `wait_agent`（有 timeout），子 agent 的最終答案會自動送回父 agent。
2. **Codex 的 issue 前提要修正**：本機模型 `gpt-6.1-sol` 走的是 **multi-agent V2**（工具在 `collaboration` namespace，用 `task_name` 定址），不是 V1 的 `multi_agent_v1`；而且**沒有自訂角色時 `agent_type` 參數根本不出現**，內建的 `explorer`／`worker` 選不到。依 dotfiles#144 不加角色，所以 `manage` 在 Codex 只能派「預設 agent」，差別全靠 message 文字。
3. **巢狀派工兩家都派得動**：Claude 預設可往下三層；Codex V2 不檢查深度（實測派到 depth 2），但同時存在的 subagent 上限只有 3 個（V2 預設 4，含 root）；名額不夠時 V2 會自動卸載已完成、閒置的 subagent，所以真正的限制是「同時在跑的 subagent 最多 3 個」。`code-review`（再派兩個）在 Codex 能跑，但 executor 還在跑時就會撞上限。
4. **subagent 都不能問使用者問題**：Claude 從所有 subagent 拿掉 `AskUserQuestion`；Codex `request_user_input` 只有 root thread 能用。權限提示：Claude 浮到主 session 由使用者答；Codex 互動 TUI 由使用者答（可按 `o` 進該 thread），但我們釘了 `auto_review`，子 agent 繼承後由 reviewer 自動審，不問人；`codex exec` 非互動時要新核准的動作直接失敗回給父 agent。
5. **agent view 都看不到 subagent 的獨立列**：`claude agents` 與 `codex agents` 都只列 root session；要進 subagent 得先進主 session，再用 Claude 的 subagent panel／`/tasks`，或 Codex 的 `/agent`。
6. **worktree 只有 Claude 原生支援**：Claude Agent 工具可帶 `isolation: "worktree"`；Codex subagent 一律跟父 agent 同 cwd，`spawn_agent` 沒有 worktree 參數。
7. **只能使用者手動叫的 skill（`implement`、`manage`）兩家 subagent 都叫不到**；能被模型叫的（`diagnosing-bugs`、`code-review`）兩家 subagent 都看得到。Codex 父 agent 在 message 裡寫 `$skill` 不會自動展開（訊息走 inter-agent 通道，不是使用者輸入），子 agent 要自己讀 `SKILL.md`。

## 對照表

| 項目 | Claude Code 2.1.295 | codex-cli 0.161.0 |
| --- | --- | --- |
| 怎麼派 | `Agent` 工具（`subagent_type`、`isolation: "worktree"`）。互動 session 預設開 fork mode，subagent 一律背景跑，Claude 不能要求前景；`-p` 與 SDK 預設關 fork mode，背景／前景由 Claude 判斷。〔文件 sub-agents〕本 session（Claude subagent）看到的 `Agent` 工具 schema 沒有 `run_in_background` 參數，只有 `isolation`。〔實測〕 | 本機模型走 V2：`collaboration.spawn_agent(task_name, message, fork_turns, model, reasoning_effort)`；`fork_turns` 預設 `all`（子 agent 繼承父 agent 全部歷史）。〔原始碼 `core/src/tools/handlers/multi_agents_spec.rs:649-685`、`models-manager/models.json` 的 `multi_agent_version`；實測 rollout `multi_agent_version: v2`〕V1（`multi_agent_v1.spawn_agent` + `agent_type`）只在模型標 v1 或沒開 V2 時用。 |
| 內建角色 | `general-purpose`、`Explore`、`Plan` 等；可在 `.claude/agents/*.md` 自訂（dotfiles#140）。 | 原始碼內建 `default`／`explorer`／`worker`〔`core/src/agent/role.rs:338-380`〕，但 `agent_type` 參數只有在有**使用者自訂角色**時才出現〔`core/src/tools/spec_plan.rs:1329`、測試 `core/tests/suite/spawn_agent_description.rs:397-398`「v1 hides agent type without roles」〕。本機沒有 `~/.codex/agents/`，實測 rollout 的 `agent_role` 都是 `null`。 |
| 能不能平行派 | 能。同時跑 20 個後再派會失敗（`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` 可調），總數不限。〔文件〕 | 能。V2 預設 `max_concurrent_threads_per_session = 4`（含 root，所以 3 個 subagent）〔`core/src/config/mod.rs:257,1624-1640`〕；V1 預設 6〔同檔 `:256`〕。V1 做完的 agent 沒 `close_agent` 也佔名額（工具描述，`multi_agents_spec.rs:347`）；V2 沒有 `close_agent` 工具，名額滿時自動卸載狀態為 Completed／Errored／Interrupted 且沒有待處理訊息的 subagent，全是執行中的才回 `AgentLimitReached`〔`core/src/agent/control/residency.rs:102-124,274-280`〕。 |
| manager 怎麼不阻塞地等 | 背景 subagent 跑的時候主 agent 繼續做事；結果在「之後的一輪」以完成通知送到。〔文件〕要續派用 `SendMessage`（用 agent ID 或名稱）。〔文件〕 | `spawn_agent` 立刻回 `task_name`／id，不等。要等就呼叫 `wait_agent`：V2 預設 30 秒、上下限 10 秒～1 小時〔`config/mod.rs:258-260`〕，會等到任一 agent 有信箱更新或逾時。工具描述明講「少用 `wait_agent`，等的時候做別的」〔`multi_agents_spec.rs:758-762`〕。續派用 `followup_task`／`send_message`。 |
| 結果怎麼回到 manager | 完成通知帶 subagent 的最終報告。〔文件〕 | 子 agent 的最終答案「立即送回父 agent」（V2 注入子 agent 的 `<multi_agent_role>` 開發者訊息）。〔實測 rollout〕`codex exec` 實測：父 agent 呼叫一次 `wait_agent` 後就拿到子 agent 原文。 |
| 權限提示跑到哪 | 背景 subagent 的權限提示浮到**主 session**，並標出是哪個 subagent 問的；使用者核准或按 Esc 拒絕這一次。agent 傳來的訊息不能代替使用者核准。〔文件〕如果主 session 本身是 `claude --bg`，session 會變成 Needs input（`claude agents --json` 的 `blocked`），要 attach 才答得了。〔文件 agent-view〕 | 子 agent 繼承父 agent 的 `approval_policy`、`approvals_reviewer`、sandbox、cwd〔`core/src/agent/child_config.rs:170-195`〕。我們釘了 `auto_review`（dotfiles#142），所以由 reviewer 自動審，不問人。若是使用者審：互動 TUI 會跳出標了來源 thread 的核准框，按 `o` 可先進那個 thread；非互動（`codex exec`）時需要新核准的動作直接失敗，錯誤回給父 agent。〔文件 subagents〕 |
| 能不能問使用者問題 | 不能。`AskUserQuestion` 從所有 subagent 拿掉，就算 `tools` 有寫也一樣。〔文件；本 subagent 的工具清單也沒有它，實測〕 | 不能。`request_user_input` 對非 root thread 回錯誤「can only be used by the root thread」。〔`core/src/tools/handlers/request_user_input.rs:67-71`〕 |
| agent view 看得到嗎 | `claude agents` 只列背景 session；「session 派出的 subagent 與 teammate 不會各自成一列」。〔文件 agent-view〕要看 subagent：進主 session，用提示框下方的 subagent panel（`Enter` 開 transcript 並能直接對它講話），做完的在 30 秒內用 `/tasks` 開。〔文件 sub-agents〕 | `codex agents` 列表濾掉 `SubAgent(ThreadSpawn)` 來源與有 `parent_thread_id` 的 thread，只列 root；子 agent 的狀態（例如等核准）只會出現在 root 那一列的細節裡。〔`tui/src/app/agents_overview_discovery.rs:130-137`、`tui/src/app/agents_overview_details.rs:130-170`〕要進 subagent：進 root session 後用 `/agent` 切換。〔文件 subagents〕 |
| subagent 能不能叫 skill | 能。背景 subagent 保留 `Skill` 工具；`skills` frontmatter 只控制預載，不限制可叫哪些。〔文件〕本 session 就是 subagent，成功叫了 `research` skill。〔實測〕但 `disable-model-invocation: true` 的 skill（`implement`、`implement-spec`、`manage`）不在 Skill 清單裡，模型叫不到。〔文件；實測本 session 清單沒有它們〕 | 能看到、能照做。子 agent 開頭就有和父 agent 一樣的 `<skills_instructions>` 清單（實測 30 個，含 `code-review`、`diagnosing-bugs`）；`allow_implicit_invocation: false` 的 `implement` 不在清單。〔實測 rollout〕父 agent 在 message 裡寫 `$diagnosing-bugs` **不會**自動注入 skill（訊息是 inter-agent `agent_message`，不是使用者輸入），子 agent 自己去讀 `~/.agents/skills/diagnosing-bugs/SKILL.md`。〔實測，`fork_turns: none`〕 |
| Codex 叫 skill 的寫法 | — | 使用者輸入 `$skill-name` 會注入 `<skill>` 區塊（實測：prompt 含 `$diagnosing-bugs` 時 rollout 有 `<skill>`）。給 subagent 時：在 message 寫 skill 名稱與 `SKILL.md` 路徑請它照做；或用預設 `fork_turns: all` 讓子 agent 繼承父 agent 已注入的 skill。〔實測〕 |
| 巢狀派工（`code-review` 會再派兩個） | 預設往下三層（`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`，`1` 關掉）；到上限才拿掉 `Agent` 工具。〔文件〕本 session 是 subagent，看得到 `Agent` 工具。〔實測〕 | V2 `spawn_agent` 不檢查深度（`agent_max_depth`「Ignored by V2」，`config/mod.rs:944-945`），子 agent 的提示也寫「Child agents can also spawn their own sub-agents」。實測 root → `/root/worker` → `/root/worker/child`（depth 2）成功。V1 預設 `max_depth = 1`，子 agent 再派會回「Agent depth limit reached」〔`config/mod.rs:266`、`tools/handlers/multi_agents/spawn.rs:74-80`〕。V2 的限制是同時執行 3 個 subagent：reviewer + 兩個 review subagent 剛好滿，executor 若還在跑就會撞 `AgentLimitReached`；executor 已完成則會被自動卸載讓出名額〔`core/src/agent/control/residency.rs:102-124,274-280`〕。 |
| 獨立 worktree／分支 | `Agent` 工具帶 `isolation: "worktree"`：在暫時的 git worktree 跑，沒改東西就自動清掉；Bash 在主 checkout 執行會失敗。subagent 也有 `EnterWorktree`／`ExitWorktree`。〔文件；工具 schema 實測〕 | 沒有。子 agent 的 cwd 直接複製父 agent 當下的 cwd〔`child_config.rs:181-183`〕，`spawn_agent` 沒有 worktree 參數〔`multi_agents_spec.rs:649-685`〕。`--worktree` 只存在於整個 session 層級（`codex exec --worktree`，`--help`）。子 agent 自己 `git worktree add` 要寫 `.git`，在我們的 `workspace-write`（`.git` 唯讀）下會走核准（dotfiles#138）。 |

## 對 `manage` 的含意（給 map #20 的輸入，不是決定）

- **executor**：Claude 用 `Agent` + `isolation: "worktree"`；Codex 只能同一個 checkout，平行的 executor 要靠 message 切開不重疊的檔案範圍（內建 `worker` 角色描述也這樣要求，但這個角色在沒有自訂角色時選不到）。
- **reviewer 跑 `code-review`**：兩家都派得動巢狀。Codex 要等 executor 結束（`wait_agent`）再派 reviewer，不然 3 個執行名額不夠；Codex 的 skill 要在 message 裡寫明路徑。`code-review` 找不到 spec 時「問使用者」那步，在兩家 subagent 都做不到，要改成回報給 manager。
- **使用者進去對話**：兩家的 agent view 都只到主 session 那層，`manage` 的指引要寫「先進主 session，再用 Claude 的 subagent panel／`/tasks` 或 Codex 的 `/agent`」。

## 未驗

- Codex 互動 TUI 的核准框與 `o`、`/agent` 切換：只有文件，沒在 TUI 實測（本次只跑 `codex exec`）。
- Codex V1 路徑（`agent_type`、depth 1）：只看原始碼，本機模型走 V2 沒法實測。
- 實際讓 Codex subagent 跑完整 `code-review`（兩個 review subagent）：只驗了 depth 2 的派工，沒跑真實 review。
- Claude 前景 subagent、`claude --bg` 裡的 subagent 權限提示：只有文件。

## 實測紀錄

在 `/home/ubuntu/.claude/jobs/19dc6e0a/tmp/cx-exp`（非 git 目錄）跑 `codex exec --skip-git-repo-check -s read-only --json "<prompt>"`，rollout 在 `~/.codex/sessions/2026/10/09/`：

1. 派一個 subagent，叫它再派一個並回 OK：三個 rollout，`source.subagent.thread_spawn.depth` 依序 1、2，`agent_path` `/root/worker`、`/root/worker/child`，`multi_agent_version: v2`，`agent_role: null`。
2. prompt 含 `$diagnosing-bugs`：rollout 有 `<skill>` 注入，但父 agent 本身就注入了，子 agent 是用 `fork_turns: all` 繼承來的。
3. 父 prompt 不含 `$`、指定 `fork_turns: none`、message 以 `$diagnosing-bugs` 開頭：父子 rollout 都沒有 `<skill>`；子 agent 收到的是 `agent_message`（`Message Type: NEW_TASK`），自己讀 `SKILL.md` 才回出 `# Diagnosing Bugs`。

## 來源

- Claude 文件：<https://code.claude.com/docs/en/sub-agents>、<https://code.claude.com/docs/en/agent-view>
- Codex 文件：<https://developers.openai.com/codex/subagents>（308 轉到 <https://learn.chatgpt.com/docs/agent-configuration/subagents>）
- Codex 原始碼：<https://github.com/openai/codex/tree/rust-v0.161.0/codex-rs>（上表路徑皆相對於 `codex-rs/`）
- `codex --help`、`codex exec --help`、`codex agents --help`、`codex features list`（`multi_agent` stable true、`multi_agent_v2` stable false、`worktrees` stable true）
