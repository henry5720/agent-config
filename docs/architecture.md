# 結構

這個 repo 就是 skillshare 的設定目錄 `~/.config/skillshare`，整個目錄進版控（`git_root: root`）。
skillshare 的通用用法看[官方文件](https://skillshare.runkids.cc)，這份只講這個 repo 為什麼長這樣。

## 目錄樹

```text
extras/<名字>/         給模型讀的指令檔（全域規則、commit 指引），由 extras 連到各 client
mcp.yaml              三個 client 共用的 MCP server
hooks/<名字>.yaml      自己寫的 hook（skillshare 的 hook entry），每台各自 add
docs/                 給人看的文件
  skills/             skill：從哪來、裝給誰、怎麼選、怎麼關；要自己動手的 skill 各有一份
  mcp/                MCP：三個 client 怎麼共用、key、衝突、Graphify
  hooks/              hook：add、edit、Codex trusted
  research/           研究紀錄
skills/
  .metadata.json      第三方 skill 從哪裝、哪個 commit（update --all 讀它）
  <名字>/SKILL.md     自己寫的 + 第三方裝進來的，都在這層
  <名字>/scripts/     skill 要呼叫的 script 跟 skill 放一起，裝 skill 就裝到 script
tests/                自己寫的 skill 的 script 測試
```

## config.yaml 為什麼不在 repo 裡

skillshare 的 root 模式會自動 ignore `config.yaml`，`push` 時就算 commit 了也會被拿出來，因為它寫的是
這台機器的路徑。所以由 dotfiles 用 chezmoi 放（`modify_config.yaml.tmpl`）：新機器給整份基底，之後每次
apply 只釘 `targets` 和 `extras` 兩段，其餘照 skillshare 寫的留著。以後要不同機器不同配置，改那份就好。

hook 和 plugin 也存在 `config.yaml`，所以每台要各自 add（hook 見 [hooks/](hooks/README.md)）。

## extras 連到哪

`extras/` 底下每個資料夾是一個 extra，skillshare 把裡面的檔連到各 client 讀的位置：

| extra | 連到 |
|---|---|
| `agents-md`（全域規則） | `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.config/opencode/AGENTS.md` |
| `agent-commit` | `~/.config/agent-commit/instructions.md` |
| `opencode-commit` | `~/.config/opencode/commit-instructions.md` |
| `pstack-models`（pstack 每個角色用哪個模型） | `~/.claude/rules/pstack-models.md`；只給 Claude，官方 pstack 只支援 Cursor 和 Claude Code。要改就重跑 `/pstack:setup-pstack`，它會寫回這個檔 |

連到哪由 dotfiles 釘，照那台勾了哪些 client 產生，所以每次 `chezmoi apply` 都會把連結蓋回 dotfiles 寫的樣子；
要加連結怎麼做見 [AGENTS.md〈放哪〉](../AGENTS.md#放哪)。

## 全域規則的維護

全域規則每個 session 都會載入，只寫換到任何一個 repo 都還成立的事；只在特定任務用到的流程寫成 skill，
全域留一行什麼時候載入。

`<!-- CODEGRAPH_START -->` 到 `<!-- CODEGRAPH_END -->` 之間是 `codegraph install` 自己寫進
`~/.claude/CLAUDE.md` 的段落，`codegraph upgrade` 會重寫兩個標記之間的內容。所以：

- 收進這份檔，不然 codegraph 沒地方告訴 agent 要用它。
- 保留英文原文和兩個標記，不翻譯、不手改；改了下次升級就被蓋回去。
- 說明寫在這裡，不寫成全域規則裡的 HTML 註解：Claude 會拿掉 HTML 註解，Codex、OpenCode 會原樣送進
  context（見[研究紀錄](research/agent-instructions-best-practices.md)）。
