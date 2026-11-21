---
name: writing-for-humans
description: 寫給人看的文件：README、`docs/` 裡的工具文件、情境文件、說明。新增、改寫、搬動這些檔，或決定一段內容該放 README、`docs/`、`AGENTS.md`、skill 哪裡時使用。
---

# 寫給人看的文件

repo 的 `AGENTS.md` 對文件另有規定時，照 repo 的；這支只補 repo 沒寫的部分。來源：[agents.md FAQ](https://agents.md/#faq)（指引衝突時，離被改的檔最近的 `AGENTS.md` 優先）。

## 先分讀者

- 每次都要遵守的 agent 規則寫 repo 的 `AGENTS.md`，重複的流程寫成 skill，連外部系統用 MCP，一定要發生的用 hook；agent 讀的文件照 `writing-for-agents` 寫。來源：[agents.md](https://agents.md/)、[Claude Code features overview](https://code.claude.com/docs/en/features-overview)、[Codex customization](https://learn.chatgpt.com/docs/customization/overview)。
- 人和 agent 照同一份操作文件做時，只寫一份：人看的文件放步驟，`AGENTS.md` 或 skill 連過去。來源：[agents.md](https://agents.md/)（README 給人、`AGENTS.md` 只放 agent 額外需要的）。

## README

- README 只放四樣：是什麼和為什麼、安裝、裝完之後去哪、文件索引。結尾一行指向結構說明（例如 `docs/architecture.md`）和 `AGENTS.md`。其餘細節放 `docs/`，由索引連過去。來源：[GitHub About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)。

## `docs/` 的三種文件

一份文件只當一種。寫到一半發現在寫另一種，拆成兩份互連。來源：[Diátaxis](https://diataxis.fr/)。

- **工具文件（reference）**：一個工具一份，結構跟著工具走。來源：[Diátaxis reference](https://diataxis.fr/reference/)（reference 照產品本身的結構寫）。
  - 只寫 `--help` 和官網找不到的：這個 repo 為什麼這樣裝或這樣設、少用但要記的指令、踩過的坑。固定四段：為什麼裝、常用指令、坑、更多（連官網），沒內容的段省略。〈坑〉每條寫症狀、原因、解法、實測日期。來源：本 repo 和 dotfiles 的自訂慣例，見 [henry5720/dotfiles#366](https://github.com/henry5720/dotfiles/issues/366)。
- **情境文件（how-to）**：以要完成的一件事組織，可以跨好幾個工具，寫成照做的步驟和怎麼確認做好了。來源：[Diátaxis how-to guides](https://diataxis.fr/how-to-guides/)。
- **說明（explanation）**：為什麼是這個結構、取捨、背景，例如目錄樹和設定檔的來歷。不放操作步驟。來源：[Diátaxis explanation](https://diataxis.fr/explanation/)。
- 工具的通用用法連官方文件；設定檔的註解就是它的文件，不另寫一份。來源：自訂慣例，沒有外部出處。

## 交給別支 skill

- 要畫圖或決定用表格、縮排樹時，讀 `show-me` 的 SKILL.md 照它畫（它設了 `disable-model-invocation`，agent 不能用 Skill tool 叫）。來源：[humanlayer/skills 的 show-me](https://github.com/humanlayer/skills/tree/main/plugins/show-me/skills/show-me)。
- 改用詞、去掉空話時，照 `humanizer-zh`。來源：[op7418/humanizer-zh](https://github.com/op7418/humanizer-zh)。
