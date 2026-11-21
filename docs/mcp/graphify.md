# Graphify Cloud

Graphify Cloud 是雲端的程式碼圖譜：把自家 repo 的 symbol、呼叫、依賴做成圖，讓 agent 不用 grep 一路讀檔就查得到。
本機只有 `mcp.yaml` 一筆，不裝東西。agent 什麼時候用它寫在全域規則（`instructions/agents-md/AGENTS.md` 的「Graphify」段），
這份講給人看的用法、坑，和跟 codegraph 的差別。試用紀錄在 [#99](https://github.com/henry5720/agent-config/issues/99)（到 2026-12-04）。

## 人怎麼用

- **看圖、Wiki、PR review**：用帳號登入 [app.graphify.com](https://app.graphify.com)。`GRAPHIFY_API_KEY` 只給 MCP 用，登不了網頁。
- **加 repo**：在 app 的 Repositories 開啟。方案是 pro，repo 數不限。
- 其他用法看[官方 docs](https://docs.graphify.com)。

## 坑

- **換 key 後 agent 連不上（401）**：agent 啟動時讀環境變數，key 改了要從新的 zsh 重開 agent。先確認 key 本身能用：
  在 zsh 對 `https://api.graphify.com/v1/mcp` 送 `initialize`，回 200 就是 agent 拿到舊值。key 怎麼設見 [MCP 的〈API key〉](README.md#api-key)。（2026-11-21 記錄）
- **答案是舊的**：結果帶 `commitSha`，跟 `git rev-parse HEAD` 不同就以本機檔案為準。在非預設分支上幾乎一定不同。（2026-11-21 記錄）
- **PR review 只跑一次**：PR 開啟、重開、轉 ready 時跑，後續 push 不會重跑；要重跑在 PR 留言 `@graphify review`。比對基準是預設分支的圖。（2026-11-21 記錄）

## 跟 codegraph 差在哪

找定義、誰呼叫、改了影響什麼兩個都做得到，差在**看哪一版程式碼**、**一次查詢涵蓋幾個 repo**。
查第三方套件文件的 context7、搜 GitHub 公開程式碼的 grep.app 不算這類。

| | codegraph | Graphify Cloud |
|---|---|---|
| 索引在哪 | 本機 `<repo>/.codegraph/`，監看檔案自動更新 | 雲端，push 到 GitHub **預設分支**才重建 |
| 看得到 | 手上 checkout 的程式碼，含沒 push 的改動 | 預設分支最後建圖的 commit；其他分支、PR 分支不建 |
| 查多個 repo | 可以，用 `projectPath` 一次查一個；本機要有 checkout 和 `.codegraph/`，呼叫關係不跨 repo 串 | 可以，合併 workspace（例如 `teamsync-core`）一次查詢涵蓋全部 |
| 不知道在哪個 repo | 一個一個查 | `search` 一次搜所有 repo |
| 給人看的 | 沒有 | app.graphify.com 的 Graphs（圖形畫布）、Wiki；GitHub PR 上自動 review |
| 裝在哪 | dotfiles 裝 CLI，見 [codegraph.md](https://github.com/henry5720/dotfiles/blob/main/docs/tools/codegraph.md) | 只有 `mcp.yaml` 一筆，本機不裝東西 |

所以平常在 `dev` 上改程式讓 agent 用 codegraph，前後端都在本機就各查一次；不知道在哪個 repo、本機沒有的 repo、看架構圖、看 PR review 才用 Graphify。
合併 workspace 串得到的是 import、呼叫、共用型別；前端用字串組 URL 打後端 API 串不起來（[官方](https://docs.graphify.com/cookbooks/cross-repo-dependencies)：「A URL assembled at runtime isn't a static link.」），要把共用的 client 或 schema 套件也加進合併 workspace。

加新的程式碼圖譜工具時：表格加一欄，全域規則寫清楚哪些情況才用它，有自己的坑就在它的文件開〈坑〉。
