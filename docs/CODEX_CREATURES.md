# 派工單：DiveInOut 水下生物圖鑑 v4（圖卡式）

> 規劃/審查：Claude｜實作：Codex｜分支已開好：`creatures-v4`
> **不要 commit、不要碰 `.git`；不要改 `creatures.json`、`spots.json`、`weekly.json`、首頁 `index.html`**。

## 為什麼要改
現在的 `creatures/index.html`：小小的白色剪影漂在深色漸層上，越往下越暗、字幾乎看不到；大片空白；最有用的「在哪看得到／怎麼相處」要點進去才有；而且分層錯（鬼蝠魟常在 5–20m 清潔站，卻放在 30–40m）。
讀者真正想知道：「**以我的程度、在我要去的地方，看得到什麼？**」

## 資料：`creatures.json`（已備好，fetch `../creatures.json`）
```json
{"updated":"2026-09-22",
 "levels":{"snorkel":"浮潛就看得到","owd":"OWD（18m 內）","aowd":"AOWD（30m 內）","beyond":"休閒潛水看不到"},
 "creatures":[{"id":"turtle","name":"綠蠵龜","en":"Green sea turtle","kind":"爬蟲類",
   "svg":"turtle","level":"snorkel","depth":"0–20m","trait":"…","where":"…","tip":"…",
   "spots":["xiaoliuqiu","kerama",…],"warn":false}, …22 筆]}
```
- `svg`：現有 `creatures/index.html` 裡 `SVGS` 物件的 key（16 種有）；**6 種新生物是 null**（whaleshark 鯨鯊、thresher 長尾鯊、sardine 沙丁魚風暴、nudi 海蛞蝓、gardeneel 花園鰻、napoleon 拿破崙魚）
- `spots`：`spots.json` 的潛點 id（用來查名稱、region、做連結）
- `level` 四級：snorkel / owd / aowd / beyond

`spots.json` 的 region 顯示名：okinawa 沖繩、taiwan 台灣、philippines 菲律賓、palau 帛琉、indonesia 印尼、thailand 泰國、malaysia 馬來西亞、maldives 馬爾地夫、egypt 埃及。

## 任務一：重寫 `creatures/index.html`

### 插畫
- 保留現有 `SVGS` 的 16 個手繪幾何 SVG（整段搬過來），**另外用同一種畫風（單色填色幾何剪影、viewBox 0 0 100 100）補畫 6 個**：鯨鯊（寬扁頭＋身上點點）、長尾鯊（超長尾鰭上葉）、沙丁魚風暴（一團 12–20 條小魚組成的漩渦）、海蛞蝓（橢圓身體＋背上花狀鰓＋兩根觸角）、花園鰻（3–5 條從沙面冒出的細長 S 形）、拿破崙魚（額頭明顯隆起的大魚＋厚嘴唇）
- 顯示方式：**不再是白色剪影**。插畫放在卡片上方 4:3 的插畫面板，面板背景依 level 用深淺不同的海色漸層，插畫本身用 `--accent`（#2ff3e0）填色，約佔面板 60% 寬；hover 時插畫輕微上浮 4px
  - snorkel：`linear-gradient(160deg,#0f5566,#0a3a4a)`
  - owd：`linear-gradient(160deg,#0b4050,#082c3a)`
  - aowd：`linear-gradient(160deg,#083040,#061f2b)`
  - beyond：`linear-gradient(160deg,#061a24,#030d14)`
- 資料結構保留 `img` 欄位的擴充空間：若日後 creature 有 `img`（圖片網址）就顯示圖片，否則顯示 SVG（先寫好這個判斷）

### 版面
視覺變數沿用首頁 `:root`（`--ink #e9fbff`、`--dim #8fb3bf`、`--accent #2ff3e0`、`--edge`、`--card`，body 背景 `#020a10`）與 `.lab`、`.mono` 樣式。**整頁背景固定 #020a10，不再隨捲動變暗**。內文對比 ≥ 4.5:1。中文標題 line-height ≥ 1.05、letter-spacing ≥ -0.01em。

```
← DiveInOut   .lab「CREATURE GUIDE / 生物圖鑑」   h1 水下生物圖鑑
一句：選你的程度和要去的地方，看看下水會遇到誰。

篩選列（sticky，毛玻璃 rgba(2,10,16,.82)+blur；手機不 sticky，規則同 spots 頁）
  我的程度：全部｜只浮潛｜OWD｜AOWD
  我要去：  全部地區 ▾（9 個 region）
  「符合 X / 22 種」＋ 清除篩選

┌深度尺┐  ── 0–5m 浮潛就看得到 ─────────────
│ 0m   │  [卡][卡][卡][卡]
│      │  ── OWD 18m 內 ─────────────────
│ 18m  │  [卡][卡][卡][卡]…
│      │  ── AOWD 30m 內 ────────────────
│ 30m  │  …
│ 40m+ │  ── 休閒潛水看不到 ───────────────
└──────┘  [卡]
```
- 依 level 分四段，每段一個段落標題（mono 小字深度＋serif 無所謂，沿用首頁 h2 樣式）＋一句說明：
  - snorkel「0–5m · 浮潛就看得到」：「不用證照，戴上面鏡就能見面。」
  - owd「5–18m · OWD 18m 內」：「拿到初級證照，這些都是你的主場。」
  - aowd「18–30m · AOWD 30m 內」：「進階深度與洋流，大傢伙開始登場。」
  - beyond「40m+ · 休閒潛水看不到」：「用知識潛入就好。」
