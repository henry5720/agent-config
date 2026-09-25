---
name: slack-list
description: 讀寫 Slack「Bug/需求總表」上的待辦，並在該列的留言串回報進度。當使用者問「PM 有什麼待辦」「新增待辦」「Bug/需求總表」「PM 有沒有回我」時使用；要建立或指派 Slack list 待辦、設定回報對象、加回覆／留言／回報進度／通知 PM 驗收時也用。
---

# PM 的待辦表

PM（chieh）與授權使用者把 bug 與需求記在 Slack 的一張 List：**Bug/需求總表**。
讀它、看懂它、把處理進度回報回去，都走這支 skill 資料夾裡的 `scripts/slack-list`。

**不要自己組 curl，也不要用 Slack MCP 做這件事。** 腳本已經處理翻頁、
錯誤翻譯、欄位對應、討論串對應。繞過它就是重寫一次，而且會寫錯。

> 📁 **路徑**：下面的指令一律寫 `~/.claude/skills/slack-list/scripts/slack-list`，在哪個 cwd 跑都一樣。
> 本機由 skillshare sync 到那裡；container 的 skills 也掛在自己的 `~/.claude/skills`。
> 設定讀 `~/.config/slack-list/.env`，環境變數裡已經有的值優先。
> 其他 repo 只使用 runtime 明確提供的絕對路徑，不要自行猜 host/container 對應位置。

---

## 🚫 先講會做壞的三件事

1. **拿 `敘述` 欄當完整規格** —— 很多列的 `敘述` 只有「功能...」這種被截斷的字，
   真正的規格在那一列的**留言串**裡。`slack-list replies Rec0B…` 就讀得到，
   **派工或開 issue 之前一定要先讀**。實際發生過：PM 早就在留言裡裁決了，
   而我們照 `敘述` 開 issue，等於重問一次他已經答過的事。
   讀完還是不足才說「這列規格不夠」，**不要自己補一個看起來合理的需求**。
2. **假設一列 = 一張 issue** —— 實際看過的例子裡，一列的留言串包含 3 個獨立問題
   （UX 疑慮 / bug / 需求變更）。顆粒度還沒定案，不要自作主張拆或合。
3. **改 `狀態` 欄** —— 那是 PM 在維護的。唯一的例外是 `ready` 指令，
   它只會寫「PM確認中」這一個值。其他狀態一律不要碰。

---

## 📋 讀

```bash
~/.claude/skills/slack-list/scripts/slack-list rows                      # 一行一列，只印未完成
~/.claude/skills/slack-list/scripts/slack-list rows 庫存                  # 關鍵字比對整列文字，不分欄位
~/.claude/skills/slack-list/scripts/slack-list rows --assignee U0B…       # 指派給某人
~/.claude/skills/slack-list/scripts/slack-list rows --created-by U0B…     # 某人建立的列
~/.claude/skills/slack-list/scripts/slack-list rows --where 類別=bug       # 任一欄位的子字串比對
~/.claude/skills/slack-list/scripts/slack-list rows --where 類別=bug --where 狀態=PM確認   # 條件可疊加
~/.claude/skills/slack-list/scripts/slack-list rows --all                # 連已完成的也印
~/.claude/skills/slack-list/scripts/slack-list rows --columns 名稱,狀態    # 只印這幾欄，結果多的時候用
~/.claude/skills/slack-list/scripts/slack-list rows --full               # 每一格印完整內容（預設文字欄截到 120 字）
~/.claude/skills/slack-list/scripts/slack-list mine                      # local 專用：等同 --assignee 自己
~/.claude/skills/slack-list/scripts/slack-list json                      # 壓平後的 JSON，要程式處理時用
~/.claude/skills/slack-list/scripts/slack-list fields                    # 欄位名、型別、select 欄能填哪些值
~/.claude/skills/slack-list/scripts/slack-list users 小明                 # 人名關鍵字 → user ID，查 --assignee/--created-by 前先跑
~/.claude/skills/slack-list/scripts/slack-list users U0B…                # 反過來：ID → 是誰。回覆前把 ID 換成名字
```

