# 瀏覽器驗收發布規則

驗收結果是 [result.schema.json](result.schema.json) 規定的 JSON；給人看的 Markdown 由 `scripts/render-report.py` 產生。誰發布照 [hitl.md](hitl.md)「發布」；這份只管怎麼發。

- 在證據資料夾執行，`evidence` 裡每個圖片、影片都附上：
  ```sh
  cd <E>
  python3 <render-report.py> result.json > report.md
  gh pr comment <PR> -F report.md $(python3 <render-report.py> result.json --attach-list | sed 's/^/--attach /')
  ```
  `--attach` 只把 Markdown 的 `![alt](./x.png)` 換成上傳後的網址，HTML `<img src>` 不換，所以圖片一律寫 `![](./x)`。單則 comment 最多 50 個附件；超過時 render 在 stderr 印出則數，第 K 則用 `--part K` 產生內文與 attach 清單，依序發。整合分支驗某張子票時，標題加票號。
- 發布的內容只用 `./` 相對路徑或上傳後的網址；render 的輸出已符合，自己補寫的文字也照這樣寫。
- `.webm` 發布前照 `compress-video` 轉成 H.264 mp4，JSON 證據路徑改成 `.mp4` 後重新 render。GIF 直接附。沒有 ffmpeg 就附原 `.webm`，在該條 observed 註明「未轉檔，Safari 可能播不出」。`--attach` 被拒太大時，照 `compress-video` 剪短再傳。
- 截圖、錄影須是對應 SHA 的實測證據，不用示意圖替代。發布前遮蔽實際出現的密碼、token、API key 與登入憑證；trace、影片、storage state 各自檢查，遮蔽截圖不代表清理了其他檔案。
- 附件就是 `--attach-list` 列出的檔案；snapshot、trace、`auth*.json`、`.playwright-cli/` 不是證據，留在 `<E>`。正常測試業務資料（姓名、email、對話）照常保留。
