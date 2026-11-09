# 派工單:DiveInOut 每日文章+潛點資料站(A/B/C 三期)

> 規劃/審查:Claude｜實作:Codex｜背景與決策:`docs/PLAN_2026-11_每日文章與潛點資料站.md`(先讀)
> 涉及兩個 repo:
> - **DiveInOut** `/Users/sws/Sun/Claude/DiveInOut`(sssunwl/diveinout,public,GitHub Pages)
> - **SakiDive** `/Users/sws/SakiDiveDB`(sssunwl/SakiDive,public,有 `GEMINI_API_KEY` secret)
>
> 規則:
> - 每期開新分支(`feat/articles`、`feat/spots-db`、`feat/spot-enrich`),**不要 commit 到 main、不要 push**,做完我審查再合併。
> - 不放任何金鑰進 repo;DiveInOut 的程式**不准呼叫 Gemini**。
> - 純靜態、無框架、無 npm。Python 只用標準庫(建站腳本也一樣)。
> - 視覺沿用現有 `index.html` / `spots/index.html`:CSS 變數 `--ink:#e9fbff; --dim:#8fb3bf; --accent:#2ff3e0; --pop:#ff5470; --edge:rgba(47,243,224,.28); --card:rgba(255,255,255,.045)`,背景 `#020a10`,`.lab` mono 小標。**參考圖**:`docs/ref/spots.png`、`docs/ref/home.png`(現有頁截圖)。中文標題 line-height ≥ 1.05、letter-spacing ≥ -0.01em。
> - 地圖底圖用 Esri(CARTO 已要 key,之前踩過)。
> - **只做本單寫的事**,不要順手改首頁其他區塊、不要改 `creatures/` 的版面。

---

## A 期:文章上線

### A1(SakiDive repo)寫作管線改版 `_pipeline/enrich_content.py`

1. 字數:正文 800–1400 字。< 800 拒寫入;> 1600 自動要求重寫一次(第二次仍超過就照寫,log 警告)。
2. AI 腔黑名單(放在檔案頂部常數 `BANNED_PHRASES`,方便增減):至關重要、不容錯過、讓我們一起、總而言之、總之、值得一提的是、在這個.*的時代、無論您是、宛如、彷彿置身、夢幻般、絕佳、一站式、深入探討、揭開.*面紗、不僅.*更是、賦能、打造、開啟.*之旅、潛水愛好者們、親愛的、您。命中 → 把命中的詞告訴模型重寫一次;第二次仍命中 → 不寫入、exit 非 0。system prompt 也要寫進這份清單,並要求用「你」。
3. 輸出加 YAML frontmatter(程式產生,不靠模型):
   ```yaml
   ---
   title: 慶良間群島深度攻略
   slug: kerama-guide          # 小寫英數+連字號;由路線圖題目行的「slug｜」前綴提供
   category: spot | beginner | gear | safety | ocean | course | life
   spots: [kerama]             # 對應 DiveInOut spots.json 的 id,可空
   date: 2026-11-10
   summary: 第一段的前 80 字
   words: 1120
   ---
   ```
   路線圖題目格式改為 `- [ ] slug｜分類｜spots(逗號分隔,可空)｜題目`,例:`- [ ] kerama-guide｜spot｜kerama｜慶良間群島:船潛怎麼選、季節與生態`。舊格式(無 `｜`)仍要能跑(slug 用現有 filename 規則、category 用 `choose_content_dir` 推)。
4. 來源:正文內引用改成上標 `¹²³`,文末 `## 來源` 列表。網域是 facebook.com / reddit.com / instagram.com / youtube.com 的 grounding 來源丟掉不列。
5. 失敗要讓人看得到:現在失敗會 exit 0 被藏起來。改成:沒有題目時,在 Step Summary 寫「⚠️ 路線圖已空,請補題」並用 `_discord.py` 的同一個 webhook 機制(若 secret `DISCORD_WEBHOOK_SAKI` 不存在就略過)通知;剩 ≤ 7 題時也通知一次。
6. 同 `fetch_brief.py` 的做法:503/429 主模型重試後換 `gemini-flash-latest`、`gemini-2.5-flash-lite`(grounding 工具三者都支援,換模型時沿用同一 payload)。
7. 附 `tests/test_enrich_content.py`(unittest):黑名單、字數、frontmatter、新舊路線圖格式、來源網域過濾。

### A2(SakiDive repo)新路線圖

Claude 會另外提供 `內容路線圖.md` 的新題目(第一批 60 題,新格式),**Codex 不要自己編題目**。只要保證新格式能被讀。

### A3(DiveInOut repo)建站腳本 `tools/build_site.py`

輸入:環境變數 `SAKIDIVE_DIR`(預設 `../SakiDiveDB`,Actions 裡是 checkout 的路徑)。

1. 讀 SakiDive `01_潛水點/ 02_課程證照/ 03_技術裝備/` 全部 md(排除 README.md、`沖繩.md`、`課程證照資源.md` 這種索引頁 → 用清單常數 `SKIP`)。
   - 有 frontmatter 的照用;沒有的(舊 22 篇)自動推:title=第一個 `# `、slug=從檔名轉拼音不行就用 `legacy-<sha1前8碼>`,**同一篇每次 slug 要一樣**、category 由資料夾推、date=該檔在 SakiDive git log 的第一次 commit 日、`legacy: true`。
