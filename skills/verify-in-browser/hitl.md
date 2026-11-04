# 有人在旁邊時

[SKILL.md](SKILL.md) 的流程照走，這份補只有互動 session 才有的分支：使用者能回答、能看畫面、能替你登入。

## 選工具

用手上能操作瀏覽器的工具（看自己的工具清單與 `command -v playwright-cli`），依序偏好：

- 能錄影的：`playwright-cli`（錄 `.webm`）、Claude in Chrome（`claude --chrome`，錄 GIF）。
  - 使用者要看著操作或替你登入：照下面〈讓使用者看畫面、接手〉，瀏覽器還是 `playwright-cli` 自己開的那個。
  - Claude in Chrome 只在你跟使用者的 Chrome 在同一台時能用；它開的是使用者的 Chrome，可能本來就登入了。
  - 一定要使用者自己的瀏覽器（passkey、硬體金鑰、裝置 SSO），你又不在他那台：見 a2 skill（建置中）。還沒有之前，這條列進「未驗」並寫原因。
- 只能截圖的：Codex app 內建瀏覽器。

都沒有就照 SKILL.md 回 `unverifiable`。L3 的 WebKit 一律用 `playwright-cli`。

工具拒寫 `<E>` 時（chrome-devtools MCP 的截圖只能寫進 workspace 內），先存進 repo 內未追蹤的位置，再 `mv` 進 `<E>`。

## 讓使用者看畫面、接手

`playwright-cli` 開的瀏覽器是 headless 的，使用者要看或接手時，你開 dashboard、他從自己的瀏覽器連進來。

1. 背景跑 `playwright-cli show --port 9377 --host=127.0.0.1`（阻塞的 http server；port 被佔就換一個）。`--host` 一定寫 `127.0.0.1`：dashboard 沒有驗證，不能聽 `0.0.0.0`；不寫時聽 `localhost`，有的機器解析成 `::1`，下一步的 `ssh -L` 就連不到。
2. 跟使用者說：在他的電腦開 `ssh -L 9377:127.0.0.1:9377 <你這台的 ssh host>`，瀏覽器開 `http://127.0.0.1:9377`。點 session `<S>` 放大，點進畫面就能用滑鼠、鍵盤操作，按 Escape 交還。
3. 用完 `playwright-cli show --kill`，再收掉背景的 `show`。

## 登入

工具的參數會原樣進對話（MCP、內建瀏覽器的輸入動作）時，請使用者在那個瀏覽器自己登入，登好再繼續。帳密因此只留在使用者手上。

用 `playwright-cli` 時：先 `open` 登入頁，照〈讓使用者看畫面、接手〉請使用者在 session `<S>` 的畫面上登入。他說登好之後，同一個 `-s=<S>` 接著做就帶著登入狀態；先 `state-save <E>/auth.json`，後面的 session 用 `state-load` 帶（[playwright-cli.md](playwright-cli.md)〈登入〉）。

## 發布

呼叫者不是 runner 或 `pr-review-and-verify` 時，驗完由你發布。L0 沒有瀏覽器驗收 comment。

1. 這個分支有 PR（`gh pr view --json number`）就問使用者一次：「要把這份回報發成 PR #<N> 的 comment 嗎？」
2. 同意：照 [report-template.md](report-template.md) 發。
3. 不同意或沒有 PR：回報列出 `<E>` 路徑，並說明暫存資料夾不會長久保留。

## 卡住時換工具

要查**為什麼**（慢、記憶體、minify 過的錯誤、斷點），照 `remote-chrome` skill 用 `remote-chrome-headless` 在這台開 9222，接 chrome-devtools MCP；沒有這支就用手上工具看得到的 console／network，查不出原因列進「未驗」。

值得防回歸的流程，驗完提議寫成該 repo 的 Playwright e2e；要長期守住的視覺，提議 `toHaveScreenshot`。
