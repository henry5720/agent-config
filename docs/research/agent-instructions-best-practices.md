# 全域規則與 repo AGENTS.md 的官方建議，對照現有檔案

- 查證日期：2026-11-21；版本：Claude Code 2.1.330、codex-cli 0.171.0、opencode 1.18.35
- 來源標記：**文件**（官方文件）／**原始碼**（固定到本機版本的 tag）／**實測**（本機指令輸出）／**未查證**
- 審查對象：全域規則 `extras/agents-md/AGENTS.md`（審查時在 `instructions/`，symlink 成 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.config/opencode/AGENTS.md`）、本 repo 的 `AGENTS.md`、dotfiles 的 `AGENTS.md`
- 不重查、直接引用：dotfiles 的 [`docs/research/agent-instructions-sharing.md`](https://github.com/henry5720/dotfiles/blob/main/docs/research/agent-instructions-sharing.md)（三家載入行為的第一輪研究）、[`docs/architecture/agent-principles.md`](https://github.com/henry5720/dotfiles/blob/main/docs/architecture/agent-principles.md)（「規則要寫什麼」的判斷表）。本文只補那兩份沒有的：大小上限的實際算法、HTML 註解、`~/code` 祖先 `CLAUDE.md` 的影響，以及逐條對照。
- 只研究，沒有改任何檔案、沒有開 issue。

## 結論

1. **全域檔的大小在三家都沒有問題。** 6,149 bytes、84 行。Claude 建議每個檔 200 行以內〔C1〕；Codex 的 32 KiB `project_doc_max_bytes` 只算 repo 的檔，全域檔另外讀、不扣這個額度〔X2 原始碼〕；OpenCode 沒有上限〔O2 原始碼〕。最接近上限的是 dotfiles 的 `AGENTS.md`：204 行，超過 Claude 的 200 行建議；15,473 bytes，在 Codex 32 KiB 以內。
2. **同一份檔給三家用，有三個相容性問題。** (a) `@path` import 只有 Claude 會展開，Codex、OpenCode 會把它當成普通文字〔C1、X1、O2〕，所以全域檔裡不能用 import，目前也沒用。(b) block-level HTML 註解只有 Claude 會拿掉〔C1〕，Codex、OpenCode 會把它原樣送進 context〔X2、O2〕；全域檔 L63–66 那 397 bytes 的維護註解，只有在這兩家會花到 token。(c) 第 (c) 點跟全域檔無關，是 repo 層：`~/code/CLAUDE.md` 是祖先檔，所以只有 `AGENTS.md` 的子 repo（`fizzt-frontend`、`local-e2e-bootstrap`）在 Claude 預設設定下**不會載入**它們的 `AGENTS.md`〔C1〕。
3. **官方對內容的共識是：只放每個 session 都要、從 code 推不出來的事；多步驟流程改成 skill；一定要發生的事改成 hook、設定或 CI；不要靠 IMPORTANT 加強語氣。** Claude〔C1、C2、C3〕、Codex〔X1、X3〕、Anthropic 工程文章〔A1〕都這樣說；agents.md 沒有給長度或內容上的限制〔G1〕。
4. **全域檔最大的偏離是「Issue 狀態」（L44–51）。** 這是一段四個步驟、只有處理 issue 時才用到的流程，照官方說法應該改成 skill。其次是開頭 L3–8 的文件放置通則：只有寫文件時才用到，而且另外兩份 `AGENTS.md` 都引用「全域規則開頭」，要搬的話引用要一起改。L64 的註解寫「這份檔案由 chezmoi 部署」，跟現況（skillshare extras 建 symlink）不符。
5. **兩份 repo 的 `AGENTS.md` 大致符合官方建議**：有驗證指令，有踩過的坑與原因，也有不能從 code 推出的決策。dotfiles 那份需要瘦身：Windows 實機清單（L94–128）、`/implement-spec` 流程（L130–133）、文件放置表（L138–172）都只在特定任務用到，應該搬到 `docs/agents/`，`AGENTS.md` 只留連結。

## 1. 三個 client 怎麼載入

| 項目 | Claude Code 2.1.330 | Codex 0.171.0 | OpenCode 1.18.35 |
|---|---|---|---|
| 全域檔 | `~/.claude/CLAUDE.md`〔C1〕 | `$CODEX_HOME`（預設 `~/.codex`）先找 `AGENTS.override.md`，再找 `AGENTS.md`，只用第一個非空的檔〔X1；原始碼 `codex-home/src/instructions/mod.rs:41-85`〕 | `~/.config/opencode/AGENTS.md`；沒有這個檔時才讀 `~/.claude/CLAUDE.md`〔O1；原始碼 `instruction.ts:60-63,115-120`：找到第一個就 `break`，所以不會兩份都載入〕 |
| repo 檔 | 從 cwd 往上每一層的 `CLAUDE.md`、`CLAUDE.local.md` 都載入，依序串接，不互相覆蓋〔C1〕。`AGENTS.md` 只在 cwd 以上**完全沒有** `CLAUDE.md`／`.claude/CLAUDE.md`／`CLAUDE.local.md` 時才讀；`~/.claude/CLAUDE.md` 不算在這個判斷裡〔C1〕 | 從 project root（通常是 git root）往下走到 cwd，每層最多一個檔（`AGENTS.override.md` → `AGENTS.md` → fallback 檔名），用空行串接，越接近 cwd 的越後面〔X1〕。project 不受信任時不讀 repo 檔〔原始碼 `core/src/agents_md.rs:65`〕 | 從 cwd 往上找到 worktree root，每層的 `AGENTS.md` 都載入；某一層沒有 `AGENTS.md` 時才讀那層的 `CLAUDE.md`〔O1；原始碼 `instruction.ts:122-133`〕 |
| 子目錄 | 子目錄的 `CLAUDE.md` 要等 Claude 讀、寫或改到那個子目錄裡的檔時才載入〔C1〕 | 不讀 cwd 以下的子目錄〔X1〕 | 要等 agent 讀檔或列目錄碰到那一區時才載入〔O1〕 |
| 合併／衝突 | 全部串接；兩條指示矛盾時「Claude may pick one arbitrarily」〔C1〕 | 串接；越後面的越優先（「Files closer to your current directory override earlier guidance」）〔X1〕 | 串接；「does not resolve conflicts between them」〔O1〕 |
| `@path` import | 支援，相對路徑以檔案自己的位置為準，最多四層；寫在 backtick 裡不會展開〔C1〕 | 官方文件沒有提到〔X1〕；全域檔讀進來後只做 `trim()`〔原始碼 `mod.rs:69-73`〕 | 官方文件沒有提到〔O1〕；原始碼只做 `readFileString`，沒有解析〔`instruction.ts:91-93`〕。要引入其他檔得用 `opencode.json` 的 `instructions`〔O1〕 |
| HTML 註解 | block-level `<!-- -->` 送進 context 前會拿掉〔C1〕。實測：本 session 載入的 `~/.claude/CLAUDE.md` 裡確實沒有 L63–66 那段註解 | 不拿掉（只做 `trim()`）〔原始碼〕 | 不拿掉（原樣讀進來）〔原始碼〕 |
| 大小 | 建議每個檔 200 行以內，超過時啟動會出警告；超過 4 MiB 的檔整個略過。依需求才載入的檔（子目錄 `CLAUDE.md`、有 `paths` 的 rule）另外有字元上限：200K context 是 40,000 字元，超過就只給開頭〔C1〕。import 進來的檔跟原檔一起算，不會省 context〔C1〕 | `project_doc_max_bytes` 預設 32 KiB，算的是 repo 檔的**總和**；額度用完後，下一個檔會被截斷（只讀到剩下的 bytes），並附警告〔X1；原始碼 `agents_md.rs:69-99,161-171`〕。全域檔由 `codex-home` 另外讀取，不扣這個額度〔原始碼 `mod.rs`，沒有 byte 上限〕 | 沒有上限〔O1；原始碼〕 |
| 什麼時候重讀 | 每個 session 開始時讀；`/compact` 後會從磁碟重讀 project root 的 `CLAUDE.md`〔C1〕 | 每次 run 讀一次，TUI 是每次啟動 session 讀一次〔X1〕 | 未查證 |

Codex 的全域檔不扣 32 KiB 額度這一點，官方文件沒有寫清楚（文件只說「combined size」）。這裡依據的是 `rust-v0.171.0` 原始碼：額度變數 `remaining` 只出現在 `load_project_instructions` 迴圈裡，全域檔走的是 `codex-home` 的 `load_from_codex_home`。**沒有實測。**

### 共用一份檔的相容性坑

| 坑 | 影響 | 現況 |
|---|---|---|
| `@path` 只有 Claude 會展開 | 全域檔寫 `@x.md` 的話，Codex、OpenCode 只會看到一行字 | 全域檔沒有用 import，沒有問題 |
| HTML 註解只有 Claude 會拿掉 | 寫給人看的維護註解，在 Codex、OpenCode 會佔 token | L63–66 有 397 bytes，影響很小；但 L64 的內容已經過時（見下） |
| 只有 Claude 有的概念 | 「deferred tool」「tool search」（L72）是 Claude 的機制；Codex、OpenCode 有沒有對應的機制未查證 | 這段是 `codegraph install` 寫入的，有 `when available` 這個條件，影響不大 |
| Codex 會吃 `AGENTS.override.md`，Claude 不讀〔C1「Not read: … `AGENTS.override.md`」〕 | 用 override 做暫時規則的話，只有 Codex 會生效 | 沒有用 |
| Cowork 會略過 symlink 的 `~/.claude/CLAUDE.md`〔C1〕 | 在 Cowork desktop session 裡全域規則整份不見 | 目前只用 CLI，沒有影響；改用 Cowork 時要換成實體檔 |
| 祖先 `CLAUDE.md` 會擋掉子 repo 的 `AGENTS.md`（Claude 專屬） | `~/code/CLAUDE.md`（內容是 `@AGENTS.md`）是 `~/code/*` 的祖先，所以在 `~/code/fizzt-frontend`、`~/code/local-e2e-bootstrap`（只有 `AGENTS.md`，`ls` 實測）開 Claude 時，預設設定 `claude-md-or-agents-md` 只會讀到 `CLAUDE.md`，不會讀它們自己的 `AGENTS.md`〔C1「My AGENTS.md isn't loading」第 1 步〕 | 依文件推論，**未實測**。修法：在 `~/.claude/settings.json` 的 `pluginConfigs["cc-plugin-agents-md@builtin"]` 設 `claude-md-and-agents-md`（文件說已經 import 的 `AGENTS.md` 不會讀兩次）〔C1〕。這個設定只在 user／managed settings 才生效〔C1〕，所以要改 dotfiles 的 `modify_` |

## 2. 官方對內容的建議

| 主題 | 官方說法 | 來源 |
|---|---|---|
| 放什麼 | 「Keep it to facts Claude should hold in every session: build commands, conventions, project layout, "always do X" rules.」；只放「what Claude couldn't work out from the code itself」：驗證指令、會誤導人的地方、repo 裡找不到的決策、已經糾正過兩次的事 | C1、C2 |
| 什麼時候加 | 同一個錯犯第二次、同一個 review 意見出現第二次、同一句糾正又打了一次 | C1、C3、X3 |
| 不放：多步驟、特定任務 | 「If an entry is a multi-step procedure or only matters for one part of the codebase, move it to a skill or a path-scoped rule」；放在 skill 裡的長流程「doesn't weigh on your unrelated bug fix」 | C1、C2；Codex：「Skills are often the best fit for reusable workflows」X3 |
| 不放：一定要做到的事 | 「If something has to happen every time, make it a hook, a deny rule, or a managed setting. CLAUDE.md is for guidelines」；「Put guardrails in hooks」 | C2、C3；Codex：「Pair AGENTS.md with infrastructure that enforces those rules」、格式和 lint 交給 CI，X1、X3 |
| 不放：從 code 推得出來的 | 架構、目錄結構「Claude reads the repo itself」；`/doctor` 會把目錄結構、依賴清單、架構概覽刪掉，保留「pitfalls, rationale, and conventions that differ from tool defaults」 | C1、C2 |
| 不放：跟 harness 打架的 | 如果 `CLAUDE.md` 寫了 commit／PR 規則，先用 `includeGitInstructions` 關掉內建的那套，再用 `attribution` 設定署名 | C1 |
| 長度 | Claude：每個檔 200 行以內，「Longer files consume more context and reduce adherence」。Codex：「Keep it small」「Start with only the instructions that matter」。Anthropic：context 是「a finite resource with diminishing marginal returns」，但「minimal does not necessarily mean short」 | C1、C3、X3、A1 |
| 措辭 | 要具體到可以檢查：「Use 2-space indentation」而不是「Format code properly」；用 markdown 標題和條列分組 | C1 |
| 抽象程度 | 「right altitude」：太死會變成寫死的脆弱邏輯，太空泛又沒有具體訊號；給「strong heuristics」 | A1 |
| 範例 | 給幾個多樣、典型的例子，不要塞一長串 edge case | A1 |
| 強調詞 | 「adding IMPORTANT probably won't fix it」；「piling on emphasis mostly makes Claude over-apply the rule」。一直被忽略的規則，要嘛是檔案太長，要嘛應該改成 hook | C2 |
| 衝突 | 矛盾的規則 Claude 會隨便選一條；要定期檢查（`/doctor prompt-audit`） | C1 |
| 對 agent 講話的寫法 | 「describe each tool as you would to a new team member」，隱含的前提要寫出來，名稱要沒有歧義 | A2（雖然是在講 tool description，同樣適用於規則裡提到的 skill 名、路徑） |
| agents.md 標準 | 「just standard Markdown」，沒有必填欄位；建議段落：overview、build/test 指令、code style、testing、security；離被改的檔最近的那份優先，使用者在對話裡講的高於一切 | G1 |

## 3. 逐條對照

判定：✅ 符合／◐ 部分偏離／✗ 偏離。行號以 2026-11-21 的工作目錄為準。

### 全域規則 `extras/agents-md/AGENTS.md`（84 行、6,149 bytes、3,623 字元）

| 行 | 段落 | 判定 | 理由 | 建議 |
|---|---|---|---|---|
| 1–2 | 標題 | ✅ | — | — |
| 3 | 範圍：只寫換到任何 repo 都成立的事 | ✅ | 對應 Claude 對 user 檔的定位「Personal preferences for all projects」〔C1〕 | 保留 |
| 4–5 | README／`docs/` 怎麼放、工具用法連官方、設定檔註解就是文件 | ◐ | 只有寫文件時才用到，不是每個 session 都需要〔C1、C2〕。但另外兩份 `AGENTS.md` 都引用它（本 repo `AGENTS.md:30`、dotfiles `AGENTS.md:51,140`） | 搬進一支自己寫的「寫文件」skill（`writing-for-agents` 是第三方的，不能改，見本 repo `AGENTS.md:13-14`），全域只留一行觸發條件；兩份 `AGENTS.md` 的引用一起改 |
| 6–8 | 機制怎麼選：AGENTS.md／skill／MCP／hook，加官方連結 | ✅ | 跟 Claude〔C3〕、Codex〔X3〕的分法一致，每個機制一句話 | 保留；這是本 repo `AGENTS.md:30` 依賴的那句 |
| 10–12 | 語言 | ✅ | 每個 session 都要、具體。Claude 有 output style 可以放回覆格式〔C3〕，但它只有 Claude 有，共用檔不適合 | 保留 |
| 14–19 | 白話，附 ❌／✅ 範例 | ✅ | 有判斷標準，也有典型範例〔A1〕 | 保留 |
| 21–25 | 回覆 | ✅ | 具體；L25 寫明了跟 skill 衝突時聽哪邊，避開「隨便選一條」〔C1〕 | 保留 |
| 29 | 「偏好精簡的視覺呈現」 | ◐ | 偏抽象，很難判斷有沒有做到〔C1「concrete enough to verify」〕 | 改成可以檢查的寫法，例如「流程、前後比較、目錄關係先用表格或縮排樹，簡單的答案不畫圖」 |
| 30–32 | agent 指引照 skill、平台限制、mermaid | ✅ | 具體的坑，也寫了原因 | 保留 |
| 34–36 | PR body | ◐ | 只有寫 PR 時才用到〔C1〕。這段用來覆寫第三方 `pr` skill 的模板（`skills/pr/SKILL.md` 寫的是 `## Evidence`，這裡要求 `## 驗證`），是刻意的；但同一件事分寫在兩處，載入順序變了就可能衝突〔C1〕 | 另寫一支自己的 skill 包住 `pr`，把 `## 驗證` 和證據規則放進去；全域只留「寫 PR body 用 `<新 skill>`」一行 |
| 38–42 | 誠實 | ✅ | 可以檢查（有沒有附路徑、行號），從 code 推不出來 | 保留 |
| 44–51 | Issue 狀態：認領／卡住／完成／交接 | ✗ | 四個步驟的流程，只有處理 issue 時才用到，1.3 KB，佔全域檔 21%。這正是官方說要移到 skill 的那一類〔C1、C2、X3〕 | 搬成自己寫的 skill（例如 `issue-status`），全域只留「處理 issue 時先載入 `<skill>`」一行。L46 那句「repo 寫的優先」跟著搬過去 |
| 53–55 | Commit 共同作者 → 讀 `~/.config/agent-commit/instructions.md` | ◐ | 只是一行指向外部檔，成本很低。但 Claude 本身也會在 commit 時注入署名指示（`~/.claude/settings.json` 已經設了 `attribution.commit`），兩套可能打架〔C1「competes with guidance Claude Code adds」〕。要「累積多個 agent」的話，`attribution` 設定做不到 | 保留；評估改成 `prepare-commit-msg` git hook 或 Claude hook，讓它一定生效〔C2〕 |
| 57–61 | Worktree | ✅ | L59 是觸發 skill 的一行；L61 是踩過的坑，有寫原因 | 保留 |
| 63–66 | HTML 維護註解 | ✗ | 內容過時：寫「這份檔案由 chezmoi 部署」，但現在是 skillshare extras 建的 symlink（本 repo `AGENTS.md:34`、dotfiles ADR 0003）。而且在 Codex、OpenCode 會進 context（見 §1） | 修正內容，或搬到本 repo 的 `docs/`，這裡只留 START／END 標記 |
| 67–76 | CodeGraph（工具自動寫入） | ◐ | 是路由規則，有用。但 L70 的 `BEFORE` 是全大寫強調〔C2 說會讓模型過度套用〕；L72 用到 Claude 專屬的概念。而且 codegraph MCP server 自己就會送 server instructions（本 session 實測看得到「Codegraph — available」那段），在 Claude 等於重複 | 不要手改（`codegraph upgrade` 會重寫）；記下來就好，不另開 issue |
| 78–84 | Graphify 什麼時候用 | ✅ | 路由規則，從 code 推不出來，有三個可以判斷的條件 | 保留 |

做完前兩項（Issue 狀態、文件放置）之後，全域檔大約剩 60 行、4.5 KB（估算：扣掉 L44–51 約 1.3 KB、L4–5 約 0.4 KB）。

### 本 repo `AGENTS.md`（51 行、3,811 bytes）

| 行 | 段落 | 判定 | 理由 | 建議 |
|---|---|---|---|---|
| 3–4 | repo 是什麼、語言、連 README／GLOSSARY | ✅ | 短，用連結 | — |
| 8–10 | 秘密不進 repo，含例外 | ✅ | 一定要遵守、有具體做法。可以補一個 hook 或測試來強制（例如 commit 前掃 key）〔C2〕 | 選做 |
| 11–16, 25–26 | `config.yaml` 不 commit、第三方 skill 不改、用指令加、不加 OpenCode target | ✅ | 都是從 code 推不出來的坑，也寫了原因 | — |
| 17–20 | 指令只寫一份、放哪 | ◐ | 只有寫文件時才用到；跟全域 L4–5 是同一類 | 跟全域那段一起搬進「寫文件」skill，這裡只留 repo 特有的路徑（`docs/skills/<名字>.md`） |
| 30 | 「照全域規則開頭那句」 | ◐ | 依賴全域檔的內容；全域檔改了這裡就斷 | 全域 L6–8 保留的話不用動；如果搬走，要改成連到新位置 |
| 32–39 | 放哪的表 | ✅ | repo 特有、從 code 推不出來 | — |
| 43–51 | 驗證指令 | ✅ | 正是官方最推薦放的東西〔C2〕 | — |

### dotfiles `AGENTS.md`（204 行、15,473 bytes）

| 行 | 段落 | 判定 | 理由 | 建議 |
|---|---|---|---|---|
| 全檔 | 長度 | ✗ | 204 行，超過 Claude 的 200 行建議，啟動時會出警告〔C1〕。Codex 15,473／32,768 bytes 還有空間 | 把下面三段搬出去 |
| 3–13, 17–33 | 平台限制、repo 兩半、`run_` 不分資料夾 | ✅ | 會誤導人的地方，有寫原因〔C2〕 | — |
| 39–52 | 前綴表（刻意不連官方） | ✅ | 自己寫明了為什麼例外，符合「conventions that differ from tool defaults」〔C1〕 | — |
| 48 | ⚠️ 新腳本要加 `executable_` | ◐ | 用強調符號加重語氣，但這件事可以機械式檢查〔C2〕 | 在 `script/tests/` 加一個檢查（`dot_local/bin` 等可執行目錄下的檔沒有 `executable_` 就失敗），之後拿掉 ⚠️ |
| 56–66 | 秘密 | ✅ | 會漏、會炸的坑，附了驗證指令 | — |
| 70–92 | 驗證指令、e2e 說明 | ✅ | 驗證指令是官方最推薦的〔C2〕。L86–92 的 e2e 細節偏長，但每一句都是坑 | 保留 |
| 94–128 | Windows 實機清單（13 列的表） | ✗ | 只有改到 Windows 部署的檔時才用到，佔 35 行〔C1、C2〕 | 搬到 `docs/agents/windows-verification.md`，這裡留觸發條件和連結 |
| 130–133 | `/implement-spec` 時的驗證節奏 | ✗ | 只在特定 skill 的流程用到 | 搬到 `docs/agents/issue-tracker.md` 或新的 `docs/agents/` 檔 |
| 135–136 | 不要直接改家目錄那份 | ✅ | 典型的坑 | — |
| 138–172 | 文件放哪 | ◐ | 只有寫文件時才用到；L157 的 mermaid 規則跟全域 L32 重複〔C1：重複和矛盾要清掉〕；L165–171 的 #168、#309 是好的「為什麼」 | 表格（L144–151）和 L153–163 搬到 `docs/agents/docs-layout.md`；刪掉 L157；L165–171 留下 |
| 174–186 | 註解樣式 | ✅ | repo 特有的慣例，有判斷標準 | — |
| 188–204 | Agent skills 的指向 | ✅ | 都是一行連結 | — |

搬完三段之後大約剩 130 行、10 KB（估算）。

## 4. 建議開的 issue（未開）

### agent-config（henry5720/agent-config）

1. **全域規則的「Issue 狀態」改成 skill**：把 `instructions/agents-md/AGENTS.md:44-51` 的認領／卡住／完成／交接搬成自己寫的 skill，全域只留一行觸發。
2. **文件放置通則移出全域規則**：把 L4–5 和本 repo `AGENTS.md:17-20` 搬進一支自己寫的「寫文件」skill，並一起改本 repo `AGENTS.md:30`、dotfiles `AGENTS.md:51,140` 的「全域規則開頭」引用。
3. **PR body 規則改成包住 `pr` 的自寫 skill**：把 L34–36 的 `## 驗證` 和證據規則放進 skill，解決跟第三方模板 `## Evidence` 分寫兩處的問題。
4. **修正 CodeGraph 區塊上方過時的維護註解**：L63–66 寫「由 chezmoi 部署」，改成 skillshare extras（或移到 `docs/`），因為它在 Codex、OpenCode 會進 context。
5. **「照讀者選格式」L29 改成可以檢查的句子**：把「偏好精簡的視覺呈現」換成具體的條件。

### dotfiles（henry5720/dotfiles）

1. **讓 Claude 在 `~/code/<repo>` 也讀 `AGENTS.md`**：`modify_` 管的 `~/.claude/settings.json` 加 `pluginConfigs["cc-plugin-agents-md@builtin"]` = `claude-md-and-agents-md`，先實測 `~/code/fizzt-frontend` 改之前和改之後的 `/memory`。
2. **`AGENTS.md` 降到 200 行以內**：Windows 實機清單（L94–128）、`/implement-spec` 驗證節奏（L130–133）、文件放置表（L144–163）搬到 `docs/agents/`，刪掉跟全域重複的 L157。
3. **用測試取代「新腳本要加 `executable_`」的 ⚠️ 規則**：在 `script/tests/` 加檢查，通過後拿掉 L48 的強調。
4. **評估用 hook 處理 commit 共同作者**：全域 L53–55 靠 agent 自己去讀 `~/.config/agent-commit/instructions.md`，評估改用 `prepare-commit-msg` 或 Claude／Codex hook 強制，並確認不會跟 Claude 的 `attribution` 設定打架。

## 未驗

- Codex 全域檔不扣 `project_doc_max_bytes`：只看了原始碼，沒有實測。
- `~/code/CLAUDE.md` 會擋掉子 repo 的 `AGENTS.md`：依文件推論，沒有在 `~/code/fizzt-frontend` 開 Claude 實測。
- 三家各自實際送進模型的 token 數：只算了 bytes／行數／字元，沒有算 token。
- OpenCode 什麼時候重讀規則檔、Codex／OpenCode 有沒有 deferred tool 的概念：未查證。
- 「搬完後大約剩幾行」是用行數和 bytes 估的，不是實際改完再量。

## 實測紀錄

```text
$ wc -l / wc -c / wc -m
instructions/agents-md/AGENTS.md            84 行  6149 bytes  3623 字元
AGENTS.md（agent-config）                    51 行  3811 bytes  2545 字元
~/.local/share/chezmoi/AGENTS.md           204 行 15473 bytes  9867 字元
L63–66 維護註解 397 bytes；L63–76 CodeGraph 整段 1203 bytes

$ ls -la ~/.claude/CLAUDE.md ~/.codex/AGENTS.md ~/.config/opencode/AGENTS.md
三個都 -> /home/ubuntu/.config/skillshare/instructions/agents-md/AGENTS.md

$ ls ~/code/*/AGENTS.md ~/code/*/CLAUDE.md
只有 AGENTS.md：fizzt-frontend、local-e2e-bootstrap；~/code/CLAUDE.md 內容為 `@AGENTS.md`
```

## 來源

- **C1** Claude Code memory：<https://code.claude.com/docs/en/memory>（Write effective instructions、Import additional files、How CLAUDE.md files load、AGENTS.md、Troubleshoot）
- **C2** Claude Code best practices：<https://code.claude.com/docs/en/best-practices>（Keep CLAUDE.md short、Enforce the rules that can't have exceptions、What you can stop doing）
- **C3** Claude Code extend／features overview：<https://code.claude.com/docs/en/features-overview>（CLAUDE.md vs Skill、Hook vs Skill、Context cost by feature）
- **X1** Codex AGENTS.md：<https://developers.openai.com/codex/guides/agents-md>（308 轉到 <https://learn.chatgpt.com/docs/agent-configuration/agents-md>）
- **X2** Codex 原始碼 `rust-v0.171.0`：<https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/agents_md.rs>、<https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/codex-home/src/instructions/mod.rs>
- **X3** Codex customization：<https://learn.chatgpt.com/docs/customization/overview>
- **O1** OpenCode rules：<https://opencode.ai/docs/rules/>
- **O2** OpenCode 原始碼 v1.18.35（`53d1eab`）：<https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/session/instruction.ts>
- **G1** agents.md：<https://agents.md/>
- **A1** Anthropic, Effective context engineering for AI agents：<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- **A2** Anthropic, Writing effective tools for agents：<https://www.anthropic.com/engineering/writing-tools-for-agents>
