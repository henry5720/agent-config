# 用 playwright-cli 時

[SKILL.md](SKILL.md) 的流程照走，這份補 `playwright-cli` 的寫法。指令用法看 `playwright-cli` skill（或 `playwright-cli --help`）。

## 名字

session `S` = 證據資料夾的 `<名字>`（`<repo 名>-<分支名>`，`/` 換成 `-`），整趟照抄成字面值。L3 的 WebKit 用 `S-webkit`；改前對照用 `S-before`。

## 每個指令的寫法

```bash
cd <E> && playwright-cli -s=<S> <指令>
```

- **每次都要 `cd <E> &&`。** cwd 不會留到下一個指令，而 `playwright-cli` 會在當下目錄寫 `.playwright-cli/`。少了 `cd`，這些檔會落在 repo 裡。
- **每次都要 `-s=<S>`。** 不帶就用 `default` session，平行的 agent 會搶同一個瀏覽器。
- `--filename`、`state-save`、`state-load` 給絕對路徑 `<E>/…`，登入憑證 `auth.json`、`auth-<前綴>.json` 才會留在 `<E>`、不落進 repo。多角色各用 `<S>-<前綴>` session 與 `auth-<前綴>.json`，下方單角色例子照此替換。
- WebKit：先確認有裝 `ls ~/.cache/ms-playwright | grep -q webkit`，沒有就 `playwright-cli install-browser webkit`。開啟用 `open --browser=webkit <url>`，搭配 `-s=<S>-webkit`。

## 步驟對應的指令

| SKILL.md 步驟 | 指令 |
|---|---|
| 1. 開頁面、固定 viewport | repo 有設定檔時先解析絕對路徑，`open --config=<設定檔絕對路徑> <url>`，切到 `<E>` 後仍用該路徑；沒有就 `open <url>`。再 `resize 1440 900`。語系設在設定檔的 `browser.contextOptions.locale`，頂層不生效 |
| 4. 截圖 | `screenshot --filename=<E>/after-<狀態>.png` |
| 4. 錄影 | `video-start <E>/<流程>.webm`／`video-stop` |
| 4. 確認結構 | `snapshot --filename=<E>/<狀態>.yml` 或 `find "<文字>"` |
| 4. console | `console error` |
| 4. mock | `route` 攔截，資料來源記「mock」 |
| 5. 收尾 | 每個 session `close`（`attach` 的見 [hitl.md](hitl.md)）；刪掉 `<E>/.playwright-cli/` 與所有 `<E>/auth*.json` |

## 登入

1. **帶既有的登入狀態。** `<E>/auth.json` 已經有就 `state-load <E>/auth.json`。repo 有拿 token 的方法就 `--raw localstorage-set <key> "<token>"` 再 `goto`。
2. **填表單。** 密碼一進欄位就會到處出現（0.1.22 實測：`find`、填完後任何動作自動存的 `.playwright-cli/page-*.yml`，都含明文），所以：
   - 欄位用 selector 指（`'input[type=password]'`、`'getByPlaceholder("密碼")'`），不必先 snapshot。
   - 填密碼，值只在展開裡：

     ```bash
     cd <E> && playwright-cli -s=<S> --raw fill 'input[type=password]' "${X_PASSWORD:-$(grep -m1 '^X_PASSWORD=' <帳密檔絕對路徑> | cut -d= -f2- | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")}"
     ```

   - 每個 `fill`、`localstorage-set` 都加 `--raw`：不加會把產生的 Playwright code 連同值印回對話。
   - 填完密碼的下一個指令就是 `--raw click <送出按鈕>`。
   - 送出後馬上 `rm -rf <E>/.playwright-cli`，再確認登入：`--raw eval "<判斷式>"`。
   - 失敗時重開登入頁用 `goto`；成功就 `state-save <E>/auth.json`。

## 0.1.22 踩過的雷

| 症狀 | 做法 |
|---|---|
| 整棵 accessibility tree 印進對話 | 裸 `snapshot` 會直接印（官方 skill 寫存檔，實際沒有）。一律 `--filename` 或 `find` |
| 密碼、token 出現在對話或檔案 | 見「登入」 |
| repo 多出 `.playwright-cli/` | 少了 `cd <E> &&` |
