---
name: verify-in-browser
description: 瀏覽器驗收：照驗收條件逐條判定，留截圖證據。使用者要求瀏覽器驗收、runner 驗收 run、PR 驗收時使用。
---

# 瀏覽器驗收

這份規定驗多少、怎麼登入、留什麼證據、怎麼回報。產出兩樣：證據檔留在證據資料夾 `<E>`，逐條判定 JSON 交給呼叫者。證據只留本機、不 commit；發布由呼叫者負責（runner 自己寫 PR body，`pr-review-and-verify` 自己發 comment）。

瀏覽器工具用 `playwright-cli`，指令寫法、登入指令、踩過的雷看 [playwright-cli.md](playwright-cli.md)。runner 驗收 run（AFK）只走本檔與 playwright-cli.md。**有人在旁邊（互動 session）時另讀 [hitl.md](hitl.md)**：改用使用者的 Chrome 或其他瀏覽器工具、請使用者代登入、把回報發到 PR、查原因換工具，都在那裡。

## 決定驗多少

先依改動分級。級別同時是下限和上限：不到下限算沒驗完；超過上限是雜訊，整套回歸交給 CI 和 e2e。

| 級別 | 改動 | 瀏覽器 | 證據 |
|---|---|---|---|
| L0 | 沒碰畫面（純邏輯、型別、文件、設定） | 不開 | 測試輸出；畫面條件填 `skipped`，原因寫「未開瀏覽器：L0」 |
| L1 | 單一畫面狀態（欄位、顏色、文案、版面） | Chromium 走一次 | 每個改到的狀態 1 張截圖 |
| L2 | 操作流程（mutation、toast、按鈕狀態、route） | Chromium 走每個改到的操作的成功路徑 | 一個斷言一份證據：看最後狀態就截 1 張；斷言是先後順序或過程時，1 支影片取代整串截圖 |
| L3 | L2，且命中[引擎差異清單] | Chromium + WebKit | 同 L2，每張截圖標引擎 |

一次改動跨多級時取最高級。使用者指定範圍時照使用者的。呼叫端已決定要驗（例如 runner 的驗收 run）時從 L1 起算。L0 仍交相同 JSON。

**[引擎差異清單]**：iframe 嵌入、third-party cookie、SSO／跨網域登入、clipboard、原生 `date`／`file` input、檔案下載、使用者明說要看 Safari。這些是 Safari（WebKit）和 Chrome 已知行為不同的地方；不在清單上的改動只跑 Chromium，回報寫「僅 Chromium」。

**改前對照**：依改動決定，合併後線上就變成改後，改前只留得住在 PR 上。

| 改動 | 改前 |
|---|---|
| 修 bug | 必拍，證明 bug 重現過；照步驟 3 |
| 改既有畫面 | PR body 用文字寫改前怎樣即可；順手拿得到就拍，拿不到不必寫原因 |
| 新功能 | 不拍 |

「修 bug」指 issue 有 `bug` label，或這次分支的 commit 是 `fix` 類型（`fix:`、`fix(<scope>):`）；判不出時照「改既有畫面」。使用者要求改前截圖時照「修 bug」辦。

**截圖看不到的狀態**（hover、窄螢幕）各算一個斷言，各自留證據；沒驗就列進「未驗」。

**斷斷續續的問題**（閃爍、race、效能、偶發錯誤）：單張截圖證明不了，要重複 N 次記發生次數，並附一列反向對照（改前本來就正常的情境），說清楚修法在哪裡有效、哪裡無關。

## 開始前

驗收前先讀 [逐條判定契約](result-contract.md) 和 [schema](result.schema.json)。issue 有 `## Acceptance criteria` 就逐條保留原文（`criteriaSource: issue`）；沒有，或使用者只說「去看這頁」時，先把目的寫成 1～3 條可判定條件（`inferred`），再操作。

1. **確認工具。** `command -v playwright-cli` 找得到就用它；找不到就回 `unverifiable`，原因寫瀏覽器工具不在，並提示可裝 `npm i -g @playwright/cli`。L3 的 WebKit 開不了就把 WebKit 列進「未驗」，Chromium 照做。
2. **定證據資料夾 `E`，整趟照抄成字面值：** 呼叫端指定的絕對路徑優先；沒指定時，有 `$CLAUDE_JOB_DIR` 用 `$CLAUDE_JOB_DIR/tmp/verify-<名字>`，沒有用 `/tmp/verify-<名字>`；`<名字>` = `<repo 名>-<分支名>`，`/` 換成 `-`（例：`agent-config-feat-login`）。先 `mkdir -p <E> && chmod 700 <E>`：裡面會有登入狀態和工具暫存檔，只給自己讀。證據檔都落在 `<E>`；工具存到別處（例如下載資料夾）就搬進來。
3. **定環境，整趟固定：** viewport 預設 1440×900（工具調不了就記實際尺寸），語系、主題、角色帳號、後端（local／staging）。切主題走 app 自己的切換（設定頁，或它讀的儲存值後重新載入）：只改 `<html>` 的 class 只翻 CSS 變數，JS 端的主題（例如 antd `ConfigProvider`）不會跟著切，截到的是假畫面。改前改後必須相同；改前取自線上部署時例外，見步驟 3。
   - **後端版本對得上才開瀏覽器。** PR 寫了依賴的後端 commit 時，確認後端 HEAD 包含它：`git -C <後端 repo> merge-base --is-ancestor <PR 寫的 commit> <後端 HEAD>`。PR 沒寫才退回查 openapi 有沒有這次的新欄位，回報註明「用欄位推斷」。對不上就停下回報。

## 步驟