**下 `--where` 之前先跑 `fields`。** 它會把每個 select 欄的完整選項列出來，例如「狀態」
有 12 個值（`前端完成`、`後端完成`、`wireframe完成`、`UI完成`、`暫停中（待觀察）`、
`PM確認中`、`已完成`、`bootstrap`、`NAI`、`PR-Review`、`需要討論`、`需要更多資訊`）。
不先看就下條件，你只會知道自己撈到的那幾個值 —— 實際發生過：撈了整張表再 grep 統計，
統計出 4 個值就當成全部，一題花了 105 秒。**選項清單以 `fields` 的輸出為準，不要背這裡的。**

`todo`／`assigned` 是 `rows` 的舊別名，還能用，但新的查詢一律用 `rows` —— 條件加在 flag 上，
不用再記哪個子指令支援哪個條件。

⚠️ **預設只印未完成的列，而且預設就是對的。** 全表 409 列裡 234 列已完成；未完成是 3 萬字，
全表是 9 萬字，而那些字會整包進你的 context。

**`--all` 只在這兩種情況加，其他一律不加：**

1. 使用者明確要已完成／全部／歷史。
2. 不加的時候查回 **0 列**——那時要再查一次才算找過，不要直接回「表上沒有這件事」，
   它很可能只是已完成。

**查回 0 列以外的情況不要「順便」加 `--all`。** 已完成的列狀態欄常常還留著舊值，
加了就會把早就結案的事混進答案。實際發生過：同一個問題不加是 6 件、加了是 26 件，
多出來的 20 件全都已經勾完成，而回覆只說「共 26 件」。

加了 `--all` 就要做兩件事：`--columns` 裡留著「已完成」欄，回覆時講清楚其中幾件已結案。
每次印完 stderr 都會告訴你這是哪一種視角。

⚠️ **輸出太大會被截掉，而且你不會馬上發現。** 「敘述」欄佔全表輸出的一半，超過上限時
工具結果會被存成檔案、只留 2KB preview 給你。**條件先下窄，再用 `--columns` 把不需要的欄拿掉**，
不要撈回來再自己 grep —— 那是把省下的 context 又花掉一次。
一列一行是保證的（換行已經壓掉），所以 `grep -c '^\[Rec'` 數出來就是列數。

要看某一列的完整敘述，用 `rows --columns 敘述 <關鍵字> --full`，或直接讀那列的留言串
（`replies Rec0B…`）—— 留言串才是規格的正本。

`--where 欄位=值` 是通用的：欄位名可以只給一部分，對不到會把可用欄位全部列出來。
**沒比對到任何列時，stderr 會告訴你那一欄實際長什麼樣**——值的種類少（≤25）就全部列出來，
種類多就只給總數和最常見的幾個。空結果配上那份清單，才分得出是「真的沒有」「值打錯了」
還是「欄位名寫錯了」。欄位和選項都是 PM 在 Slack UI 上維護的，不要在任何地方寫死。

從 terminal/local agent問「我身上有什麼事」「跟 X 有關的」用 `mine`。
從 OpenAB 回應 Slack 訊息時，「我」是 `openab.sender.v1.sender_id`，用
`rows --assignee <sender_id> [關鍵字]`。不要用共享環境的 `SLACK_MY_USER_ID`，也不要自己撈
`json` 再土炮過濾。

每一列開頭的 `[Rec0B…]` 就是 record ID，回報時要用。

跑不動時先 `slack-list env`（確認 `~/.config/slack-list/.env` 讀到了）再 `count`（確認通得到）。
沒設定會直接報哪個變數缺，照這個資料夾的 `.env.example` 設定。

