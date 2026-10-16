---
name: daily-worklog
description: 從 git commit 產生給主管看的每日工作日誌（繁中）。當使用者說「寫日誌」「日報」「工作日誌」「把今天的 commit 整理給主管」「worklog」時使用。
---

# 每日工作日誌產生器

把一天的 git commit 翻譯成主管看得懂的工作日誌。

**這不是 `git log` 美化。** 主管不看 commit message，他看的是「做出了什麼、對誰有用、卡在哪」。
你的工作是翻譯，不是搬運。

---

## 🚫 先講會做壞的四件事

1. **只讀 `%s`（commit 標題）就開始寫** —— 標題只有 8 個字，寫出來的日誌會是
   「修好 tooltip」這種主管看不出價值的句子。真正的內容在 **commit body (`%b`)** 裡。
2. **拿 `gh search commits` 找當天的 commit** —— 它只索引預設分支，而當天的 commit 幾乎都在
   feature branch 上，**推上去了也搜不到**。gh 的正確用途是找出「動過哪些 repo」（步驟 2），
   內容一律回 local git 撈。這是實測過的。
3. **不加 `--all`** —— 站在 `main` 跑 `git log` 會漏掉一半以上的 commit。這是實測踩過的坑。
4. **git 沒有的東西自己編** —— 上班時間、開會、口頭討論、還沒 commit 的調查，git 全都看不到。
   **上班時間不要從 commit 推估**：使用者給的早上草稿有就用，沒有就留空讓他自己填。

---

## 📋 步驟

### 1. 決定範圍

- **早上草稿**：使用者可能貼一份上班時寫的草稿（步驟 8 的格式，下班時間空著）。
  有就從裡面取三樣東西，沒有就跳過這條：
  - `上班時間`：照抄。
  - `[項目]` 清單：全部保留，當天沒做事的也留空標題。
  - 既有子項：原文保留；預設不重排，步驟 8 只補 `✅` 或追加新行。使用者明確要求重分組時依步驟 8 調整分類。
- **日期**：用本地時間（`Asia/Taipei`）算，使用者沒說就是今天。日誌標題用這個日期。
- **兩個身分不一樣，不要混用**：
  - **git 的 author** 用名字做 substring 比對：`git config user.name` → 例 `henry`。
    同一個人可能有 `henry` / `henry5720` / GitHub noreply email 三種身分，
    用名字剛好三種都涵蓋，**用完整 email 會漏**。
  - **GitHub 的 login** 另外拿：`gh api user --jq .login` → 例 `henry5720`。events API 只認這個。
- **repo 範圍不要預設任何目錄。** 分兩層：gh 找出動過哪些 repo（步驟 2），
  local git 讀內容（步驟 4）。

### 2. 發現層：今天動過哪些 repo

```bash
LOGIN=$(gh api user --jq .login)
# created_at 是 UTC，台北 +8：本地 08-20 = 08-19T16:00Z ~ 08-20T16:00Z
gh api "users/$LOGIN/events?per_page=100" --jq '
  [ .[] | select(.type=="PushEvent")
        | select(.created_at >= "2026-08-19T16:00:00Z" and .created_at < "2026-08-20T16:00:00Z")
        | {repo: .repo.name, ref: .payload.ref} ] | unique'
```

實測（2026-08-20）回四個 repo，含 private repo 與 feature branch。其中 `henry5720/dotfiles`
根本不在 `~/code` 底下（本機是 `~/.local/share/chezmoi`）—— 這就是為什麼發現層要問 GitHub，
不要掃自己習慣的那個目錄。

這個來源有四個限制，先知道再用：

- **時間是 UTC。** 拿本地日期字串直接比對會回空陣列，凌晨的 commit 在 GitHub 上算前一天。
- **payload 沒有內容。** `payload.size`、`payload.commits` 都是 `null`，只拿得到 repo 和 branch，
  所以它只能當發現層。
- **只撈得到近期。** `per_page=100`，第 4 頁直接回 422（`pagination is limited`），
  大約 300 筆 / 90 天。要補更早的日誌走步驟 3 的 fallback。
- **未推的 commit 看不到。** 這是刻意的 —— 沒推的算還沒做完，不進當天日誌。
  真的要算，改走 fallback 掃本機。

### 3. 對到本機 clone

