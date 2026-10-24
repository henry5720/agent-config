# 逐條判定契約

結構唯一來源是 [result.schema.json](result.schema.json)：JSON Schema draft-07，所有欄位必填、用不到填 `null`，物件不收多餘欄位。`criteria` 每筆先寫 `observed` 再下 `status`。

## 判定

- `passed`：看到的畫面符合條件，至少一個證據檔，`reason: null`。
- `failed`：看到的和條件矛盾，`reason` 必填；判不準是環境還是 code 造成時也判 `failed`。
- `skipped`：無法從畫面判定（主觀、不在畫面上、缺角色帳號、需要外部副作用、被本次 diff 沒碰的 staging API 擋住），`reason` 必填。它不是 Playwright healer 的「跳過壞測試」；已觀察到矛盾就填 `failed`。
- `unverifiable`：整份驗收因工具不存在、dev server 起不來、登入失敗等環境問題無法開始。`unverifiableReason` 必填，`criteria: []`，不逐條判。
- `verified`：至少一條 criterion，`unverifiableReason: null`；`criteriaSource: inferred` 時只有 1～3 條。全部 skipped 仍是 verified。

這些跨欄位規則由 render script 與 runner 在 schema 之外驗證，避免把 Claude 結構化輸出不接受的條件關鍵字塞進 schema。

## 證據與來源

`sha` 是實際驗的 commit。`evidenceDir` 是呼叫端可讀取的證據資料夾絕對路徑；runner 呼叫時填 runner 主機上的路徑，sandbox 掛載路徑不同時以呼叫端提供的對照為準。

`evidence` 只放相對 `evidenceDir` 的證據檔名，可用子目錄；不放絕對路徑、`..`、登入狀態、snapshot 或 trace。`account` 是帳號變數前綴（例如 `E2E_ADMIN`），不登入填 `null`，不填帳密。`observed` 三種 status 都必填；記實際操作、引擎／環境、真實 API 或 mock、必要的改前對照或沒拿到的原因，讓人能判讀證據。

`verifier.model` 寫實際判定 model，`same_model` 寫是否與實作相同，不知道時不可猜 true。`consoleErrors` 保留錯誤原文；`related` 對照 diff 分 yes／no／unknown，不確定就 unknown。`stagingRecords` 是 `<E>/state.json` 的筆數，沒有建立資料為 0。

## Render

表格欄位固定為 `條件 | 結果 | 帳號 | 看到什麼／原因 | 證據`。failed／skipped 同時顯示 observed 與 reason；沒有帳號或證據用「—」。console error 的 yes／unknown 逐條列，no 只列數量。附上 model、staging 資料筆數與 inferred 註記。runner 的 PR body 用同欄位與文字自行 render，不呼叫 script。
