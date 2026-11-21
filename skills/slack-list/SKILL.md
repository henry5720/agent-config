---
name: slack-list
description: 讀寫 Slack「Bug/需求總表」上的待辦與每列的留言串。使用者問「PM 有什麼待辦」或要查表上的事、要新增待辦、要回報進度或通知 PM 驗收、問「PM 有沒有回我」、要設定某列的回報對象時使用。
---

# PM 的待辦表

PM（chieh）與授權使用者把 bug 與需求記在 Slack 的一張 List：**Bug/需求總表**。
讀它、看懂它、把處理進度回報回去，一律走這支 skill 資料夾裡的 `scripts/slack-list`：
翻頁、錯誤翻譯、欄位對應、討論串對應它都處理好了。自己組 curl 或改用 Slack MCP 等於重寫一次，而且會寫錯。

> 📁 **路徑**：下面的指令一律寫 `~/.claude/skills/slack-list/scripts/slack-list`，在哪個 cwd 跑都一樣。
> 內文寫 `slack-list <指令>` 時指的也是這支；它不在 PATH 上，要打完整路徑。
> 本機由 skillshare sync 到那裡；container 的 skills 也掛在自己的 `~/.claude/skills`。
> 設定讀 `~/.config/slack-list/.env`，環境變數裡已經有的值優先。
> **原生 Windows**（不是 WSL）每個指令前面加 `py -3`，不要用 `python3`。沒有 `py` 就請使用者照
> agent-config 的 `docs/skills/slack-list.md`〈Windows〉裝 Python。
> 其他 repo 只使用 runtime 明確提供的絕對路徑，host/container 的對應位置以 runtime 給的為準。

要做的不只是讀時，先讀對應那份：

- 建立待辦、改既有列的回報對象 → [add.md](add.md)
- 被派去查一件待辦、開 GitHub issue → [issue.md](issue.md)
- 回報進度、通知 PM 驗收、讀 PM 的回覆 → [progress.md](progress.md)
- 把 prototype／截圖等檔案交到某列的留言串 → [artifact.md](artifact.md)

---

## 🚫 紅線：這三件會做壞

1. **規格以該列的留言串為準，`敘述` 欄只是索引。** 很多列的 `敘述` 只有「功能...」這種被截斷的字，
   真正的規格在那一列的**留言串**裡。派工或開 issue 之前一定先跑 `slack-list replies Rec0B…`；
   沒讀留言就去查 repo，拿到的需求會比實際的少一半。實際發生過：PM 早就在留言裡裁決了，
   而我們照 `敘述` 開 issue，等於重問一次他已經答過的事。
   讀完還是不足，就回報「這列規格不夠」並列出缺什麼，需求留給使用者補，不自己補一個看起來合理的。
2. **一列開幾張 issue、前後端要不要拆兩張，遇到時問使用者。** 顆粒度討論過但沒結論。
   實際看過的例子裡，一列的留言串包含 3 個獨立問題（UX 疑慮 / bug / 需求變更），拆或合都不能自作主張。
3. **`狀態` 欄留給 PM 維護。** 唯一會寫它的是 `ready` 指令，而且只寫「PM確認中」這一個值。

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

**下 `--where` 之前先跑 `fields`。** 它會把每個 select 欄的完整選項列出來，選項清單以它的輸出為準。
不先看就下條件，你只會知道自己撈到的那幾個值 —— 實際發生過：撈了整張表再 grep 統計，
統計出 4 個值就當成全部，一題花了 105 秒。

⚠️ **預設只印未完成的列，而且預設就是對的。** 全表 409 列裡 234 列已完成；未完成是 3 萬字，
全表是 9 萬字，而那些字會整包進你的 context。

**`--all` 只在這兩種情況加：**

1. 使用者明確要已完成／全部／歷史。
2. 不加的時候查回 **0 列** —— 那時再加 `--all` 查一次才算找過，它很可能只是已完成，
   兩次都 0 列才回「表上沒有這件事」。

