# 派工單：DiveInOut 潛點地圖 v2 + 首頁深度刻度調整

> 規劃/審查：Claude｜實作：Codex｜分支已開好：`spots-map-v2`
> **不要 commit、不要碰 `.git`、不要改 `spots.json`（資料已由 Claude 備好）、不要改 `creatures/`**。做完我會自己開瀏覽器審查再 commit。

## 背景

DiveInOut 是給華語「想潛水的人」看的泛亞洲潛旅生活誌，純靜態網站（GitHub Pages，無 build、無框架、無 npm）。
現在首頁第 04 段「潛點地圖」是一張世界地圖撒 30 個點：沖繩/菲律賓的點擠成一團點不準、手機難操作、只能逐點點開、沒辦法比較或篩選。
讀者真正要回答的問題是：「**我（這個程度）、在這個月、想看某種生物 → 能去哪？**」

## 任務一：新頁面 `spots/index.html`（主要工作）

獨立頁面，網址 `/diveinout/spots/`。可用 `?m=12&lv=beginner` 這類參數分享（例如「12 月能去哪」的連結）。

### 技術限制
- 單一 HTML 檔，CSS/JS 內嵌，跟現有 `index.html`、`creatures/index.html` 同樣做法
- 只能用 CDN：Leaflet 1.9.4（`https://unpkg.com/leaflet@1.9.4/dist/`）＋ Leaflet.markercluster 1.5.3（`https://unpkg.com/leaflet.markercluster@1.5.3/dist/`：`leaflet.markercluster.js`、`MarkerCluster.css`、`MarkerCluster.Default.css`，但群聚圖示要改成下方自訂樣式）
- 資料來源：`fetch('../spots.json')`
- 底圖：直接用 CARTO dark_all 圖磚（`https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png`，右下角保留 attribution「© OpenStreetMap © CARTO」）。**不要**再用 world.geo.json 那套國家多邊形（小島看不到、效能差）

### 視覺語言（沿用首頁，不要另創風格）
CSS 變數直接照抄首頁 `:root`：
```
--ink:#e9fbff; --dim:#8fb3bf; --accent:#2ff3e0; --pop:#ff5470;
--edge:rgba(47,243,224,.28); --card:rgba(255,255,255,.045)
body 背景 #020a10；卡片背景 var(--card)、邊框 1px rgba(255,255,255,.1)、圓角 12px
```
字體、`.lab`（mono 小標＋前面 34px 青色橫線）、`.mono` 樣式照抄首頁。
中文標題：line-height ≥ 1.05、letter-spacing ≥ -0.01em（方塊字不可擠）。
內文文字對背景對比 ≥ 4.5:1（`--dim` 在 #020a10 上可以；不要再調更暗）。

### 資料欄位（`spots.json` → `spots[]`，每筆都有）
| 欄位 | 型別 | 說明 |
|---|---|---|
| id, name, place, lat, lng | string/number | |
| level | string | 原始中文難度（顯示用） |
| type | string | 原始中文入水方式（顯示用） |
| season | string | 原始中文季節說明（顯示用） |
| see | string | 亮點 |
| note | string | 注意事項 |
| warn | boolean | true = 季節/規範資訊需出發前覆核 |
| region | `okinawa`\|`taiwan`\|`philippines`\|`palau`\|`indonesia`\|`thailand`\|`malaysia`\|`maldives`\|`egypt` | |
| levelMin | `beginner`\|`intermediate`\|`advanced` | 最低建議程度 |
| entry | array of `shore`\|`boat`\|`liveaboard`\|`snorkel` | |
| months | int[]（1–12） | 最佳月份 |
| tags | array of `turtle`\|`manta`\|`whaleshark`\|`shark`\|`macro`\|`wreck`\|`school`\|`terrain`\|`coral`\|`mola` | 可見亮點 |

顯示用中文對照：
- region：沖繩、台灣、菲律賓、帛琉、印尼、泰國、馬來西亞、馬爾地夫、埃及
- levelMin：beginner＝新手 OK、intermediate＝建議 AOWD、advanced＝進階（強流/深潛經驗）
- entry：shore＝岸潛、boat＝船潛、liveaboard＝船宿、snorkel＝可浮潛
- tags（附 emoji）：🐢 海龜、🦈 鯊魚、🪽 鬼蝠魟（manta）、🐋 鯨鯊、🔍 微距、⚓ 沉船、🐟 魚群風暴、🪨 地形洞穴、🪸 珊瑚、🌕 翻車魚（mola）

