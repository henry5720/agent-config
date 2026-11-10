---
name: pms-tracking
description: 在 PMS 開、更新給 PM 看的追蹤單，讓 PM 不用看 GitHub 也能掌握進度。使用者說「同步進度到 PMS」「PMS 開單／開追蹤單」「更新 PMS 進度」「問題轉工作」時使用；從 Slack 待辦或 GitHub map 開單、需要在 PMS 留一份給 PM 看時也用。
---

# PMS 追蹤單

**追蹤單**是 PM 在 PMS 上看進度的那一張：用白話列出大項目，完成一項就打勾。內容的權威在 GitHub（map 或 issue），PMS 只放給 PM 看的摘要，並附上 GitHub 連結。

## 連線

- 用 `pms` MCP；專案追蹤、自己的子任務與工時共用這個連線。
- 這個 session 載不到 PMS 工具時（`ToolSearch` 找不到），就用 headless 跑：

  ```bash
  claude -p --allowedTools 'mcp__pms' < prompt.txt
  ```

  - prompt 從 stdin 傳。`--allowedTools` 會把後面的參數全部吃掉，所以 prompt 不能直接接在後面。
  - 寫入的 prompt 要寫死 `clientMutationId`（UUIDv4），並要求它讀回驗證、回報 id 和 version。
  - 先跑一次唯讀的，確認專案、權限和現有的單。

## 步驟

1. **找專案與權限**：用 `get_my_context` 確認身分與 capabilities，再用專案名稱找到 `projectId`。名稱對不上時列出候選，不要自己猜 ID。
2. **找現有追蹤單**：先看 GitHub 端有沒有「PM 追蹤」那行連結（map 寫在 Notes）。沒有的話，在專案裡依標題找。找到就走步驟 4，否則走步驟 3。
3. **建立**，依權限擇一：
   - 有 `project:work.create`：建**工作**，大項目放 checklist（`set_checklist`）。
   - 沒有：建**問題**（`manage_project_issues` report），大項目放描述。描述**只有建立時寫得進去**：問題的負責人只能改狀態和處理時間（2026-11-03 改描述回 forbidden「問題負責人只能更新狀態與處理時間」）。所以之後的變動都在問題底下留言（`manage_project_discussions` post，targetType=issue），描述開頭也要寫明「新增、完成的項目會在留言補上」。
   - 有些專案會拒絕開問題（回 forbidden「此專案為唯讀」）。這時改發專案留言（targetType=project），之後用 `edit_own` 更新那則留言。
4. **更新進度**：拿 GitHub 端的實際狀態（已關的票、已 merge 的 PR）對照追蹤單，兩個方向都要查：
   - 追蹤單上的每一項：狀態有沒有變。
   - GitHub 上每張還開著或剛關掉的票：追蹤單上有沒有對應的項目。沒有的列出來，問使用者要不要補。

   只改有變動的項目。工作改 checklist；問題就在問題底下留一則留言，寫這次新增或完成了哪些項目。
5. **問題轉工作**：手上只有問題、但現在有 `work.create` 了，就照問題內容建工作，再把問題的 `linkedTaskId` 設成新的工作，問題改 `resolved`。
6. **兩邊互連**：
   - PMS 單的開頭附 GitHub 連結。
   - GitHub 端加一行「PM 追蹤」，連到 PMS 單，網址格式：
     `https://pms.teamsync.com.tw/c/<tenant>/app?section=projects&project=<projectId>&issue=<issueId>&panel=fields`
     工作的話，把 `issue=<id>` 換成 `work=<id>`。
7. **讀回驗證**：標題、內容的頭尾、負責人、兩邊的連結都要對上才算完成。headless 的回報要寫出它讀回了哪些欄位。

**完成條件**：PMS 單和 GitHub 一致，兩邊互相連到，而且有讀回的證據。

## 寫法（給 PM 看）

- **開頭兩三句**：這件事在解決什麼、時程，再附 GitHub 連結。
- **依範圍分組**：`【規劃與決策】`、`[<repo>]（一句話說明它是什麼）`、`[<模組>]`。PM 不知道 repo 名稱代表什麼，所以每組都要補那句說明。
- **一項一行**：`<n>. [<動作>] <一句白話>`，做完的在行尾加 ✅。術語換成白話，例如「SSRF 檢查」寫成「地端打回本站會被擋」。
- **動作只用這組**：
  - `[調查]`：研究、查證，還沒動手做
  - `[決策]`：定案一個做法
  - `[設計]`：設計資料表、規則、權限、流程
  - `[開發]`：新功能
  - `[調整]`：改既有行為，或配合需求修改
  - `[修正]`：bug
  - `[開會]`：會議、試點
  - `[文件]`：文件
- **研究、決策、設計也要分開列**：讓人看得出哪些是判斷和設計的工作，不是只有寫程式。
- **結尾寫 `【風險】`**：每條開頭加 ⚠️，寫會影響時程、需要別人協助的事。
