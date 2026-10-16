---
name: pr-review-and-verify
description: >-
  使用者明確呼叫本 skill、說「收這個 PR」，或要求完整執行 PR 獨立審查與驗收時使用；
  開 PR 或一般要求 review 本身不啟動收尾流程。
argument-hint: "<PR> [draft]"
---

# PR 獨立審查與驗收

本 skill 由使用者明確啟動一輪。你是**流程負責人**：派獨立審查、修正、驗證、回覆、發布收尾。依序完成每一步的完成條件再進下一步。

```text
1. 固定範圍        head SHA、需求、既有意見、有沒有 reviewer
2. 獨立審查        乾淨 context 審 → 你逐條驗證 → [head 閘門] → 發 report
3. 修正與驗證      只修明確 bug；測試、typecheck、瀏覽器（看整張 PR）
4. 回覆 threads    每條回原 thread
5. 收尾            [head 閘門] → 更新 body → 列 CI 狀態 → [head 閘門] → 收尾 comment
```

## 規則選用

- **審查方法**：用目前 repo 自己的 review skill；沒有才用共用的 `code-review`。它負責怎麼審，本 skill 負責流程與發布；它自己的發布規則改由 [發布模式] 決定。
- **[發布模式]**：呼叫參數沒有 `draft` 時直接發布。有 `draft` 時整輪只停兩次，都在對外發布前：步驟 2 的 report；步驟 5 的發布（thread 回覆、PR body、收尾 comment 一起）。停的時候給使用者草稿檔路徑與本機證據路徑，使用者說「發」才發；[blocked comment] 也一樣先給草稿。
- **衝突時的優先順序**：本 skill 的明確要求（含發布授權）只在它管的範圍內優先於一般 repo 規則；其他未衝突的 repo 規則照常適用。兩項明確要求仍無法判定先後時，完成不受影響的工作，發 [blocked comment]，再問使用者；不自行推定。
- **驗證**：照 repo 規定與本次指定的 verification skill。瀏覽器驗收用 `verify-in-browser`；它只回報結果與本機證據路徑，附件由你在步驟 5 發布。
- **PR body**：用 `pr` skill。

## 兩個共用動作

**[head 閘門]**：發布任何 report、回覆、body 或 comment 之前，重新查遠端 head。head 變了 → 讀新增差異 → 更新受影響的 finding 與驗證範圍，發布的內容要對應新 head。每項結果保留它實際測過的 commit SHA。

**[blocked comment]**：遇到規則衝突、待決需求、驗證受阻等已知阻塞時，先完成不受影響的工作，過 [head 閘門]，發一則「收尾未完成」PR comment：已完成工作、阻塞來源與檔案／行號、影響、未完成與未驗範圍、需要使用者做的決定。若 PR body 的 `## 驗證` 會把舊 head 或未通過的結果寫成完成，先一起更正。發布後才問使用者。沒有發布權限時，把同樣內容留在 session 並說明原因。

## 一輪流程

### 1. 固定範圍

讀 PR 的 base、遠端 head SHA、需求來源（issue／spec）、`reviewRequests`，以及全部一般 comments、整體 reviews 與 inline threads（含已解決）。把每項既有意見對回原 thread、程式碼位置與目前狀態。

**完成條件：** head、需求、每項既有意見、有沒有 reviewer 都有來源；拿不到的內容已標明缺項與影響。

### 2. 獨立審查並發布 report

審查在**乾淨的 context** 裡做：審查者只拿到 PR 號碼、head SHA 與需求來源，不帶你的推理。能派 subagent 就派；不能時開新的 headless session。兩者都做不到才在原 session 審，report 標題寫「非獨立審查」。

收回 findings 後，逐條回原始碼驗證，驗不過的不發布。每項寫出證據位置、影響與建議處理，分成：

- **明確 bug**：步驟 3 修。
- **需求取捨**：問使用者。
- **寫法／可優化**：只列在 report，不修、不擋收尾。

過 [head 閘門] 後照 [發布模式] 把 report 發到 PR、取得 URL。修正與瀏覽器驗收都在這之後。