OpenAB 每則訊息會附 `openab.sender.v1` JSON。只有當 runtime context 指向這張 List 的原生
item 留言串時，才用裡面的 `channel_id` 和 `thread_id` 反查待辦列；這不是任意 OpenAB thread
讀取器，也不會把一般 channel/DM 當成待辦列：

```bash
~/.claude/skills/slack-list/scripts/slack-list context --channel <channel_id> --thread-ts <thread_id>
```

## ➕ 建立待辦

`add` 由 OpenAB backlog agent 與 local agent 都可以跑。

⚠️ **同名去重是 read-then-write，而那把鎖只在單一 runtime 內有效。**
`add_lock()` 鎖的是 `/tmp/slack-list-add-<list_id>.lock`——container 的 `/tmp`
與 host 的 `/tmp` 是兩個檔案，所以**跨 runtime 同時建同名列會各建一列**，Slack 那邊也沒有
unique 約束擋。窗口很窄（要同一個標題、落在同幾秒內），代價是多一列、請使用者去 UI 刪
（沒有刪除指令）。撞到才修鎖，不要為它預先加機制。

**建之前一定要先查重**（`rows <關鍵字>`；0 列時再加 `--all` 查一次），這是唯一真正管用的
防線，不是那把鎖。

只有使用者明確要求「新增／建立待辦」才寫入。使用者明確給標題時直接建立；若要從一大段話
濃縮標題或敘述，先把準備寫入的內容貼出來確認。到期日按 `Asia/Taipei` 換成實際
`YYYY-MM-DD`，回覆時也顯示該日期；沒把握就問，不要猜。

`--assignee` 與 `--requested-by` 必須是同一個 ID（腳本會擋），差別只在那個 ID 從哪來：

| 跑在哪 | ID 來源 | 來源對話 |
|---|---|---|
| OpenAB | `openab.sender.v1.sender_id` | 帶 `--source-channel` / `--source-thread` |
| local（終端機） | `~/.config/slack-list/.env` 的 `SLACK_MY_USER_ID` | **兩個都省略** |

```bash
# OpenAB
~/.claude/skills/slack-list/scripts/slack-list add \
  --title "<使用者明確給出或已確認的標題>" \
  --description "<選填>" \
  --due YYYY-MM-DD \
  --assignee <openab.sender.v1.sender_id> \
  --requested-by <openab.sender.v1.sender_id> \
  --source-channel <openab.sender.v1.channel_id> \
  --source-thread <openab.sender.v1.thread_id>

# local
~/.claude/skills/slack-list/scripts/slack-list add \
  --title "<使用者明確給出或已確認的標題>" \
  --description "<選填>" \
  --assignee "$SLACK_MY_USER_ID" \
  --requested-by "$SLACK_MY_USER_ID"
```

local 省略來源對話時那一列只是少一行「來源對話」——`--requested-by` 仍會寫進發起者註記，
所以 `reporter --default` 之後找得到 fallback 對象。**不要為了填滿欄位隨便塞一個 channel／ts**，
`chat.getPermalink` 取不到就會中止建立。

使用者明確說「回報給 @某人」時，從 Slack mention 取可靠的 `U…` ID，加
`--report-to U…`。說「不要通知任何人」才加 `--no-reporter`。**不要用顯示名稱猜 ID** ——
只有 mention 和 `slack-list users <關鍵字>` 算可靠來源，後者回超過一個人時要先問是哪一位。
沒特別說時預設回報給 sender。

`add` 會自行處理精確同名：active列存在時不建第二列，而是把 sender 追加到 assignees，
並補一則再次回報的來源；原本就有 sender 時只補來源。既有列在「PM確認中」時不改指派，
只回既有連結。使用者確認是復發或另一件事後，才用同一組參數加 `--force`。
命中既有列時保留原回報對象，`add` 的 `--report-to` / `--no-reporter` 不套用；使用者看過合併結果後
仍要改，才另跑 `reporter`。

