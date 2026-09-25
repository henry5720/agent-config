---
name: company-imagegen
description: 透過公司既有受限 runtime command 或 MCP 產生圖片 artifact；接受文字、圖片或音訊輸入，PNG 預設，只有明確要求才產生 self-contained HTML。
---

# Company image generation

這支 skill 是公司圖片產生能力的使用規則，不是新 gateway 或 API 的規格。

## 輸入與輸出

- 接受使用者提供的 text、image 或 audio input；先保留來源與用途，再交給既有 runtime。
- 輸出預設是 **PNG**。使用者沒有明確要求 HTML 時，不要產生 HTML。
- 只有使用者明確要求時，才輸出 **self-contained HTML**；HTML 必須能獨立開啟，並清楚標示
  它不是預設輸出。
- 若使用者明確要求 Markdown 說明，另外輸出 Markdown；不要拿 Markdown 取代 PNG。
- 不添加未被要求的格式，不把 runtime 的暫存檔當成已交付 artifact。

## Runtime 邊界

1. 只檢查並呼叫 deployment 已提供的受限 runtime command 或 MCP。以當前 container 的工具
   描述、環境文件或 MCP schema 為準。
2. 不在 skill 裡放 key、token、secret、credential 或任何 secret 的預設值。
3. 不發明 gateway HTTP URL、endpoint、header、payload 或 retry protocol；找不到既有受限
   command/MCP 時，明確回報「runtime 未提供」，不要自行用 HTTP 代替。
4. 只把 runtime 回傳的檔案視為輸出，保留它的錯誤與限制；不要宣稱沒有跑過的生成成功。

## Slack 交付

若這次工作來自 Slack，PNG、Markdown 或使用者明確要求的 self-contained HTML 要回到**原生
item thread**。使用 `slack-list artifact` 的 `record_id` 入口，讓工具從 List 查回原 thread
與 channel；remote 呼叫要加 `--remote`，HTML 再加 `--html`。不要自行指定別的
channel/thread，也不要另開 broker 或新的討論串。

若 deployment 沒有 Slack runtime context（至少要能辨識原 record/thread），可以產生 local
artifact，但必須在回報中說明「無法保證回原 thread」，不能把 local 路徑說成 Slack 已交付。
