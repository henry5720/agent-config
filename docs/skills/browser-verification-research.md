# Browser 驗收政策研究記錄

研究記錄日期：2026-10-08。保留研究時使用的來源連結與證據界線；不是 agent 必讀指引。本文不代表所有連結已於記錄日重新查證。

## 研究結論

- Matt Pocock 的 X 原文說的是「Playwright MCP + Ralph」，不是 Chrome DevTools MCP，也沒有要求每次 UI 修改都開瀏覽器。可見的幾則留言分享了其他人的工具選擇，不能代表整串留言或普遍共識。
- 官方工具文件能說明各工具的定位與功能，不能證明某一工具對所有任務最好。本次未找到公平、同任務的 Playwright CLI、Playwright MCP、Chrome DevTools MCP token 數值比較；不要把單一案例的比例當通用結論。
- 官方 agent 指引與研究支持指令保持精簡、明確，但沒有直接實驗比較瀏覽器分類表、一句原則或不寫規則的效果。長時程 app 開發案例支持明確做端到端驗證，不足以推論每個小 UI 改動都必須驗收。

## 來源與限制

**核心來源**

- [Matt Pocock 的 X 原文](https://x.com/mattpocockuk/status/2010298867947073968)：原文提到 Playwright MCP + Ralph；只讀到部分公開留言，不是完整留言存檔。
- [Mattias 的可見留言](https://x.com/mattiasgeniar/status/2010305243511394392)：分享自己改用 Chrome MCP 的經驗，不代表群體共識。
- [Sam 的可見留言](https://x.com/8am1am/status/2010299051636601341)：個人推薦 Playwriter，提及速度與輕量感受，不是比較測試。
- [Damien 的可見留言](https://x.com/dctanner/status/2010369747334857053)：個人試用多種工具後的選擇，不是代表性抽樣。
- [AI Hero：11 Tips For AI Coding With Ralph Wiggum](https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum)：Feedback Loops 提到 Playwright MCP；文章是實務建議，不是普遍政策或對照實驗。
- [Microsoft Playwright CLI README](https://github.com/microsoft/playwright-cli/blob/main/README.md)：說明 CLI 的定位與功能；其 token 效率描述是產品方主張，不是獨立 benchmark。
- [Microsoft Playwright MCP README](https://github.com/microsoft/playwright-mcp/blob/main/README.md)：用來對照 MCP 介面與 CLI；兩者不能混稱。
- [Chrome DevTools MCP README](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/README.md)：說明 live Chrome、console、network、performance 等能力，不是與其他工具的同條件比較。
- [Anthropic：Claude Code memory](https://code.claude.com/docs/en/memory)：建議 instructions 具體、精簡，程序性內容按需載入；不是 browser policy 實驗。
- [OpenAI Codex customization 原網址](https://developers.openai.com/codex/concepts/customization)（已 redirect 至[目前頁面](https://learn.chatgpt.com/docs/customization/overview)）：提供 customization 指引；不能據此推導 browser 驗收分類政策。

**延伸閱讀與證據界線**

- [Anthropic：Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)：描述特定長時程 app harness 的端到端測試經驗，並非小型 UI 修改的受控比較。
- [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)：研究一般 repo instructions 與 coding agent 任務，不是 browser policy 或前端驗收實驗。
- [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/)：OpenAI 專案經驗談 context 與文件分層，不是受控研究。
- [Pulumi：agent-browser 案例](https://www.pulumi.com/blog/self-verifying-ai-agents-vercels-agent-browser-in-the-ralph-wiggum-loop/)：特定頁面和任務的第三方案例；字元估算不能當普遍 token 節省率，也不是 CLI 對 MCP 的公平比較。
- [Matt Pocock 後續影片](https://www.youtube.com/watch?v=pSritFeoYFo)：研究素材僅有搜尋摘要，未取得完整逐字稿；不據此宣稱已核實影片結論。另有一篇 [LinkedIn 貼文](https://www.linkedin.com/posts/mapocock_whenever-youre-working-with-an-ai-agent-activity-7308525035994923008-2TQ0)，不是上述 X 原文，不能混稱。

## 曾考慮的分類表（未採用為固定政策）

研究時曾討論以下分類，僅是考慮過的建議，沒有官方共識或直接實驗支持；不作為執行命令，也不要求每次依表分類或逐項驗收。

| 改動類型 | 當時考慮的驗證方向 |
|---|---|
| 視覺、layout、responsive 或可見狀態 | 看受影響畫面；有助判斷時留截圖 |
| click、input、modal、loading、error、route 等行為 | 操作相關流程；需要診斷時看 console 或 network |
| 修錯字、註解、文件，且沒有排版或行為風險 | 可考慮略過瀏覽器；文字長度、翻譯或插值有影響時不能一概視為無風險 |
| 難重現問題或需桌機登入狀態 | 考慮用 Chrome DevTools MCP 診斷；適合時補可重現測試 |
| 登入／環境卡住，與這次修改無關 | 可停止擴張除錯，回報未驗範圍與阻礙 |

## 最後決策與重新檢討條件

目前採用的原則是：使用者要求瀏覽器驗收，或 agent 判斷需要透過瀏覽器確認畫面／行為時才驗；依驗證目的選擇操作、狀態和必要證據，回報實際驗過與未驗的部分。小 UI 改動不自動觸發，也不要求所有狀態都截圖。工具分工維持現行文件所述：一般操作驗證使用 Playwright CLI，需要 live desktop session 或深度診斷時考慮 Chrome DevTools MCP。

若實際任務反覆出現漏驗、虛報、工具不適用或成本瓶頸，再用具體案例重新檢討最小必要規則或工具；目前沒有足夠證據新增固定分類表，也沒有可引用為通用結論的 token 節省比例。
