# Codex 能不能開「使用者事後進得去對話」的背景 session

> 對應 issue：[agent-config#21](https://github.com/henry5720/agent-config/issues/21)（map：#20）
> 調查日期：2026-10-09。CLI：`codex-cli 0.161.0`；本機常駐的 app-server daemon 是 `0.162.0`（`ps` 看到 `~/.codex/packages/app-server-daemon/releases/0.162.0-…/bin/codex app-server --listen unix:// … --managed-daemon`）。
> 原始碼引用一律釘在 tag [`rust-v0.161.0`](https://github.com/openai/codex/tree/rust-v0.161.0/codex-rs)（commit `979011409de0`）。
> 標記：**實測**＝這次在本機跑過；**原始碼**＝讀 openai/codex；**help**＝`codex … --help` 輸出；**文件**＝官方文件。

## 結論

做得到，但要看 manager 是在哪裡跑。Codex 裡對應 `claude --bg` 的東西，是讓 session 跑在共用的 app-server daemon 上。進到同一個 daemon 的 session 會出現在 `codex agents`，使用者可以打開接手，包括回答權限提示。

| Claude                       | Codex 對應                                                                                                                                                   | 狀態                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| `claude --bg "<prompt>"`     | manager 在 **Codex 互動 TUI** 裡：用模型內建的 `codex_tui.create_thread` tool                                                                                | 實測可用                                     |
|                              | manager 不在 TUI 裡：透過 `codex app-server proxy` 送 JSON-RPC `thread/start` + `turn/start`，送完就斷線                                                     | 實測可用，但沒有現成 CLI 指令，要自己寫 client |
|                              | `codex exec … &`                                                                                                                                             | 能在背景跑，但**不是** daemon session（見下） |
| `claude agents --json`（state） | TUI 內：`codex_tui.wait_threads`／`read_thread`；TUI 外：JSON-RPC `thread/list`／`thread/read` 的 `status`                                                     | 實測可用；**沒有** `codex agents --json`      |
| `claude logs <id>`           | TUI 內：`codex_tui.read_thread`；TUI 外：`thread/read`（`includeTurns`）或直接讀 `thread.path` 指向的 rollout JSONL；`codex exec` 用 `-o <file>`／`--json` | 實測可用                                     |
| `claude attach <id>`         | `codex agents` → 選任務 Enter，或 `codex resume <thread-id>`                                                                                                  | 實測可用                                     |
| 追加訊息                     | `codex queue --thread <uuid> --message …`；TUI 內 `codex_tui.send_message_to_thread`                                                                         | 實測：只對 daemon 已載入的 thread 會自動跑     |

做不到的：

- **沒有一行就開 daemon 背景 session 的 CLI 指令**（像 `claude --bg`）。`codex exec` 不走 daemon；`codex queue` 只能對既有 thread 追加訊息；`codex remote-control` 是給遠端配對用的。
- **沒有 `codex agents --json`**。`codex agents` 只有 TUI，而且非 TTY 會直接拒絕。
- **`codex exec` 不會停下來等權限**：它把 approval 固定成 `never`，遇到 approval request 直接拒絕。所以「卡在權限、等使用者進去按」這個流程 `codex exec` 沒有。
- `codex_tui.*` tools 只在互動 TUI 連著本機 daemon 時才有。`codex exec` 裡的 manager 拿不到。

## 1. 三條開背景 session 的路

### 1a. `codex exec`（背景跑得動，但不在 daemon 上）

- **原始碼**：`codex exec` 用的是 in-process app server（[`exec/src/lib.rs:1022`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/exec/src/lib.rs#L1022) `InProcessAppServerClient::start`），不連 daemon。
- **原始碼**：headless 時 approval 預設 `AskForApproval::Never`（[`exec/src/lib.rs:591`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/exec/src/lib.rs#L591)），收到 `CommandExecutionRequestApproval`／`FileChangeRequestApproval`／`ToolRequestUserInput` 一律回 “not supported in exec mode”（[`exec/src/lib.rs:2091-2125`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/exec/src/lib.rs#L2091-L2125)）。唯一例外是 approvals reviewer 設成 auto review 時改走自動審查（同檔 `:781-806`）。
- **實測**：`codex exec -C <dir> --json -o last.txt "reply OK-A" &` 會在背景跑完，`-o` 檔寫入 `OK-A`，stdout JSONL 有 `thread.started`（帶 `thread_id`）與 `turn.completed`。沒有把 stdin 接到 `/dev/null` 時，stderr 會印 `Reading additional input from stdin...`，背景跑要加 `</dev/null`。
- **實測**：執行中的 exec thread 會出現在 daemon 的 `thread/list`，但 `status` 是 `notLoaded`，`codex agents` 裡顯示 **Inactive**。daemon 不知道它在跑，也看不到它的進度。
- **實測**：跑完後 `codex resume <thread-id>` 打得開，看得到完整對話，可以繼續聊（這時改由 daemon 載入）。
- **未驗**：exec 還在跑時，從 `codex agents`／`codex resume` 打開同一個 thread 會怎樣（兩個 process 同時寫同一份 rollout）。沒測，manager 不該這樣用。

### 1b. 互動 TUI 內的 `codex_tui` task tools（manager 在 Codex TUI 裡時的原生做法）

- **原始碼**：互動 TUI 連到本機 daemon 時（`AppServerTarget::LocalDaemon`，[`tui/src/app/startup.rs:384`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/app/startup.rs#L384)），會起一個本機 MCP server，namespace 是 `codex_tui`，把以下 tools 給模型用（[`tui/src/dynamic_tools.rs`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/dynamic_tools.rs)）：
  `list_threads`、`list_archived_threads`、`read_thread`、`wait_threads`、`send_message_to_thread`、`create_thread`、`fork_thread`、`set_thread_title`、`set_thread_archived`。
  embedded app server（例如 `--no-daemon`、`codex exec`）時這組 tools 是關的（[`tui/src/app_server_session.rs:447`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/app_server_session.rs#L447)、`:513-521`）。
- **原始碼**：`create_thread`（[`dynamic_tools.rs:471`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/dynamic_tools.rs#L471)）在 daemon 上開一個**頂層** thread，沿用呼叫者的 cwd、model、approval policy、approvals reviewer、sandbox／permission profile，可選 `title`，然後 `turn/start`，回傳 `{"threadId"}`，不等它跑完。限制：
  - prompt 上限 **1,000 bytes**（`MAX_INPUT_BYTES`，`:85`），會包成 `<codex_delegation><source_thread_id>…</source_thread_id><input>…</input></codex_delegation>`（`:1114-1125`）。長的開頭指令要先寫進檔案，prompt 只放「讀某檔照做」。
  - tool 說明寫 “only when the user explicitly asks for a new task”。這跟 dotfiles 已定的「Codex subagent 只在使用者／AGENTS.md／skill 明確要求時才派」一致。
  - `create_thread`、`send_message_to_thread`、`fork_thread` 設成 `approval_mode: "prompt"`，其他 tools 自動核准（[`tui/src/dynamic_tools_mcp.rs:120-127`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/dynamic_tools_mcp.rs#L120-L127)）。
- **原始碼**：`wait_threads`（`:781`）最多等 8 個 thread、單次最多 `120000` ms（`:88`）。醒來的原因有三種（`:931-958`）：`turnCompleted`（跑完）、`actionableStatus`（`active` 且帶 `waitingOnApproval`／`waitingOnUserInput` flag，也就是卡在權限或提問）、`inactiveStatus`（`notLoaded`／`systemError`）。回傳內容包含最後一則 assistant 訊息。
- **實測**：在 tmux 裡開 `codex`（本機 config 是 `approval_policy = "on-request"` + `approvals_reviewer = "auto_review"`），叫它用 `create_thread` 開 “probe E child”（prompt `reply with exactly OK-E`），再 `wait_threads`、`read_thread`。結果依序是 `{"threadId":"01a11eee-…"}` → `{"timedOut":false,"wake":{…"reason":"turnCompleted"…}}` → 最後訊息 `OK-E`，共 21 秒。這次**沒有出現人工核准畫面**，推測 approval 被 `auto_review` 處理掉了；`approvals_reviewer` 設成人工時會不會跳提示，**未驗**。
- **實測**：子 thread 的 `parentThreadId` 是 `null`、`source` 是 `vscode`、`name` 是 `probe E child`。`codex agents` 裡看得到 “probe E child”（Ready），能直接打開。

### 1c. 直接對 daemon 講 JSON-RPC（manager 不在 TUI 裡時）

- **help**：`codex app-server proxy` 是 “Proxy stdio bytes to the running app-server control socket”。
- **原始碼**：control socket 走的是 **WebSocket over Unix socket**（[`app-server-transport/src/transport/unix_socket.rs:168`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/app-server-transport/src/transport/unix_socket.rs#L168) `accept_hdr_async_with_config`），不是一行一個 JSON。所以 client 要先做 HTTP Upgrade 握手、送 masked frame，不能直接 `echo '{…}' | codex app-server proxy`（**實測**：直接送 JSON 行完全沒有回應）。
- **實測**：用約 60 行 Python（stdlib，自己做 WebSocket 握手與 frame）透過 `codex app-server proxy` 送出 `initialize` → `initialized` → `thread/start {cwd}` → `turn/start {threadId, input:[{type:"text",text:…}]}`，拿到 `turn.status = "inProgress"` 後**馬上斷線**。15 秒後重新連線 `thread/read {includeTurns:true}`，thread `status: idle`，turn `completed`，`agentMessage.text = "OK-B"`。斷線之後 daemon 照樣把 turn 跑完。
- **原始碼**：daemon 只在「沒有訂閱者」**而且**「thread 不是 active」兩個條件都成立、再過一段 delay 之後才 unload thread（[`app-server/src/request_processors/thread_lifecycle.rs:56-63`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/app-server/src/request_processors/thread_lifecycle.rs#L56-L63)、`:370` 若 `AgentStatus::Running` 不 unload、`:416`）。所以 client 斷線不會殺掉正在跑的 turn。
- **實測（卡權限）**：`thread/start {approvalPolicy:"untrusted", sandbox:"read-only"}`，再 `turn/start` 叫它 `touch probe-c.txt`，然後斷線。25 秒後 `thread/list` 顯示 `status: {"type":"active","activeFlags":["waitingOnApproval"]}`。`codex agents` 把它列在 **Needs input**，詳情寫 “Waiting for approval.”。按 Enter 打開後出現完整核准畫面（`$ touch probe-c.txt`，`1. Yes, proceed (y)`…）。按 `y` 之後檔案建立、回覆 `DONE-C`。斷線期間那個權限請求被保留著，使用者事後進去答得了。
- 這條路功能齊全，但要 manager 自己帶一支 WebSocket JSON-RPC client。protocol 標成 experimental（`codex app-server --help` 標 `[experimental]`），而且 CLI 0.161 和 daemon 0.162 版本可能不同。官方文件說 app-server 指令 “may change without notice”。

### `codex queue` 與 `codex remote-control`

- **help**：`codex queue --thread <THREAD> --message <TEXT>` 是 “Queue a message for an existing session”。它**不能開新 session**。
- **原始碼**：queue 存在 daemon，thread idle 時才 dispatch（[`ext/queue/src/service.rs:405`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/ext/queue/src/service.rs#L405) `dispatch_if_idle`、`:549` `on_thread_idle`）。手動 start 時 thread 必須已載入（“resume the thread before starting a queued message”，[`thread_queue_processor.rs:194`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/app-server/src/request_processors/thread_queue_processor.rs#L194)）。
- **實測**：對 daemon 已載入、idle 的 thread（probe E child）`codex queue --thread <uuid> …`，回 `Queued message … for thread …`，15 秒內自動跑出 `OK-Q`。對 `notLoaded` 的 exec thread 下同一個指令也回 “Queued”，但 15 秒後沒有跑，`thread/queue/list` 裡還留著那一筆（之後用 `thread/queue/delete` 清掉）。
- **實測**：`--thread "probe E child"`（用 thread 名稱）回 `No active session found matching 'probe E child'.`；用 UUID 才成功。原始碼只在 `SessionCollection::Active` 裡用名稱找（[`tui/src/session_queue_commands.rs:98`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/session_queue_commands.rs#L98)），為什麼找不到沒有再追。manager 一律用 UUID。
- **help／文件**：`codex remote-control start|stop|pair` 管理「開了 remote control 的 daemon」並產生配對碼。官方 CLI reference 寫 “Managed remote-control clients and SSH remote workflows use these commands”。這是給遠端裝置連進來用的，跟開背景 session 無關。

## 2. 會不會出現在 `codex agents`、使用者怎麼接手

- **help**：`codex agents` 是 “Browse all agent sessions on the shared local app-server daemon”。
- **原始碼**：overview 分兩路列 thread。一路是 interactive，另一路是 `[Exec, AppServer]` 來源（[`tui/src/app/agents_overview_discovery.rs:61`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/app/agents_overview_discovery.rs#L61)）。會濾掉 ephemeral、有 `parent_thread_id` 的、以及 `SubAgent(ThreadSpawn)` 來源的 thread（`:129-137`）。所以**原生 `spawn_agent` 派出的 subagent 不會出現在 `codex agents`**（原始碼），`create_thread` 開的才會。
- **原始碼**：分組對應（[`tui/src/app/agents_overview_view.rs:66-88`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/app/agents_overview_view.rs#L66-L88)）：

  | `ThreadStatus`                                       | 顯示        |
  | ---------------------------------------------------- | ----------- |
  | `active` + `waitingOnApproval`／`waitingOnUserInput`，或 `systemError` | Needs input |
  | `active`（沒有 flag）                                | Working     |
  | `idle`                                               | Ready       |
  | `notLoaded`                                          | Inactive    |

- **實測**：同一個畫面同時看到 probe A（exec，Inactive）、probe B（JSON-RPC，Ready）、probe C（JSON-RPC 卡權限，Needs input）、probe E child（create_thread，Ready）。
- **接手方式（實測）**：`codex agents` → 方向鍵選 → Enter；或 `codex resume <thread-id>`。兩種都會接上 daemon 裡的 thread，pending 的核准請求也會出現。
- **原始碼＋實測（離開但不中斷）**：在 daemon 模式的 TUI，turn 跑到一半、composer 是空的時候按 `Ctrl+C`，會跳出 “Task is still running”，選項有 Cancel task／**Run in background**（“Exit Codex and leave the task running”）／Exit（[`tui/src/app/input.rs:453-520`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/tui/src/app/input.rs#L453-L520)）。實測選 Run in background 後 TUI 結束，turn 照樣跑完（`DONE-D`）。如果還有排隊中的 follow-up，就不會出現 Run in background 這個選項（`allow_background` 條件）。

## 3. manager 怎麼知道跑完／卡住、怎麼讀輸出

- **沒有** `codex agents --json`（help：`codex agents` 沒有 `--json`；**原始碼**：非 TTY 時直接回 “stdin is not a terminal”，[`cli/src/main.rs:2420-2426`](https://github.com/openai/codex/blob/rust-v0.161.0/codex-rs/cli/src/main.rs#L2420-L2426)）。
- manager 在 Codex TUI 裡：用 `codex_tui.wait_threads`。`reason` 是 `turnCompleted` 代表完成，`actionableStatus` 代表卡權限或提問，這時請使用者 `codex agents` 進去。輸出用 `read_thread`（可帶 `includeOutputs`，每個 item 最多 20,000 字元）。
- manager 不在 TUI 裡：用 JSON-RPC `thread/read`／`thread/list` 看 `status.type` 與 `activeFlags`，讀 turn 的 `agentMessage`（`phase: "final_answer"`）。thread 物件的 `path` 指向 `~/.codex/sessions/YYYY/MM/DD/rollout-…-<id>.jsonl`，可以直接讀（**實測**：`thread/list` 回傳裡有這個欄位）。
- `codex exec`：用 process 結束、`-o <file>`（最後訊息）、`--json`（`turn.completed`／錯誤事件）判斷。它不會進入「等權限」狀態，權限不足時那個動作被拒，模型自己處理。

## 4. 對 #20 spec 的意義（給 grilling 用的事實，不是決定）

- `/manage` 在 Codex 互動 TUI 下跑時，最接近 Claude 流程的原生做法是 `create_thread` → `wait_threads` → `read_thread`。使用者用 `codex agents` 看、進去接手、回答權限。要注意 1,000 bytes 的 prompt 上限，以及 `create_thread` 需要核准（`approval_mode: "prompt"`）。
- 如果 `/manage` 本身跑在 `codex exec`，`codex_tui` tools 不存在。退路只有 `codex exec &`（使用者事後只能 resume 看結果、不能中途接權限），或自己寫 JSON-RPC client。
- 原生 `spawn_agent` subagent 不會出現在 `codex agents`，只有 `create_thread`／daemon 頂層 thread 會。

## 實驗紀錄與清理

- scratch 目錄：`/home/ubuntu/.claude/jobs/19dc6e0a/tmp/scratch`。用 tmux 開 `codex agents`／`codex resume`／`codex`，再用 `capture-pane` 讀畫面。
- daemon 是使用者原本就在跑的（10/8 起的），沒有自己起或停 daemon，也沒有改 `~/.codex/config.toml`。
- 實驗產生的 5 個 thread（A `01a11eea-1864…`、B `01a11eea-ad61…`、C/D `01a11eeb-148e…`、E `01a11eed-4a3b…`、E child `01a11eee-316d…`）都已經 `codex archive`。留在 exec thread 上的 queued message 已經用 `thread/queue/delete` 刪掉。tmux session 都關了。
- 官方文件（[CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)，原 `developers.openai.com/codex/cli/reference` 308 轉址過去）在 2026-10-09 **沒有寫** `codex agents`、`codex queue`、`--no-daemon` 或 daemon 機制，只在 `/import` 段落提到 “local app-server daemon”。所以上面關於 daemon 的事實都來自原始碼與實測。
