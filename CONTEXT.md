# agent-config

三台機器共用的 AI agent skills 與 MCP。這份只是詞彙表。

## Language

**Source**:
這個 repo 裡的 `skills/` 與 `mcp.yaml`，所有機器上 skill 和 MCP 的唯一來源。
_Avoid_: 本機 skill

**Target**:
skillshare 把 skill 同步過去的 client 目錄。現在有兩個：`claude`（`~/.claude/skills`）和 `codex`（`~/.agents/skills`）。
_Avoid_: client

**Client**:
實際讀 skill、呼叫 MCP 的程式：Claude Code、Codex、OpenCode。OpenCode 是 client，但不是 target。

**Local skill**:
target 目錄裡不是 skillshare 放進去的條目，例如 herdr、obsidian-wiki 自己連的。這是 `skillshare status` 的用語，不代表錯誤。
_Avoid_: 自己寫的 skill

**Own skill**:
自己寫、直接放在 `skills/<名字>/` 的 skill，`.metadata.json` 裡沒有它。
_Avoid_: local skill、personal skill

**Third-party skill**:
用 `skillshare install` 從別人的 repo 裝進來的 skill，來源記在 `skills/.metadata.json`。`update --all` 會覆蓋它。

**Sync**:
把 source 的 skill 以 symlink 放進各 target（`skillshare sync`）。只處理 skill，不處理 MCP。

**MCP sync**:
把 `mcp.yaml` 的 server 寫進各 client 的原生設定檔（`skillshare sync mcp -g`），只動 skillshare 自己寫的條目。`pull` 不會做這一步。

## Relationships

- 一個 **Source** 會 **Sync** 到多個 **Target**
- 一個 **Client** 可以讀多個 **Target**（OpenCode 同時讀兩個）
- **Own skill** 和 **Third-party skill** 都在 **Source** 裡；**Local skill** 只在 **Target** 裡

## Flagged ambiguities

- 「local」在 skillshare 是「不是它放的」，不是「自己寫的」。自己寫的一律叫 **Own skill**。
- 「sync」單講只指 skill。要寫進 client 的 MCP，一定講 **MCP sync**。