events 給的是 `owner/name`，要換成本機路徑。**用 remote URL 反查，不要用資料夾名字猜**
（`ShuChenAI/teamsync-frontend` 剛好同名是巧合，`henry5720/dotfiles` 的本機目錄叫 `chezmoi`）。

```bash
find "$HOME" -maxdepth 6 \
  \( -name node_modules -o -name .cache -o -name .npm -o -name .pnpm-store \
     -o -name .venv -o -name .nvm \) -prune -o -name .git -type d -print 2>/dev/null |
while read -r g; do
  d=${g%/.git}
  u=$(git -C "$d" remote get-url origin 2>/dev/null) || continue
  echo "$(echo "$u" | sed -E 's#\.git$##; s#.*[:/]([^/]+/[^/]+)$#\1#')  $d"
done
```

- ⚠️ **不要把 `.local` 加進 prune 清單。** `~/.local/share/chezmoi` 是 dotfiles repo，
  剪掉就漏掉那天所有 dotfiles 的工作（實測 2026-08-20 有 4 筆）。
- `-maxdepth 6` 抓到 28 個 repo，放到 10 只多一個工具的暫存 repo
  （`~/.local/share/orca/…/.tmp/plugins`），那是垃圾。
- 全掃 `$HOME` 再跑一輪 `git log` 是 2.8 秒。**不要為了省這 3 秒把範圍寫死成某個目錄** ——
  `~/code` 是某個人的習慣，不是這支 skill 的前提。
- **對不到的要講出來**：「`owner/name` 今天有 push，本機找不到 clone，這段沒進日誌」。
  不要靜靜跳過。

**gh 不能用時的 fallback**（離線、沒裝 gh、要補 90 天前的日誌）：同一段 `find`，
改成直接問每個 repo 有沒有當天的 commit。

```bash
DAY=2026-08-20; NEXT=2026-08-21; WHO=henry
find "$HOME" -maxdepth 6 \
  \( -name node_modules -o -name .cache -o -name .npm -o -name .pnpm-store \
     -o -name .venv -o -name .nvm \) -prune -o -name .git -type d -print 2>/dev/null |
while read -r g; do
  d=${g%/.git}
  n=$(git -C "$d" log --all --author="$WHO" --since="$DAY 00:00" --until="$NEXT 00:00" \
        --oneline 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && echo "$n  $d"
done
```

使用者要縮小範圍就在 prompt 裡講（「只看 `~/code`」），不要自己推斷，也不要拿當前 session 的
cwd 當範圍 —— 一天的工作常常散在 frontend + backend + 文件 + dotfiles，cwd 只是其中一個。

### 4. 抓出當天 commit 的完整內容

對步驟 2／3 撈到的每個 repo 抓完整內容，重點是 `%b`，不是只有 `%s`：

```bash
git -C <repo> log --all --author="$WHO" --since="$DAY 00:00" --until="$NEXT 00:00" \
  --reverse --date=format:"%H:%M" \
  --format="=== %h %ad%n%s%n%n%b%n"
```

搭配檔案異動規模（判斷「這件事有多大」用的）：

```bash
git -C <repo> log --all --author="$WHO" --since="$DAY 00:00" --until="$NEXT 00:00" \
  --no-merges --format="=== %h %s" --stat
```

### 5. 算出「提交數 / PR 數」

新格式**沒有**「N 筆提交 / M 個 PR」開頭句，PR 編號改附在每件事後面的括號裡。
所以這步的重點是撈 PR 編號；提交數只是自己判斷工作量用的，不寫進日誌。

```bash
# 提交數：排除 merge commit
git -C <repo> log --all --author="$WHO" --since="$DAY 00:00" --until="$NEXT 00:00" --no-merges --oneline | wc -l

# PR 數 + 編號：只看 merge commit
git -C <repo> log --all --author="$WHO" --since="$DAY 00:00" --until="$NEXT 00:00" --merges --format="%s"
# → "Merge pull request #1737 from ShuChenAI/fix/forms-table-header-align"
```

實測（2026-08-11）：14 個 commit = 10 筆提交 + 4 個 merge。

> merge commit 不算「做了幾件事」，但它是**唯一能拿到 PR 編號**的地方。
> 編號要對到正確的那件事：看 merge commit 的 branch 名（`fix/forms-table-header-align`）
> 對應到哪一組 commit。

### 6. 補 git 看不到的部分（有 `gh` 就一定要做）