### 版面
**桌機（≥ 960px）**
```
┌──────────────────────────────────────────────────────────┐
│ ← DiveInOut   .lab「DIVE SPOTS / 潛點」  h1 潛點地圖       │
│ 一句說明：選月份、程度、想看的，找出你能去的潛點。          │
├──────────────────────────────────────────────────────────┤
│ 篩選列（sticky top:0，毛玻璃背景 rgba(2,10,16,.82)+blur）   │
├──────────────────────┬───────────────────────────────────┤
│ 結果清單 420px        │ 地圖（填滿剩餘寬度，                │
│ 獨立捲動              │ 高度 = 100dvh − 篩選列高度，sticky）│
│ 「符合 12 / 30 個潛點」│                                   │
│ [卡片] [卡片] …       │                                   │
└──────────────────────┴───────────────────────────────────┘
```
**手機（< 960px）**：篩選列下方一個分段切換 `[ 清單 | 地圖 ]`（預設「清單」）。地圖模式時地圖高 `calc(100dvh - 篩選列 - 切換列)`。在清單點某張卡的「在地圖上看」→ 自動切到地圖並飛到該點。
篩選列在手機上要能橫向滑動（每組一行，`overflow-x:auto`，隱藏捲軸），不可撐爆寬度；整頁不得出現水平捲動，左右留白 16px。

### 篩選（組內 OR、組間 AND）
1. **月份**（單選）：`全部` + `1月`…`12月` 共 13 個 chip。旁邊一個「這個月」快捷鍵，按下選中亞洲時區（Asia/Taipei）的當月。預設 = `全部`。
   規則：選 N 月 → 只留 `months` 含 N 的潛點。
2. **我的程度**（單選，三選一，預設 `全部`）：
   - `全部`
   - `剛拿 OWD / 新手` → levelMin == beginner
   - `有 AOWD` → levelMin ∈ {beginner, intermediate}
   - `進階`（顯示全部，但這個選項存在是為了讓讀者有「被照顧到」的感覺）→ 全部
3. **入水方式**（多選 chip）：岸潛／船潛／船宿／可浮潛 → 潛點 `entry` 與選中的有交集即符合
4. **想看**（多選 chip）：10 個 tags → 潛點 `tags` 與選中的有交集即符合
5. **地區**（下拉 select）：全部＋9 個地區

- 任一篩選變動：更新清單、更新地圖標記（不符合的從地圖移除）、地圖 `fitBounds` 到結果（padding 40px、maxZoom 7；無結果時不動）
- 有篩選時顯示「清除篩選」文字按鈕
- 無結果：清單顯示空狀態「這個組合目前沒有潛點。試試放寬月份或程度？」＋「清除篩選」按鈕
- 狀態同步到 URL query（`m`、`lv`、`e`、`t`、`r`，多選用逗號），用 `history.replaceState`；載入時從 URL 還原

### 清單排序
先依「是否符合目前選的月份」（有選月份時全部都符合，就不影響），再依 levelMin（beginner → advanced），同級依 name。

### 潛點卡片
```
┌───────────────────────────────────────┐
│ 青之洞窟                 [新手 OK]      │  ← 名稱 17px 900；程度 badge 右上
│ 📍 日本・沖繩 恩納村                    │
│ [岸潛] [可浮潛]   🐟 🪨                 │  ← entry badge + tags emoji（title 屬性寫中文）
│ 1 2 3 4 5 6 7 8 9 10 11 12             │  ← 12 格月份條
│ 陽光穿透的藍光洞穴、不怕人的熱帶魚群     │  ← see，最多 2 行省略
│ ⚠️ 季節需覆核（僅 warn=true）  在地圖上看 → │
└───────────────────────────────────────┘
```
- **月份條**：12 個等寬小格（高 6px、間距 2px、圓角 2px），`months` 內的格子填 `--accent`（透明度 .85），其餘 `rgba(255,255,255,.08)`；目前選中的月份那格加 1px 白色外框。格子下方 mono 10px 標 1–12（手機可只標 1、4、7、10、12）
- 程度 badge 顏色：beginner `#2ff3e0`、intermediate `#ffb24d`、advanced `#ff5470`（文字深色 #04202c，確保對比）
- hover 卡片 → 對應地圖標記放大＋發光；hover 標記 → 對應卡片加邊框 `--edge`
- 點卡片 → 地圖 `flyTo`（zoom 9，duration .8），打開該點 popup；點標記 → 清單捲到該卡片並高亮 1.5 秒

