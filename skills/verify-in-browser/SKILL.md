---
name: verify-in-browser
description: 當使用者要求瀏覽器驗收，或 agent 判斷需要透過瀏覽器確認畫面／行為時使用。
---

# 瀏覽器驗收

指令用法看 `playwright-cli` skill（或 `playwright-cli --help`）。這份只補它沒寫的：驗多少、怎麼登入、留什麼證據、怎麼回報、卡住換什麼。

本 skill 只做驗收：證據存在本機暫存資料夾，回報給呼叫者。不 commit 證據，不經使用者同意不發布到 PR／issue；呼叫者是 `pr-review-and-verify` 時由它發布，其他情況見步驟 6。

## 決定驗多少

先依改動分級。級別同時是下限和上限：不到下限算沒驗完，超過上限是在製造雜訊。

| 級別 | 改動 | 瀏覽器 | 證據 |
|---|---|---|---|
| L0 | 沒碰畫面（純邏輯、型別、文件、設定） | 不開 | 測試輸出；回報環境寫「未開瀏覽器」 |
| L1 | 單一畫面狀態（欄位、顏色、文案、版面） | Chromium 走一次 | 每個改到的狀態 1 張截圖 |
| L2 | 操作流程（mutation、toast、按鈕狀態、route） | Chromium 走每個改到的操作的成功路徑 | 一個斷言一份證據：看最後狀態就截 1 張；斷言是先後順序或過程時，1 支影片取代整串截圖 |
| L3 | L2，且命中[引擎差異清單] | Chromium + WebKit | 同 L2，每張截圖標引擎 |

一次改動跨多級時取最高級。使用者指定範圍時照使用者的。

**[引擎差異清單]**：iframe 嵌入、third-party cookie、SSO／跨網域登入、clipboard、原生 `date`／`file` input、檔案下載、使用者明說要看 Safari。這些是 Safari（WebKit）和 Chrome 已知行為不同的地方；不在清單上的改動只跑 Chromium，回報寫「僅 Chromium」。

**改前對照**：依改動決定，合併後線上就變成改後，改前只留得住在 PR 上。

| 改動 | 改前 |
|---|---|
| 修 bug | 必拍，證明 bug 重現過；照步驟 3 |
| 改既有畫面 | PR body 用文字寫改前怎樣即可；順手拿得到就拍，拿不到不必寫原因 |
| 新功能 | 不拍 |

使用者要求改前截圖時照「修 bug」辦。

**截圖看不到的狀態**（hover、窄螢幕）各算一個斷言，各自留證據；沒驗就列進「未驗」。

**斷斷續續的問題**（閃爍、race、效能、偶發錯誤）：單張截圖證明不了，要重複 N 次記發生次數，並附一列反向對照（改前本來就正常的情境），說清楚修法在哪裡有效、哪裡無關。

使用者要用他的 Chrome、或要看著操作時，改走 `chrome-mcp` skill。整套回歸交給 CI 和 e2e。

## 開始前

1. **確認有裝。** `command -v playwright-cli`。沒有（WSL、ARM 不裝）就改走 `chrome-mcp` skill；那也不能用，就把整個驗收列進「未驗」。不要自己 `npm i -g`。L3 另確認 WebKit：`ls ~/.cache/ms-playwright | grep -q webkit`，沒有就 `playwright-cli install-browser webkit`；裝不起來把 WebKit 列進「未驗」，Chromium 照做。
2. **定名字，整趟照抄成字面值：**
   - session `S` = `<repo 名>-<分支名>`，`/` 換成 `-`（例：`agent-config-feat-login`）。L3 的 WebKit 用 `S-webkit`；改前對照用 `S-before`。
   - 證據資料夾 `E` = 絕對路徑。有 `$CLAUDE_JOB_DIR` 用 `$CLAUDE_JOB_DIR/tmp/verify-<S>`，沒有用 `/tmp/verify-<S>`。先 `mkdir -p <E> && chmod 700 <E>`：裡面會有 `auth.json` 和含明文密碼的 `.playwright-cli/`，只給自己讀。
3. **定環境，整趟固定：** viewport 預設 `1440 900`（`resize 1440 900`），語系、主題、角色帳號、後端（local／staging）。改前改後必須相同；改前取自線上部署時例外，見步驟 3。
   - **後端版本對得上才開瀏覽器。** PR 寫了依賴的後端 commit 時，確認後端 HEAD 包含它：`git -C <後端 repo> merge-base --is-ancestor <PR 寫的 commit> <後端 HEAD>`。PR 沒寫才退回查 openapi 有沒有這次的新欄位，回報註明「用欄位推斷」。對不上就停下回報。

## 每個指令的寫法

```bash
cd <E> && playwright-cli -s=<S> <指令>
```

- **每次都要 `cd <E> &&`。** cwd 不會留到下一個指令，而 `playwright-cli` 會在當下目錄寫 `.playwright-cli/`。少了 `cd`，這些檔會落在 repo 裡。
- **每次都要 `-s=<S>`。** 不帶就用 `default` session，平行的 agent 會搶同一個瀏覽器。
- `--filename`、`state-save`、`state-load` 給絕對路徑 `<E>/…`。`auth.json` 是登入憑證，絕不能落在 repo。
- WebKit：`open --browser=webkit <url>`，搭配 `-s=<S>-webkit`。

## 步驟

