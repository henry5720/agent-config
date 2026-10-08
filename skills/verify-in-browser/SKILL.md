---
name: verify-in-browser
description: 當使用者要求瀏覽器驗收，或 agent 判斷需要透過瀏覽器確認畫面／行為時使用。
---

# 瀏覽器驗收

指令用法看 `playwright-cli` skill（或 `playwright-cli --help`）。這份只補它沒寫的：什麼時候驗、怎麼登入、留什麼證據、卡住換什麼。

## 決定是否驗

使用者要求瀏覽器驗收時，或改動需要透過實際畫面／操作才能確認時，才往下走；一般 UI 改動不會自動觸發本流程。若這次不需要瀏覽器，照實回報未做及原因。整套回歸交給 CI 和 e2e。

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
3. **依驗證目的選擇狀態和證據**：走能回答驗證問題的操作與狀態，不必把所有可能狀態都走過。需要視覺證據時，對有用的狀態執行 `screenshot --filename=<E>/<狀態>.png` 並查看圖片；確認結構時用 `snapshot --filename=<E>/<狀態>.yml` 再讀檔，或 `find "<文字>"` 只撈需要的節點。檢查 `console error`，記下錯誤數並分清楚是這次改出來的還是原本就有的（例：`favicon.ico` 404）。
4. **收尾：** `close`；`rm -rf <E>/.playwright-cli <E>/auth.json`。dev server 是你起的就關掉。

步驟 3 的完成條件：所選的驗證操作已完成，必要證據已查看並留在暫存路徑；沒走到但與驗證目的相關的部分，回報時列為「未驗」及原因。不要為了湊截圖而截取與驗證無關的狀態。

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

例：TeamSync 是 `/login` 的帳密表單（placeholder「帳號」「密碼」、按鈕「登 入」），登入成功的判斷是 `!!localStorage.getItem('token')`。參考 `teamsync-tutorials/shared/shoot-lib.mjs` 的 `login()`，帳密在該 repo 的 `.env`（`TS_OWNER_USER`／`TS_OWNER_PASSWORD`）。

## 0.1.22 踩過的雷

| 症狀 | 做法 |
|---|---|
| 整棵 accessibility tree 印進對話 | 裸 `snapshot` 會直接印（官方 skill 寫存檔，實際沒有）。一律 `--filename` 或 `find` |
| 密碼、token 出現在對話或檔案 | 見「登入」 |
| repo 多出 `.playwright-cli/` | 少了 `cd <E> &&` |

## 回報

寫進 PR body 的「## 驗證」段（沒開 PR 就寫在回報裡）：

| 項目 | 內容 |
|---|---|
| 驗證結果 | 說明驗了什麼、觀察到什麼；只在有截圖時列出檔名 |
| console | 錯誤數；新出現的錯誤原文 |
| 未驗 | 與驗證目的相關但沒走到的項目和原因（沒裝 `playwright-cli`、要特定資料、要另一個角色、要真的寄信…）。沒有就寫「無」 |

有截圖要附在 PR 上時，不 commit 進 repo：

```bash
gh pr comment <PR> --body "<驗證結果>" --attach '<E>/<狀態>.png'
```

- 需要比較版面、樣式差異時，可附改前／改後截圖；改前畫面在動手前先截，或從隔離的 base 環境取得。
- 截圖會上傳到 GitHub：只截測試資料，畫面上有真實客戶資料就不附圖，改用文字描述。
- 截圖格式、大小限制見 `playwright-cli` skill 的 PR attachments。

## 卡住時換工具

要查**為什麼**（慢、記憶體、minify 過的錯誤、斷點），或使用者要看著瀏覽器操作、要用他桌機 Chrome 的登入狀態，換 `chrome-mcp` skill。

值得防回歸的流程，驗完提議寫成該 repo 的 Playwright e2e。
