# remote-chrome：背景與排錯

給讀 [SKILL.md](SKILL.md) 之後還想知道「為什麼這樣設」、或照步驟做卻連不上的人和 agent。
工具本身的用法看官方：chrome-devtools MCP 看 `ChromeDevToolsMCP/chrome-devtools-mcp`，
playwright-cli 看 `microsoft/playwright-cli`。

## 全貌

```
chrome-devtools MCP（Claude Code、Codex、OpenCode）
        │  --browser-url=http://127.0.0.1:9222
        ▼
127.0.0.1:9222  ←  remote-chrome-headless 開的 headless Chrome（同一台）
```

- **只綁 127.0.0.1。** 9222 等於完整的瀏覽器控制權（含 profile 裡所有登入狀態），而且沒有驗證，
  不要對 LAN、tailnet 或網際網路開放。
- **只查原因時才開。** 操作、驗收用 `playwright-cli open`，它自己開瀏覽器、走 pipe、不佔 9222。
  兩者並存不衝突。
- **9222 同時只有一個 Chrome。** 開著就是在用，查完 Ctrl+C。多個 agent 在同一台查原因時共用同一個。
- **登入狀態**在 `~/.local/state/chrome-mcp-profile`，關掉再開還在。沒有畫面，要登入的網站讓 agent 自己填表登入。
  （目錄名沿用 skill 改名前的 `chrome-mcp-profile`，改了會換成空 profile。）

## 安裝

Chrome 由 dotfiles 的選裝工具 `headless-chrome` 裝：已經 init 過的機器跑 `tools` 勾它，
或 `chezmoi edit-config` 把它加進 `tools` 再 `chezmoi apply`。裝的是 Google 官方 `.deb`，
`fonts-noto-cjk`、`fonts-noto-color-emoji` 同一次裝好 —— 少了字型，截圖裡中文和 emoji 全是方框。
`~/.local/bin/remote-chrome-headless` 是 dotfiles 放的 symlink，指到這個 skill 的 script；新機器要等
agent-config 裝好之後 symlink 才有目標。

**WSL 不提供 `headless-chrome`**，所以 WSL 上 chrome-devtools MCP 沒有 Chrome 可接。查原因到有
`headless-chrome` 的機器（例如 company-ec2）做。不要在 WSL 自己裝 Linux Chrome 或
`npx puppeteer browsers install chrome`：會多一個 agent 連錯的瀏覽器。

## script 做的事

1. 先檢查 `curl`、`jq` 在不在（判斷 Chrome 起來沒靠它們，少了會白等 15 秒）。
2. 9222 已經有 Chrome 就不開、直接沿用，印出是哪個 process 佔著；9222 是別的服務就失敗，同樣印出是誰。
3. 開 `google-chrome --headless`，只聽 `127.0.0.1:9222`。不加 `--no-sandbox`：官方 `.deb` 帶
   `/etc/apparmor.d/chrome` 和 setuid 的 `chrome-sandbox`，Ubuntu 24.04 限制 unprivileged userns 也開得起來。
4. 等 endpoint 真的通了才印「按 Ctrl+C」，最多 15 秒。
5. 停在前景。Chrome 用 `setpriv --pdeathsig TERM` 啟動：script 不管怎麼結束（Ctrl+C、TERM、關 herdr pane
   時整棵被砍、連 SIGKILL），kernel 都會叫 Chrome 收掉，幾秒內放掉 9222。以前用 trap 自己 `kill`，被 SIGKILL 時收不到。

## MCP 設定

`chrome-devtools` 定義在 agent-config 的 `mcp.yaml`，`skillshare sync mcp -g` 寫進三個 client。
新增、改參數、升版本都改 `mcp.yaml`，三個 client 的參數刻意一致：

```
--browser-url=http://127.0.0.1:9222   連 remote-chrome-headless 開的 Chrome，不要自己開
--no-usage-statistics                 不回報使用統計
--no-performance-crux                 跑效能分析時不去 CrUX API 查別人網站的公開數據
```