1. **起 dev server，`open <url>`，`resize` 成固定 viewport。**
2. **登入**（頁面要登入才看得到時），見下一節。
3. **改前對照（修 bug 或使用者要求時）。** 照順序取，拿到就停。截圖都存 `<E>/before-<狀態>.png`，用 session `S-before`，viewport、操作與改後相同。
   - **base 的線上部署**：該 repo 的 `AGENTS.md`／docs 寫了網址與查部署 commit 的方法，且下面三條都成立才用：部署 commit 與 merge-base 在這次改到的路徑上沒有差異（`git diff --name-only <merge-base> <部署 commit> -- <改到的路徑>` 輸出為空）；這張 PR 依賴的後端改動還沒部署；部署端開得到改到的頁面（模組開關、feature flag）。只截唯讀畫面，不在共用環境寫入。回報的環境表為改前另寫一列：網址、部署 commit、資料來源。
   - **本機 base**：`git worktree add <tmp>/before <merge-base>`，另一個 port 起 dev server。後端用 base 時期的版本：這張 PR 沒改後端契約就用改後那台；改了就用不含那些改動的舊版後端，回報註明資料來源。
   - 都拿不到：回報寫「只有改後：<原因>」。
4. **依級別操作並留證據。** 截圖 `screenshot --filename=<E>/after-<狀態>.png`（L3 加引擎：`after-webkit-<狀態>.png`），截完查看圖片。斷言是先後順序或過程（暫存 → 儲存 → 重開一致、處理中無法關閉、按上一頁回到哪頁）時，錄 60 秒內的影片 `video-start <E>/<流程>.webm`／`video-stop` 取代那串截圖，登入完才開始錄。確認結構用 `snapshot --filename=<E>/<狀態>.yml` 或 `find "<文字>"`。檢查 `console error`，分清這次改出來的和原本就有的。每張截圖記下資料來源：真實 API，或 mock／`route` 攔截。
5. **收尾：** `close`（每個 session）；`git worktree remove <tmp>/before`；`rm -rf <E>/.playwright-cli <E>/auth.json`。dev server 是你起的就關掉。
6. **發布（呼叫者不是 `pr-review-and-verify` 時）。** 這個分支有 PR（`gh pr view --json number`）就問使用者一次：「要把這份回報發成 PR #<N> 的 comment 嗎？」
   - 同意：影片先照 `compress-video` 壓成 mp4，再照 `pr-review-and-verify` 的「附件」規則發（`--attach`、遮蔽憑證）。在整合分支上驗某張子票時，標題寫票號。
   - 不同意或沒有 PR：回報列出 `<E>` 路徑，並說明暫存資料夾不會長久保留。

步驟 4 的完成條件：達到該級別的下限，證據已查看並留在 `<E>`；需要改前對照卻沒有時，回報寫了原因；與驗證目的相關但沒走到的，列進「未驗」。不為湊截圖去截無關的狀態。

## 登入

照優先順序：

1. **帶既有的登入狀態，不碰表單。** `<E>/auth.json` 已經有就 `state-load <E>/auth.json`。repo 有拿 token 的方法（API、script）就 `--raw localstorage-set <key> "<token>"` 再 `goto`。
2. **填表單。** 照該 repo 既有的登入方式（先找 e2e 的登入 helper 或截圖腳本）。

填表單的規矩，因為密碼一進欄位就會到處出現（0.1.22 實測：`find`、填完後任何動作自動存的 `.playwright-cli/page-*.yml`，都含明文）：

- 欄位用 selector 指（`'input[type=password]'`、`'getByPlaceholder("密碼")'`），不必先 snapshot。要先 snapshot 找 ref，只能在填密碼**之前**。
- 帳密照 dotenv 的順序取：環境變數有值就用它，沒有才讀帳密檔（該 repo e2e 讀的那個 `.env`）。值只出現在指令的 `${…}`／`$(…)` 展開裡，不 `source`、不 `cat` 帳密檔：

  ```bash
  cd <E> && playwright-cli -s=<S> --raw fill 'input[type=password]' "${X_PASSWORD:-$(grep -m1 '^X_PASSWORD=' <帳密檔絕對路徑> | cut -d= -f2- | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")}"
  ```

- 不知道變數名時只列名字：`env | grep -o '^[A-Za-z_][A-Za-z0-9_]*='`、`grep -o '^[A-Za-z_][A-Za-z0-9_]*=' <帳密檔絕對路徑>`。

- 每個 `fill`、`localstorage-set` 都加 `--raw`：不加會把產生的 Playwright code 連同值印回對話。
- 密碼最後填，填完下一個指令就是 `--raw click <送出按鈕>`，中間不 `snapshot`、不 `find`、不讀 `.playwright-cli/`。
- 送出後馬上 `rm -rf <E>/.playwright-cli`，再確認登入：`--raw eval "<判斷式>"` 只回 true／false，不要印 token。
- 失敗（還停在登入頁）就先 `goto` 登入頁清掉欄位，再查原因。
- 成功就 `state-save <E>/auth.json`，之後用第 1 種方式。

## 0.1.22 踩過的雷

| 症狀 | 做法 |
|---|---|
| 整棵 accessibility tree 印進對話 | 裸 `snapshot` 會直接印（官方 skill 寫存檔，實際沒有）。一律 `--filename` 或 `find` |
| 密碼、token 出現在對話或檔案 | 見「登入」 |
| repo 多出 `.playwright-cli/` | 少了 `cd <E> &&` |

## 回報

L1–L3：**回報前讀 [report-template.md](report-template.md)**，照它的格式寫，同時回報每個證據檔的絕對路徑 `<E>/…`。不確定某個級別該寫多細時，看 [examples.md](examples.md) 裡同級別的那則。

L0：不發 comment，PR body 的 `## 驗證` 寫一行「未開瀏覽器：<原因>」。

## 卡住時換工具

要查**為什麼**（慢、記憶體、minify 過的錯誤、斷點），或要用使用者桌機 Chrome 的登入狀態，換 `chrome-mcp` skill。

值得防回歸的流程，驗完提議寫成該 repo 的 Playwright e2e；要長期守住的視覺，提議 `toHaveScreenshot`。
