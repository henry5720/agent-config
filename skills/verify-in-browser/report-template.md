# 瀏覽器驗收發布規則

驗收結果是 [result.schema.json](result.schema.json) 規定的 JSON（填法見[契約](result-contract.md)）；給人看的 Markdown 由 `scripts/render-report.py` 產生，格式以 script 為準。

## 誰發布

| 呼叫者 | 誰發、發在哪 |
|---|---|
| runner | runner 自己寫 PR body，你只交 JSON |
| `pr-review-and-verify` | 它併進收尾 comment，你只交 JSON 與 `<E>` |
| 其他（互動 session） | 你發。這個分支有 PR（`gh pr view --json number`）就問使用者一次：「要把這份回報發成 PR #<N> 的 comment 嗎？」同意才照下面發；不同意或沒有 PR，回報列出 `<E>` 路徑，並說明暫存資料夾不會長久保留 |

L0 沒有瀏覽器驗收 comment，PR body 的 `## 驗證` 寫「未開瀏覽器：<原因>」。

## 怎麼發

在證據資料夾執行，`before` 與 `evidence` 裡每個圖片、影片都附上。`<E>` 不在 repo 裡，`gh` 推不出 repo，一定要帶 `-R`：

```sh
cd <E>
uv run <render-report.py> result.json > report.md
gh pr comment <PR> -R <owner>/<repo> -F report.md $(uv run <render-report.py> result.json --attach-list | sed 's/^/--attach /')
```

- render 提示分則時，用 `--part K` 依序產生。整合分支驗某張子票時，標題加票號。
- render 先驗 schema 與跨欄位語意，格式錯先修 JSON 再 render。
- 要更新已發的 comment 時原地改：已上傳的圖沿用原網址 PATCH；要新上傳就用 `gh pr comment -R <owner>/<repo> --edit-last --attach`。發布的內容不寫本機路徑；自己補寫的圖片用 `![](./x)`，`--attach` 不改寫 `<img src>`。
- `--attach` 被拒太大時，照 `compress-video` 剪短再傳。

## 證據檢查

- 截圖、錄影須是對應 SHA 的實測證據，不用示意圖替代。發布前遮蔽實際出現的密碼、token、API key 與登入憑證；trace、影片、storage state 各自檢查，遮蔽截圖不代表清理了其他檔案。
- snapshot、trace、`auth*.json`、`.playwright-cli/` 不是證據，留在 `<E>`。正常測試業務資料（姓名、email、對話）照常保留。