從既有 item 留言串要求新增時，**即使標題不同也先顯示目前待辦與準備新增的內容，確認是另一件事**。
腳本也會擋下第一次呼叫；確認後才加 `--force`。不要為了省一次對話直接略過。

成功後只回新增／合併結果、實際到期日及 deep link。若工具說列已建立但來源／回報設定失敗，
照實回報；不要重跑 `add`，否則可能建出重複列。若是「建立結果不明」，也先到List搜尋同名列，
不能直接重跑。這支工具不修改標題、敘述、日期，也不刪列。

### 設定既有列的回報對象

任何授權使用者都能在 item 留言串明確要求變更；用 `context` 取得 record ID後執行：

```bash
~/.claude/skills/slack-list/scripts/slack-list reporter Rec0B… --user U0B…  # 回報給被 mention 的一人
~/.claude/skills/slack-list/scripts/slack-list reporter Rec0B… --default    # 真人建立者／bot 建列發起者
~/.claude/skills/slack-list/scripts/slack-list reporter Rec0B… --none       # 驗收時不 @ 人
```

一列可以有多位指派對象，但回報對象至多一位。不要從 assignee 猜該通知誰。

---

## 🔍 被派去查一件待辦時

**草稿／issue body 的格式照你所在 repo 的 `CLAUDE.md` 觸發表指的那份規範**，不在這裡寫第二份。
怎麼查由你自己決定。

這裡只補一件那份規範不可能知道的事，因為它不碰 Slack：

⚠️ **`敘述` 欄常常只有「功能…」，真規格在那一列的留言串裡**（`slack-list replies`）。
沒讀留言就去查 repo，你拿到的需求會比實際的少一半。

## 🔑 開 issue 一定要先埋指紋

先跑 `slack-list env` 看 `ISSUE_MODE`：

- `agent`：照本節既有流程，用 `gh` 查重並開 issue。
- `manual`：**沒有 GitHub credential，不准嘗試 `gh` 或要求 token。** 偵察寫完草稿後，用
  `slack-list draft` 把 Markdown、指紋搜尋頁與 New issue 頁交回原生 item 留言串，然後停。
  只有既有待辦列能走這條發布流程；DM 或一般 channel 的口述需求要先用 `add` 對應到待辦列。

```bash
~/.claude/skills/slack-list/scripts/slack-list draft Rec0B… \
  --md drafts/<日期>/<短名>.md \
  --repo ShuChenAI/<repo> \
  --summary "<一句定位結論>" \
  --requested-by <openab.sender.v1 的 sender_id>
```

`manual` mode 的核准動作是人從 GitHub 網頁提交，或把附件交給有 `gh` 權限的 local agent。
不要聲稱已完成 GitHub 查重；只能提供搜尋連結讓核准者確認。

**開 issue 前必做，不是加分項。** 待辦從 Slack 進 GitHub 的流程裡，開 issue 的是 agent
不是人，沒有人在那個位置擋重複，所以這步漏掉就一定會開出重複的任務。

```bash
# 1. 先比對，任何一筆命中就不要開，去那張既有的 issue 上留言
gh issue list --search "Rec0B…" --state all

# 2. 沒命中才開。body 第一行放這個，然後才是簡報
> Slack 來源：[Rec0B…](<WORKSPACE>/lists/<TEAM_ID>/<LIST_ID>?record_id=Rec0B…)
```

**開完不用另外記。** 那行指紋就是正本，`--search` 立刻查得到，工具不留副本。

`Rec0B…` 就是 `todo` / `mine` / `assigned` 每列開頭印的那串。`<WORKSPACE>`、`<TEAM_ID>`、`<LIST_ID>`
從 `slack-list env` 印出來的那三行拿。`progress`、`ready` 等指令最後印的就是這條連結，有的話直接抄。

⚠️ **指紋要「看得見」，不要藏在 `<!-- -->` 裡。** GitHub 搜尋會不會索引 HTML 註解沒有定論，
而整套去重就靠這個查詢，賭不起。放成可見的引言行還有兩個好處：你點得回 Slack 那列，
別人看 issue 也知道來源。

