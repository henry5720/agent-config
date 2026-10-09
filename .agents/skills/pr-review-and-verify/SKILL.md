---
name: pr-review-and-verify
description: >-
  使用者明確呼叫本 skill、說「收這個 PR」，或要求完整執行 PR 作者自審與驗收時使用；
  開 PR 或一般要求 review 本身不啟動作者收尾流程。
---

# PR 自審與驗收

本 skill 僅由作者明確啟動一輪；在原 session 完成自審、必要修正與驗證、既有意見回覆及 PR 收尾。先按順序完成每階段條件，再進下一階段。

## 規則選用

- 自審先找目前 repo 明確適用的 review skill；有就用它，沒有才用共用 `code-review`。被選中的 review skill 負責審查方法，本 skill 負責作者流程與收尾。
- 使用者明確指定某 skill 或流程時，該 skill 對本次工作的具體要求及發布授權優先於衝突的一般 repo 指引；其他未衝突的 repo 規則仍適用。只在指定範圍套用優先權，不把它擴張成覆蓋整個 repo。單獨使用原 skill 時，仍遵守該 skill 自己的流程與發布規則。
- 先依適用範圍判定差異。若兩項明確要求仍無法並行或判定優先順序，先完成不受衝突影響的工作，停止受影響工作。回到使用者詢問前，若目前是 PR 作者回合且有 GitHub 發布權限，先重新核對遠端 head；head 有變就讀新增差異並更新影響與驗證範圍，再由本輪唯一 publisher 發布一則「收尾未完成」PR comment，列出已完成工作、兩邊原文與檔案／行號、衝突影響、未完成／未驗項目及需要使用者決定的下一步。若無發布權限，在 session 明確記錄權限阻礙及相同資訊，不假稱已發布。發布或記錄後再詢問使用者；不得先等答案才回報已知阻塞，也不得自行推定優先順序。
- 驗證使用 repo 規定及本次明確指定的 verification skill。需要實際畫面或操作才能判定時，使用 `verify-in-browser` 及其指向的瀏覽器工具 skill。
- 需要寫或更新 PR body 時，使用原有 `pr` skill；不要複製它的 body 範本或 review 方法。

## 一輪流程

### 1. 固定 PR 範圍

讀取 PR 的 base、最新遠端 head、目前工作分支／HEAD 與需求來源；讀取所有一般 PR comments、整體 reviews，以及完整 inline review threads（含未解決及已解決項目）。記錄 head SHA，並把每項 feedback 對回原 thread、程式碼位置與目前狀態。看不到必要資料或權限不足時，記下缺項與影響；能完成的部分照做。

**完成條件：** review 範圍、base、遠端 head、需求和每項既有意見都有來源；任何不可取得的內容已明確標出。

### 2. 發布自審 report

針對固定 head 執行適用的 repo review skill（沒有才用 `code-review`），並以最新原始碼核對舊 finding 與作者聲稱已完成的修正。每項 finding 寫出證據位置、影響及建議處理；區分明確 bug、需求取捨、寫法／優化建議。需求取捨先問使用者；寫法與可優化建議只列在 report，不自動修改，也不作為阻擋收尾的 bug。

自審完成後，先向 PR 發布本輪 report 並取得 URL，再開始修正或 browser 驗收；開啟頁面、讀取畫面狀態與派發 browser 驗收任務都在此後執行。每次發布 report、thread 回覆、結果或 body 前，都重新查最新遠端 head；如 head 有變，先讀新增差異、更新受影響 finding 及驗證範圍，再發布與新 head 相符的內容。

**完成條件：** report URL 已取得，且發布先於修正及 browser 驗收；finding 皆有當前程式碼證據與分類。發布受阻時記錄原因，不假稱已發布。

### 3. 修正明確 bug 並驗證

只直接修正證據充分、修法明確且符合需求的 bug。需求或風險取捨交由使用者決定；不把建議性優化轉成自動修改。依 repo 規則與改動選必要驗證，不盲跑全套；需要畫面／操作驗收時依 `verify-in-browser` 執行。

每項驗證記錄實際測試的 commit SHA、範圍、指令或操作、結果及證據。沿用結果時保留原測試 SHA，不改標成新 commit。每有新 commit，對照該 commit 的差異與各項測試範圍，判定哪些舊結果仍適用、哪些受影響；只重跑受影響及 repo 要求的項目。發現問題就修正並重驗受影響範圍，保留各版本結果與對應關係。