**完成條件：** report URL 已取得，且發布早於任何修正；每條 finding 都有目前程式碼的證據與分類。

### 3. 修正與驗證

只修證據充分、修法明確且符合需求的 bug。依 repo 規則選驗證範圍，只跑受影響的部分。

**瀏覽器驗收看整張 PR**，不是只看這輪修正：只要改到使用者會操作的路徑（mutation、toast、按鈕狀態、route），每個改到的操作至少走一次成功路徑。沒走或觸發不了的狀態，逐項列出操作名稱與原因。

每項驗證記錄 commit SHA、範圍、指令或操作、結果與證據。有新 commit 時，只重跑受它影響的項目，舊結果保留原本的 SHA。

**完成條件：** 明確 bug 已修；必要驗證都有結果和對應的 SHA，未驗項目都有原因。

### 4. 回覆既有意見

inline 意見回原 thread；一般留言與整體 review 回原對話，不另開頂層留言。逐項交代處理結果、commit 與驗證；沒修的說明原因；已過時的引用目前程式碼說明。

**完成條件：** 每項既有意見都有回覆，或列為發布受阻；待 reviewer 確認的項目清楚可見。

### 5. 收尾

使用者啟動本 skill，即授權你發布本輪 report、thread 回覆、PR body 更新與收尾 comment；什麼時候發照 [發布模式]。你是本輪唯一的 publisher；其他參與的 agents 把修改、commit 與驗證交回給你。

1. 過 [head 閘門]，用 `pr` skill 更新 PR body 與 `## 驗證`：實際指令或操作、結果、證據、未驗原因、剩餘風險，對應已核對的 head。
2. 列出該 head 上 `gh pr checks` 每一項的狀態。有失敗 → 不算完成；pending → 列為未驗，不等它跑完；PR 是 draft → 寫明「CI 沒跑，轉 ready 才會跑」。
3. 過 [head 閘門]，發一則本輪唯一的收尾 comment：已核對的 head、最終驗證結果、未驗原因、待 reviewer 確認的項目，以及結束狀態。不重貼整份 body；有新增風險才補 Merge Danger。

**附件**：`verify-in-browser` 回報的就是照它 `report-template.md` 寫好的 comment，存成檔案直接發，在證據資料夾裡執行，body 引用的每張圖各帶一個同樣相對路徑的 `--attach`：`cd <E> && gh pr comment <PR> -F <回報檔> --attach './x.png'`。body 裡的 `./x.png` 會被換成上傳後的網址（限制見 `playwright-cli` 的 PR attachments）。L0 沒有瀏覽器驗收 comment，只寫進 `## 驗證`。附件不 commit，要對應實測的操作與 SHA。測試環境預設附上有助判讀的真實截圖，正常的測試業務資料（姓名、email、對話）照常保留；發布前遮蔽實際出現的密碼、token、API key 與登入憑證。遮蔽截圖不等於清理了 trace、影片或 storage state，那些各自檢查。附截圖還是影片，照 `verify-in-browser` 的證據判準。

**完成條件：** 收尾 comment 的 URL 已取得，內文含 head、驗證結果、CI 狀態、未驗原因與結束狀態；重新讀取 PR body，`## 驗證` 對應同一個 head。

## 結束狀態

- **「本輪完成，等待 review」**：report 已發布、明確 bug 已修、需求決策已有答案、必要驗證通過且 SHA 正確、既有意見都已回覆、CI 沒有失敗、body 與收尾 comment 對應同一個 head，而且 PR 有 reviewer。
- **「本輪完成，尚未指派 reviewer」**：同上，但 PR 沒有 reviewer。
- **「收尾未完成」**：上面任何一項沒達成，發 [blocked comment] 後問使用者。有新證據就繼續做；同樣的失敗重現且沒有新線索，或需要改需求、擴大範圍時，停下來問，不無限重試。

每輪由使用者重新啟動。resolve thread、approve 與 merge 都由人操作，不代做。
