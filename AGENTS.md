# AGENTS.md

這是 skillshare 的設定目錄，也是 git repo（`henry5720/agent-config`）。文件、註解、commit message
用繁體中文。文件入口見 [README.md](README.md)，詞彙見 [GLOSSARY.md](GLOSSARY.md)。

## 規則

- **公開 repo，秘密不進來。** MCP 的 key 用 `fromEnv`；skill 的 token 放 `~/.config/<skill>/.env`，
  repo 只留 `.env.example`。公司的 Slack ID、URL 用佔位值（`U0123456789`、`<workspace>`）；
  要 OAuth 登入才能用的 MCP URL 例外，可以寫實值（例如 `mcp.yaml` 的 `pms`）。
- **不要 commit `config.yaml`。** skillshare 會自動 ignore，也會在 push 時拿掉；它由 dotfiles 的
  chezmoi 管。
- **第三方 skill 不要手改。** 看 `skills/.metadata.json` 有沒有那支：有就是第三方，`update --all`
  會蓋掉。要改就另存成自己的 skill。
- **新增 skill 或 MCP 用 skillshare 指令，不要手寫 `.metadata.json`。** `install` 會記來源，
  `mcp add` 會寫 `mcp.yaml`。
- **指令只寫一份，agent 要執行的放這裡。** agent 要執行的東西（script、一行指令、守則、完成條件）寫在這個 repo 的
  skill，agent 只靠 agent-config 就能做完；連線也是（`remote-access` skill）。dotfiles 放安裝和給人看的情境、理由，
  引用這裡的 script 和指令，不抄步驟。這個 repo 給人看的照種類放：人要自己動手（跑 script、設定、排錯）的寫
  `docs/skills/<名字>.md`，MCP 的寫 `docs/mcp/`，hook 的寫 `docs/hooks/`，repo 結構和 `config.yaml`、extras 的來歷寫
  `docs/architecture.md`，一樣引用 skill 的指令、不抄。README 只當入口。通用概念連官方或高品質來源，不抄。
  SKILL.md 只寫什麼時候走哪條、agent 要做的步驟和完成條件、只有 agent 要守的限制；坑和實測紀錄放同一支 skill 的
  `reference.md`、參數看 script 的 `--help`、給人看的理由在 dotfiles，從 SKILL.md 直接連過去（只隔一層）。
- **script 只包脆弱的操作。** 會漏秘密、會忘記收、順序錯就壞的才寫成 `scripts/`；一兩行標準指令寫在文件裡，
  讓人自己打、自己改參數。
- **skill 資料夾裡不放 README。** skill 資料夾會被 sync 到各 client；給人看的照上面那條放。
  第三方 skill 帶來的 README 不動。
- **不要加 OpenCode target。** OpenCode 會讀 `~/.claude/skills` 和 `~/.agents/skills`，加了會
  同一支出現三次。

## 放哪

該用哪種機制照 `writing-for-humans` skill〈先分讀者〉（細節看官方）。決定後，在這個 repo 放：

| 機制 | 放哪 |
|---|---|
| 全域規則 | `instructions/agents-md/AGENTS.md`；skillshare extras 連到 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.config/opencode/AGENTS.md`。要加連結改 dotfiles 的 `modify_config.yaml.tmpl`，不要用 `skillshare extras` 指令（下次 `chezmoi apply` 會蓋回去） |
| skill | `skills/<名字>/`；補第三方 skill 沒寫的步驟也是另寫一支 |
| MCP | `skillshare mcp add`，寫進 `mcp.yaml` |
| hook | 自己寫的定義放 `hooks/<名字>.yaml`，用 `skillshare hooks add <名字> --file` 存進 `config.yaml` 再 sync（每台都要 add，步驟在 [docs/hooks/](docs/hooks/README.md)）；工具自己裝的（herdr、codegraph、wakatime）不收，重裝時它們會再寫一次 |
| plugin | `skillshare plugin add`，記在 `config.yaml` 的 `plugins:`（不進 repo，每台各自 add）。wakatime 的由 dotfiles apply 裝，不收 |
| agent | `agents/<名字>.md`，`skillshare sync agents` 連到 `~/.claude/agents`（路徑由 dotfiles 的 `modify_config.yaml.tmpl` 釘）。Codex 的 subagent 是 TOML，要用時另走 extras 的 `codex-agents` extension |

## 改完怎麼驗證

```bash
uv run --isolated --no-project --with-requirements tests/requirements.txt \
  python3 -B -m unittest discover -s tests  # 動到自己寫的 skill 的 script、hooks/ 時
skillshare sync --dry-run               # skill 會怎麼落到 target
skillshare sync mcp -g --dry-run        # MCP 會怎麼寫進三個 client
skillshare hooks sync -g --dry-run      # hook 會怎麼寫進 Claude Code、Codex
```

驗完用 `skillshare push` 推（它會 commit 再 push），其他機器怎麼跟上見 [docs/skills/〈跨機器〉](docs/skills/README.md#跨機器)。
