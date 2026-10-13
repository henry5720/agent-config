---
name: archive-branches
description: 封存不會 merge 的分支（wayfinder 的 research/*、prototype 的 prototype/* 這類），結論定案後把內容搬到該去的地方再刪分支。map 或原型定案、這類分支開始堆積、使用者說「封存」「清分支」時使用。
---

# 封存分支

`research/*`、`prototype/*` 這類分支是做決定時的材料，永遠不 merge。決定做完，分支只剩保存的用途，
**封存**（archive）就是把每條分支的內容放到長期會被找到的地方，再刪掉分支，讓分支清單只剩進行中的工作。

## 1. 列出候選

列出 remote 上不會 merge 的分支，逐條確認可以封存：

- 對應的 issue 已關（或 map 已收斂成 spec），而且分支沒有開著的 PR。
- 分支名或第一個 commit 對不到 issue 的，問使用者，不要猜。

完成條件：每條候選都對到一張已關的 issue，或使用者明確說可以封存。

## 2. 決定每條的去處

讀完分支上的每個檔案再決定。同一條分支的不同檔案可以去不同地方：

| 內容 | 去處 |
|---|---|
| 這個 repo 之後還會當現況查的事實、規則、參考資料 | repo 的 docs 或 ADR，開 PR 收進主線。濃縮成仍成立的部分；整份都是長期參考就原文收，標明查核日 |
| 只是當時做決定的歷史紀錄（統計、排程、已被程式碼或 ADR 取代的對照） | 對應 issue 的留言，全文放 `<details>` |
| 要能跑起來回顧的程式碼（原型） | annotated tag `archive/<原分支名>` |
| 純手測頁、假資料，沒有要回答的問題 | 不保存，直接刪 |

- 客戶資料、秘密、個資（客戶的界限值、量測值、token）不進 repo、不貼 issue：放 repo 外，留言與文件只寫結構與規則，數值換成「（略）」。
- 收進 docs 的文件連 issue，不連分支（分支稍後會刪）。

完成條件：每個檔案都有去處，表格列給使用者確認後才動手。

## 3. 搬

- docs／ADR：照 repo 的 PR 流程開 PR，merge 後才刪分支。
- issue 留言：留言開頭寫「研究原文存檔（查核日 YYYY-MM-DD）」與原分支、路徑，說明舊連結會失效。
- tag：`git tag -a archive/<原分支名> origin/<原分支名> -m "<issue> 的原型（結論：…）"`，
  `git push origin archive/<原分支名>`，再用 `git ls-remote --tags origin 'archive/*'` 確認 tag 指向原分支頂端。
  issue 補一則留言放 tag 連結（`/tree/archive/<原分支名>`）與 `git checkout archive/<原分支名>`。

完成條件：每個去處都看得到內容：PR 已 merge、留言網址、remote 上的 tag。

## 4. 刪分支

```
git push origin --delete <分支…>
git fetch --prune origin
```

刪分支與貼客戶來源內容可能被權限擋下：把整理好的指令交給使用者用 `!` 執行，不換別的方式繞過。

完成條件：`git branch -r` 列不到這些分支，tag 仍在。
