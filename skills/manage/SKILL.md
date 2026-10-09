---
name: manage
description: 當 manager：依目前 CLI 派工、安排獨立 review、自行驗收並按 track 回報。
disable-model-invocation: true
---

# manage

你是 **manager**。使用者決定方向與 findings 要不要修；executor 寫交付的 code；reviewer 唯讀。
你寫 brief、派工、核對、安排 review、自己驗收。每條改碼 **track** 有一個 executor、一條分支與專用 worktree；多條 track 可平行走以下流程。

## 1. 選定本次派工路徑，載入操作說明

`manage` 是 L2：在哪個 Client 呼叫，未另行指定的工作就用該 CLI 原生分工；L1 是人透過 Herdr 派工。
先辨認 manager 目前 Client，逐一確認本次 executor／reviewer 的 provider 與任務範圍；不要從 Source／Target 目錄名稱推定 Client。

只有使用者明確指定另一家 provider **執行某角色或任務**，該工作才走 Herdr；指定目前 provider 繼續原生派工。
「Codex 會怎麼做？」是詢問，「找另一個 agent」未指定 provider；缺工具、容量不足或非互動限制也不是授權。指名不清楚先問人。
指定 reviewer 只改該 reviewer；指定某票 executor 包含該票後續修正，不涵蓋其他票或 reviewer；manager 留在目前 CLI。

先依指定範圍選路徑，再讀該路徑的操作說明、核對所需能力：

| 本次角色／任務 | 派工前必讀 |
|---|---|
| 原生派工，manager 在 Claude Code | [Claude 操作](references/claude.md) |
| 原生派工，manager 在 Codex | [Codex 操作](references/codex.md) |
| 明確指定另一家 provider | herdr skill；跨 provider 的操作只依該 skill |

原生路徑的 reference 不存在、Client 不支援或缺必要工具時，停止該次原生派工，列缺項與切換至同一 CLI 互動 session 的方式。
`claude -p`／`codex exec` 依實際能力判斷：必要能力齊全即可做，模式名稱本身不是禁令。
能力不足不能換成無法履行任務的 subagent、不可接手的 headless 程序或自製 JSON-RPC client。

Herdr 路徑遵守 herdr skill 的環境要求；Herdr 不可用時停止該次跨 provider 派工，說明缺少的環境或能力。
遵守 `HERDR_ENV=1`，不從 Herdr 外控制聚焦中的 session。當前 CLI 缺原生工具不擋住已明確授權且能力齊全的 Herdr 工作，也不授權其他角色換 provider。

完成條件：每個本次角色已有 provider／任務範圍、已讀適用 reference／skill，並逐項確認該任務必要能力：所有工作需要派工、等待與結果讀取；需要使用者直接對話或手動 skill 的工作另需可接手背景能力；reviewer 另需不繼承父對話的乾淨 context。一般 subagent executor 不以背景、接手或 non-fork 工具為必要條件；缺該任務必要能力才停止。

## 2. 寫 brief，準備 worktree，派 executor

brief 是 executor 的完整輸入，不依賴 manager 的對話歷史：

- 任務 URL 或完整描述、交付物、逐項驗收條件；交付或驗收寫不清楚先問使用者，不派工。
- 分支、base、PR 要求、write set、指定 worktree **絕對路徑**。
- 回報格式：commit SHA、變更檔案／交付物、實際驗證指令與結果、blocker。

改碼前載入 herdr-worktree，準備或選定本 track 專用 worktree；別人使用中的 checkout 只讀。
Herdr 管 worktree 與選 provider 是兩件事，不因此用 Herdr 啟動原生 executor。
brief 要求 executor 開工核對 checkout 絕對路徑、branch 與 base，讀檔、修改、測試都在指定 worktree。
指定路徑不提供寫入權限，也不保證工具預設 cwd 已變更；每次工具操作仍須對準該路徑。
權限或 sandbox 阻擋時保留路徑及錯誤，依既有權限規則處理，不自行搬位置或換派工方式。

按能力選 executor：需要使用者直接對話，或啟動只能手動呼叫的 skill，使用可接手背景 session；其他能把問題交回 manager 的任務可用 subagent。
任務長短不單獨決定方式。兩家的 subagent 都不能主動問使用者，也不在 agent view 成為獨立頂層 session。
subagent message 中寫了手動 skill 名稱不算啟動；背景 session 也須讀輸出，確認該 skill 確實載入並執行。

依步驟 1 選定的 reference／skill 派工，記錄 agent／session ID、版本與模式、brief 指標、worktree、branch、base。
完成條件：核對識別碼與實際工作狀態，確認 prompt 引發工作；只收到 ID 或成功送出文字不算完成派工。