- 卡片網格：桌機 4 欄、平板 3 欄、手機 2 欄（間距 12px）。篩選後某段 0 張就整段隱藏
- **左側深度尺（只在 ≥ 960px）**：sticky 的細直線，標 0 / 18 / 30 / 40+，一個亮點隨捲動顯示目前在哪一段（用 IntersectionObserver 判斷目前段落）；點刻度捲到該段
- 空狀態：「這個組合沒有收錄的生物。試試放寬程度或地區？」＋清除篩選

### 篩選邏輯
- 程度（單選，累進）：只浮潛 → level=snorkel；OWD → snorkel+owd；AOWD → snorkel+owd+aowd；全部 → 全部（含 beyond）
- 地區（單選）：生物的 `spots` 中任一潛點的 region = 選中地區。`spots` 為空的（水母、鮟鱇）在選了地區時不出現
- URL 同步：`?lv=owd&r=philippines`，`history.replaceState`，載入時還原

### 卡片
```
┌────────────────────┐
│   [插畫面板 4:3]     │  ← 右上角小 badge：level 簡稱（浮潛/OWD/AOWD/—）
├────────────────────┤
│ 綠蠵龜               │  ← 16px 900
│ Green sea turtle    │  ← mono 11px dim
│ 爬蟲類 · 0–20m        │  ← 12px dim
│ 小琉球、慶良間…       │  ← 最多 1 行，spots 名稱前 2 個＋「等 N 處」
└────────────────────┘
```
整張卡是 button，點開詳細。

### 詳細（桌機置中 modal 最寬 560px；手機底部 bottom sheet 最高 85dvh 可捲）
- 上方插畫面板（同卡片，較大）
- 名稱＋英文名＋kind＋depth＋level 全名
- 三段：**牠是誰**（trait）、**在哪看得到**（where；`warn` 為 true 時後面加「⚠️ 需覆核」小字）、**怎麼跟牠相處**（tip，用淡 accent 底色的提示框強調）
- 「在這些潛點遇得到」：spots 轉成 chip（潛點名稱），點 chip → `../spots/?focus=<spotId>`
- 關閉：右上 ×、點遮罩、Esc；開啟時鎖背景捲動；焦點移到 modal 內，關閉後回到原卡片
- URL：開啟時 `#<creatureId>`，直接開 `creatures/#manta` 會自動打開鬼蝠魟

## 任務二：`spots/index.html` 小改
1. 支援 `?focus=<spotId>`：載入後等同點了該潛點的「在地圖上看」（桌機 flyTo zoom 9＋開 popup；手機切到地圖）。不存在的 id 忽略。**popup 要完整可見**（flyTo 完成後打開 popup，並確保 autoPan 生效，popup 上緣不可被地圖切掉）
2. popup 與卡片加一行「🐠 在這裡看得到」：fetch `../creatures.json`（失敗就不顯示，不可讓頁面壞掉），列出 `spots` 含此潛點的生物名稱，每個是連到 `../creatures/#<id>` 的小連結；沒有就不顯示這行

## 驗收（逐條回報，沒實際跑的不要說驗證過）
1. 「只浮潛」→ 5 種：綠蠵龜、小丑魚、水母、鯨鯊、沙丁魚風暴
2. 「OWD＋菲律賓」→ 8 種：綠蠵龜、小丑魚、章魚、河魨、清潔蝦、鯨鯊、沙丁魚風暴、海蛞蝓
3. `?r=okinawa` → 8 種：綠蠵龜、小丑魚、章魚、河魨、裸胸鯙、魟魚、鬼蝠魟、鎚頭鯊
4. `creatures/#manta` 直接開啟鬼蝠魟詳細
5. spots 頁墨寶的 popup 出現「在這裡看得到：綠蠵龜、小丑魚、沙丁魚風暴」
6. `spots/?focus=malapascua` 飛到馬拉帕斯加並完整顯示 popup
7. 375px 兩頁無水平捲動；手機 bottom sheet 可捲到底
8. 6 個新 SVG 畫好，跟舊的同風格

## 不要做的事
- 不要 commit／碰 `.git`；不要改 json 資料檔與首頁
- 不要加 npm／build／框架
- 規格沒寫的不要做；想法寫在回報最後「建議」