**完成條件：** 明確 bug 已處理；必要且受影響的驗證有結果和準確版本，未驗項目有原因。尚需使用者決策或驗證受阻時保留阻塞狀態，不以部分通過宣稱完成。

### 4. 逐項回覆原 review threads

逐一核對一般留言、整體 reviews 及 inline threads；inline feedback 回原 thread，一般留言與整體 review 回原有對話，不另開重複頂層留言。逐項交代處理結果、最新程式碼位置／commit 與相關驗證。未修項目說明原因和待決事項；待 reviewer 確認的 thread 明列。feedback 若已過時，也引用目前程式碼證據說明，不默默略過。

**完成條件：** 每項既有意見都有原 thread 回覆或明確列為發布受阻；待 reviewer 確認事項仍清楚可見。

### 5. 發布收尾並同步 PR body

作者明確啟動本 skill，即授權入口 agent 發布本輪自審 report、原對話／thread 回覆、本輪收尾結果及 PR body 更新，不逐則詢問草稿；授權僅限這些本輪發布。入口 agent 是本輪唯一 publisher；參與修正的其他 agents 把修改、commit 和驗證交回，不另行發布。

發布收尾前再次查遠端 head。若有新差異，先讀取並依影響補做 review／驗證，再更新回覆和結果；任何結果都保留它實際對應的 commit。用 `pr` skill 更新 PR body 摘要及 `## 驗證`，列出實際指令／操作、結果、證據、未驗及原因、剩餘風險；讓 body 明確對應最新已核對的 head，本輪 comments 保留歷史。視覺證據按需附真實截圖；只有靜態圖不足以表達互動時才附短影片，憑證不得發布，附件不 commit。

body 更新後，另發布一則本輪唯一的收尾結果 comment。它是獨立的最終紀錄：自審 report、逐項 thread／review 回覆及 PR body 都不能代替它。用精簡文字列出本輪實際核對的 head、最終驗證結果、未驗項目及原因、仍待 reviewer 確認的 threads，並明確寫出「本輪完成，等待 review」或「收尾未完成」；沿用摘要與證據的寫法，不重複貼整份 PR body；有新增風險才補 Merge Danger。每次發布前重新核對遠端 head；若 head 改變，先檢查新增差異並補做受影響的 review／驗證，再同步 body 與收尾結果。

若有規則衝突、待決需求或其他已知阻塞，先完成不受影響的工作，再於詢問使用者前發布「收尾未完成」PR comment。comment 記錄已完成工作、阻塞來源及位置、影響、未完成／未驗範圍與下一步決定；發布前核對遠端 head，並在 head 漂移時先讀新增差異。若 PR body 的 `## 驗證` 會把舊 head 或未通過的驗證寫成目前完成狀態，先同步 body 至最新 head 並標明未驗與風險；不要把這則 blocked comment 說成成功 report，也不要等待使用者回答後才發布已知阻塞。

**完成條件：** 已取得可直接開啟的本輪收尾結果 comment URL，且其內文列明最新已核對 head、最終驗證結果、未驗原因、待 reviewer 確認 threads 與明確結束狀態；重新讀取 PR body，確認 `## 驗證` 對應同一 head。缺少 comment URL、comment 內容或 head 一致性任一證據時，不回報本輪完成；發布受阻時回報「收尾未完成」及原因。

## 結束狀態

只有下列條件全滿足才回報 **「本輪完成，等待 review」**，且該狀態也出現在本輪收尾結果 comment：自審 report 已發布；明確 bug 已處理、需求決策已有答案；必要驗證通過且版本對應準確；既有意見逐項回原 thread 回覆；剩餘 reviewer 確認、未驗和風險已列出；遠端 head 已核對；PR body 的 `## 驗證` 對應該 head；本輪收尾結果 comment 已發布並取得 URL，comment 與 body 的 head 一致。

任何必要項目未完成、head 變動尚未檢查、驗證受阻、權限不足或仍待需求決策時，回報 **「收尾未完成」**，列出已完成事項、阻塞及影響、未驗原因與下一步。PR 作者回合若可發布，先核對最新 head，必要時讀取新增差異並更新驗證範圍，再發布 blocked comment；只有發布權限不足時，才將相同阻塞資料留在 session 並說明原因。發布或記錄後再詢問所需決定，不宣稱完成。有新證據或可繼續工作就續做；相同失敗重現且沒有新線索，或需要改需求／擴大範圍時停止並詢問，不無限重試。

每輪新 review 都由使用者重新啟動。reviewer 負責確認及 resolve threads；merge 由人操作。本 skill 不代 reviewer resolve／approve，也不自動 merge。
