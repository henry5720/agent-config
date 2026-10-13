# PR body 與 review comment 的現行格式盤點

> 研究票：henry5720/agent-config#15（map #12「PR 收尾流程」）。調查日 2026-10-09。
> 只盤點現況，不提新格式；新格式由 #18 決定。

## 結論

- **沒有任何一份是 PR body 的完整骨架。** teamsync-frontend 沒有 PR template（`.github/` 底下只有 `dependabot.yml`、`scripts/`、`workflows/`），repo 文件只硬性要求 `Closes #N`。真正規定「要有哪一段」的只有使用者全域 `CLAUDE.md`（`## 驗證`）和 Matt 的 `pr` skill（`## Summary`／`## Evidence`／`## Merge Danger`），而這兩份的標題互相衝突。
- **大家都要求的只有兩件事**：結論先講；驗證段要寫實際做了什麼。「未驗」只有全域 `CLAUDE.md`、`verify-in-browser`、teamsync `CLAUDE.md` 要求，Matt 的 `pr` 和 `pr-review` 都沒有。
- **衝突有四處**：段落標題（`## 驗證` 對上 `## Evidence`）、改前／改後截圖（Matt 必附，其他按需）、mermaid（`show-me`／Matt 預設用，全域規則說終端機和 Slack 看不到）、HTML（`show-me` 產本機 HTML，全域規則說 PR 不放只能本機看的 HTML）。
- **最大的缺口在兩支 skill 之間**：`pr-review` 期待作者在 PR 描述裡列「已知限制／待後端／刻意不做」，但沒有任何寫 PR body 的來源要求這一段。另外 `pr-review` 的草稿格式沒有「未驗」，也不查未 resolved 的 review threads，所以它寫出的「可以 merge」不符合 teamsync `CLAUDE.md` 的驗收結論規則。
- **實際做法（抽樣 3 張已 merge 的 PR）**：三張都有 `Closes #N`、`## 改了什麼`、`## 驗證`，`## 驗證` 裡也都有「未驗」；三張都寫「本機未跑測試，交給 CI」，跟 teamsync `CLAUDE.md` 說本機那次驗證「是 PR 之前唯一的閘門」直接衝突。三張都沒有截圖，也沒有 mermaid。

## 來源與引用寫法

| 代號 | 來源 | 版本 |
|---|---|---|
| **G** | 使用者全域 `~/.claude/CLAUDE.md`（不在任何 repo） | 2026-10-09 本機檔 |
| **T** | teamsync-frontend `CLAUDE.md` | `ShuChenAI/teamsync-frontend@32684c573` |
| **T-issue** | teamsync-frontend `docs/guides/workflow/github-issue-standards.md` | 同上 |
| **T-commit** | teamsync-frontend `docs/guides/workflow/git-commit-standards.md` | 同上 |
| **T-wf** | teamsync-frontend `.github/workflows/close-dev-leaf-issues.yml` | 同上 |
| **PR** | teamsync-frontend `.claude/skills/pr-review/SKILL.md` | 同上 |
| **PR-tpl** | teamsync-frontend `.claude/skills/pr-review/references/output-template.md` | 同上 |
| **V** | 本 repo `skills/verify-in-browser/SKILL.md` | `origin/main@195a709` |
| **A** | 本 repo `skills/playwright-cli/references/pr-attachments.md` | 同上 |
| **S** | 本 repo `skills/show-me/SKILL.md`（third-party，來自 `humanlayer/skills`，見 `skills/.metadata.json:307-312`） | 同上 |
| **M** | `mattpocock/skills` `skills/engineering/pr/SKILL.md`（未安裝） | 該檔最新 commit `e484a80` |
| **AC** | 本 repo `CLAUDE.md` | `origin/main@195a709` |

下文 `G:33` 代表 G 的第 33 行，其餘代號同理。

## 矩陣：段落／要求 × 來源

「—」＝該來源沒提。

