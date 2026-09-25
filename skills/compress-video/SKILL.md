---
name: compress-video
description: 把螢幕錄影壓成能貼進 Slack 回報的證據影片。當使用者說「影片太大」「壓一下影片」「錄了測試影片要傳給 PM」時使用；其他 skill 要把錄影附進回報前也用。
---

# 證據影片

錄下來的測試影片是**證據**，不是作品。它只需要做到一件事：PM 打開它，
看得出那個 bug 發生在哪一格。取捨全部從這裡推出來 —— 畫質可以很差，
但**播不出來就等於沒有證據**。

用 `ffmpeg`，不要包一層腳本。這支 skill 提供的是判斷，不是指令別名。

---

## 🚫 先講會做壞的三件事

1. **預設用 h265** —— 它省最多，但 HEVC 能不能播取決於對方的 OS、GPU 和瀏覽器，
   是擲骰子。PM 在 Slack 裡點開看到黑畫面，證據就沒送到。
   **預設 h264**；h265 只在你確定收件人整條路徑都在 Apple 生態（macOS + Safari／
   QuickTime）時才用，那時才需要 `-tag:v hvc1`。
2. **沒剪就整支壓** —— 兩分鐘的錄影裡通常只有 8 秒是證據。剪掉其餘的比任何
   codec 參數都有效，而且不損畫質。剪跟壓是**同一條指令**（步驟 3），不是兩步。
3. **想走 `slack-list` 上傳** —— 它不吃 mp4。artifact 白名單是
   `.html .md .css .js .json .png .zip`（`../slack-list/scripts/slack-list:71`），remote 更窄，
   只剩 `.png .md .html`（`../slack-list/scripts/slack-list:75`），單檔上限 10 MB（`../slack-list/scripts/slack-list:78`）。
   影片是**你自己拖進那一列的 item 留言串**，工具幫不上忙。

---

## 1. 先量原檔

```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate \
  -of default=nw=1 IN.mp4
```

**做完的條件**：你講得出長度、解析度、fps、大小。不看就壓等於猜要調哪個參數 ——
90 秒的 4K 60fps 和 15 秒的 720p 30fps，該動的東西完全不同。

## 2. 決定哪幾秒是證據

問使用者「哪一段在證明這件事」，前後各留 2 秒讓 PM 看得到上下文。

**做完的條件**：你有一組起訖時間，或確定整支都是證據。

## 3. 剪跟壓一起做

```bash
ffmpeg -y -hide_banner -ss 00:00:38 -to 00:00:52 -i IN.mp4 \
  -c:v libx264 -crf 28 -preset slow -pix_fmt yuv420p \
  -an -movflags +faststart out.mp4
```

整支都要就拿掉 `-ss`／`-to`。**`-ss` 一定放在 `-i` 前面** —— 放後面的話它是輸出選項，
配 `-c copy` 會把該段開頭到前一個 keyframe 之間的畫面整段丟掉。實測：從一支 8.7 MB
的影片剪 6 秒出來只剩 53 KB，下一步直接罵 `Output file does not contain any stream`。
剪跟壓合成一條就不會踩到，因為這裡本來就要重編碼。

每個 flag 都在服務「證據」：

| flag | 為什麼 |
|---|---|
| `libx264` | 到處都播得動。相容性 > 檔案大小 |
| `-crf 28` | 糊到看得出發生什麼事就夠。要更小往上加，UI 文字會先糊掉 |
| `-pix_fmt yuv420p` | 螢幕錄影常吐 4:4:4 或 10-bit，很多播放器不解 |
| `-an` | 聲音通常不是證據。有口述講解才拿掉這個 flag |
| `+faststart` | moov 移到檔頭，Slack 才能邊載邊播，不用整支載完 |

收件人確定是 Apple 生態（macOS + Safari／QuickTime）時，才換 h265：

```bash
ffmpeg -y -hide_banner -ss 00:00:38 -to 00:00:52 -i IN.mp4 \
  -c:v libx265 -crf 30 -preset slow -an -tag:v hvc1 out.mp4
```

**h265 的 `-crf 28` 不等於 h264 的 `-crf 28`。** CRF 是品質目標不是壓縮率，兩個
codec 的刻度不同 —— x265 的 28 瞄準的畫質比 x264 的 28 高，所以檔案**不一定比較小**。
實測同一段 14 秒 1080p：h264 crf 28 出 4.8 MB，h265 crf 28 出 8.7 MB，而且慢 7 倍。
所以不要承諾壓縮比，**壓完看實際數字**；要 h265 真的省，crf 得往上調到 30–32。

### 還是太大

照這個順序往下砍，不要跳著調：

1. **再剪短** —— 一律先回頭問還有沒有廢話可以砍
2. **降解析度** `-vf scale=-2:720`（4K/1440p 錄的一定要做這步）
3. **砍 fps** `-r 15` —— UI 操作 15fps 完全看得懂，動畫或捲動流暢度是證據時才留著
4. **最後才拉 crf**（32、36）—— 文字最先糊，而文字常常就是證據本身

三樣一起上：

```bash
ffmpeg -y -hide_banner -ss 00:00:38 -to 00:00:52 -i IN.mp4 \
  -vf scale=-2:720 -r 15 -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p \
  -an -movflags +faststart out.mp4
```

## 4. 驗

把證據那一秒抽成圖，**真的打開看**：

```bash
ffmpeg -y -hide_banner -loglevel error -ss 00:00:06 -i out.mp4 -frames:v 1 check.png
ls -l out.mp4
```

`-ss` 給的是**壓完那支**的時間軸，不是原檔的 —— 剪掉前面 38 秒之後，原本第 44 秒
的畫面在 `out.mp4` 裡是第 6 秒。

用 Read 讀 `check.png`。**做完的條件**：你在那張圖上認得出 bug —— 錯誤訊息讀得出來、
該紅的地方是紅的。認不出來就是壓過頭，回第 3 步降一級。

驗完刪掉 `check.png`，只留 `out.mp4`。

## 5. 交

告訴使用者三件事：**壓完多大、從多大壓來的、拖進哪裡**。
拖進的地方是那一列的 item 留言串（`slack-list replies Rec…` 讀得到的同一條）。

影片貼上去之後，回報進度走 `slack-list`，見
[slack-list skill](../slack-list/SKILL.md) —— 影片本身不是回報，
留言串裡那段「怎麼重現、預期什麼、實際什麼」才是。

---

## 沒有 ffmpeg

`ffmpeg -version` 不通就先裝：Debian/Ubuntu `sudo apt install ffmpeg`、
macOS `brew install ffmpeg`。裝完確認 `libx264` 有編進去
（`ffmpeg -version | grep -o enable-libx264`），沒有的話上面每一條指令都會失敗。
