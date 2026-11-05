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

腳本：`~/.claude/skills/expose-port/scripts/expose-port-funnel`（`--help` 看參數）。它照[共通規則](https://github.com/henry5720/dotfiles/blob/main/docs/remote-access.md#共通規則)前景跑：不加 `--bg`，停著直到收到 Ctrl+C／SIGTERM 才撤掉 Funnel。

**收乾淨的判準**（這支和下面手動的做法都一樣）：那個對外 port 的 tailscale CLI 行程剩 0 個，**而且**從公網打公開網址連不上（`000`，或公開 DNS 查不到）。`tailscale funnel status` 不算數：前景 Funnel 不會列成 serve config，印 `No serve config` 時公網照樣回 `401`（2026-11-05 在 henry-laptop 實測）。停掉叫 tailscale 的那一端（ssh、WSL 的 `powershell.exe`）也不會停掉 Windows 上的 `tailscale.exe`，口子會一直開著。

1. **對好 `Host`**：Funnel 不能改寫 `Host`，轉進來的 `Host` 是公開網址。app 綁 loopback 又檢查 `Host` 時，請 app 改綁 `0.0.0.0`，並確認防火牆沒放行那個 port 的 inbound（不然區網能直連）。
   完成條件：app 綁的位址接受公開網址當 `Host`。
2. **挑對外 port**：只能用 `443`、`8443`、`10000`，預設 `8443`。`tailscale funnel status` 只看得到 `--bg` 留下的設定，看不到別人前景開著的；腳本開之前會再查那個 port 的 tailscale 行程和公網，有人在用就拒絕。
3. **開**：背景跑（Claude Code 的 Bash `run_in_background`）：

   ```bash
   ~/.claude/skills/expose-port/scripts/expose-port-funnel open --port <app port> --https <對外 port> --path <路徑> \
     --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' \
     -- <兩次驗證都帶的 curl 參數，例如 -X POST -H … -d …>
   ```

   tailscale 不在這台的 PATH 上、或要叫別台的（例如 WSL 叫 Windows 那邊的），用環境變數 `TAILSCALE` 給整條指令。沒設時腳本自己判斷要不要 sudo。
   完成條件：輸出出現 `公網驗證：不帶驗證=<碼>（要 <碼>），帶驗證=<碼>（要 <碼>）` 兩邊相符，接著 `公開網址：https://…`。驗證沒過時腳本已經撤掉 Funnel、exit 1；照 [reference.md](reference.md) 查原因。
4. **交網址**：把 `公開網址` 那行交給 app skill 或使用者。驗證用的 key 由 app 自己的規則交。
5. **收掉**：用完對背景那支送 SIGTERM（`TaskStop`、`kill -TERM <pid>`）。它停掉 tailscale CLI（`TAILSCALE` 叫 Windows 的時候從 PowerShell 停 `tailscale.exe`），再從公網確認連不上。
   完成條件：輸出有 `tailscale funnel :<port> 的行程剩 0 個（要 0）`、`公網 https://…：000`，最後是 `Funnel :<port> 已收乾淨`。印 `還沒收乾淨` 時照 [reference.md](reference.md)〈收掉後還在〉處理。接著由 app 停掉它的 server（app 的文件寫怎麼確認沒有程式在聽那個 port）。背景那支已經不在（session 斷過、被 SIGKILL）時，跑 `~/.claude/skills/expose-port/scripts/expose-port-funnel close --https <對外 port>`，完成條件相同。

### 那台沒有這支腳本

開出去的那台沒有 skillshare（或沒有 WSL 的 Windows）時，第 1、2 步照上面做，第 3 步改成請使用者在那台開一個終端機（Windows 用 PowerShell）貼上，開著別關：

```bash
tailscale funnel --https=<對外 port> <app port>    # Linux 沒設 operator 要加 sudo；不加 --bg
```

1. **開**：完成條件：使用者說貼了、視窗停著沒有回到提示字元（印出網址或要你開權限的 admin console 連結都算開著；後者先請使用者開好權限再貼一次）。
2. **驗**：從你這邊跑：

   ```bash
   ~/.claude/skills/expose-port/scripts/expose-port-funnel verify --url https://<那台的機器名>.<tailnet>.ts.net:<對外 port> --path <路徑> \
     --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' -- <curl 參數>
   ```

   完成條件：輸出出現 `公網驗證：…` 兩邊相符，接著 `公開網址：https://…`。沒過就照第 3 步收掉，再照 reference.md 查原因。
3. **交網址、收掉**：交網址同上面第 4 步。用完請使用者在那個視窗按 Ctrl+C，再貼下面這行（Windows PowerShell；Linux 用 `pgrep -fc 'tailscale funnel'`）：

   ```powershell
   Get-Process tailscale -ErrorAction SilentlyContinue | Stop-Process -Force; (Get-Process tailscale -ErrorAction SilentlyContinue | Measure-Object).Count
   ```

   `tailscale` 這個名字只對到 CLI 的 `tailscale.exe`，不會停掉 tailscale 本身（`tailscaled`、`tailscale-ipn`）。接著從你這邊跑 `expose-port-funnel check-closed --url https://<機器名>.<tailnet>.ts.net:<對外 port>`。
   完成條件：使用者那行印 `0`，`check-closed` exit 0（印出 `000` 或公開 DNS 查不到）。再由 app 停掉它的 server。

## quick tunnel

腳本：`~/.claude/skills/expose-port/scripts/expose-port-quick-tunnel`（`--help` 看參數）。cloudflared 給一個 `https://<隨機>.trycloudflare.com`，不用 Cloudflare 帳號，轉進 app 的 `127.0.0.1:<port>`。

開之前對一次 app 的需求和這四項限制（[Cloudflare 官方文件](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)），app 撐不住就停下來回報使用者：

- **不支援 SSE**：app 靠 SSE 推資料時可能會壞。2026-11-05 在 henry-laptop 實測，單次請求用 SSE 回的（MCP `initialize`、`tools/list`）收得到；長時間開著的 SSE stream **未實測**。
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

   - **那台沒有這支腳本**（例如別人的 Windows）：請使用者在那台 PowerShell 貼上，開著別關。沒裝 cloudflared 先跑 `winget install --exact --id Cloudflare.cloudflared`。裝完當下的 PowerShell 找不到 `cloudflared`（PATH 要重開才更新），所以直接給完整路徑：

     ```powershell
     & 'C:\Program Files (x86)\cloudflared\cloudflared.exe' tunnel --url http://127.0.0.1:<app port> --http-host-header localhost   # app 不檢查 Host 就拿掉最後兩個字
     ```

     請使用者把輸出裡 `https://<隨機>.trycloudflare.com` 那行給你，從這邊驗：

     ```bash
     ~/.claude/skills/expose-port/scripts/expose-port-quick-tunnel verify --url <那個網址> --path <路徑> \
       --expect-without <碼> --expect-with <碼> --auth-header-cmd '<印出 header 的指令>' -- <curl 參數>
     ```

   完成條件：輸出出現 `公網驗證：不帶驗證=<碼>（要 <碼>），帶驗證=<碼>（要 <碼>）` 兩邊相符，接著 `公開網址：https://…`。驗證沒過時 `open` 已經停掉 cloudflared、exit 1；`verify` 沒過就照第 4 步請使用者收掉。原因照 [reference.md](reference.md) 查。
3. **交網址**：把 `公開網址` 那行交給 app skill 或使用者。
4. **收掉**：
   收乾淨的判準：轉那個 port 的 cloudflared 剩 0 個，**而且**從公網打網址連不上（Cloudflare 回 `530`，或公開 DNS 查不到）。停掉叫 cloudflared 的那一端（ssh、WSL）不會停掉 Windows 上的 `cloudflared.exe`（2026-11-05 在 henry-laptop 實測），要另外停。
   - **這台**：對背景那支送 SIGTERM。它停掉 cloudflared（`CLOUDFLARED` 叫 Windows 的時候也從 PowerShell 停 `cloudflared.exe`），再從公網確認。完成條件：輸出有 `cloudflared → :<port> 剩 0 個（要 0）` 和 `公網 https://…：530`（或公開 DNS 查不到），exit 0。背景那支已經不在時，跑 `expose-port-quick-tunnel close --port <app port> --url <公開網址>`，完成條件相同（沒有網址時不帶 `--url`，只確認行程數）。
   - **那台**：請使用者在 cloudflared 視窗按 Ctrl+C，再貼下面這行；接著從你這邊跑 `expose-port-quick-tunnel check-closed --url <公開網址>`。

     ```powershell
     Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force; (Get-Process cloudflared -ErrorAction SilentlyContinue | Measure-Object).Count
     ```

     完成條件：印出 `0`（假設那台沒有別的 cloudflared），`check-closed` exit 0。

   接著由 app 停掉它的 server（app 的文件寫怎麼確認沒有程式在聽那個 port）。