1. **起 dev server，開頁面，調成固定 viewport。** repo 有 playwright-cli 設定檔或要設語系時，照 [playwright-cli.md](playwright-cli.md)「步驟對應的指令」。
2. **登入**（頁面要登入才看得到時），見下一節。每在 staging 建立一筆資料，立即 append 一筆到 `<E>/state.json` 的 JSON array：`{ "name": "資料名稱", "account": "帳號變數前綴", "created": "METHOD path", "undo": null }`。知道刪除方式就把 `undo` 填成 `METHOD path`，用不到或未知時填 JSON `null`；request 只記 method 與 path，不記 token、密碼、request body 或帶憑證的 query。記錄先落盤才繼續，crash 後仍可由人用 `test-api` 倒序清理。
3. **改前對照（修 bug 或使用者要求時）。** 照順序取，拿到就停。截圖都存 `<E>/before-<狀態>.png`，另開一個瀏覽器 session，viewport、操作與改後相同。
   - **base 的線上部署**：該 repo 的 `AGENTS.md`／docs 寫了網址與查部署 commit 的方法，且下面三條都成立才用：部署 commit 與 merge-base 在這次改到的路徑上沒有差異（`git diff --name-only <merge-base> <部署 commit> -- <改到的路徑>` 輸出為空）；這張 PR 依賴的後端改動還沒部署；部署端開得到改到的頁面（模組開關、feature flag）。共用環境只截唯讀畫面。回報的環境表為改前另寫一列：網址、部署 commit、資料來源。
   - **本機 base**：`git worktree add <tmp>/before <merge-base>`，另一個 port 起 dev server。後端用 base 時期的版本：這張 PR 沒改後端契約就用改後那台；改了就用不含那些改動的舊版後端，回報註明資料來源。
   - 都拿不到：回報寫「只有改後：<原因>」。
4. **依級別操作並留證據。** 截圖存 `<E>/after-<狀態>.png`（L3 加引擎：`after-webkit-<狀態>.png`），截完查看圖片。斷言是先後順序或過程（暫存 → 儲存 → 重開一致、處理中無法關閉、按上一頁回到哪頁）時，登入完才開始錄 60 秒內的影片 `<E>/<流程>.webm`（GIF 也算影片）取代那串截圖。工具錄不了影就改連續截圖 `<E>/<流程>-01.png`、`-02.png`…，回報註明「無錄影：<工具>」。確認結構用 snapshot 或找文字。檢查 console error，分清這次改出來的和原本就有的。每張截圖記下資料來源：真實 API，或 mock／攔截。
5. **收尾：** 關掉你開的每個瀏覽器 session；`git worktree remove <tmp>/before`；刪掉 `<E>` 裡所有 `auth*.json` 與 `.playwright-cli/`（多角色檔也要清）；保留證據、結果 JSON 與 `state.json`。dev server 是你起的就關掉。

步驟 4 的完成條件：

- 達到該級別的下限，證據已查看並留在 `<E>`。
- 每個證據檔都對應一條條件，檔名寫進結果 JSON：寫在該條 criterion 的 `evidence`；`unverifiable` 時沒有 `evidence` 可放，寫進 `unverifiableReason`。
- 需要改前對照卻沒有時，回報寫了原因；與驗證目的相關但沒走到的，列進「未驗」。

## 登入

條件牽涉角色時，先照 repo 文件找「角色 → 帳號變數前綴」；找不到對照或缺少值，該條填 `skipped`，`reason` 寫缺少的變數名（不寫值）；每條只用它指定的角色判定。每個角色各開 session，登入狀態各存 `<E>/auth-<前綴>.json`。已找到帳號但登入流程失敗是 `unverifiable`，整份 `criteria` 留空。

照優先順序：

1. **帶既有的登入狀態，不碰表單。** 用上次存下的登入狀態；repo 有拿 token 的方法（API、script）就寫進 localStorage 再重新載入。
2. **填表單。** 照該 repo 既有的登入方式（先找 e2e 的登入 helper 或截圖腳本）。

填表單時帳密只出現在 shell 展開裡，對話和檔案都看不到：

- 帳密照 dotenv 的順序取：環境變數有值就用它，沒有才讀帳密檔（該 repo e2e 讀的那個 `.env`）。值只出現在指令的 `${…}`／`$(…)` 展開裡，不 `source`、不 `cat` 帳密檔。
- 不知道變數名時只列名字：`env | grep -o '^[A-Za-z_][A-Za-z0-9_]*='`、`grep -o '^[A-Za-z_][A-Za-z0-9_]*=' <帳密檔絕對路徑>`。
- 要先 snapshot 找欄位，只能在填密碼**之前**。密碼最後填，填完下一個動作就是送出。
- 確認登入只回 true／false，不印 token。失敗（還停在登入頁）就先重開登入頁清掉欄位，再查原因。成功就存下登入狀態，之後用第 1 種方式。
- 指令照 [playwright-cli.md](playwright-cli.md)「登入」。

## 驗收條件與回報

唯一的驗收結果是符合 schema 與[契約](result-contract.md)的 JSON，存成 `<E>/result.json`；runner 透過結構化結果取得同一份內容。原因、操作、改前對照、環境限制與資料來源都寫進對應的 `observed`／`reason`，這份 JSON 就是完整回報。

呼叫者不是 runner 時，再用 `uv run <skill 絕對路徑>/scripts/render-report.py <E>/result.json` 印 Markdown 給人看（已有 `jsonschema` 的 Python 也可直接 `python3` 執行）。render 先驗 schema 與跨欄位語意，格式錯先修 JSON。L0 的 PR body `## 驗證` 寫「未開瀏覽器：<原因>」。
