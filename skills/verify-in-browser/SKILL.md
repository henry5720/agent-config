---
name: verify-in-browser
description: 當使用者要求瀏覽器驗收，或 agent 判斷需要透過瀏覽器確認畫面／行為時使用。
---

# 瀏覽器驗收

指令用法看 `playwright-cli` skill（或 `playwright-cli --help`）。這份只補它沒寫的：什麼時候驗、怎麼登入、留什麼證據、卡住換什麼。

本 skill 只做驗收：證據存在本機暫存資料夾，回報給呼叫者。不 commit 證據，也不自己發布到 PR／issue；要附到 PR 時，由 `pr-review-and-verify` 發布，或由使用者自己上傳。

## 決定是否驗

使用者要求瀏覽器驗收時，或驗證目的需要透過實際畫面／操作才能判定時，執行本流程。若畫面或操作不影響本次驗證，照實回報未做及原因；單元測試不代替必要的畫面驗收。整套回歸交給 CI 和 e2e。

使用者要用他的 Chrome、或要看著操作時，改走 `chrome-mcp` skill。

## 開始前

1. **確認有裝。** `command -v playwright-cli`。沒有（WSL、ARM 不裝）就改走 `chrome-mcp` skill；那也不能用，就把整個驗收列進「未驗」。不要自己 `npm i -g`。
2. **定兩個名字，整趟照抄成字面值：**
   - session `S` = `<repo 名>-<分支名>`，`/` 換成 `-`（例：`agent-config-feat-login`）。
   - 證據資料夾 `E` = 絕對路徑。有 `$CLAUDE_JOB_DIR` 用 `$CLAUDE_JOB_DIR/tmp/verify-<S>`，沒有用 `/tmp/verify-<S>`。先 `mkdir -p <E>`。

## 每個指令的寫法

```bash
cd <E> && playwright-cli -s=<S> <指令>
```

- **每次都要 `cd <E> &&`。** cwd 不會留到下一個指令（Claude Code 每次 Bash 會重設，Codex 每個 exec 獨立），而 `playwright-cli` 會在當下目錄寫 `.playwright-cli/`（每步的 snapshot、console log）。少了 `cd`，這些檔會落在 repo 裡。
- **每次都要 `-s=<S>`。** 不帶就用 `default` session，平行的 agent 會搶同一個瀏覽器。
- `--filename`、`state-save`、`state-load` 給絕對路徑 `<E>/…`。`auth.json` 是登入憑證，絕不能落在 repo。

## 步驟

1. **起 dev server，`open <url>`。**
2. **登入**（頁面要登入才看得到時），見下一節。
3. **依驗證目的選擇操作、狀態和證據**：走能回答驗證問題的畫面與操作，不必把所有可能狀態都走過。對有用的視覺狀態留下截圖 `screenshot --filename=<E>/<狀態>.png`，不先判斷環境、不逐張詢問；截圖後查看圖片。要證明的是跨狀態的**先後**（暫存 → 儲存 → 重開一致、刪除 → 取消 → 還原、關閉前先確認）時，用 `video-start <E>/<流程>.webm`／`video-stop` 錄一支 60 秒內的短影片，登入完成後才開始錄；只證明單一狀態（欄位有沒有、顏色、篩選後剩幾筆）時截圖就夠。確認結構時用 `snapshot --filename=<E>/<狀態>.yml` 再讀檔，或 `find "<文字>"` 只撈需要的節點。檢查 `console error`，記下錯誤數並分清楚是這次改出來的還是原本就有的（例：`favicon.ico` 404）。
4. **收尾：** `close`；`rm -rf <E>/.playwright-cli <E>/auth.json`。dev server 是你起的就關掉。

步驟 3 的完成條件：所選的驗證操作已完成，必要證據已查看並留在暫存路徑；沒走到但與驗證目的相關的主題、操作或狀態，回報時列為「未驗」及原因。不要為了湊截圖而截取與驗證無關的狀態。

## 登入

照優先順序：

1. **帶既有的登入狀態，不碰表單。** `<E>/auth.json` 已經有就 `state-load <E>/auth.json`。repo 有拿 token 的方法（API、script）就 `--raw localstorage-set <key> "<token>"` 再 `goto`。
2. **填表單。** 照該 repo 既有的登入方式（先找 e2e 的登入 helper 或截圖腳本）。

填表單的規矩，因為密碼一進欄位就會到處出現（0.1.22 實測：`find`、填完後任何動作自動存的 `.playwright-cli/page-*.yml`，都含明文）：

- 欄位用 selector 指（`'input[type=password]'`、`'getByPlaceholder("密碼")'`），不必先 snapshot。要先 snapshot 找 ref，只能在填密碼**之前**。
- 帳密只從 `.env` 讀需要的那個 key，直接塞進指令，不 `source`、不 `cat .env`（不知道變數名就 `grep -o '^[A-Z_]*=' <repo 絕對路徑>/.env`）：

  ```bash
  cd <E> && playwright-cli -s=<S> --raw fill 'input[type=password]' "$(grep -m1 '^X_PASSWORD=' <repo 絕對路徑>/.env | cut -d= -f2- | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")"
  ```

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

回報給呼叫者（使用者，或呼叫本 skill 的 `pr-review-and-verify`）：

| 項目 | 內容 |
|---|---|
| 實測版本 | 驗證時的 commit SHA |
| 驗證結果 | 說明驗了什麼、觀察到什麼 |
| console | 錯誤數；新出現的錯誤原文 |
| 證據 | 每個截圖／影片的絕對路徑 `<E>/…` 與它證明的狀態；畫面上拍到密碼、token、API key、登入憑證時標明哪個檔 |
| 未驗 | 與驗證目的相關但沒走到的項目和原因（沒裝 `playwright-cli`、要特定資料、要另一個角色、要真的寄信…）。沒有就寫「無」 |

- 截圖、錄影是實測證據，不用手繪圖或示意圖替代。
- 有用前後比較時，改前／改後使用相同資料、視窗大小與操作；改前畫面在動手前取得，或從隔離的 base 環境取得。拿不到改前就明說只有改後，不要求每次都做比較。
- 證據留在 `<E>`，收尾只清 `.playwright-cli/` 與 `auth.json`；snapshot、trace 這類非證據檔不列進回報。

## 卡住時換工具

要查**為什麼**（慢、記憶體、minify 過的錯誤、斷點），或使用者要看著瀏覽器操作、要用他桌機 Chrome 的登入狀態，換 `chrome-mcp` skill。

值得防回歸的流程，驗完提議寫成該 repo 的 Playwright e2e。