⚠️ **不要靠 GitHub 自己的重複偵測。** 那個只在網頁表單被證實，
`gh issue create` 走不走得到官方沒講。當它不存在。

### 一列預設一張 issue

拆成多個任務是**例外**（顆粒度還沒定案，見最下面）。真的拆了，每一個都各自埋同一個指紋，
再用 `slack-list progress` 在該列的留言串貼一則「拆成 #1801 #1802 #1803」讓後面的人看得到。

### 只有正本，沒有快取

「這一列對到哪幾張 issue」的唯一答案是 `gh issue list --search "Rec0B…" --state all`。
工具不存副本 —— 存了就是養一份會過期的東西。

issue 格式走 runtime 明確提供的目標 repo（例如 mounted 的 `teamsync-frontend`）的
`docs/guides/workflow/github-issue-standards.md`
與 `docs/agents/issue-tracker.md`（`gh issue create --type` 是必要的），
規格不足的掛 `needs-triage`。

---

## 📣 回報

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

四條規矩：

- **`ready` 只在使用者說可以驗收時跑。** 它會推播吵到 PM。
  你自己覺得寫完了不算；測試綠了也不算；**沒 push 的 commit 不算**。
  不確定就跑 `progress`，那個不吵人。
  **這一列如果拆成多張 issue，要全部關掉才算** —— 跑之前先
  `gh issue list --search "Rec0B…" --state open`，有東西回來就不要跑。
  （`ready` 自己不查 GitHub，這步是你的責任。）
- **`ISSUE_MODE=manual` 時不跑 `ready`。** 遠端 backlog agent 看不到 private GitHub issue，
  無法證明這一列拆出的任務全關了；驗收由有 GitHub 權限的 local implementation agent 回報。
- **前端單一律 `--report`，不要用 `--changed`／`--verify` 湊。** 模板見下面那節。
  「怎麼驗收」寫得出來才算做完，那是 PM 唯一真正需要的東西 ——
  「測試一下」等於沒寫，要寫成「開哪個頁面 → 做什麼 → 看到什麼」。
  白話：PM 不看 commit，不要貼 SHA 或函式名。
- **`--url` 要帶測試連結，`ready` 才跑得動。** 前端的分支預覽網址是
  branch 名稱把 `/` 與其他非英數字元換成 `-`，接 `.<PREVIEW_DOMAIN>`（`slack-list env` 印得出來）
  —— `fix/spc-update` → `https://fix-spc-update.<PREVIEW_DOMAIN>`。
  **腳本自己不推導**（它不知道你在哪個 repo 的哪個 branch），
  所以要你算出來傳進去；發出去之前它會先確認連得到，連不到就中止。
  分支預覽要 CI 跑完才會有；後端單、純文件單這種本來就沒有畫面可看的，用 `--no-url`。

`--quiet` 不 `@` 人，只有使用者明講「先別吵他」時才用。

⚠️ **`@` 的是「回報對象」，不是「指派對象」。** 明確 `reporter` 設定優先；沒有設定時，
真人建立的列用 `created_by`，bot 代建的列用來源註記裡的發起者。找不到就不 `@` 人，
絕不拿 assignee 猜。

沒有任何刪除指令。要撤回已發的訊息，跟使用者說，讓他自己刪。

### 交付 prototype／artifact

backlog agent 要把 container `/home/node/drafts` 下的 prototype 或其他交付物交給 PM 時，使用
專用的 `artifact` 指令，交付到該列**既有的原生 item 留言串**。這不是任意 channel 的檔案
上傳器：`record_id` 必須來自原 Slack item/runtime context，工具會自己查回正確的 thread 與
channel。

```bash
~/.claude/skills/slack-list/scripts/slack-list artifact Rec0B… \
  --file /home/node/drafts/<日期>/<檔名> \
  --kind prototype \
  --summary "可操作的庫存匯出 prototype"
```