**為什麼關掉 Claude Code 官方的 chrome-devtools plugin**：它的 args 沒有 `--browser-url`，會想自己開
Chrome 然後失敗（`Target closed`）；不關的話同一組工具出現兩份，Claude 有一半機率挑到壞的。
dotfiles 的 `home/dot_claude/modify_settings.json.tmpl` 在 `~/.claude/settings.json` 把它關掉。

## 設定放在哪

| 設定 | 在哪個 repo | 路徑 |
|---|---|---|
| MCP 條目 | agent-config | `mcp.yaml` |
| skill 與 script | agent-config | `skills/remote-chrome/`（`SKILL.md`、這份、`scripts/remote-chrome-headless`） |
| 指令 symlink | dotfiles | `home/dot_local/bin/symlink_remote-chrome-headless.tmpl` → `~/.local/bin/remote-chrome-headless` |
| 裝 Chrome 與字型 | dotfiles | `home/.chezmoiscripts/run_onchange_after_install-headless-chrome.sh.tmpl`（選裝工具 `headless-chrome`） |
| 關官方 plugin | dotfiles | `home/dot_claude/modify_settings.json.tmpl` |

## 排錯

| 症狀 | 原因 |
|---|---|
| `Target closed` / `Target.setDiscoverTargets` | 走到沒有 `--browser-url` 的設定了 —— 官方 plugin 又被開起來（dotfiles `chezmoi apply` 修回來），或 MCP 條目被改掉（`skillshare sync mcp -g` 修回來） |
| `claude mcp list` 顯示 Failed | 9222 沒有 Chrome。先跑 `remote-chrome-headless`，再 `/mcp` 重連 |
| `remote-chrome-headless` 說 9222 已有服務、不是 Chrome | 它印出的那行就是佔著的 process。請使用者決定要不要關 |
| `remote-chrome-headless` 說已經有 Chrome、不用開 | 上一次開的還在（或別人開的），MCP 直接能用；查完記得把那個收掉 |
| `remote-chrome-headless` 說「Chrome 啟動失敗」 | 看 `~/.local/state/chrome-mcp-profile.log`。dbus／UPower 的 ERROR 是沒有桌面環境的正常雜訊，不是原因 |
| 找不到 `google-chrome` | 這台沒勾 `headless-chrome`（WSL 不提供，見〈安裝〉） |
| 截圖中文或 emoji 是方框 | 字型沒裝。確認 `chezmoi edit-config` 的 `tools` 有 `headless-chrome`，再 `chezmoi apply` |
| 開出來的分頁一直是 `about:blank`，`new_page` 逾時 | 9222 被別的 Chrome 搶走（例如 Playwright 起的 `ms-playwright/chromium` 開了 9222）。`ss -ltnp \| grep 9222` 找出來關掉 |

驗證整條路通了：

```bash
remote-chrome-headless                             # 另一個終端機：停在前景
curl -s 127.0.0.1:9222/json/version | jq .Browser  # 看得到版本號，User-Agent 是 HeadlessChrome
claude mcp list                                    # chrome-devtools 顯示 Connected
```

## 為什麼用官方 `.deb`

2026-09-21 研究過裝 Chrome for Testing 跑 headless：要自己處理固定版本與 SHA256、AppArmor 擋 sandbox、
一串系統套件。2026-10-03 改裝 Google 官方 `.deb`，這些大多消失：apt 補齊系統套件、Ubuntu 內建的
AppArmor profile 放行它、`chrome-sandbox` 帶 setuid，不加 `--no-sandbox` 也開得起來；版本跟著 apt 升級，不釘。

## 拿掉的做法

以前 `remote-chrome` 還有一支在 WSL 開 Windows Chrome（專用 profile）、經 ssh 反向轉發把 9222 帶到遠端主機的 script。
2026-11 拿掉（dotfiles #260、#261）：專用 profile 沒有人的登入狀態，Chrome 136 起又不能對日常 profile 開 debugging port。
要用人自己的瀏覽器時改走 `playwright-cli attach --extension`（dotfiles #260 的 a2）。
