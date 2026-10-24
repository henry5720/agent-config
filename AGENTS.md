# AGENTS.md

這是 skillshare 的設定目錄，也是 git repo（`henry5720/agent-config`）。文件、註解、commit message
用繁體中文。操作方式見 [README.md](README.md)，詞彙見 [GLOSSARY.md](GLOSSARY.md)。

## 規則

- **公開 repo，秘密不進來。** MCP 的 key 用 `fromEnv`；skill 的 token 放 `~/.config/<skill>/.env`，
  repo 只留 `.env.example`。公司的 Slack ID、URL 用佔位值（`U0123456789`、`<workspace>`）。
- **不要 commit `config.yaml`。** skillshare 會自動 ignore，也會在 push 時拿掉；它由 dotfiles 的
  chezmoi 管。
- **第三方 skill 不要手改。** 看 `skills/.metadata.json` 有沒有那支：有就是第三方，`update --all`
  會蓋掉。要改就另存成自己的 skill。
- **新增 skill 或 MCP 用 skillshare 指令，不要手寫 `.metadata.json`。** `install` 會記來源，
  `mcp add` 會寫 `mcp.yaml`。
- **skill 資料夾裡不放 README。** skill 資料夾會被 sync 到各 client；給人看的寫
  `docs/skills/<名字>.md`，只有人要自己動手（跑 script、設定、排錯）的 skill 才寫。
  第三方 skill 帶來的 README 不動。
- **不要加 OpenCode target。** OpenCode 會讀 `~/.claude/skills` 和 `~/.agents/skills`，加了會
  同一支出現三次。

## 放哪

該用哪種機制照全域規則開頭那句（細節看官方）。決定後，在這個 repo 放：

| 機制 | 放哪 |
|---|---|
| 全域規則 | `instructions/agents-md/AGENTS.md`；chezmoi 連到 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.config/opencode/AGENTS.md` |
| skill | `skills/<名字>/`；補第三方 skill 沒寫的步驟也是另寫一支 |
| MCP | `skillshare mcp add`，寫進 `mcp.yaml` |
| hook | dotfiles（chezmoi 管 `settings.json`） |

## 改完怎麼驗證

```bash
uv run --isolated --no-project --with-requirements tests/requirements.txt \
  python3 -B -m unittest discover -s tests  # 動到自己寫的 skill 的 script 時
skillshare sync --dry-run               # skill 會怎麼落到 target
skillshare sync mcp -g --dry-run        # MCP 會怎麼寫進三個 client
```

驗完用 `skillshare push` 推（它會 commit 再 push）。其他機器 `skillshare pull && skillshare sync mcp -g`。
