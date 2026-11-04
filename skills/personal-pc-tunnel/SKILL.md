---
name: personal-pc-tunnel
description: 要使用者在個人電腦開一條 ssh 轉發才做得到的瀏覽器工作：接上使用者日常的 Chrome（passkey、硬體金鑰、裝置 SSO）。一定要使用者自己的瀏覽器、你又不在他那台時使用。
---

# personal-pc-tunnel

你在已配置主機（例如 company-ec2）上，瀏覽器預設用這台自己的 headless 瀏覽器（`playwright-cli open`，流程照 `verify-in-browser` skill）。這個 skill 只處理那條走不通、要借使用者個人電腦的情況，共同點是使用者要開一條 ssh 轉發，而且只綁 127.0.0.1：轉過來的東西都沒有驗證。

## 接使用者日常的 Chrome

只在**一定要使用者自己的瀏覽器**時用：passkey、硬體金鑰、裝置 SSO，也就是 headless 瀏覽器怎樣都登不進去的網站。使用者要看畫面、要替你登入，走 headless 瀏覽器 + `playwright-cli show`（`verify-in-browser` 的 hitl.md〈讓使用者看畫面、接手〉），不用打擾他的 Chrome。

接上之後你只看得到使用者貼網址的那一個分頁，`goto` 會直接換掉那個分頁的內容，所以一定請他貼在**新分頁**。

1. **確認有工具**：`command -v personal-chrome-attach`（`~/.claude/skills/personal-pc-tunnel/scripts/personal-chrome-attach` 是同一支）。它要 `playwright-cli` ≥ 0.1.23（dotfiles 選裝工具 `playwright-cli` 裝的）。沒有就停下來回報。
2. **請使用者做準備**（一次講完，等他說好）：
   - 第一次用：日常 Chrome 裝 [Playwright Extension](https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm)。
   - 在個人電腦開 ssh 轉發，開著別關：`ssh -N company-ec2-attach`（dotfiles 的 ssh config 有這個別名；沒有就用 `ssh -N -L 127.0.0.1:9555:127.0.0.1:9555 <你這台的 ssh host>`）。這條說 port 被佔而失敗，就是他另一台還開著。
3. **跑腳本**：背景跑 `personal-chrome-attach -s=<S>`（Claude Code 的 Bash `run_in_background`），它會停在前景直到 session 結束。等使用者的時間預設 300 秒，`--timeout=<秒>` 可改。
   - 印出 `chrome-extension://…connect.html?…` 網址 → 原樣交給使用者，請他貼進日常 Chrome 的新分頁網址列。有印「沒設 PLAYWRIGHT_MCP_EXTENSION_TOKEN」時，提醒他貼完還要在 extension 畫面選這個分頁、按允許。
   - 說 9555 已經有人在聽 → 照它印出的 process 回報使用者，請他決定；不要自己殺。
   - 逾時或 attach 失敗 → 它已經收乾淨、exit 1。問使用者卡在哪一步，再重跑（網址每次不同）。
   完成條件：輸出出現「已接上,session:<S>」。
4. **操作**：跟 headless 瀏覽器一樣用 `playwright-cli -s=<S> <指令>`。先 `tab-list`，應該只有一個分頁。
5. **收尾**：`playwright-cli -s=<S> detach`（dotfiles #248 實測過：Chrome 和分頁留著）。
   完成條件：背景的 `personal-chrome-attach` 印出「session <S> 結束了」並 exit 0。最後請使用者關掉那條 ssh。

使用者想每次只貼網址、不用選分頁：請他把 extension 狀態頁上的 token 設成**你這邊**的環境變數 `PLAYWRIGHT_MCP_EXTENSION_TOKEN`（他自己設在你跑的 shell 看得到的地方）。token 不進任何 repo，也不要叫他貼進對話。
