# 一般對話何時主動使用視覺呈現：研究

研究日期：2026-10-09。支援決策票：[show-me 本地改動的去留](https://github.com/henry5720/agent-config/issues/17)。這是研究建議，不代表使用者已決定修改全域指引或 skill。

## 結論

建議全域偏好以「讓讀者更容易理解目前問題」決定呈現形式，不把流程、元件關係、狀態變化寫成情境白名單。這三種是例子；比較、比例、排名、分布、地理、程式形狀與修改前後也可能適合圖、表、樹或 diff。[S1][S2][S3]

寬鬆指引仍應要求簡單、少量、平台可閱讀。目的不是每次畫圖，而是不用使用者另行要求就能選適合的形式。以下是綜合來源後的指引草案，沒有研究或實測證明此措辭會保證 agent 主動採用：

> 主動選擇最容易理解的呈現方式；當圖、表、樹狀結構或具體示例比文字更清楚時，直接使用，無須等我要求。依接收平台選擇能直接閱讀的形式，只保留回答目前問題所需的資訊；簡單內容用短文。

將「能直接閱讀」套用到具體平台時，仍需先確認 renderer 與附件能力，不能因為 skill 能產生 HTML 就假定接收者能開啟它。這點是使用者的平台偏好；以下政府指引的適用範圍是統計圖表，並非跨 agent 設定契約。

## 可核對的一手原文

| 來源 | 實際原文 | 對這次問題的意義 |
| --- | --- | --- |
| UK Government Analysis Function，Choosing the right chart | “Think about the message your chart is aiming to get across.” | 先看想讓讀者理解的訊息，再選形式。[S1] |
| 同上，Statistical relationships | “The right chart will depend on the values in your data and the statistical story you’re telling.” | 圖表選擇取決於資料與訊息，並非固定三情境。[S1] |
| 同上，relationships 表 | “Distribution”, “Time series”, “Ranking”, “Deviation”, “Correlation”, “Magnitude”, “Spatial”, “Part-to-whole”, “Flow” | 公開的一手圖表指引已列九種關係，涵蓋流程以外的使用需求。[S1] |
| ONS，Common relationships in data visualisations | “Consider the important trend or comparison you want to convey to the user and use the chart type that best illustrates it.” | 以讀者要理解的趨勢或比較為準。[S2] |
| ONS，Choose simple and familiar charts | “Use simple charts that will be familiar to users whenever possible.” | 給 agent 自由選形式，仍應限制成讀者能理解的簡單形式。[S2] |
| 同上 | “Complex or unfamiliar charts can be difficult to interpret and may obscure the relationships you are trying to display.” | 更複雜的圖並不等於更清楚，不應強制每次作圖。[S2] |
| show-me 上游 | “Pick the smallest view that makes the key point clear.” | 上游本身也是按清晰程度選最小呈現。[S3] |
| show-me 上游 guidance | “Use your judgement and don't overwhelm the user.” | 少量視覺呈現即可，不要求把所有形式都使用一遍。[S3] |

UK 指引另問 “Can I simplify this? Can I break it down in another way? Am I trying to communicate too many messages within one chart?”；在 bar chart guidance 說 “a well structured table can often be as powerful as a chart.”。因此「圖比較清楚才用圖，表或短文也可以」比「有複雜問題就畫圖」更符合來源。[S1]

show-me 除了 Mermaid 互動／流程外，原文還列 pseudocode、runtime call tree、component tree、file tree、diff、完整 copyable code block，以及 UI layout／state comparison 的 focused HTML。把它濃縮成流程、元件、狀態三類，會漏掉它實際提供的其他形式。[S3]

## 適用範圍與未驗

這份研究只核對第一方文件和公開 source。UK 與 ONS 是統計圖表指引，可支撐「依訊息與讀者選形式」以及「不要把情境列死」；不應把它們說成 agent prompting 實驗。show-me 是 skill 作者自己的 source，可核對既有呈現方式和限制。[S1][S2][S3]

上游 show-me 的 frontmatter 仍是 `disable-model-invocation: true`，但本研究未查驗各 client 對此 flag 的實際行為；也沒有在 Claude Code、Codex 或 OpenCode 執行主動選圖實測。全域指引草案不是保證觸發的機制。未修改全域設定、skills、GitHub tickets 或 PR；研究檔未 commit、未 push。

## 來源與取得方式

- [S1] [UK Government Analysis Function：Data visualisation: charts](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-charts/)；讀取完整 HTML，核對 Choosing the right chart、Statistical relationships、Bar charts 章節。
- [S2] [Office for National Statistics：Overall considerations — Choosing a chart type](https://service-manual.ons.gov.uk/data-visualisation/chart-types/choosing-a-chart-type)；從 [Chart types](https://service-manual.ons.gov.uk/data-visualisation/chart-types) 的真實連結進入，讀取完整 HTML，核對 Overview、Common relationships、Choose simple and familiar charts 章節。
- [S3] [humanlayer/skills：show-me SKILL.md](https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md)；讀取 [raw main 全文](https://raw.githubusercontent.com/humanlayer/skills/main/plugins/show-me/skills/show-me/SKILL.md)，核對 frontmatter、呈現例子與 guidance。main 是浮動來源，本文描述的是研究日期取得版本。

實際執行 `curl -L --max-time 30 -sS <來源 URL> -o <暫存檔>` 取得來源，HTML 用 Python 3 標準庫 `html.parser.HTMLParser` 擷取文字。初次猜測的 ONS `/data-visualisation/choosing-a-chart` 為 Page not found，未作為證據；後續由官方入口追到上述正確連結。
