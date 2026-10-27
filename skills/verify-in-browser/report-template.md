# 瀏覽器驗收發布規則

驗收結果是 [result.schema.json](result.schema.json) 規定的 JSON；給人看的 Markdown 由 `scripts/render-report.py` 產生。誰發布照 [hitl.md](hitl.md)「發布」；這份只管怎麼發。

- 把 render 結果存成檔案，在證據資料夾執行 `gh pr comment <PR> -F <回報檔> --attach './x.png'`。body 中各證據路徑改成 `./<相對路徑>`，每個附件各帶一個相同路徑的 `--attach`，上傳後會換成網址。整合分支驗某張子票時，標題加票號。
- `.webm` 發布前照 `compress-video` 轉成 H.264 mp4，JSON 證據路徑改成 `.mp4` 後重新 render。GIF 直接附。沒有 ffmpeg 就附原 `.webm`，在該條 observed 註明「未轉檔，Safari 可能播不出」。`--attach` 被拒太大時，照 `compress-video` 剪短再傳。
- 截圖、錄影須是對應 SHA 的實測證據，不用示意圖替代。發布前遮蔽實際出現的密碼、token、API key 與登入憑證；trace、影片、storage state 各自檢查，遮蔽截圖不代表清理了其他檔案。
- 附件只挑證據檔；snapshot、trace、`auth*.json`、`.playwright-cli/` 留在 `<E>`。正常測試業務資料（姓名、email、對話）照常保留。
