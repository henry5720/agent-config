---
name: pms-workflow
description: PMS 的個人用法：開、更新給 PM 看的追蹤單（「PMS 開單」「同步進度到 PMS」「問題轉工作」）；打卡（上班卡、下班匯總、補打卡）。
---

# PMS 的個人用法

`pms` MCP 提供功能，規則看它的工具說明；這份只寫使用者的流程和實際踩過的雷。

- 開、更新**追蹤單**，或把問題轉成工作：讀 [tracking.md](tracking.md)。
- **打卡**（上班卡、下班匯總、補打卡）：讀 [punch.md](punch.md)。

## 連線

- 用 `pms` MCP；追蹤單、打卡、自己的子任務與工時共用這個連線。
- 這個 session 載不到 PMS 工具時（`ToolSearch` 找不到），就用 headless 跑：

  ```bash
  claude -p --allowedTools 'mcp__pms' < prompt.txt
  ```

  - prompt 從 stdin 傳。`--allowedTools` 會把後面的參數全部吃掉，所以 prompt 不能直接接在後面。
  - 寫入的 prompt 要寫死 `clientMutationId`（UUIDv4），並要求它讀回驗證、回報 id 和 version。
  - 先跑一次唯讀的，確認專案、權限和現有的單。

## 找目標

寫入前用名稱查出真實的 id 和目前 version：專案用 `get_my_context` 和專案名稱，工作用 `query_project`
（operation=work，帶 `projectId` 和 `query`）。名稱對不上時列出候選給使用者選，id 一律從查詢結果抄。
