---
name: verify-in-browser
description: 改完 UI 或前端行為、回報完成之前，用 playwright-cli 開 headless 瀏覽器自己驗收並留證據。使用者叫你「驗收」時也用。
---

# 改完前端，自己驗收再回報

指令用法看 `playwright-cli` skill（或 `playwright-cli --help`）。這份只補它沒寫的：什麼時候驗、怎麼登入、留什麼證據、卡住換什麼。

## 步驟

1. **開證據資料夾，之後每個指令都在這裡跑。** `playwright-cli` 會在當下目錄寫 `.playwright-cli/`（每步的 snapshot、console log）；在 repo 根目錄跑會多出一堆未追蹤檔。有 `$CLAUDE_JOB_DIR` 就用 `$CLAUDE_JOB_DIR/tmp/verify`，沒有就用 `/tmp/verify-<分支名>`。
2. **起 dev server，`playwright-cli open <url>`。**
3. **登入**（頁面要登入才看得到時）：照該 repo 既有的登入方式走：先找 e2e 的登入 helper 或截圖腳本，照它的步驟填表單。
   - 帳密從 `.env` 讀進環境變數，在同一個指令裡用：`set -a; . <repo 絕對路徑>/.env; set +a; playwright-cli --raw fill <密碼欄> "$X_PASSWORD"`（現在在證據資料夾裡，`./.env` 讀不到）。**一定要加 `--raw`**：不加的話 `fill` 會把產生的 Playwright code 連同明文密碼印回對話。
   - 登入一次就 `state-save auth.json`，之後 `state-load auth.json`，不用每次重填。`auth.json` 是登入憑證，放證據資料夾，不進 repo。
   - 例：TeamSync 是 `/login` 的帳密表單（placeholder「帳號」「密碼」、按鈕「登 入」），登入成功的判斷是 `localStorage` 有 `token`。參考 `teamsync-tutorials/shared/shoot-lib.mjs` 的 `login()`，帳密在該 repo 的 `.env`（`TS_OWNER_USER`／`TS_OWNER_PASSWORD`）。
4. **把這次改到的每個狀態走一遍**：初始、操作後、錯誤／空資料。每走到一個狀態：
   - `screenshot --filename=<狀態>.png`，然後自己看那張圖。
   - 看結構一律 `snapshot --filename=<狀態>.yml` 再讀檔，或用 `find "<文字>"` 只撈要的節點。0.1.22 的裸 `snapshot` 會把整棵樹印進對話。
   - `console error`：記下錯誤數，分清楚是這次改出來的還是原本就有的（例：`favicon.ico` 404）。
5. **`playwright-cli close`**。dev server 是你起的就關掉。

步驟 4 的完成條件：改動影響到的每個狀態都有一張截圖，或明列在「未驗」裡。

## 回報

回報完成時附上：

| 項目 | 內容 |
|---|---|
| 走過的狀態 | 每個狀態一行：做了什麼 → 看到什麼 → 截圖路徑 |
| console | 錯誤數；新出現的錯誤原文 |
| 未驗 | 沒走到的狀態和原因（要特定資料、要另一個角色、要真的寄信…）。沒有就寫「無」 |

PR 要附圖時用 `gh pr comment --attach`（見 `playwright-cli` skill 的 PR attachments）。

## 卡住時換工具

`playwright-cli` 是拿來「操作、看結果」的。要查**為什麼**就換 chrome-devtools MCP（`chrome-mcp` skill）：

- 慢：要 performance trace、lighthouse
- 要看 minify 過的 code 在哪一行出錯、斷點
- 記憶體洩漏：heap snapshot
- 使用者要看著瀏覽器操作，或要用他桌機 Chrome 的登入狀態

值得防回歸的流程，驗完提議寫成該 repo 的 Playwright e2e。
