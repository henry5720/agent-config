# Discord

讓 Claude Code、Codex 用你自己的 Discord bot 讀頻道、發訊息。server 是社群專案
[PaSympa/discord-mcp](https://github.com/pasympa/discord-mcp)（MIT），版本釘在 `mcp.yaml`。

方向別搞反：這份是「agent 去操作 Discord」。要「在 Discord 裡叫 agent 做事」是另一回事，
Claude 有官方的 [channels](https://code.claude.com/docs/en/channels)，不走這裡。

## 為什麼這樣設

- **用 bot，不用個人帳號。** agent 發的訊息顯示成 bot。拿個人帳號的 user token 跑（selfbot）違反 Discord 條款，帳號會被封。
- **只開 `discovery,messages`。** 100 個工具全開約吃 35k tokens，這兩組 25 個、約 10k。要管角色、頻道再加，組名見 server 的 README〈Expose only what you need〉。
- **token 走 dotfiles。** `mcp.yaml` 只留 `fromEnv: DISCORD_TOKEN`，值存在 chezmoi 的 `discordBotToken`，跟 context7、graphify 的 key 同一套（見 [〈API key〉](README.md#api-key)）。

## 設定步驟

每台要用的機器都做一次 3～5；1、2 只做一次。

1. **建 bot。** 到 [Discord Developer Portal](https://discord.com/developers/applications) → New Application → **Bot**：
   - **Reset Token**，複製 token（只顯示一次）。
   - 同一頁打開 **Server Members Intent** 和 **Message Content Intent**。server 預設兩個都會要，沒開會連不上。
2. **邀進伺服器。** 把 **General Information** 的 Application ID 填進網址再打開：

   ```
   https://discord.com/oauth2/authorize?client_id=<Application ID>&scope=bot&permissions=2270827458424055
   ```

   這串權限涵蓋所有工具。只用訊息的話，授權畫面只留 View Channels、Send Messages、Send Messages in Threads、Read Message History、Add Reactions、Attach Files，其他取消。
3. **存 token。** 跑 `chezmoi edit-config`，在 `[data]` 加一行，存檔後套用：

   ```toml
   discordBotToken = "<bot token>"
   ```

   ```bash
   chezmoi update   # 拉 dotfiles 最新版再套用；舊版 dotfiles 不認得 discordBotToken
   ```

   Linux 會寫進 `~/.config/zsh/env.zsh`，Windows 會設成使用者環境變數 `DISCORD_TOKEN`。
4. **同步 MCP。**

   ```bash
   skillshare pull                   # 先拿到含 discord 的 mcp.yaml
   skillshare sync mcp -g --dry-run  # 應該只有 claude、codex 各一筆 discord add
   skillshare sync mcp -g
   ```

5. **重開 agent。** 從**新的 zsh** 開 Claude Code 或 Codex，舊 shell 沒有 `DISCORD_TOKEN`。
   Codex 還要先重開背景 daemon，MCP 是 daemon 開的：`zsh -c 'codex app-server daemon restart'`
   （原因見 dotfiles 的 [codex〈坑〉](https://github.com/henry5720/dotfiles/blob/main/docs/tools/codex.md#坑)）。

## 確認做好了

- 開 agent 前，在新 zsh 跑 `echo ${DISCORD_TOKEN:+set}`，要印出 `set`。
- Claude Code：`/mcp` 看到 `discord` 是 connected。Codex：`codex mcp list` 有 `discord`。
- 叫 agent「列出 bot 看得到的 Discord 伺服器和頻道」，有回清單就通了。
- 連不上時先查步驟 1 的兩個 intent 有沒有開。

## 給同事用

每個人建自己的 bot（步驟 1、2），**不要共用 token**：拿到 token 的人就能完全控制那個 bot，大家發的訊息也分不出是誰。
沒用這套 dotfiles 的人，把 token 放進自己的 shell 環境（例如 `~/.zshrc` 裡 `export DISCORD_TOKEN=...`），再直接加：

```bash
claude mcp add discord -s user -e 'DISCORD_TOKEN=${DISCORD_TOKEN}' -e DISCORD_MCP_TOOLSETS=discovery,messages \
  -- npx -y @pasympa/discord-mcp@2.4.0
codex mcp add discord --env DISCORD_MCP_TOOLSETS=discovery,messages -- npx -y @pasympa/discord-mcp@2.4.0
```

Codex 的 token 要從環境轉進去：在 `~/.codex/config.toml` 的 `[mcp_servers.discord]` 加 `env_vars = ["DISCORD_TOKEN"]`，
改完照步驟 5 重開 daemon。

公司的 agent-company bot（OpenAB）預設不理其他 bot 的訊息，所以這個 MCP 不能拿來 @它。

## 安全

- bot 能做的 = 你在步驟 2 給的權限。agent 發錯訊息就是 bot 發的，別給管理權限。
- 只讀不寫：在 `mcp.yaml` 的 `env` 加 `DISCORD_MCP_READ_ONLY: "true"`，剩 11 個唯讀工具。
- token 外洩：Developer Portal 按 **Reset Token**，再做一次步驟 3。

## 更多

- 所有環境變數與工具清單：[PaSympa/discord-mcp README](https://github.com/pasympa/discord-mcp#configuration)
- 升級：改 `mcp.yaml` 的版本號，`skillshare sync mcp -g`。
