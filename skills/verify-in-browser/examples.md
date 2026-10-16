
# 範例：各級別的驗收 comment

---

## L0 — 純邏輯改動（不發 comment，只寫在 PR body）

```markdown
## 驗證
- `pnpm test run src/app/modules/inventory/utils` → 2 files, 18 passed
- 未開瀏覽器：只改 `maintenancePlan.ts` 的計算，沒碰畫面
```

---

## L1 — 修 bug：空清單提示文字

## 瀏覽器驗收

**結論：** 空清單改顯示「尚無維護計畫」，有資料時畫面不變。

| SHA | 引擎 | 視窗 | 語系／主題 | 角色 | 後端 | 資料 |
|---|---|---|---|---|---|---|
| `a2f11e9` | Chromium | 1440×900 | zh-TW／淺色 | admin | staging | 真實 API |

**怎麼驗的：** 開 `/inventory/maintenance`，篩選到沒有結果的部門，再切回有資料的部門。

| 狀態 | 改前（`origin/dev`） | 改後（PR） |
|---|---|---|
| 空清單 | ![](./before-empty.png) | ![](./after-empty.png) |
| 有資料 | ![](./before-list.png) | ![](./after-list.png) |

**console：** 0 個新錯誤（登入頁 S3 logo 403 原本就有）
**未驗：** WebKit — 沒命中引擎差異清單；深色主題 — 這次沒改樣式

---

## L2 — 新功能：批次清除（沒有改前）

## 瀏覽器驗收

**結論：** 批次清除走完確認 → 執行 → toast → 清單更新，取消時不送出 request。

| SHA | 引擎 | 視窗 | 語系／主題 | 角色 | 後端 | 資料 |
|---|---|---|---|---|---|---|
| `a2f11e9` | Chromium | 1440×900 | zh-TW／淺色 | admin | staging | 真實 API |

**怎麼驗的：** 勾 3 筆 → 清除 → 取消；再勾 3 筆 → 清除 → 確認，看 toast 和清單筆數。

| 狀態 | 改後（PR） |
|---|---|
| 確認對話框 | ![](./after-confirm.png) |
| 成功 toast、清單剩 12 筆 | ![](./after-done.png) |

錄影：`clear-flow.webm`（取消 → 再操作 → 確認，約 20 秒）

**console：** 0 個新錯誤
**未驗：** 清除失敗的錯誤 toast — staging 觸發不了 500；viewer 角色 — 沒有測試帳號

---

## L3 — iframe 嵌入（命中引擎差異清單）

## 瀏覽器驗收

**結論：** 兩個引擎都能在 app 內開啟 dashboard，關閉後舊 session 回 401。

| SHA | 引擎 | 視窗 | 語系／主題 | 角色 | 後端 | 資料 |
|---|---|---|---|---|---|---|
| `523849a` | Chromium | 1440×900 | zh-TW／淺色 | company A member | staging | 真實 API（403／404 為 mock） |
| `523849a` | WebKit（Linux Playwright，不等於 Safari） | 1440×900 | zh-TW／淺色 | company A member | staging | 真實 API（403／404 為 mock） |

**怎麼驗的：** 點 dashboard 卡片 → 看 iframe 內 3 筆資料 → 工具列 reload → 關閉 → 用舊 bearer 重送。

| 狀態 | Chromium | WebKit |
|---|---|---|
| 內嵌資料 | ![](./after-chromium-rows.png) | ![](./after-webkit-rows.png) |
| 403（mock） | ![](./after-chromium-403.png) | ![](./after-webkit-403.png) |

**console：** 0 個新錯誤（兩個引擎）
**未驗：** 真 Safari／macOS — 沒有機器；WebKit 原生整頁 refresh — Linux WebKit 在登入頁就 crash，與本次無關

---

## 斷斷續續的問題 — 圖示閃爍（照 #2931）

## 瀏覽器驗收

**結論：** 修法有效：大量 re-mount 已快取圖示時不再閃空白；單顆圖示本來就不閃。

| SHA | 引擎 | 視窗 | 語系／主題 | 角色 | 後端 | 資料 |
|---|---|---|---|---|---|---|
| `b765f45` | Chromium | 1440×900 | zh-TW／淺色 | admin | local | 真實 API |

**怎麼驗的：** 兩個 dev server（`origin/dev`、PR head），同一份 React 反覆 mount 已快取圖示，每個 `requestAnimationFrame` 檢查有沒有 `opacity: 0` 佔位。

| 情境 | 改前（`origin/dev`） | 改後（PR） |
|---|---|---|
| 一次 re-mount 500 顆，30 次 | 30/30 閃空白 | 0/30 |
| 每 400ms re-mount 400 顆，15 次（錄影） | 15/15 | 0/15 |
| 單顆 re-mount，200 次（反向對照） | 0/200 | 0/200 |

同一時刻的 frame：![](./same-frame-before-vs-after.png)

**console：** 0 個新錯誤（S3 logo 403 原本就有）
**未驗：** 真實頁面（table 重繪、條件渲染）— 只單獨 mount `ScIcon`
