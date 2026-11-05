---
name: expose-port
description: 把本機某個 port 開成 tailnet 外連得到的公開網址：開、從公網驗證、收。要把本機 port 開給 tailnet 外的人或 agent，或要收掉公開網址時使用。
---

# expose-port

公開網址誰拿到都能連，擋陌生人的只剩 app 自己的驗證。所以這支只開**有驗證的 app**，交出網址前從公網確認「不帶驗證被拒、帶了通過」，用完一定收掉。

連的人在 tailnet 內就不用這支：直接連 tailnet IP，不開公網（[判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)）。

## 選分支

開出去的那台**跑得到登入使用者 tailnet 的 tailscale** → Funnel（下面）。那台不加進使用者的 tailnet（別人的機器、臨時借用）→ Cloudflare quick tunnel，這個分支還沒寫，停下來回報使用者。差異看 [比較表](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#比較表)。

## 跟 app 要的輸入

叫這支的 app skill（例如 windows-mcp）要給齊，缺一項就回去問 app 的文件或使用者：

| 輸入 | 例子（windows-mcp） |
|---|---|
| 本機 port | `8000` |
| app 對 `Host` 的要求 | 綁 loopback 時只接受 `localhost` |
| 驗證打哪個路徑、帶什麼請求 | `/mcp`，POST MCP `initialize` |
| 不帶驗證、帶驗證各要回什麼 | `401`、`200` |
| 怎麼拿驗證 header | 一支印出 `Authorization: Bearer <key>` 的指令 |

驗證 header 由指令印出、腳本自己讀，你不用也不要看到 key。

## Funnel

腳本：`~/.claude/skills/expose-port/scripts/expose-port-funnel`（`--help` 看參數）。它照[共通規則](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#共通規則)前景跑：不加 `--bg`，停著直到收到 Ctrl+C／SIGTERM 才撤掉 Funnel，忘了收也不會像 `--bg` 那樣留下持久設定。

1. **對好 `Host`**：Funnel 不能改寫 `Host`，轉進來的 `Host` 是公開網址。app 綁 loopback 又檢查 `Host` 時，請 app 改綁 `0.0.0.0`，並確認防火牆沒放行那個 port 的 inbound（不然區網能直連）。
   完成條件：app 綁的位址接受公開網址當 `Host`。
2. **挑對外 port**：只能用 `443`、`8443`、`10000`。先跑 `tailscale funnel status`，挑沒被用的；預設 `8443`。
3. **開**：背景跑（Claude Code 的 Bash `run_in_background`）：

   ```bash
   ~/.claude/skills/expose-port/scripts/expose-port-funnel open --port <app port> --https <對外 port> --path <路徑> \
     --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' \
     -- <兩次驗證都帶的 curl 參數，例如 -X POST -H … -d …>
   ```

   tailscale 不在這台的 PATH 上、或要叫別台的（例如 WSL 叫 Windows 那邊的），用環境變數 `TAILSCALE` 給整條指令。沒設時腳本自己判斷要不要 sudo。
   完成條件：輸出出現 `公網驗證：不帶驗證=<碼>（要 <碼>），帶驗證=<碼>（要 <碼>）` 兩邊相符，接著 `公開網址：https://…`。驗證沒過時腳本已經撤掉 Funnel、exit 1；照 [reference.md](reference.md) 查原因。
4. **交網址**：把 `公開網址` 那行交給 app skill 或使用者。驗證用的 key 由 app 自己的規則交。
5. **收掉**：用完對背景那支送 SIGTERM（`TaskStop`、`kill -TERM <pid>`）。
   完成條件：輸出最後是 `Funnel :<port> 剩 0 條（要 0）`，再由 app 停掉它的 server（app 的文件寫怎麼確認沒有程式在聽那個 port）。背景那支已經不在（session 斷過）時，跑 `~/.claude/skills/expose-port/scripts/expose-port-funnel close --https <對外 port>`，完成條件相同。

### 那台沒有這支腳本

開出去的那台沒有 skillshare 時，請使用者在那台開一個終端機貼上，開著別關：

```bash
tailscale funnel --https=<對外 port> <app port>    # Linux 沒設 operator 要加 sudo；不加 --bg
```

公網驗證照 [reference.md](reference.md)〈在本機驗不到 Funnel〉從你這邊打。收掉時請使用者按 Ctrl+C，再跑 `tailscale funnel status` 確認沒有那個 port。