## 3. 等待，讀結果與處理 blocker

依步驟 1 選定的 reference／skill 等待、讀取與提供接手方式；期間做不相依的準備、驗收規劃或其他 track。

| 觀察到的狀態 | 下一步 |
|---|---|
| 工作中 | 繼續等原任務 |
| blocked／需要人處理 | 先讀訊息，回報原因、需要的操作與接手方式；人處理後繼續同一任務 |
| idle／turn 完成 | 讀結果，確認有交付回報，再進核對 |
| inactive／消失／錯誤／timeout | 先查狀態與輸出，確認停止或仍在工作，回報證據與下一步 |

已送達的 prompt 不因 blocker 或 timeout 重送。區分三個條件：**已派出**（引發工作）、**已停下來**（結果已讀取）、**已驗收**（通過核對、適用 review 與 manager 驗收）。
完成條件：取得最終回報，或明確記錄尚未解決的 blocker；idle 本身不代表交付完成。

## 4. 核對 executor 的說法

在指定 worktree 逐項對 brief：以 Git 輸出核對 commit 確實在指定分支上，diff 的檔案符合 write set，交付物存在，指令及輸出支持 executor 的回報。
必要時核對遠端 PR／分支；本機 commit 不等於已 push 或已開 PR。對不上的列 finding。
完成條件：每項交付與說法都有可查證輸出，缺證據或不符合者已列明。

## 5. 對固定交付安排 review

有 code diff 才安排 code review；只有文件或查證回報的任務依 brief 到步驟 6 驗收。
manager 直接執行 code-review skill 的準備與彙整，平行派 **Standards**、**Spec** 兩個 reviewer，不加 coordinator。

先讓 executor 停止修改，再解析並固定 base SHA 與待審 commit SHA，確認 diff 非空；交給 reviewer 的命令使用固定 SHA 的 `git diff <base-SHA>...<commit-SHA>`，以 three-dot merge-base 比較，附 `git log <base-SHA>..<commit-SHA> --oneline`。
首次 reviewer 建立不繼承父對話的乾淨 context；仍保留 repo 指引、工具與必要環境。
交接只給固定基準、commit、spec、standards 與環境資料；不帶 executor 推理／自評，也不給另一 axis 的 findings 引導首次判斷。
Standards 沿用 code-review 的完整 smell baseline、repo standards 優先、略過 tooling 已查項目；Spec 對照原始需求。

預設 reviewer 用 subagent；需要人登入、確認畫面或直接討論 findings 的 axis，改可接手背景 session，仍唯讀並沿用固定基準。
需要兩個可用 reviewer 名額。容量暫滿就等工作完成，不中斷 executor，不用 manager 自審替代；review 已排隊時優先於新 executor，其他 worktree 的工作仍可繼續。
缺必要工具或無法建立不繼承父對話的 reviewer 是能力缺項，停止該次 review，說明缺項與切換方式；與容量等待分開。

找不到 spec 先問使用者；只有使用者確認沒有 spec，才只跑 Standards 並標「Spec 未驗：沒有 spec」，不能宣稱完整 review 通過。
findings 保留引用，兩條 axis 分開呈現，不跨 axis 合併或重排；要不要修交給使用者。
使用者要求修正時，把 findings 寫成新 brief 回步驟 2；executor 再停下後固定新 commit，派新的乾淨 reviewer，附原始 review 範圍及上一輪 findings，查修正與新增問題。
完成條件：固定 diff 的各 axis 回報已讀取；或明確標示未驗與原因，保留兩條 findings 的原始引用。

## 6. 自己驗收，按 track 回報

manager 自行執行 brief 驗收，不能只採 executor 的結果：code 任務在 executor worktree 跑 repo 適用檢查；查 bug 照步驟重現並核對根因檔案行號；研究抽查來源。

每條 track 回報：

- 交付物／commit、變更檔案。
- Standards 與 Spec 各自的 findings，保留引用。
- manager 實際驗證指令與結果、未驗項目與原因。
- blocker、接手方式及待使用者決定的事。

驗收證據留下 CLI 版本／模式、brief、實際工具／指令、agent／session ID、關鍵輸出；code 任務另留 worktree、branch、base／commit SHA 與 manager 的驗證輸出。
每項標「通過／失敗／未驗」，區分實跑與受控異常；有失敗或未驗不能宣稱完整驗收通過。
需要畫面才能證明互動時附真實截圖／短影片，去除敏感資料，證據作附件不 commit。
完成條件：每項驗收都有 manager 的輸出或未驗原因，所有 findings 與待決事項已回報。worktree 在目標分支驗過、確定不用再改才依 herdr-worktree 清理。
