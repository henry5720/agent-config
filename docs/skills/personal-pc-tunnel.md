# personal-pc-tunnel

agent 在已配置主機（例如 company-ec2）上做事，一定要用**你日常的 Chrome**（passkey、硬體金鑰、裝置 SSO）時，
它會照這個 skill 請你開一條 ssh 轉發、貼一個網址。agent 怎麼做寫在
[`skills/personal-pc-tunnel/SKILL.md`](../../skills/personal-pc-tunnel/SKILL.md)，這份只寫你要做的事。
只是要看 agent 的畫面或替它登入，不走這條：見 [verify-in-browser](verify-in-browser.md)。

## 你要做的

1. **第一次**：日常 Chrome 裝 [Playwright Extension](https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm)。
2. **每次**：個人電腦開 `ssh -N company-ec2-attach`（dotfiles 的 ssh config 帶的別名，等於
   `ssh -N -L 127.0.0.1:9555:127.0.0.1:9555 company-ec2`），開著別關。說 port 被佔就是你另一台還開著。
3. agent 給你一個 `chrome-extension://…` 網址：貼進**新分頁**的網址列（agent 會直接改這個分頁）。
   沒設 token 時，再在 extension 畫面選這個分頁、按允許。
4. agent 說 detach 了就關掉那條 ssh。Chrome 和分頁都會留著。

agent 只看得到你貼網址的那一個分頁，其他分頁讀不到。

## 只貼網址就好：設 token

extension 的狀態頁上有一個 token（「Set this environment variable to bypass the connection dialog」）。
把它設成**已配置主機那邊**的環境變數 `PLAYWRIGHT_MCP_EXTENSION_TOKEN`（agent 跑的那個 shell 看得到就好，
不要放進任何 repo），之後只要貼網址，不用選分頁。

## 為什麼這樣接

relay 在已配置主機上、只綁 127.0.0.1、沒有驗證，所以只能經 ssh 轉發進去。`playwright-cli` 每次給的 relay
port 是隨機的，`personal-chrome-attach` 把它轉到固定的 9555，你的 ssh 指令才能每次一樣。決策與實測見
dotfiles [#248](https://github.com/henry5720/dotfiles/issues/248)、ADR
[0001](https://github.com/henry5720/dotfiles/blob/main/docs/adr/0001-browser-tools-drive-vs-debug.md)。