```bash
# 你 review 別人的 PR —— 那不是自己的 commit，git 完全看不到
gh search prs --reviewed-by=@me --updated=$DAY

# commit body 沒交代清楚時，看 PR 描述和相關 issue
gh pr view 1737 --json title,body,files --jq '.title, .body'
gh issue list --author "@me" --state all --search "created:$DAY OR updated:$DAY"
```

**能查的就不要問使用者**（步驟 9 的清單因此少一條）。查完是空的，才在收尾時確認一次。

commit 有動到 ADR / 規格文件時，**直接讀那份 md** —— 設計決策的理由都在裡面，
比 commit body 更完整。

### 7. 翻譯成主管語言

這是整個流程的核心。逐條 commit 問自己：**「這件事修好之後，使用者少了什麼麻煩？」**

| 原始 commit | ❌ 搬運 | ✅ 翻譯 |
|---|---|---|
| `fix(chat/forms): tooltip for every truncated column header` | 修好表頭 tooltip | 長欄名被截斷時滑過去看完整名稱 —— 原本只有部分欄位有效（必填欄位名後面那顆紅星讓程式抓不到文字），現在必填／非必填 × 排序／批量編輯四種狀況行為一致，並補 4 項自動化測試 |
| `chore(config): untrack agent artifacts, ignore output dirs` | 清理 gitignore | 清掉 20 個被誤上傳到版控的一次性產物（PNG／Excel／報表，約 3.3MB），並補上忽略規則，避免下次又被帶進來 |
| `feat(review): 審核授權設定` | 新增審核授權功能 | 定案七項設計決定，並查證出三件會影響做法的事：現成權限畫面不能重用、後端沒有「改角色」動作、三個模組的授權畫面該共用的是零件不是整個畫面 |

翻譯守則：

- **一件事一行**：`[動詞] 一句白話`，工作項目底下不再展開細項。術語能換就換
  （「TanStack Query 快取失效」→「切換後資料沒更新」）。上表「✅ 翻譯」欄示範的是
  要找的資訊，寫進日誌時壓成一句。
- **動詞只用這組**，讓人一眼看出在做什麼：
  `[開發]` 新功能、`[調整]` 改既有行為或配合需求、`[修正]` bug、`[開會]`、
  `[review]` 看別人的 PR、`[文件]`、`[調查]` 還沒動手改的研究、`[整理]` 清理／重構。
  真的套不上才另用一個兩字動詞。
- **帶上實測數字**。commit body 裡的「錯位 0px」「1051 個檔案」「3.3MB」「4 項測試」
  是日誌最有說服力的部分，一定要撈出來。
- **不要每個 commit 一條**。同一件事的多個 commit 要合併成一條；
  順手改的 lint / format / rename 直接不寫。