| 要求 | G 全域 | T（含 T-issue／T-wf） | PR／PR-tpl（review comment） | V 回報 | A 附件 | S show-me | M Matt `pr` | 實際（3 張 PR） |
|---|---|---|---|---|---|---|---|---|
| 結論先講 | 先講結論 `G:20` | — | 第一句＝結論 `PR-tpl:6`、`PR-tpl:41` | — | — | 省掉開場白 `S:7` | 省掉開場白 `M:37` | 沒有一句話的結論，直接 `Closes #N` + `## 改了什麼` |
| 必備標題 | `## 驗證` 一律要有 `G:33` | 只要求 `Closes #N` `T:163`、`T-issue:40-45` | 自訂分區，結尾固定 `## 驗過乾淨` `PR-tpl:8-19`、`PR-tpl:35-37` | 寫進 `## 驗證` `V:76` | — | — | `## Summary`／`## Evidence`／`## Merge Danger` `M:14-33` | `## 改了什麼` + `## 驗證`（3/3），另有 `## 測試`、`## 拍板`、`## 後續` |
| 改了什麼 | — | 只有「編寫清晰的 PR 描述」`T-commit:211-215` | — | — | — | — | Summary 用圖／diff／樹表示 `M:17`、`M:39-41` | 純文字條列或表格（3/3） |
| 實際跑過的指令與結果 | 列出指令與結果 `G:33` | 本機那次驗證是 PR 前唯一閘門 `T:71-74` | 每條 finding 要能說「怎麼驗」`PR:142` | 驗了什麼、觀察到什麼 `V:80` | — | — | 測試結果、console 輸出屬 A 級證據 `M:164` | 「本機未跑測試，交給 CI」（3/3），畫面操作逐條 ✅ |
| 未驗與原因 | 要列 `G:33` | 未觸發的狀態要明列未驗 `T:81` | —（只有 `## 驗過乾淨`，沒有未驗區）`PR-tpl:17-19` | 要列，沒有就寫「無」`V:82` | — | — | — | 都有（3/3） |
| console 錯誤 | — | — | — | 錯誤數 + 新錯誤原文 `V:81` | — | — | 屬證據之一 `M:164` | 2/3 寫「console 無錯誤」 |
| 截圖 | 按需；優先真實截圖；說明圖不算證據 `G:35` | 單元測試不能代替畫面驗收 `T:81` | — | 有截圖才列檔名 `V:80` | 能省 reviewer checkout 才附；refactor、純後端不附 `A:7` | — | 截圖是 S 級證據 `M:162` | 0/3 附圖 |
| 改前／改後 | — | — | — | 要比較版面時「可」附 `V:90` | 列為可附的一種 `A:7` | — | **必附** Before／After `M:21-22`、`M:160` | 0/3 |
| 影片 | 只有靜態圖表達不了互動才附 `G:35` | — | — | — | 新流程可附短影片；免費方案上限 10 MB `A:7`、`A:33` | — | — | 0/3 |
| 附件放哪 | 當附件、不 commit 進 repo `G:36` | — | — | 用 `gh pr comment --attach` 放留言 `V:84-88` | `gh pr create/edit --attach`，可在 body 內嵌 `A:3`、`A:21-29` | — | — | — |
| 敏感資料 | 不能有 `G:36` | — | — | 畫面有真實客戶資料就不附圖 `V:91` | — | — | — | — |
| mermaid | 終端機和 Slack 看不到，改用文字箭頭或縮排樹 `G:29` | — | — | — | — | 預設可用 `S:47-57` | Summary 可用 `M:81-91` | 0/3 |
| HTML | PR／GitHub 不放只能本機看的 HTML `G:28` | — | — | — | — | 寫 HTML 再 `open` `S:118-122` | — | — |
| 風險／影響範圍 | 要附路徑、行號或指令輸出 `G:41` | — | — | — | — | — | `**Door:**` 單向／雙向門 + `**Blast Radius:**` `M:24-32`、`M:166-170` | 0/3 有風險段；#3075 有一行「疊在另一張 PR 上，合併後要改 base」 |
| 已知限制／刻意不做 | — | — | 作者有列的只能提及、不擋 `PR:64`、`PR-tpl:45` | — | — | — | — | 0/3 有這一段（只有「未驗」和「後續」） |
| 關票語法 | — | `Closes #N`，一張葉單一個，父單不放 `T-issue:40-43`；整合分支用 `Part of #N` `T-issue:64`；workflow 會先拿掉 code block 和 inline code 再比對 `T-wf:37-40` | — | — | — | — | — | `Closes #N`（3/3），另有 `Refs #N` |
| 詞彙來源 | — | — | — | — | — | — | `GLOSSARY.md` `M:37` | — |
| 每條長度 | — | — | 一條一行、不放 code block、最多 3 行；少於約 5 條就用聊天口吻 `PR-tpl:42`、`PR-tpl:47-48` | — | — | 用最小的那種視圖 `S:7` | 同 S `M:41` | 段落長、技術細節多 |
| 狀態符號 | — | — | 不用 emoji、不用 ✅⚠️ `PR-tpl:46` | — | — | — | — | 驗證段大量使用 ✅、⚠️ |
| 發出前給人看 | — | — | 草稿先給使用者，同意後才發 `PR:109`、`PR:138` | — | — | — | — | — |
| 驗收結論用詞 | — | 先逐條對照未 resolved 的 threads；分開說「已驗範圍通過」與「整張 PR 驗收完成」`T:80-82` | 全修好就明說「可以 merge」`PR:116`、`PR-tpl:6` | — | — | — | — | — |

