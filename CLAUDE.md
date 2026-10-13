# CLAUDE.md

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
- **給人看的文件放 `docs/`，不放 skill 資料夾。** `SKILL.md` 是給 agent 的；skill 資料夾會被
  sync 到各 client，裡面不放 README。只有人要自己動手（跑 script、設定、排錯）的 skill 才寫
  `docs/skills/<名字>.md`。流程、邊界、狀態先畫 mermaid 或表格，畫不出來才用文字。
  第三方 skill 帶來的 README 不動。
- **不要加 OpenCode target。** OpenCode 會讀 `~/.claude/skills` 和 `~/.agents/skills`，加了會
  同一支出現三次。

## 放哪

新增或改一條 agent 指引前，照「要的效果」對表決定放哪：

| 要的效果 | 放哪 | 依據 |
|---|---|---|
| 每個 session 都該知道的事實、「一律怎麼做」 | `instructions/agents-md/AGENTS.md`（部署成全域 `CLAUDE.md`） | [memory](https://code.claude.com/docs/en/memory)：CLAUDE.md 只放每個 session 都要的事實與規則，控制在 200 行內 |
| 特定時機才用的多步驟流程 | 自己的 skill `skills/<名字>/SKILL.md` | [memory](https://code.claude.com/docs/en/memory)：multi-step procedure 移到 skill；[skills](https://code.claude.com/docs/en/skills)：觸發時才載入 |
| 不論 agent 怎麼判斷都要擋下或一定要發生 | hook（`settings.json`，由 dotfiles 的 chezmoi 管） | [memory](https://code.claude.com/docs/en/memory)：CLAUDE.md 是 context 不是強制，要強制用 hook |
| 讓 agent 連外部工具或資料 | MCP，`skillshare mcp add` 寫進 `mcp.yaml` | [MCP](https://code.claude.com/docs/en/mcp) |
| 補第三方 skill 沒寫的步驟 | 另寫自己的 skill，第三方原檔不動 | 上方「第三方 skill 不要手改」 |
| 給人看的說明 | `docs/` | 上方「給人看的文件放 `docs/`」 |

對不到任何一列時，先查官方文件（[索引](https://code.claude.com/docs/llms.txt)）再決定，決定後把那一列補進這張表。

## 改完怎麼驗證

```bash
python3 -m unittest discover -s tests   # 動到自己寫的 skill 的 script 時
skillshare sync --dry-run               # skill 會怎麼落到 target
skillshare sync mcp -g --dry-run        # MCP 會怎麼寫進三個 client
```

驗完用 `skillshare push` 推（它會 commit 再 push）。其他機器 `skillshare pull && skillshare sync mcp -g`。