這不是 `draft` 的別名，**不要拿 `draft` 交 prototype／artifact，也不要拿 `artifact` 交 issue body**。
`draft` 保留「完整 Markdown issue body + GitHub 查重／建立連結」的人工發布流程；prototype／artifact
只用 `artifact`。

安全限制由腳本強制：`--file` resolve 後必須仍在 `/home/node/drafts` 底下，原路徑是 symlink、directory
或其他非 regular file 都會拒絕；副檔名白名單是 `.html`、`.md`、`.css`、`.js`、`.json`、`.png`、`.zip`
（不分大小寫）。單檔上限是 10 MiB；工具會先對安全 fd 做 `fstat`，再以 stream 讀取並再次
檢查上限。成功只在原 item 留言串附檔並發一則不含 `@` 的簡短訊息，不改狀態，也不寫 List
的「檔案」欄。

不要把 artifact 交到 DM、一般 channel 或新開的 thread。若 runtime 沒有原 Slack item 的
`record_id`/thread context，不能保證回到原 thread；先回報這項 deployment 限制，不要猜 channel。

預設 local CLI 保留上述副檔名白名單。remote runtime 要明確加 `--remote`，只接受 `.png`、`.md`、
`.html`；`.html` 還必須由呼叫者加 `--html`。成功完成 upload 與 thread 訊息後，工具會刪除
來源 regular file；upload、complete 或 post 任一步失敗都保留來源，避免無法重試或查證。

container cron／entrypoint 可呼叫：

```bash
~/.claude/skills/slack-list/scripts/slack-list cleanup
```

它只刪除 `/home/node/drafts` 內超過或正好 24 小時的 regular artifact，不追 symlink，也不會
掃描 root 以外的檔案。

上傳或 complete 失敗時不會發訊息。若訊息發送失敗，附件可能已經上傳；先檢查 item 留言串，**不要直接重試**，
避免重複附件。

這條流程的 external dependency scopes 是 `files:write`、`chat:write`，以及查找既有 item 留言串沿用的讀取
scopes（目前私有 channel 使用 `groups:read`、`groups:history`）。新增或調整 scope 後必須重新 Install app，
並使用 rotation 後的新 token；不要拿舊 token 直接重試。

### 驗收報告固定四段

`--report` 吃一份 md，整份就是 Slack 訊息本體。**照 [`report-template.md`](report-template.md) 寫**，
四段是 `改了什麼` → `⚠️ 要先知道的事`（有才寫）→ `怎麼驗收` → `QA case` 表格。
少任何一段腳本就不發，所以模板不用背 —— 忘了就跑一次看它罵什麼。

- **✅ 只能來自實際跑過的測試。** 先跑（例：`vitest run src/app/modules/inventory`），
  再把 `describe`／`it` 標題翻成 PM 看得懂的情境。**憑印象打勾就是給 PM 一份假的覆蓋率**，
  而這件事腳本驗不了 —— 只有你會知道你沒跑。
- **⬜ 後面要寫為什麼測不到**（「純顏色，要人工看」「你 08/17 驗過，這次沒動」）。
  只打一個框，PM 分不出那是漏掉還是刻意不測。（這條腳本會擋。）
- **「怎麼驗收」要指名現成資料**，寫「`PMV 低庫存示範品`」不要寫「找一個低庫存的品項」——
  PM 得自己造資料的驗收步驟，等於沒寫。
- **⚠️ 那段沒有行為改變就整段刪掉。** 固定要寫就會被硬填，填出來的是廢話，PM 下次整段跳過。

md 的 H1 標題與「測試網址：」那行會被腳本拿掉（訊息本身已經有），檔案自己留著是對的。

⚠️ **不要再用 `--md` 附一份同樣的報告。** 報告本體已經在訊息裡了，`--md` 是給真正額外的
東西用的（截圖、PM 給的規格檔）。那個附件會寫進該列的「檔案」欄，而且是**累加**的
（`scripts/slack-list:1904`）—— 每跑一次 `ready` 就多一份，最後那一欄是一疊同名的舊版本。

