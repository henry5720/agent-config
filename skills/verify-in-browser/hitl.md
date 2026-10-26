# 有人在旁邊時

[SKILL.md](SKILL.md) 的流程照走，這份補只有互動 session 才有的分支：使用者能回答、能看畫面、能替你登入。

## 選工具

用手上能操作瀏覽器的工具（看自己的工具清單與 `command -v playwright-cli`），依序偏好：

- 能錄影的：`playwright-cli`（錄 `.webm`）、Claude in Chrome（`claude --chrome`，錄 GIF）。
  - 使用者要用他的 Chrome（含它的登入狀態）、或要看著操作時，用 Claude in Chrome；它開的是使用者的 Chrome，可能本來就登入了。
  - 有設定 `remote-chrome` skill 時，`playwright-cli` 也能接它開的 Chrome 並錄影：`open <url>` 換成 `attach --cdp=http://127.0.0.1:9222` 再 `goto <url>`；收尾用 `detach`，只斷開 session、Chrome 留著（playwright-cli skill `references/session-management.md`〈Detach〉）。接的是桌機 Chrome 時使用者看得到畫面。
- 只能截圖的：Codex app 內建瀏覽器。

都沒有就照 SKILL.md 回 `unverifiable`。L3 的 WebKit 一律用 `playwright-cli`。

工具拒寫 `<E>` 時（chrome-devtools MCP 的截圖只能寫進 workspace 內），先存進 repo 內未追蹤的位置，再 `mv` 進 `<E>`。

## 登入

工具的參數會原樣進對話（MCP、內建瀏覽器的輸入動作）時，請使用者在那個瀏覽器自己登入，登好再繼續。帳密因此只留在使用者手上。

## 發布

呼叫者不是 runner 或 `pr-review-and-verify` 時，驗完由你發布。L0 沒有瀏覽器驗收 comment。

1. 這個分支有 PR（`gh pr view --json number`）就問使用者一次：「要把這份回報發成 PR #<N> 的 comment 嗎？」
2. 同意：照 [report-template.md](report-template.md) 發。
3. 不同意或沒有 PR：回報列出 `<E>` 路徑，並說明暫存資料夾不會長久保留。

## 卡住時換工具

要查**為什麼**（慢、記憶體、minify 過的錯誤、斷點），有設定 `remote-chrome` skill 時用它開的 Chrome 接 chrome-devtools MCP；沒有就用手上工具看得到的 console／network，查不出原因列進「未驗」。

值得防回歸的流程，驗完提議寫成該 repo 的 Playwright e2e；要長期守住的視覺，提議 `toHaveScreenshot`。
