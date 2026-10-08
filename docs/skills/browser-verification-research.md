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

**PR 視覺證據與交付**

- [Zulip：Presenting visual changes](https://github.com/zulip/zulip/blob/main/docs/contributing/presenting-visual-changes.md)：專案明文要求視覺改動提供截圖，並優先 still；只有互動需要時才用影片並補靜態圖。這是 Zulip 自己的貢獻規範，不是跨專案硬規則。
- [Zed CONTRIBUTING](https://github.com/zed-industries/zed/blob/main/CONTRIBUTING.md)、[Kilo Code CONTRIBUTING](https://github.com/Kilo-Org/kilocode/blob/main/CONTRIBUTING.md)、[Fleet PR template 變更](https://github.com/fleetdm/fleet/commit/71177c9b030dd4bedd8553e6c6e9d16f507285dd)：成熟專案各有 UI 圖片／影片政策或採用背景；要求不一致，不能推成普遍規範。
- [GitHub PR template 說明](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository) 與[保護分支說明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)：template 是提示 PR 作者填資料；required checks/reviews 是可設定的 merge gate。欄位或附件存在，不等於 UI 實際正確或已驗證。
- [OpenAI Codex manual](https://developers.openai.com/codex/codex-manual.md)、[Codex best practices](https://developers.openai.com/codex/learn/best-practices) 與 [Anthropic Claude Code memory](https://code.claude.com/docs/en/memory)：支持把具體、使用者特定的交付期待寫短並按需展開；沒有要求所有 PR 都附截圖或影片。
- [Anthropic long-running agent harness 案例](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)：顯示明確要求端到端驗收對該長時程 app harness 有用；不是小型 UI patch 或 PR 截圖政策的受控研究。

以上連結保留供日後閱讀；本次沒有重新逐一核驗所有頁面或其最新內容。專案規範是各自案例，不代表業界一致標準；沒有直接研究能證明固定附件政策會改善所有 PR review。

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

目前採用的原則是：日常 browser 驗證由 agent 自主判斷，不因每個 UI 改動一律啟動；使用者要求驗收時執行，並依驗證目的選擇操作、狀態和必要證據，回報實際驗過與未驗的部分。工具分工維持現行文件所述：一般操作驗證使用 Playwright CLI，需要 live desktop session 或深度診斷時考慮 Chrome DevTools MCP。

PR 交付依受眾提供最小但足以理解的視覺說明。UI 截圖依情況附上；互動影片只在 still 不足以說明流程時考慮。這是目前使用者的交付偏好，不是所有 PR 的硬性要求；說明圖本身不代表已實際驗證。沒有驗過的內容要明確標示，不虛報。沿用 repo 現有 PR/CI 機制，不另造 template 或 CI gate。

若實際 review 反覆缺少理解改動所需的視覺說明，或出現漏驗、虛報、工具不適用等具體問題，再按案例重新檢討最小必要規則；目前沒有足夠證據把既有分類表改成 mandatory policy，也沒有通用 token 節省比例。

`show-me` 來自上游 `humanlayer/skills`；正文與 description 保持上游內容。本機僅開放自主呼叫：`SKILL.md` 的 `disable-model-invocation: false`，以及 `agents/openai.yaml` 的 `allow_implicit_invocation: true`。上游更新後須核對這兩個設定；它們允許自主呼叫，不保證每次觸發，各 client 仍依自身載入機制運作。