### 地圖
- 初始視野：`fitBounds` 全部 30 點（padding 40px）
- 使用 markercluster：`maxClusterRadius: 44`、`showCoverageOnHover:false`、`spiderfyOnMaxZoom:true`
- 單點標記：沿用首頁「浮標」樣式（直徑 15px 青色圓、2px #eafcff 白邊、青色外發光）
- 群聚標記：自訂 `iconCreateFunction`，圓形（依數量 32/38/44px），背景 rgba(47,243,224,.18)、1.5px `--accent` 邊、白色 mono 數字；**不要**用 markercluster 預設的黃綠紅配色
- 滾輪：一般滾輪不縮放（避免搶頁面捲動）；按住 ⌘/Ctrl＋滾輪或觸控板捏合才縮放（首頁已有這段做法可參考）；手機雙指可縮放
- Popup：沿用首頁 `.pop` 的毛玻璃樣式，內容 = 名稱、地點、程度＋入水 badge、🗓 最佳季節（`season` 原文＋warn 時「⚠️需覆核」）、👀 亮點（see）、⚠️ 注意（note）

### 頁尾
一行免責：「季節與規範會變動，標 ⚠️ 者出發前請向當地潛店確認。座標為概略中心點。」＋資料更新日（`spots.json` 的 `updated`）。

## 任務二：首頁第 04 段改成「入口」

現在首頁 `<section>`（`.lab` 為「04.0M — REEF / 珊瑚礁」）內嵌整張 Leaflet 地圖。改成輕量入口，**首頁完全移除 Leaflet（CSS、JS、world.geo.json 那段 fetch、地圖相關 CSS）**：

- 標題維持「潛點地圖」，副標改成「泛亞洲 × 世界經典，共 N 點。先選月份，看你能去哪。」（N 由 spots.json 長度動態填，**不要寫死 24**，現在寫 24 是錯的，實際 30）
- 一排 12 個月份 chip（當月那顆預設亮起），點 chip → 前往 `spots/?m=N`
- 「這個月推薦」：列出 `months` 含當月、且 levelMin == beginner 的前 3 個潛點，用小卡（名稱、地點、see 一行），點卡片 → `spots/?m=當月`
- 一顆主要按鈕 `.cta`「打開潛點地圖 →」連到 `spots/`

## 任務三：首頁往下捲的深度刻度

現在各段的深度標籤是 00 / 02 / 04 / 05 / 06 / 35 / 40M，前面幾段幾乎沒往下、後面突然跳到 35m，沒有意義。改成對應真實潛水里程碑，讓「越往下讀、越深入」有感：

| 段落 | 新標籤 |
|---|---|
| 本週情報 | `00.0M — SURFACE / 海面` |
| 新手上路 | `05.0M — SHALLOWS / 體驗潛水深度` |
| 潛點地圖 | `12.0M — REEF / 珊瑚礁` |
| 潛水實操 | `18.0M — OWD LIMIT / 初級潛水員上限` |
| 技潛 & 專長 | `30.0M — AOWD LIMIT / 進階潛水員上限` |
| 海洋日誌 | `35.0M — LOG / 海洋日誌` |
| 關於 | `40.0M — SEABED / 休閒潛水極限` |

- 每段標題旁的大號背景數字（現在是 00、02、04…那個半透明大字）與右側刻度尺（`.rtick` 那條）同步改成 00、05、12、18、30、35、40，刻度尺上各點的**垂直位置要依深度比例**（0→40m 線性），不是等距
- 背景隨捲動變暗的效果保留，但**最暗不可讓 `--dim` 文字對比低於 4.5:1**；若目前最深處已經低於，把最深色調亮到符合

## 驗收清單（你做完自己先過一遍，並在回報中逐條說明）
1. `spots/` 選「12 月＋剛拿 OWD」→ 應剛好 8 個：砂邊、墾丁、綠島、墨寶、阿尼洛、歐斯陸、斯米蘭、紅海
2. 只選「想看：鬼蝠魟」→ 剛好 5 個：石垣島、Nusa Penida、科莫多、四王群島、馬爾地夫
3. URL `spots/?m=1&lv=beginner&t=turtle` 直接打開能還原篩選，結果剛好 2 個：綠島、墨寶
4. 沖繩本島（青之洞窟、砂邊、萬座、殘波岬、瀨底島，彼此 < 40km）在初始縮放時聚成一顆群聚，點開能分開
5. 首頁不再載入任何 leaflet 資源；首頁「共 N 點」顯示 30
6. 375px 寬無水平捲動
7. 你跑不了瀏覽器沒關係，請說明哪些是靠讀程式碼確認、哪些沒驗證到——**不要宣稱驗證過你沒實際跑過的東西**

## 不要做的事
- 不要 commit／不要碰 `.git`
- 不要改 `spots.json`、`weekly.json`、`creatures/`、`企劃.md`
- 不要新增 npm、build 工具、框架
- 不要改首頁除了第 04 段與深度刻度以外的內容
- 規格沒寫的「順手優化」一律不要做，有想法寫在回報最後的「建議」段落
