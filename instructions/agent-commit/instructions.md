# Commit 共同作者

誰改的誰 commit：每顆 commit 只標下這顆 commit 的 agent。只記工具身分，model、effort 與用量交給其他工具。

## 身分

- Claude Code：`Co-authored-by: Claude Code <noreply@anthropic.com>`
- Codex：`Co-authored-by: Codex <noreply@openai.com>`
- OpenCode：`Generated with OpenCode.`（正文標記；目前沒有已確認的官方共同作者 email）
- 其他 agent：沿用該工具已確認的 attribution；email 未確認時使用正文文字標記。

## 提交

1. 保留主要作者與既有 trailers、其他工具的標記。共同作者放尾端 trailer 區塊，正文標記放區塊前。
2. 加上自己的標記，恰好一次。
3. 提交後用 `git show -s --format=%B HEAD` 確認；缺少或重複時修正剛建立的 commit，確認後才回報完成。

採用其他 agent 的修改時，讓它自己 commit 那部分。