其他情況都用預設視角。已完成的列狀態欄常常還留著舊值，「順便」加 `--all` 會把早就結案的事混進答案。
實際發生過：同一個問題不加是 6 件、加了是 26 件，多出來的 20 件全都已經勾完成，而回覆只說「共 26 件」。

加了 `--all` 就要做兩件事：`--columns` 裡留著「已完成」欄，回覆時講清楚其中幾件已結案。
每次印完 stderr 都會告訴你這是哪一種視角。

⚠️ **輸出太大會被截掉，而且你不會馬上發現。** 「敘述」欄佔全表輸出的一半，超過上限時
工具結果會被存成檔案、只留 2KB preview 給你。**條件先下窄，再用 `--columns` 把不需要的欄拿掉**；
撈回來再自己 grep 等於把省下的 context 又花掉一次。
一列一行是保證的（換行已經壓掉），所以 `grep -c '^\[Rec'` 數出來就是列數。

要看某一列的完整敘述，用 `rows --columns 敘述 <關鍵字> --full`，或直接讀那列的留言串
（`replies Rec0B…`）—— 留言串才是規格的正本。

`--where 欄位=值` 是通用的：欄位名可以只給一部分，對不到會把可用欄位全部列出來。
**沒比對到任何列時，stderr 會告訴你那一欄實際長什麼樣** —— 值的種類少（≤25）就全部列出來，
種類多就只給總數和最常見的幾個。空結果配上那份清單，才分得出是「真的沒有」「值打錯了」
還是「欄位名寫錯了」。欄位和選項都是 PM 在 Slack UI 上維護的，每次以 `fields` 的輸出為準。

「我身上有什麼事」「跟 X 有關的」：從 terminal/local agent 問就用 `mine`。
從 OpenAB 回應 Slack 訊息時，「我」是 `openab.sender.v1.sender_id`，用
`rows --assignee <sender_id> [關鍵字]` 過濾（共享環境的 `SLACK_MY_USER_ID` 不是當次發訊息的人）。

每一列開頭的 `[Rec0B…]` 就是 record ID，回報時要用。

OpenAB 每則訊息會附 `openab.sender.v1` JSON。只有當 runtime context 指向這張 List 的原生
item 留言串時，才用裡面的 `channel_id` 和 `thread_id` 反查待辦列；這不是任意 OpenAB thread
讀取器，一般 channel/DM 不對應任何待辦列：

```bash
~/.claude/skills/slack-list/scripts/slack-list context --channel <channel_id> --thread-ts <thread_id>
```

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
  Local 自己的 ID 從 `~/.config/slack-list/.env` 的 `SLACK_MY_USER_ID` 拿（`mine` 已經處理好）；OpenAB 當次使用者
  從 `openab.sender.v1.sender_id` 拿，交給 `rows --assignee`。
- **名稱前綴（`T` / `V` / `S` / `D` / `B` + 數字）是某種模組代號，但對應關係還沒確認。**
  要拿前綴判斷模組時先問使用者，字面上像哪個模組不算數。
- **`狀態` 是多選，而且前端後端分開** —— 一件事可能同時牽涉
  `teamsync-frontend` 和 `teamsync-backend`。實際路徑以 runtime 提供的 mounted repo 為準；兩邊都要看，只看前端會漏。

---

## ⚠️ 跑不動、撞到會浪費時間的

- **跑不動時先 `slack-list env`**（確認 `~/.config/slack-list/.env` 讀到了）**再 `count`**（確認通得到）。
  沒設定會直接報哪個變數缺，照這個資料夾的 `.env.example` 設定。
- **Slack 失敗時 HTTP 回 200**，錯誤在 body 的 `ok:false`。腳本已經翻成人話，照著做。
  `missing_scope` 一律是「加完 scope 要重裝 app，token 會換一組新的」。
- **表的 schema 改不動。** 加欄位、加選項都回 `missing required field: id`，
  新元素的 id 只有 Slack 發得出來。要動欄位只能請使用者去 UI 改。
