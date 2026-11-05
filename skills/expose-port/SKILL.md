---
name: expose-port
description: 把本機某個 port 開成 tailnet 外連得到的公開網址：開、從公網驗證、收。要把本機 port 開給 tailnet 外的人或 agent，或要收掉公開網址時使用。
---

# expose-port

公開網址誰拿到都能連，擋陌生人的只剩 app 自己的驗證。所以這支只開**有驗證的 app**，交出網址前從公網確認「不帶驗證被拒、帶了通過」，用完一定收掉。

連的人在 tailnet 內就不用這支：直接連 tailnet IP，不開公網（[判準](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#判準)）。

## 選分支

開出去的那台**跑得到登入使用者 tailnet 的 tailscale** → [Funnel](#funnel)。那台不加進使用者的 tailnet（別人的機器、臨時借用）→ [quick tunnel](#quick-tunnel)。差異看 [比較表](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#比較表)。

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

開出去的那台沒有 skillshare（或沒有 WSL 的 Windows）時，第 1、2 步照上面做，第 3 步改成請使用者在那台開一個終端機（Windows 用 PowerShell）貼上，開著別關：

```bash
tailscale funnel --https=<對外 port> <app port>    # Linux 沒設 operator 要加 sudo；不加 --bg
```

1. **開**：完成條件：使用者說貼了、視窗停著沒有回到提示字元（印出網址或要你開權限的 admin console 連結都算開著；後者先請使用者開好權限再貼一次）。
2. **驗**：照 [reference.md](reference.md)〈在本機驗不到 Funnel〉從你這邊打，網址是 `https://<那台的機器名>.<tailnet>.ts.net:<對外 port><路徑>`。
   完成條件：不帶驗證、帶驗證各回 app 給的碼。沒過就照第 3 步收掉，再照 reference.md 查原因。
3. **交網址、收掉**：交網址同上面第 4 步。用完請使用者在那個視窗按 Ctrl+C，再跑 `tailscale funnel status`。
   完成條件：`tailscale funnel status` 的輸出沒有那個對外 port 的 `https://` 行（443 的那行網址不帶 port；只剩 `No serve config` 或別的 port 都算收乾淨）。再由 app 停掉它的 server。

## quick tunnel

腳本：`~/.claude/skills/expose-port/scripts/expose-port-quick-tunnel`（`--help` 看參數）。cloudflared 給一個 `https://<隨機>.trycloudflare.com`，不用 Cloudflare 帳號，轉進 app 的 `127.0.0.1:<port>`。

開之前對一次 app 的需求和這四項限制（[Cloudflare 官方文件](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)），app 撐不住就停下來回報使用者：

- **不支援 SSE**：app 靠 SSE 推資料時可能會壞（例如 MCP streamable HTTP 的串流回應）。
- **每條最多 200 個並行請求**，超過的回 `429`。
- **網址每次都變**：每開一次是新網址，重開就要重交。
- **官方只給測試、開發用**：用完就收，不長駐。

1. **對好 `Host`**：app 綁 loopback 又檢查 `Host` 時，帶 `--host-header localhost`（cloudflared 的 `--http-host-header`）。app 留在 loopback，不用放行防火牆 inbound。
   完成條件：決定好帶不帶 `--host-header`、帶什麼值。
2. **開**：看 cloudflared 跑在哪台。
   - **這台**（`cloudflared --version` 有輸出）：背景跑（Claude Code 的 Bash `run_in_background`）：

     ```bash
     ~/.claude/skills/expose-port/scripts/expose-port-quick-tunnel open --port <app port> [--host-header localhost] --path <路徑> \
       --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' \
       -- <兩次驗證都帶的 curl 參數>
     ```

   - **那台沒有這支腳本**（例如別人的 Windows）：請使用者在那台 PowerShell 貼上，開著別關。沒裝 cloudflared 先跑 `winget install --exact --id Cloudflare.cloudflared`，再重開 PowerShell。

     ```powershell
     cloudflared tunnel --url http://127.0.0.1:<app port> --http-host-header localhost   # app 不檢查 Host 就拿掉最後兩個字
     ```

     請使用者把輸出裡 `https://<隨機>.trycloudflare.com` 那行給你，從這邊驗：

     ```bash
     ~/.claude/skills/expose-port/scripts/expose-port-quick-tunnel verify --url <那個網址> --path <路徑> \
       --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' -- <curl 參數>
     ```

   完成條件：輸出出現 `公網驗證：不帶驗證=<碼>（要 <碼>），帶驗證=<碼>（要 <碼>）` 兩邊相符，接著 `公開網址：https://…`。驗證沒過時 `open` 已經停掉 cloudflared、exit 1；`verify` 沒過就照第 4 步請使用者收掉。原因照 [reference.md](reference.md) 查。
3. **交網址**：把 `公開網址` 那行交給 app skill 或使用者。
4. **收掉**：
   - **這台**：對背景那支送 SIGTERM。完成條件：輸出最後是 `cloudflared → :<port> 剩 0 個（要 0）`。背景那支已經不在時，跑 `expose-port-quick-tunnel close --port <app port>`，完成條件相同。
   - **那台**：請使用者在 cloudflared 視窗按 Ctrl+C，再貼 `(Get-Process cloudflared -ErrorAction SilentlyContinue | Measure-Object).Count`。完成條件：印出 `0`。

   接著由 app 停掉它的 server（app 的文件寫怎麼確認沒有程式在聽那個 port）。
