# CLAUDE.md

這是 skillshare 的設定目錄，也是 git repo（`henry5720/agent-config`）。文件、註解、commit message
用繁體中文。操作方式見 [README.md](README.md)，詞彙見 [CONTEXT.md](CONTEXT.md)。

## 規則

- **公開 repo，秘密不進來。** MCP 的 key 用 `fromEnv`；skill 的 token 放 `~/.config/<skill>/.env`，
  repo 只留 `.env.example`。公司的 Slack ID、URL 用佔位值（`U0123456789`、`<workspace>`）。
- **不要 commit `config.yaml`。** skillshare 會自動 ignore，也會在 push 時拿掉；它由 dotfiles 的
  chezmoi 管。
- **第三方 skill 不要手改。** 看 `skills/.metadata.json` 有沒有那支：有就是第三方，`update --all`
  會蓋掉。要改就另存成自己的 skill。
- **新增 skill 或 MCP 用 skillshare 指令，不要手寫 `.metadata.json`。** `install` 會記來源，
  `mcp add` 會寫 `mcp.yaml`。
- **不要加 OpenCode target。** OpenCode 會讀 `~/.claude/skills` 和 `~/.agents/skills`，加了會
  同一支出現三次。

## 改完怎麼驗證

```bash
python3 -m unittest discover -s tests   # 動到自己寫的 skill 的 script 時
skillshare sync --dry-run               # skill 會怎麼落到 target
skillshare sync mcp -g --dry-run        # MCP 會怎麼寫進三個 client
```

驗完用 `skillshare push` 推（它會 commit 再 push）。其他機器 `skillshare pull && skillshare sync mcp -g`。