- **卡住的、有風險的要寫出來**，寫在第四段用 ⚠️ 標。主管最怕的是事後才知道。
  例：「⚠️ 把權限發給職級 3 以下目前不會生效,缺口在後端(已開單 backend#902)」。

### 8. 排版輸出

日誌全文放進單一 `txt` code block，方便複製；說明與追問放在 block 外。
固定使用主管提供的骨架，直接貼進公司群組（標點沿用半角 `,` `;`，`)` 也照抄，不要「修正」成全角）：

```txt
日期：MM/DD
上班時間：HH:MM
下班時間：HH:MM
───────────────────
【一、今日工作內容與時間】
[<repo 名稱>]
〈<工作分類 A>〉
1. [<動詞>] <一句白話>✅
2. [<動詞>] <一句白話>

〈<工作分類 B>〉
1. [<動詞>] <一句白話>✅

[<另一個 repo 名稱>]
1. [<動詞>] <一句白話>✅

───────────────────
【二、當日新增工作事項】
1. [<動詞>] <一句白話>
───────────────────
【三、待辦事項】
1. [<動詞>] <跨日待辦，不標 ✅>
───────────────────
【四、進度更新回報】
1. <白話總結、已驗證數字或交付結果>
2. ⚠️ <需要主管知道的風險、限制或下一步>
```

範例（有給早上草稿：`[開發工具]` 當天沒事也保留，`3.` 是 git 撈到、草稿沒寫的）：

```txt
日期：10/12
上班時間：09:51
下班時間：18:42
───────────────────
【一、今日工作內容與時間】
[開發工具]

[teamsync-frontend]
1. [開會] 跟客戶開會釐清需求✅
2. [調整] 根據後端 api contract 改前端✅
3. [修正] 匯出 Excel 欄位順序錯亂✅

───────────────────
【二、當日新增工作事項】
無
```

各段各有用途，不要混：

| 段落 | 內容 | 語氣 |
|---|---|---|
| 一 | 今天的工作 | repo → 可選工作分類 → 編號工作；完成的行尾標 `✅` |
| 二 | 今天新增、調整或結案的工作 | 同上格式；沒有就寫「無」 |
| 三 | 尚未完成、需跨日追蹤的工作 | 照 backlog 原分類與文字列出；不標 `✅`；沒有就寫「無」 |
| 四 | 給主管的結果與風險 | 一到三條，帶實測數字；風險用 `⚠️`；沒有就寫「無」 |

#### repo 與工作分類

- **第一層 `[repo 名稱]`**：用 remote 的 `name`；有早上草稿時沿用草稿的項目名稱。
- **第二層 `〈工作分類〉`**：repo 當天有兩個以上不同工作主題時，依主題分組；只有一個主題時直接列工作。
  工作分類是讓主管分辨工作主題的標題，可以是產品模組、功能、流程或工具設定，不限定為程式碼模組，也適用所有 repo。
  每個工作分類從 1 重新編號；沒有第二層時，每個 repo 從 1 開始。
- **分類名稱與歸屬**：先用使用者指定的名稱，其次查 repo 文件、PR 或 commit 的明確主題；無法確認時留在 repo 層。
  repo 層的未分類工作先列，再列工作分類；不為湊分類猜名稱。
- **跨分類工作只列一次**：歸入能說明用途的共用分類，句子交代影響範圍；各分類自己的串接工作仍可分別列出。
- **套用段落**：第一段依上述規則分組；第二、三段有多個主題時也可分組，但既有 backlog 的分類與文字照抄。
  第四段維持一到三條結果與風險摘要。

例如同一 repo 同時調整安裝與工具設定，共用的錯誤提示只列一次（以下為假資料）：

```txt
[example-tools]
〈安裝流程〉
1. [調整] 安裝前先列出將新增的工具✅

〈工具設定〉
1. [修正] 重新開啟時保留使用者選擇✅

〈共用錯誤提示〉
1. [調整] 統一安裝與工具設定失敗時的重試說明✅

[example-docs]
1. [文件] 補上首次使用說明✅
```

#### 草稿與其他格式規則

- **對到草稿的規則**：預設保留草稿的標題、文字與順序；只有使用者明確要求重分組時，
  才依上述分類規則調整標題、位置與編號，既有工作原句與完成標記保留。
  - git 有證據完成草稿上的某一行 → 該行行尾補 `✅`，文字不動。
  - 做了草稿沒寫的事 → 在對應的既有分類或 repo 最後追加一行，編號接續；保留草稿時不擅自新建第二層。
  - repo 不在草稿的項目裡 → 新增一個 `[repo 名稱]`，並在回覆裡另外講一句「這個不在你早上的清單」。
  - 草稿上沒 `✅`、git 也沒證據的行 → 照原樣保留，**不要自己打 `✅`**（開會之類 git 看不到的，由使用者自己標）。
- **完成標記**：`✅` 緊貼行尾，不加空格；只標工作項目，不標 repo 或工作分類標題。
- **白話優先**：子項不寫 commit type、PR 編號、函式名或框架名稱。
- **時間欄位**：
  - 上班時間：早上草稿有就照抄，沒有就留 `上班時間：` 空白讓使用者填。**不要從 commit 推估。**
  - 下班時間：用產生日誌當下的本地時間 `TZ=Asia/Taipei date +%H:%M`；早上草稿已填就照抄。
  - 主管若要求逐項耗時，要問使用者；commit 的時間只可作為內部排序證據。
- **第二段只寫有證據的新工作**：今天建立／更新的 issue、使用者提供的新增事項，或明確記錄的後續工作。不要把推測的下一步編成待辦。
- **第四段要說結果**：優先寫測試數字、已解決的使用者問題與已知限制；`⚠️` 只用在主管需要知道的風險。
- **跨日待辦照抄**：來源是 backlog 檔（見下面「產出放哪」）；只把今天完成的項目移出第三段並更新 backlog，不要每天重編。

### 9. 收尾一定要問

git 和 gh 都抓不到、**必須跟使用者確認**的（時間欄位不在這裡，照步驟 8 的規則填）：

- 有沒有開會、教育訓練、支援別人 debug
- 有沒有「今天想了很久但還沒 commit」的調查
- 有沒有不想寫進日誌的內容
- backlog 檔裡的待辦有沒有增減（有就一起改檔案）

先送出日誌，再把這幾題一次問完；使用者補了就改稿重送。
唯一允許空著的欄位是沒有早上草稿時的上班時間。

---

## 💾 產出放哪

**日報／週報本身不存檔**，直接把日誌放在對話的單一 `txt` code block 讓使用者複製。
它的唯一讀者是公司表單，貼完就沒人回頭讀；而 `work-docs`、`agent-config` 兩個 repo 都是
**public**（`gh repo view` 確認過，work-docs 還開了 GitHub Pages），把模組名、PR 編號、
內部進度寫進去等於公開發佈。

使用者明講要存檔才存，兩個條件：預設路徑在 `~/.claude/`（不是任何 git repo），
而且寫之前先講一句「這裡面有模組名和內部進度」。使用者自己指定路徑就照他的，
但那個路徑落在 git repo 裡時要先問一次。

週報同理，只是範圍從一天拉成一週，多做兩件事：
開頭加**一句話總結**，結尾加**時間分佈表**（依 repo / 模組估工時）。

唯一固定要落地的是**跨日進度清單**（步驟 8 的第三段來源），因為 git 產不出來：

```
~/.claude/worklog-backlog.md      # 預設；使用者指定別的就用他給的
```

- 選這個預設的原因：`~/.claude` 不是 git repo，不會被推上公開 remote，
  而且不管在哪個 repo 底下叫這支 skill，路徑都一樣。
- 格式就照工作項目列，一個模組一段；已完成項目保留並標 `✅`：

  ```markdown
  [審核模組] 切版+功能+串接api
  - 審核流程設定
  - 審核中心✅
  - 群組標籤✅
  - 建表 Step3✅
  - 表格設定·審核
  ```

- 寫日誌時**只取未完成項目**填進第三段；定稿後把今天完成的項目標 `✅` 寫回去。
- 檔案不存在就問使用者這次有哪些待辦，順手建起來；不要自己生子項。

---

## 🕳️ 已知陷阱

| 陷阱 | 症狀 | 解法 |
|---|---|---|
| 用 `gh search commits` 找 commit | 明明推了卻搜不到，或撈到同名的別人 | 它只索引預設分支，`author:` 也對不到未連結的 email。發現層用 events，內容用 local git |
| 拿本地日期比對 events 的 `created_at` | 回空陣列 | events 是 UTC，本地日界要換算（台北 −8 小時） |
| prune 掉 `.local` | 漏掉 dotfiles（chezmoi）那天所有工作 | prune 清單只放 `node_modules` `.cache` `.npm` `.pnpm-store` `.venv` `.nvm` |
| 拿 cwd 或 `~/code` 當掃描範圍 | 漏掉後端 / 文件 / dotfiles repo | 發現層問 gh；fallback 掃 `$HOME`，要縮小範圍讓使用者講 |
| 沒加 `--all` | commit 數量明顯偏少 | 一律加 `--all` |
| 用 email 當 `--author` | 漏掉 GitHub noreply 身分的 commit | 用名字做 substring 比對 |
| 把 merge commit 算進提交數 | 數字虛胖 | 提交數用 `--no-merges`，PR 用 `--merges` |
| 只讀 `%s` | 日誌乾癟、沒有數字 | 一律撈 `%b` |
| 跨午夜的 commit | 邊界抓錯 | `--since`／`--until` 是本地時間；深夜 commit 先問使用者算哪一天 |
| commit body 是英文 | 日誌混語言 | 工作項目與分類用繁中；第一層用 repo 原名，技術名詞保留英文 |
| 從 commit 時間推上班時間 | 主管看到的時間跟打卡對不上 | 早上草稿有就照抄，沒有就留空 |
| 改寫早上草稿的子項 | 使用者對不出自己早上寫的那行 | 草稿原文不動，只補 `✅` 或追加新行 |
| 自己編待辦子項 | 清單每天長不一樣，主管對不上 | 讀進度清單，只更新 ✅ |
| 把日誌存進 repo | 內部進度被推到 public repo | 日誌只輸出文字，使用者明講才落檔 |