## 重疊

1. **結論先講**：G、PR-tpl、S、M 都要求（`G:20`、`PR-tpl:41`、`S:7`、`M:37`）。M 的 `## Summary` 放的是圖，不是一句結論，所以「結論」到底是一句話還是一張圖，各來源沒有共識。
2. **驗證段**：G、V、M 都有一段專放證據（`G:33`、`V:76`、`M:19-22`），內容大同小異，都是「實際跑過什麼 + 結果」。
3. **截圖當附件、不進 repo**：G 和 V 一致（`G:36`、`V:84`）；A 提供做法（`A:3`）。
4. **按需附圖**：G、V、A 都是「有用才附」（`G:35`、`V:40`、`A:7`）。
5. **S 和 M 的視覺化段落幾乎逐字相同**：M 自己標了 credit 給 humanlayer `show-me`（`M:4-9`）；`M:41-156` 跟 `S:7-128` 內容一樣，差別只在 component tree 的 code fence 標成 `text` 而不是 `tsx`（`M:65`、`S:31`）。

## 衝突

1. **段落標題**：G 要求「一律有 `## 驗證`」（`G:33`）；M 的模板是 `## Evidence`（`M:19`），而且用英文標題，G 卻要求用繁中（`G:9`）。直接套 M 的模板就會違反 G。
2. **改前／改後截圖**：M 規定每個 PR 都要 Before／After（`M:21-22`、`M:160`）；G 明講「不要求每個 PR 都附圖或錄影」（`G:35`）；V 和 A 只把改前／改後當成「可以附」（`V:90`、`A:7`）。
3. **mermaid**：S 和 M 都把 mermaid 列成預設選項（`S:47-57`、`M:81-91`），本 repo 寫文件也偏好 mermaid（`AC:18`）；G 說終端機和 Slack 不渲染（`G:29`）。GitHub 的 PR body 和 comment **會**渲染：用 `gh api markdown -f mode=gfm` 送一段 ```` ```mermaid ```` 進去，回傳的是 `data-type="mermaid"` 的 render 容器，不是普通 `<pre>`。所以衝突只在三個地方：草稿在終端機給人看時（`PR:109`）、PR 內容轉貼到 Slack 時、agent 在終端機讀 `gh pr view` 時。
4. **HTML**：S 遇到 UI 或密度高的主題時會寫 HTML 檔並 `open`（`S:118-122`）；G 禁止 PR 放只能本機看的 HTML（`G:28`）。另外 `open` 是 macOS 指令，本機是 Linux。
5. **附件放 body 還是留言**：V 把截圖放進另開的 `gh pr comment`（`V:87`）；A 示範 `gh pr create --attach` 加上 `![alt](./file.png)`，圖會內嵌在 body 裡（`A:21-29`）。G 只說「作為附件」（`G:36`），沒說放哪。已確認本機 `gh` 2.102.0 的 `gh pr comment --help` 有 `--attach`。
6. **「可以 merge」的門檻**：PR 全修好就說「可以 merge」（`PR:116`）；T 要求先逐條核對未 resolved 的 review threads，結論還要分「已驗範圍」與「整張 PR」（`T:80-82`）。PR 的 Step 0 只抓 `comments,reviews`（`PR:28`）；`gh pr view --json` 能用的欄位裡沒有 review thread，`references/commands.md` 也找不到 thread／resolved 的查法。也就是說，照 PR 做完的 reviewer 拿不到 T 要求的資訊。
7. **狀態符號**：PR-tpl 禁止 ✅⚠️（`PR-tpl:46`）。這條只管 review comment；實際 PR body 的驗證段整段都是 ✅。兩種格式要統一時才算衝突。
8. **規則和實際做法**：T 說本機驗一次是 PR 前唯一的閘門，CI 只跑受影響的 test、紅了也擋不住 merge（`T:71-74`）；抽樣的三張 PR 都寫「本機未跑測試，交給 CI」。這三張符合 G 的「未驗要列出來」（`G:33`），卻不符合 T 的「不能省」。

## 缺口

1. **teamsync 沒有 PR template**：`.github/` 沒有 `pull_request_template.md`，`git ls-files` 也找不到任何 `*pull_request*`。T 和 T-commit 只要求 `Closes #N` 和「清晰的描述」（`T:163`、`T-commit:213`）。
2. **寫 PR 的一方沒有「已知限制」段**：PR 讀描述時會找「已知限制」「待後端」「刻意不做」（`PR:64`），但 G、T、V、M 都沒有要求作者寫這一段。抽樣的 PR 用「未驗」和「後續」代替，兩者意思不一樣：「未驗」是沒驗到，「已知限制」是刻意不做。
3. **review comment 沒有「未驗」**：PR-tpl 只有 `## 驗過乾淨`（`PR-tpl:17-19`），沒有地方寫「這次 review 沒看到的東西」，例如沒跑的測試、沒進的後端 repo。G 的誠實規則（`G:40-41`）和 T 的「未觸發狀態要列未驗」（`T:81`）在 review 這邊沒人接。
4. **自審視角**：PR 是 reviewer 寫給別人看的（`PR:109` 要先給使用者過目才發）；自己的 PR 自審完要放 body 的 `## 驗證`、另發 comment，還是不留紀錄，沒有任何來源規定（map #12 的 Notes 也提到這個落差）。
5. **風險段**：只有 M 有 Merge Danger（`M:24-32`）。teamsync 這邊，堆疊 PR（`T:163` 允許疊在別張上）要不要在 body 寫 base 依賴沒有規定；#3075 是作者自己加的。
6. **詞彙檔名**：M 要用 `GLOSSARY.md`（`M:37`）；teamsync 與本 repo 用的是 `CONTEXT.md`（teamsync 有多份模組層級的 `CONTEXT.md`，例如 `frontend/e2e/CONTEXT.md`；本 repo 是根目錄的 `CONTEXT.md`）。直接用 M 的 `pr` skill 會找不到詞彙檔。
7. **影片壓縮**：A 寫了 10 MB 上限（`A:33`），G 和 V 都沒有指向 `compress-video` skill。

