# agent-config

[skillshare](https://github.com/runkids/skillshare) 的設定目錄（`~/.config/skillshare`）。三台機器的
Claude Code、Codex、OpenCode、pi 共用同一份全域規則、skills、MCP 和 hook，改一次全部跟著動。
dotfiles（chezmoi）負責裝 skillshare 和各 client 的設定，這個 repo 負責 client 要讀的內容。

## 安裝

照 dotfiles 的 [new-machine-setup.md](https://github.com/henry5720/dotfiles/blob/main/docs/new-machine-setup.md) 做：
它會裝 skillshare、clone 這個 repo、放好 `config.yaml`。規則、skill、MCP、plugin 各歸誰管看 dotfiles 的
[architecture.md](https://github.com/henry5720/dotfiles/blob/main/docs/architecture.md)。

## 裝完之後去哪

- 裝、更新、同步 skill 和 MCP：[skillshare 官方文件](https://skillshare.runkids.cc)。
- 這台改完怎麼推、其他台怎麼跟上：[docs/skills/〈跨機器〉](docs/skills/README.md#跨機器)。
- 詞彙（source、target、local…）：[GLOSSARY.md](GLOSSARY.md)。

## 文件索引

- [docs/skills/](docs/skills/README.md)：skill 從哪來、裝給誰、怎麼選、怎麼關，以及要自己動手的 skill 的說明。
- [docs/mcp/](docs/mcp/README.md)：四個 client 怎麼共用 MCP、API key、sync 衝突、Graphify。
- [docs/hooks/](docs/hooks/README.md)：自己寫的 hook 怎麼 add、edit，Codex 要設 trusted。

改這個 repo：結構看 [docs/architecture.md](docs/architecture.md)，規則看 [AGENTS.md](AGENTS.md)。
