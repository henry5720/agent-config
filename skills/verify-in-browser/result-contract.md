# 逐條判定契約

結構唯一來源是 [result.schema.json](result.schema.json)：JSON Schema draft-07，所有欄位必填、用不到填 `null`，物件不收多餘欄位。給人看的格式由 `scripts/render-report.py` 決定，這份只管每個欄位填什麼。`criteria` 每筆先寫 `steps`、`observed` 再下 `status`。

## 判定

- `passed`：看到的畫面符合條件，至少一個證據檔，`reason: null`。
- `failed`：看到的和條件矛盾，`reason` 必填；判不準是環境還是 code 造成時也判 `failed`。
- `skipped`：無法從畫面判定（主觀、不在畫面上、缺角色帳號、需要外部副作用、被本次 diff 沒碰的 staging API 擋住），`reason` 必填。它不是 Playwright healer 的「跳過壞測試」；已觀察到矛盾就填 `failed`。
- `unverifiable`：整份驗收因工具不存在、dev server 起不來、登入失敗等環境問題無法開始。`unverifiableReason` 必填，`criteria: []`，不逐條判；已拍的證據檔名寫進 `unverifiableReason`。
- `verified`：至少一條 criterion，`unverifiableReason: null`；`criteriaSource: inferred` 時只有 1～3 條。全部 skipped 仍是 verified。

這些跨欄位規則由 render script 在 schema 之外驗證，避免把 Claude 結構化輸出不接受的條件關鍵字塞進 schema。

## 環境：整趟寫一次

`environment` 放每條都一樣的事，條件裡不再重寫。每格一句，沒有就 `null`：

| 欄位 | 寫什麼 | 例 |
|---|---|---|
| `frontend` | 驗的是哪裡跑的哪個 commit | `本機 dev server @ 80dec84f32` |
| `backend` | 哪台後端，與後端版本怎麼確認的 | `api.scfg.io（版本：openapi 有 node-types，用欄位推斷）` |
| `browser` | 引擎、viewport、語系、主題 | `Chromium 1440×900、zh-TW、淺色` |
| `data` | 讀寫的原則 | `讀取走真實 API；寫入以 route 攔截回 mock，共用環境 0 筆` |
| `before` | 改前畫面從哪來（網址、部署 commit、資料來源） | `線上部署 https://…（部署 commit def456）` |

## 每一條

- `criterion`：issue 的原文，或推出來的條件；不改寫。
- `steps`：照順序，一步一個字串，寫動作不寫結果（「選 Gemini Flash Lite」「填 70000」「按套用」）。mock 了什麼也寫成一步（「node-types 回 500」）。`skipped` 沒操作時給 `[]`。
- `observed`：只寫看到什麼，一兩句，帶畫面上的原文（toast、警告、按鈕字）。環境、步驟、資料來源已有自己的欄位，不重寫。有改前時寫改前看到什麼。
- `dataSource`：這條用的資料是 `real`、`mock`，或兩者都有 `mixed`；沒操作的 `skipped` 填 `null`。`passed`、`failed` 必填。
- `account`：帳號變數前綴（例如 `E2E_ADMIN`），不登入填 `null`，不填帳密。
- `evidence` 放改後的證據檔名，`before` 放改前的，都相對 `evidenceDir`、可用子目錄；每個證據檔都要出現在某條的 `before` 或 `evidence`（`unverifiable` 時在 `unverifiableReason`）。絕對路徑、`..`、登入狀態、snapshot、trace 不算證據。證據存成圖片、mp4 影片，或 UTF-8 文字檔（console、request、測試輸出）。

`change` 照 [SKILL.md](SKILL.md)「改前對照」逐條填：
- `fixed`：`before` 非空時 `beforeReason: null`；`before` 為空時 `beforeReason` 必填（拿不到改前的原因），兩者擇一。
- `changed`：`before` 可空，`beforeReason: null`。
- `kept`、`new`：`before: []`、`beforeReason: null`。

## 其他欄位

`sha` 是實際驗的 commit。`evidenceDir` 是呼叫端可讀取的證據資料夾絕對路徑；runner 呼叫時填 runner 主機上的路徑，sandbox 掛載路徑不同時以呼叫端提供的對照為準。`verifier.model` 寫實際判定 model，`same_model` 寫是否與實作相同，不知道時不可猜 true。`consoleErrors` 保留錯誤原文；`related` 對照 diff 分 yes／no／unknown，不確定就 unknown。`stagingRecords` 是 `<E>/state.json` 的筆數，沒有建立資料為 0。
