# agent-config

三台機器共用的 AI agent skills、MCP 與 agent instructions。這份只是詞彙表。

## Language

**Source**:
這個 repo 裡的 `skills/`、`mcp.yaml` 與 `instructions/`，所有機器上 skill、MCP 和 **Instructions** 的唯一來源。
_Avoid_: 本機 skill

**Target**:
skillshare 把 skill 同步過去的 client 目錄。現在有兩個：`claude`（`~/.claude/skills`）和 `codex`（`~/.agents/skills`）。
_Avoid_: client

**Client**:
實際讀 skill、呼叫 MCP 的程式：Claude Code、Codex、OpenCode。OpenCode 是 client，但不是 target。

**Local skill**:
target 目錄裡不是 skillshare 放進去的條目，例如 obsidian-wiki 自己連的。這是 `skillshare status` 的用語，不代表錯誤。
_Avoid_: 自己寫的 skill

**Own skill**:
自己寫、直接放在 `skills/<名字>/` 的 skill，`.metadata.json` 裡沒有它。
_Avoid_: local skill、personal skill

**Third-party skill**:
用 `skillshare install` 從別人的 repo 裝進來的 skill，來源記在 `skills/.metadata.json`。`update --all` 會覆蓋它。

**Instructions**:
給模型讀的指令文字，每台機器都一樣，例如全域 `AGENTS.md`（Claude 那邊叫 `CLAUDE.md`）與 commit 指引。內容在這個 repo 的 `instructions/<名字>/`，由 skillshare 的 **Extras sync** 連到各 client 讀的位置；連到哪寫在 `config.yaml` 的 `extras` 段，由 dotfiles 的 chezmoi 釘（決策見 [ADR 0003](https://github.com/henry5720/dotfiles/blob/main/docs/adr/0003-agent-instructions-linked-by-skillshare-extras.md)）。
_Avoid_: 設定、rules

**Settings**:
給程式讀的設定：依機器不同、要合併進 app 自己會改寫的檔案，或是安裝腳本，例如 `settings.json`、`config.toml`、`opencode.json`、skillshare 自己的 `config.yaml`。由 dotfiles 的 chezmoi 管，不放這個 repo；`mcp.yaml` 是例外，由 **MCP sync** 寫進各 client。
_Avoid_: 指令、instructions

**Agent**:
skillshare 的 native agent，也就是一個 subagent 定義檔（`agents/<名字>.md`），由主 agent 派工時才載入。目前沒有使用；要用時先在 target 加上 `agents` 路徑。
_Avoid_: 用來指 `AGENTS.md`（那是 **Instructions**）

**Sync**:
把 source 的 skill 以 symlink 放進各 target（`skillshare sync`）。不處理 MCP 與 **Instructions**；`skillshare sync --all` 會連 **MCP sync**、**Extras sync** 一起做。

**MCP sync**:
把 `mcp.yaml` 的 server 寫進各 client 的原生設定檔（`skillshare sync mcp -g`），只動 skillshare 自己寫的條目。`pull` 不會做這一步。

**Extras sync**:
把 **Instructions** 以 symlink 連到各 client 讀的位置（`skillshare sync extras`），照 `config.yaml` 的 `extras` 段。dotfiles 的 `chezmoi apply` 改到 extras 段時會自動跑。

## Relationships

- 一個 **Source** 會 **Sync** 到多個 **Target**
- **Instructions** 的內容在 **Source** 裡，由 **Extras sync** 連到各 client；連到哪由 chezmoi 釘在 `config.yaml`；**Settings** 在 chezmoi
- 一個 **Client** 可以讀多個 **Target**（OpenCode 同時讀兩個）
- **Own skill** 和 **Third-party skill** 都在 **Source** 裡；**Local skill** 只在 **Target** 裡

## Flagged ambiguities

- 「local」在 skillshare 是「不是它放的」，不是「自己寫的」。自己寫的一律叫 **Own skill**。
- 「sync」單講指 skill 的 symlink，不含 MCP 與 **Instructions**；要寫進 client 的 MCP，一定講 **MCP sync**，連指令檔講 **Extras sync**。注意 `skillshare sync` 這個指令不帶子指令時只同步 skill。

## PR 收尾詞彙

**PR 自審與驗收（PR review and verification）**:
作者處理自己 PR 的自審、修正、驗證與回報；既有決策中的「PR 收尾」指同一段流程，merge 由人操作。
_Avoid_: 把本輪完成當成已獲准 merge

**收尾一輪（Closing round）**:
從一次啟動到本輪完成或受阻回報的一段工作。新 review 可啟動下一輪。

**入口 skill（Entry skill）**:
提供作者自審與驗收整輪流程的指引，讓 agent 按條件接續各支 skill。

**自審 report（Self-review report）**:
作者自審後對問題、影響及程式碼位置的紀錄；不是修正與驗證已完成的結論。

**收尾結果（Closing result）**:
一輪工作的處理結果、驗證證據、未驗項目與仍待處理事項。

**未驗（Unverified）**:
與驗證目的相關、尚未執行或未涵蓋的項目及原因。
