# Graphify：跟 codegraph 怎麼分

兩個都把程式碼做成圖給 agent 查，找定義、誰呼叫、改了影響什麼都做得到。差在**看哪一版程式碼**、**能不能跨 repo**。
agent 該用哪個寫在全域規則的「Graphify」段（`instructions/agents-md/AGENTS.md`），這份講給人看的差別和坑。
試用紀錄在 [#99](https://github.com/henry5720/agent-config/issues/99)（到 2026-12-04）。

| | codegraph | Graphify Cloud |
|---|---|---|
| 索引在哪 | 本機 `<repo>/.codegraph/`，監看檔案自動更新 | 雲端，push 到 GitHub **預設分支**才重建 |
| 看得到 | 手上 checkout 的程式碼，含沒 push 的改動 | 預設分支最後建圖的 commit；其他分支、PR 分支不建 |
| 跨 repo | 不行，一次一個專案 | 可以，有合併 workspace（例如 `teamsync-core`） |
| 給人看的 | 沒有 | app.graphify.com 的 Graphs（圖形畫布）、Wiki；GitHub PR 上自動 review |
| 裝在哪 | dotfiles 裝 CLI，見 [codegraph.md](https://github.com/henry5720/dotfiles/blob/main/docs/ai-agent/codegraph.md) | 只有 `mcp.yaml` 一筆，本機不裝東西 |

所以平常在 `dev` 上改程式讓 agent 用 codegraph；跨前後端查、看架構圖、看 PR review 才用 Graphify。

## 人怎麼用

- **看圖、Wiki、PR review**：用帳號登入 [app.graphify.com](https://app.graphify.com)。`GRAPHIFY_API_KEY` 只給 MCP 用，登不了網頁。
- **加 repo**：在 app 的 Repositories 開啟。方案是 pro，repo 數不限。
- 其他用法看[官方 docs](https://docs.graphify.com)。

## 坑

- **換 key 後 agent 連不上（401）**：agent 啟動時讀環境變數，key 改了要從新的 zsh 重開 agent。先確認 key 本身能用：
  在 zsh 對 `https://api.graphify.com/v1/mcp` 送 `initialize`，回 200 就是 agent 拿到舊值。key 怎麼設見 dotfiles 的 `docs/after-install.md`。
- **答案是舊的**：結果帶 `commitSha`，跟 `git rev-parse HEAD` 不同就以本機檔案為準。在非預設分支上幾乎一定不同。
- **PR review 只跑一次**：PR 開啟、重開、轉 ready 時跑，後續 push 不會重跑；要重跑在 PR 留言 `@graphify review`。比對基準是預設分支的圖。
