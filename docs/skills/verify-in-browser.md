# verify-in-browser：agent 改完前端自己開瀏覽器驗收

agent 改完 UI，用 [`playwright-cli`](https://github.com/microsoft/playwright-cli) 開 headless
Chrome 自己點一遍、截圖、看 console，回報時附證據和「未驗」清單。不必每次都由你去點。

工具怎麼分工的決定在 dotfiles 的
[ADR 0001](https://github.com/henry5720/dotfiles/blob/main/docs/adr/0001-browser-tools-drive-vs-debug.md)，
調查與 token 實測在
[docs/research/agent-browser-tools.md](https://github.com/henry5720/dotfiles/blob/main/docs/research/agent-browser-tools.md)。

## 兩支 skill、一支 MCP 怎麼分

| 要做的事 | 用什麼 | skill |
|---|---|---|
| 操作頁面、改完驗收 | `playwright-cli` headless | `verify-in-browser`（自己寫的）＋ `playwright-cli`（官方） |
| 查原因：慢、記憶體、minify 過的錯誤 | chrome-devtools MCP | [`chrome-mcp`](chrome-mcp.md) |
| 你要看著 agent 操作、或要用你桌機的登入狀態 | chrome-devtools MCP 接桌機 Chrome | [`chrome-mcp`](chrome-mcp.md) |
| 值得防回歸的流程 | 寫成該 repo 的 Playwright e2e | — |

| skill | 來源 | 內容 |
|---|---|---|
| `playwright-cli` | 第三方，`microsoft/playwright-cli` 的 `skills/playwright-cli`，`.metadata.json` 記來源 | 指令用法 |
| `verify-in-browser` | 自己寫的 | 什麼時候驗、怎麼登入、留什麼證據、卡住換 chrome-mcp |

官方那支是第三方，`update` 會蓋掉，所以驗收的規矩另外寫一支，不併進去。

`playwright-cli` 的瀏覽器走 pipe，不佔 9222，跟 `chrome-mcp`／`chrome-headless` 可以同時開。

## 你要做的事

| 什麼時候 | 做什麼 |
|---|---|
| 新機器 | dotfiles chezmoi 選裝工具勾 `playwright-cli`（用 `headless-chrome` 裝的 Chrome；WSL、ARM 不裝） |
| 升級 `@playwright/cli` 後 | 官方 skill 釘在跟 CLI 同一版的 commit，要手動跟（見下方） |
| 要 agent 驗需要登入的頁面 | 確認那個 repo 的 `.env` 有帳密；agent 照 repo 既有的登入流程填表 |

### 升級 playwright-cli 後跟上 skill

skill 釘在 `microsoft/playwright-cli` 的某個 commit（`.metadata.json` 的 `branch`），跟本機 CLI 同版，
跟 herdr 一樣，避免 skill 寫的指令 CLI 沒有。上游沒打 `v0.1.x` tag，所以釘 commit：找
`chore: mark v<新版>` 那顆。

```bash
playwright-cli --version
gh api 'repos/microsoft/playwright-cli/commits?per_page=20' --jq '.[] | .sha[:12] + " " + (.commit.message | split("\n")[0])' | grep 'mark v'
skillshare install https://github.com/microsoft/playwright-cli.git/skills/playwright-cli --branch <commit> --force && skillshare sync
```

裝好的 skill 應該跟 npm 套件裡帶的一字不差：

```bash
diff -r ~/.config/skillshare/skills/playwright-cli \
  "$(npm root -g)/@playwright/cli/node_modules/playwright-core/lib/tools/skills/playwright-cli"
```

`playwright-cli install --skills` 也能裝，但它寫進當下專案的 `.claude/skills/`，只有 Claude Code
看得到、也不記來源，所以改由 skillshare 裝。

## 踩過的雷（0.1.22）

| 症狀 | 原因與做法 |
|---|---|
| 整棵 accessibility tree 印進對話 | 裸 `snapshot` 會直接印出來（官方 skill 寫的是存檔，實際沒有）。一律 `snapshot --filename=<名字>.yml` 再讀檔，或用 `find` |
| 密碼出現在對話紀錄 | `fill` 的輸出含產生的 Playwright code，值是明文。填密碼要加 `--raw` |
| repo 多出 `.playwright-cli/` | 它寫在當下目錄。agent 要在證據資料夾裡跑指令 |