2. Markdown → HTML:自己寫一個小轉換器(標題、段落、粗體、清單、連結、表格、引用、上標)。舊文那種 `[來源 N](超長網址)（抓取：日期）` 要轉成上標 `<sup><a href="#src-N">N</a></sup>`,來源收進文末 `<details>` 摺疊區。
3. 產出:
   - `articles/index.json`:`[{slug,title,category,date,summary,words,spots,cover,legacy}]` 新到舊。
   - `articles/<slug>/index.html`:每篇一個靜態頁(不是 `?slug=` 渲染器,Google 要讀得到)。含 `<title>`、meta description、`og:title/og:description/og:image`、canonical、JSON-LD `Article`。版面:封面 → 分類/日期/字數/閱讀分鐘 → 正文(最大寬 720px,行高 1.8)→ 相關潛點卡(有 `spots` 才顯示,連 `spots/<id>/`)→ 同分類其他 3 篇 → 來源摺疊。舊文頂部加小標「深度攻略・資料抓取於 YYYY-MM-DD」。
   - `articles/index.html`:列表頁,分類篩選 chips(潛旅/新手/裝備/安全/保育/課程/生活),卡片=封面+標題+摘要+日期。
   - `news/index.html`:讀 `00_每日簡報/*.md`,每份取「今日重點」轉卡片,新到舊。順便把 `weekly.json` 改成最新一份的重點(首頁 0m 區塊讀它)。
4. 封面 `tools/covers.py`(被 build_site 呼叫):每篇產 `assets/covers/<slug>.svg`,1200×630。
   - 深海漸層(依分類換主色:spot 青綠、beginner 淺藍、gear 鋼藍、safety 珊瑚紅 `--pop`、ocean 海草綠、course 紫、life 暖黃)。
   - 背景用程式畫的元素(依 slug 當亂數種子,同篇每次一樣):等深線、氣泡、光束;左上 `DiveInOut` 字標+分類英文 mono 小字;標題 2 行內自動斷行,最多 22 字,超過截斷加「…」。
   - 字體用 CSS font stack(`"PingFang TC","Noto Sans TC",sans-serif`),SVG 內不嵌字。
   - **og:image** 社群平台不吃 SVG → 另外產一張全站共用 `assets/og-default.png`(用標準庫寫 PNG 也行,或者手動放一張品牌圖;我審查時決定)。每篇 og:image 先指向它。
   - **不得**抓任何外部照片。
5. 首頁 `index.html` 只加兩件事:導覽列加「文章」「情報」連結;0m 區塊下方加「最新 3 篇文章」卡片(讀 `articles/index.json`)。其餘不動。
6. `sitemap.xml` + `robots.txt`(所有文章頁、潛點頁)。

### A4(DiveInOut repo)每日 Actions `.github/workflows/daily-build.yml`

- `cron: "30 2 * * *"`(11:30 JST,在 SakiDive 10:00、Sarayuki 11:00 之後)+ `workflow_dispatch`。
- checkout 自己 + checkout `sssunwl/SakiDive`(public,不需 token)到 `_src/SakiDive`(`fetch-depth: 0`,因為要讀 git log 日期)。
- `python3 tools/build_site.py` → 只 `git add articles news assets/covers spots weekly.json sitemap.xml` → 有變更才 commit「每日建站 YYYY-MM-DD」→ push。
- `.gitignore` 加 `_src/`。
- 失敗要紅燈(這條不吃 Gemini,失敗就是程式壞了,要看得到)。

### A 驗收(我會逐項開瀏覽器查)

- [ ] `articles/` 列出 22 篇舊文,每篇有封面、上標來源可點、摺疊來源
- [ ] 用 `--task` 手動跑一篇新文:frontmatter 齊、800–1400 字、無黑名單詞、無 FB/Reddit 來源
- [ ] 手機 375px 無橫向捲動
- [ ] `python3 -m unittest` 全過
- [ ] `tools/build_site.py` 連跑兩次,第二次 `git status` 乾淨(輸出要穩定)

---

## B 期:潛點資料站

### B1 資料結構升級 `spots.json` schema v3(向下相容,舊欄位保留)

新增欄位:
| 欄位 | 說明 |
|---|---|
| `country` | `japan`/`taiwan`/`philippines`/`indonesia`/`malaysia`/`thailand`/`palau`/`maldives`/`egypt`… |
| `area` | 子區 id,例 `okinawa-main`/`kerama`/`miyako`/`ishigaki`/`yonaguni`/`izu`/`kenting`/`green-island`/`xiaoliuqiu`/`cebu`/`bohol`/`dumaguete`/`anilao`/`coron`/`bali`/`raja-ampat`/`komodo`/`sipadan`/`similan`… 對照表放 `areas.json`(`{id,name,country,region,lat,lng}`,`region` 例 `okinawa` 讓「選沖繩」能一次撈 okinawa-main+kerama+miyako+ishigaki+yonaguni) |
| `monthly` | `{"1":[{"c":"humpback","p":"high|mid|low"}], … "12":[…]}`,`c`=creatures.json id,`p`=機率 |
| `monthlyNote` | 一句話,例「1–3 月座頭鯨季,船上看為主」 |
| `waterTemp` / `visibility` | `{"1":21,…}` / 字串,可空 |
| `sources` | `[{url,title,checked}]` |
| `checked` | 最後查證日 |
| `article` | 介紹文 slug(由 build_site 從 frontmatter `spots` 反查,不手填) |

