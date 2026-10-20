---
name: compress-video
description: 壓影片：把錄影（mp4、webm、mov）壓成給人看的小檔 h264 mp4。使用者說影片太大、要把錄影傳給別人或附到 PR／issue 時使用；其他 skill 要附錄影前也用。
---

# 壓影片

壓出來的影片是**給人看的**：對方點開就要播得出來、看得出發生什麼事。畫質可以很差，
但**播不出來就等於沒送到**。下面每個偏離 ffmpeg 預設的選擇都從這裡推出來。

輸入格式不限（playwright 錄影是 `.webm`、手機是 `.mov`），輸出一律 h264 mp4。
直接用 `ffmpeg`，這支 skill 提供的是判斷。

## 1. 先量原檔

先 `ffmpeg -version | grep -o enable-libx264`；沒輸出就照最下面「沒有 ffmpeg」處理再繼續。

```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate \
  -of default=nw=1 IN.webm
```

**做完的條件**：講得出長度、解析度、fps、大小，以及使用者有沒有給目標大小。
90 秒 4K 60fps 和 15 秒 720p 30fps，該動的參數完全不同。

## 2. 決定要留哪幾秒

兩分鐘的錄影裡通常只有幾秒是重點。剪掉其餘的比任何 codec 參數都有效，而且不損畫質。
問使用者「哪一段是要給人看的」，前後各留 2 秒上下文。

**做完的條件**：有一組起訖時間，或確定整支都要。

## 3. 剪跟壓一條指令

```bash
ffmpeg -y -hide_banner -ss 00:00:38 -to 00:00:52 -i IN.webm \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:v libx264 -crf 28 -preset slow -pix_fmt yuv420p \
  -an -movflags +faststart out.mp4
```

整支都要就拿掉 `-ss`／`-to`。**`-ss` 放在 `-i` 前面**，剪跟壓合成一條：分兩步先用
`-c copy` 剪、`-ss` 又放在 `-i` 後面時，開頭到前一個 keyframe 的畫面會整段丟掉 ——
實測從 8.7 MB 的影片剪 6 秒只剩 53 KB，下一步直接 `Output file does not contain any stream`。

| flag | 為什麼 |
|---|---|
| `scale=trunc(iw/2)*2:…` | libx264 + yuv420p 要偶數寬高。playwright 的 webm 可能是奇數尺寸，801×601 實測直接 `width not divisible by 2`、輸出 0 byte；加了這個裁成 800×600。偶數輸入不受影響 |
| `libx264` | 到處都播得動。相容性 > 檔案大小 |
| `-crf 28` | 糊到看得出發生什麼事就夠。UI 文字會最先糊 |
| `-pix_fmt yuv420p` | 螢幕錄影常吐 4:4:4 或 10-bit，很多播放器不解 |
| `-an` | 聲音通常沒用。有口述講解才拿掉 |
| `+faststart` | moov 移到檔頭，網頁上才能邊載邊播 |

VFR 的 webm 照上面指令壓，實測正常；要固定 fps 用下面的 `-r`。

**h265 只在確定收件人整條路徑都在 Apple 生態（macOS + Safari／QuickTime）時用。**
HEVC 能不能播取決於對方的 OS、GPU、瀏覽器，點開黑畫面就白壓了。要用時：

```bash
ffmpeg -y -hide_banner -ss 00:00:38 -to 00:00:52 -i IN.webm \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:v libx265 -crf 30 -preset slow -pix_fmt yuv420p -an -tag:v hvc1 -movflags +faststart out.mp4
```

h265 的 crf 刻度跟 h264 不同：x265 的 28 瞄準的畫質比 x264 的 28 高。實測同一段 14 秒 1080p，
h264 crf 28 出 4.8 MB、h265 crf 28 出 8.7 MB 且慢 7 倍。要 h265 真的省，crf 得拉到 30–32，
而且壓完看實際數字，不要承諾壓縮比。

### 有目標大小

使用者給了上限（例如「10 MB 以內」）就照它；沒給就先照上面壓，壓完看實際大小。
需要硬性上限時反推碼率：**碼率（Mbps）≈ 目標 MB × 8 ÷ 秒數**，取九成留餘裕，加在 `-crf` 後面：

```bash
  -crf 28 -maxrate 0.7M -bufsize 1.4M    # 目標 1 MB、10 秒：0.8M 取九成
```

畫面簡單時 crf 會讓它更小，複雜時被 maxrate 壓住。實測 10 秒 1080p60：目標 1 MB 出 0.95 MB、
目標 2 MB 出 1.89 MB。

### 還是太大

上傳被拒或超過目標時，照這個順序往下砍：

1. **再剪短** —— 先回頭問還有沒有可以砍的段落
2. **降解析度** `-vf scale=-2:720`，直式（手機）錄影用 `scale=720:-2`。`-2` 會自動取偶數，
   所以直接換掉步驟 3 的 `-vf`（只能有一個 `-vf`）
3. **砍 fps** `-r 15` —— UI 操作 15fps 看得懂；動畫或捲動流暢度就是重點時才留著
4. **最後才拉 crf**（32、36）—— 文字最先糊，而文字常常就是重點

```bash
ffmpeg -y -hide_banner -ss 00:00:38 -to 00:00:52 -i IN.webm \
  -vf scale=-2:720 -r 15 -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p \
  -an -movflags +faststart out.mp4
```

細調 crf／preset 時看 FFmpeg 官方 H.264 指南：<https://trac.ffmpeg.org/wiki/Encode/H.264>。

## 4. 驗

把重點那一秒抽成圖：

```bash
ffmpeg -y -hide_banner -loglevel error -ss 00:00:06 -i out.mp4 -frames:v 1 check.png
ls -l out.mp4
```

`-ss` 是**壓完那支**的時間軸：剪掉前面 38 秒後，原檔第 44 秒在 `out.mp4` 是第 6 秒。

用 Read 讀 `check.png`。**做完的條件**：圖上認得出重點 —— 錯誤訊息讀得出來、該紅的地方是紅的。
認不出來就是壓過頭，回「還是太大」退一級。驗完刪掉 `check.png`。

## 5. 交

回報三件事：**壓完多大、從多大壓來、輸出路徑**。上傳交給呼叫端或使用者；
被拒說太大時，回「還是太大」往下砍。

---

## 沒有 ffmpeg

`ffmpeg -version` 不通就先裝：Debian/Ubuntu `sudo apt install ffmpeg`、macOS `brew install ffmpeg`。
裝完確認有 `libx264`（`ffmpeg -version | grep -o enable-libx264`），沒有的話上面每條指令都會失敗。