## 抽樣 PR 摘要（ShuChenAI/teamsync-frontend，最近 3 張已 merge）

`gh pr list -R ShuChenAI/teamsync-frontend --state merged -L 3`，取得 #3080、#3075、#3070。三張是**同一位作者**、結尾都有 Claude Code 署名，所以只代表 agent 產出的 PR，不代表整個團隊。

| | #3080 | #3075 | #3070 |
|---|---|---|---|
| 第一行 | `Closes #N` | `Closes #N` + 一行 ⚠️ 堆疊 base 提醒 | `Closes #N` |
| 段落 | 改了什麼／測試／驗證 | 拍板／改了什麼／驗證 | 改了什麼／驗證／後續 |
| 改了什麼 | 表格 | 粗體小標 + 條列 | 條列 |
| 本機測試 | 未跑，交給 CI | 未跑，交給 CI | 未跑，交給 CI |
| 畫面驗證 | 有（✅ 逐條、日期、環境） | 有（旗標開關兩組） | 有（含權限帳號） |
| 未驗 | 有 + 原因 | 有 | 有 |
| 截圖／影片／mermaid | 無 | 無 | 無 |
| 其他關聯 | `Refs #N` | — | — |

## 沒查到或沒驗證的

- G 是本機檔，不在任何 repo，所以行號沒有 commit 可以釘住；其他人重查時行號可能已經變了。
- 「Slack 不渲染 mermaid」是 G 的說法（`G:29`），這次沒有實際貼到 Slack 測試；GitHub 會渲染這件事有用 Markdown API 確認過。
- M 尚未安裝，這次只讀了 `SKILL.md`；同目錄的 `CREDITS.md` 和 `agents/` 沒讀。
- 只抽了 3 張 PR，而且是同一位作者，不能拿來推論其他作者或人手寫的 PR。