### 讀回覆

PM 的回覆都在該列的 item 留言串裡。

```bash
~/.claude/skills/slack-list/scripts/slack-list replies            # 掃整張表，只列「有別人回過」的
~/.claude/skills/slack-list/scripts/slack-list replies Rec0B…     # 看某一列（預設只印別人回的）
~/.claude/skills/slack-list/scripts/slack-list replies Rec0B… --all   # 連 bot 自己發的也印
```

**使用者問「PM 有沒有回我」「有什麼新回覆」就跑不帶參數那個。**
不要自己去開 Slack MCP 讀 channel —— 那會撈到一堆跟待辦無關的訊息。

---

## 🗂️ 這張表長什麼樣

實際欄位以 `~/.claude/skills/slack-list/scripts/slack-list fields` 為準。**輸出和 `--where`／`--columns` 用的都是
Slack UI 上那個中文欄位名**，不是 `Col0B8…` 這種內部 id。常見的幾欄：

| 欄位 | 內容 |
|---|---|
| 指派對象 | user ID，例如 `U0123456789`。**一列可以掛多人**，輸出是空白分隔的字串 |
| 已完成 | checkbox；有勾才印「是」。勾選或封存的列不擋同名新需求 |
| 到期日 | `YYYY-MM-DD`，相對日期以 `Asia/Taipei` 換算 |
| 名稱 | 帶前綴代號，例如 `T04 退貨表供應商欄位刪除`、`V01 在途欄位調整` |
| 敘述 | 一段說明，**常常被截斷或只有幾個字**；預設印到 120 字，要全文加 `--full` |
| 狀態 | 多選，輸出已經是人看的標籤（`PM確認中`…），不是 `OptXXXX` 代碼 |

三個要注意的：

- **assignee 只有 ID，沒有名字。** 兩個方向都走 `slack-list users`：給關鍵字得到 ID，
  給 `U…` 得到是誰（打 `users.list`，比對 ID、帳號、顯示名稱與全名；缺 `users:read` 時回
  `missing_scope`，那時請對方直接給 `U…`）。**回覆給人看之前，把 ID 換成名字** ——
  貼一串 `U0123456789` 出去，對方還要自己去查那是誰。
  Local自己的 ID 從 `~/.config/slack-list/.env` 的 `SLACK_MY_USER_ID` 拿（`mine` 已經處理好）；OpenAB當次使用者
  從 `openab.sender.v1.sender_id` 拿，交給 `rows --assignee`。
- **名稱前綴（`T` / `V` / `S` / `D` / `B` + 數字）是某種模組代號，但對應關係還沒確認。**
  不要憑字面猜它對到哪個模組，要用就先問使用者。
- **`狀態` 是多選，而且前端後端分開** —— 一件事可能同時牽涉
  `teamsync-frontend` 和 `teamsync-backend`。實際路徑以 runtime 提供的 mounted repo 為準；只看前端會漏。

---

## ⚠️ 撞到會浪費時間的

- **表的 schema 改不動。** 加欄位、加選項都回 `missing required field: id`，
  新元素的 id 只有 Slack 發得出來。要動欄位只能請使用者去 UI 改。
- **沒有 Events API。** Slack 不會推送 List 或討論串的變動。
  PM 在串裡回了什麼，要自己跑 `conversations.replies` 撈。
- **Slack 失敗時 HTTP 回 200**，錯誤在 body 的 `ok:false`。腳本已經翻成人話，照著做。
  `missing_scope` 一律是「加完 scope 要重裝 app，token 會換一組新的」。

---

## 🚧 還沒定案的（不要自己發明）

- **顆粒度**：一列開幾張 issue？前後端要不要拆兩張？討論過沒結論，遇到時**問使用者**。