- `region` 欄位現有值保留(舊頁面在用),新頁面改用 `country`+`area`。
- **現有 30 點的 monthly 初稿**由 `tools/seed_monthly.py` 產生:用 `creatures.json` 每種生物的 `spots[]`+`months`(若 creatures 沒有月份就把該生物列在所有最佳月份、`p:"low"`、`monthlyNote` 寫「月份待查證」)。**不准憑記憶填生物月份**;真正的月份由 C 期的查證管線覆蓋。
- `creatures.json` 需要新生物時(例如座頭鯨、錘頭鯊、花園鰻)只新增 id/name/en/kind,`svg` 用現有通用圖示,我之後再補圖。

### B2 地區篩選

`spots/index.html` 加兩層篩選:國家 chips → 選了之後出現該國 area/region chips(日本 → 沖繩全部/本島/慶良間/宮古/石垣/與那國/伊豆…)。選「沖繩全部」= 所有 `areas.json` 裡 `region:"okinawa"` 的點。URL 參數 `?c=japan&r=okinawa` 可分享。地圖同步縮放到該區。列表模式顯示數量「沖繩 9 個潛點」。

### B3 排名頁 `ranking/index.html`

- 推薦指數公式見規劃書,**寫成 `tools/score.py` 在建站時算好**,寫進 `spots.json` 的 `score:{total,parts:{diversity,season,beginner,signature,trust}}`,前端不自己算。
- 頁面頂部一段「排名怎麼算」把公式寫清楚(五項配分)+「目前沒有用瀏覽數,這不是熱門排行」。
- 切換:全部 / 依國家 / 依地區 / 新手 / 指定月份(月份排名 = 該月 `monthly` 物種數,`p:high` 算 2、mid 1、low 0.5)。
- 每列:名次、潛點名、地區、總分+五段小條圖、連個別頁。
- **頁面文字不准出現「熱門」二字**。

### B4 潛點個別頁 `spots/<id>/index.html`(build_site 產生)

依序:麵包屑(國家 › 地區 › 潛點)→ 名稱+地點+程度/入水/最佳月份 chips → 小地圖(Leaflet,Esri)→ **1–12 月生物月曆**(12 格,每格放該月生物小圖示,深淺=機率;點格子展開清單,生物名連 `creatures/?id=`;`monthlyNote` 放上方;資料來源是 seed 的格子角落標「待查證」)→ 水溫/能見度(有才顯示)→ 介紹(有 `article` 就嵌入文章摘要+「讀完整介紹」;沒有就顯示 `see`+`note`)→ 推薦指數拆解 → 注意事項(`warn` 時黃框「出發前請覆核季節與規範」)→ 同地區其他潛點 → 來源與最後查證日。
SEO:同 A3 的 meta + JSON-LD `TouristAttraction`。

### B 驗收
- [ ] `spots/?c=japan&r=okinawa` 列出全部沖繩點,數量對
- [ ] 30 個點都有個別頁,月曆 12 格齊,seed 資料標「待查證」
- [ ] 排名頁公式說明在、沒有「熱門」字樣、分數跟 `tools/score.py` 一致
- [ ] 舊 `spots/` 地圖功能不退化(月份/程度/生物篩選照常)

---

## C 期:潛點擴充管線(SakiDive repo)

`_pipeline/enrich_spots.py` + workflow `daily-spot-enrichment.yml`(`cron: "30 1 * * *"` = 10:30 JST):
- 從 `data/spot_queue.md` 取前 2 個未完成(格式 `- [ ] id｜名稱｜國家｜area`;**Claude 提供佇列**)。
- 每點:讀 SakiDive 裡提到這個點的 md 當素材 → Gemini + Google Search grounding(最多 4 查詢)→ 要求輸出**純 JSON**(schema = B1 欄位)。程式驗證:座標在亞洲範圍、`months` 1–12、creature id 存在(不存在就放進 `newCreatures` 待審清單,不自己加)、`sources` ≥ 2 且非 FB/Reddit。驗證不過就不寫入、log 原因。
- 寫 `data/spots/<id>.json`,打勾佇列。DiveInOut 的 build_site 讀這個資料夾,**覆蓋** spots.json 同 id 的 seed 欄位(以查證資料為準)。
- 同樣 503 換模型、路線圖將空時通知。
- 單元測試:JSON 驗證器。

---

## 交件

每期做完:列出改了哪些檔、怎麼本機預覽(`python3 -m http.server` 在 DiveInOut 根目錄)、哪些驗收項自評已過、哪裡沒把握。不要 commit。
