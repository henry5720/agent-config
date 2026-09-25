---
name: company-imagegen-fallback
description: 內建 image_gen tool 不可用且使用者明確要求生圖或編輯圖片時，使用本機 fallback wrapper。
# wrapper 讀的是 ~/.codex/config.toml 的 provider，只給 codex。
targets: [codex]
---

# Company ImageGen fallback

只有在內建 `image_gen` tool 不可用，而且使用者明確要求生圖時，才使用這個 fallback。

## 使用方式

在工作區執行 wrapper，將產出指定到 `output/imagegen/`：

```bash
~/.local/bin/imagegen-fallback generate \
  --prompt "使用者要求的圖片描述" \
  --out output/imagegen/result.png
```

一般圖片編輯也可以使用同一個 wrapper 的 `edit`：

```bash
~/.local/bin/imagegen-fallback edit \
  --image path/to/input.png \
  --prompt "使用者要求的修改" \
  --out output/imagegen/edited.png
```

所有產出都放在目前工作區的 `output/imagegen/`；不要把產出寫到其他位置，除非使用者
明確指定。

## 憑證與範圍

- 不要讀取、顯示、複製或猜測 API key，也不要把 key 放進 prompt、指令、文件或輸出。
- wrapper 會從 `~/.codex/config.toml` 讀取目前 `model_provider` 的設定，並在執行期間提供
  `OPENAI_BASE_URL` 與 `OPENAI_API_KEY`；不要自行設定或要求使用者貼 key。
- 不要覆蓋系統的 `imagegen` skill，也不要修改 `~/.codex` 裡的 runtime skill。
