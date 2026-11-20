# 回報進度、通知驗收、讀回覆

[SKILL.md](SKILL.md) 的分支：在某列的留言串回報進度、通知 PM 驗收，或看 PM 回了什麼。

**回報寫進該列原生的 item 留言串** —— PM 本來就在那裡講話。
Slack 在建列時就替每一列開好串了，腳本只查既有串、不另建串，對應關係也不用維護
（Slack 自己是正本）。

```bash
# 中間進度：只回在串裡，不 @ 人、不改狀態
~/.claude/skills/slack-list/scripts/slack-list progress Rec0B… "後端改完，佈建零失敗行"

# 可以驗收了：@ 回報對象 + 狀態改成「PM確認中」
~/.claude/skills/slack-list/scripts/slack-list ready Rec0B… \
  --url    https://fix-spc-update.<PREVIEW_DOMAIN> \
  --report drafts/<日期>/reports/report-<issue>-<短名>.md

# 沒有畫面可看的單（後端、純文件）：沒有 QA table 可寫，用 flag
~/.claude/skills/slack-list/scripts/slack-list ready Rec0B… --no-url \
  --changed "生產單建立時就佔料，完工才落帳" \
  --verify  "建一張生產單，確認投入明細出現在異動紀錄"
```

## `ready` 的四條規矩

- **`ready` 只在使用者說可以驗收時跑。** 它會推播吵到 PM。
  你自己覺得寫完了不算；測試綠了也不算；**沒 push 的 commit 不算**。
  不確定就跑 `progress`，那個不吵人。
  **這一列如果拆成多張 issue，要全部關掉才算** —— 跑之前先
  `gh issue list --search "Rec0B…" --state open`，回空才跑。
  （`ready` 自己不查 GitHub，這步是你的責任。）
- **`ISSUE_MODE=manual` 時驗收交給 local agent，這裡只跑 `progress`。** 遠端 backlog agent 看不到 private GitHub issue，
  無法證明這一列拆出的任務全關了；驗收由有 GitHub 權限的 local implementation agent 回報。
- **前端單一律用 `--report` 寫驗收報告**；`--changed`／`--verify` 只給沒畫面的單。
  「怎麼驗收」寫得出來才算做完，那是 PM 唯一真正需要的東西 ——
  「測試一下」「找一個低庫存的品項」這種要 PM 自己猜步驟、造資料的，等於沒寫。
- **`--url` 要帶測試連結，`ready` 才跑得動。** 前端的分支預覽網址是
  branch 名稱把 `/` 與其他非英數字元換成 `-`，接 `.<PREVIEW_DOMAIN>`（`slack-list env` 印得出來）
  —— `fix/spc-update` → `https://fix-spc-update.<PREVIEW_DOMAIN>`。
  **腳本自己不推導**（它不知道你在哪個 repo 的哪個 branch），
  所以要你算出來傳進去；發出去之前它會先確認連得到，連不到就中止。
  分支預覽要 CI 跑完才會有；後端單、純文件單這種本來就沒有畫面可看的，用 `--no-url`。

`--quiet` 不 `@` 人，只有使用者明講「先別吵他」時才用。

⚠️ **`@` 的是「回報對象」，不是「指派對象」。** 明確 `reporter` 設定優先；沒有設定時，
真人建立的列用 `created_by`，bot 代建的列用來源註記裡的發起者。找不到就不 `@` 人；assignee 不拿來替代。

沒有任何刪除指令。要撤回已發的訊息，跟使用者說，讓他自己刪。

## 驗收報告固定四段

`--report` 吃一份 md，整份就是 Slack 訊息本體。**照 [report-template.md](report-template.md) 寫**，
每段怎麼寫看模板裡的提示。少任何一段腳本就不發，所以段落不用背 —— 忘了就跑一次看它罵什麼。
模板以外還要守的：

- **✅ 只能來自實際跑過的測試。** 先跑（例：`vitest run src/app/modules/inventory`），
  再把 `describe`／`it` 標題翻成情境。**憑印象打勾就是給 PM 一份假的覆蓋率**，
  而這件事腳本驗不了 —— 只有你會知道你沒跑。
- **⬜ 後面要寫為什麼測不到**（「純顏色，要人工看」「你 08/17 驗過，這次沒動」）。
  只打一個框，PM 分不出那是漏掉還是刻意不測。（這條腳本會擋。）

md 的 H1 標題與「測試網址：」那行會被腳本拿掉（訊息本身已經有），檔案自己留著是對的。

⚠️ **`--md` 只附報告以外的東西**（截圖、PM 給的規格檔）。報告本體已經在訊息裡了，別再用 `--md` 附一份。
那個附件會寫進該列的「檔案」欄，而且是**累加**的（`cmd_ready` 把新檔追加到既有附件後面）——
每跑一次 `ready` 就多一份，最後那一欄是一疊同名的舊版本。

## 讀回覆

PM 的回覆都在該列的 item 留言串裡。Slack 沒有 Events API，不會推送 List 或討論串的變動，要自己跑 `replies` 撈。

```bash
~/.claude/skills/slack-list/scripts/slack-list replies            # 掃整張表，只列「有別人回過」的
~/.claude/skills/slack-list/scripts/slack-list replies Rec0B…     # 看某一列（預設只印別人回的）
~/.claude/skills/slack-list/scripts/slack-list replies Rec0B… --all   # 連 bot 自己發的也印
```

**使用者問「PM 有沒有回我」「有什麼新回覆」就跑不帶參數那個**；它只看待辦列的留言串，
用 Slack MCP 讀 channel 會撈到一堆跟待辦無關的訊息。
