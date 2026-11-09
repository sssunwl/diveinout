# DiveInOut 潛旅生活誌

泛亞洲潛旅生活誌,生活風+新手友善,先不談錢、純養受眾。線上 https://sssunwl.github.io/diveinout/ (repo sssunwl/diveinout,**public**)。
規劃與決策:`docs/PLAN_2026-11_每日文章與潛點資料站.md`;工單:`docs/CODEX_TASK_2026-11-09.md`。

## 資料流(兩個 repo)

```
SakiDive repo(~/SakiDiveDB,有 GEMINI_API_KEY secret)
  10:00 JST  _pipeline/enrich_content.py  內容路線圖.md 挑一題 → 01/02/03 資料夾寫一篇 md(含 frontmatter)
  10:30 JST  _pipeline/enrich_spots.py    data/spot_queue.md 挑 2 點 → data/spots/<id>.json
  每週一      _pipeline/fetch_brief.py     本機 launchd → 00_每日簡報/
DiveInOut repo(本資料夾,不放任何金鑰、不呼叫 Gemini)
  11:30 JST  tools/build_site.py          讀 SakiDive → articles/ news/ spots/<id>/ ranking/ spots.json areas.json sitemap
```

- **產物不要手改**:`articles/`、`news/`、`spots/<id>/`、`ranking/`、`spots.json`、`areas.json`、`sitemap.xml`、`assets/covers/` 都是 build_site 生成。要改就改 `tools/` 再重跑:`SAKIDIVE_DIR=~/SakiDiveDB python3 tools/build_site.py`。
- 潛點原始資料:`data/spots_seed.json`(手動維護的 30 點);查證資料在 SakiDive `data/spots/`,同 id 會覆蓋 seed。
- 測試:`python3 -m unittest discover -s tests`(兩個 repo 各自有)。

## 規則

- 新文章 800–1400 字、禁 AI 腔(黑名單在 SakiDive `enrich_content.py` 的 `BANNED_PHRASES`)、用「你」不用「您」;封面一律程式生成(`tools/covers.py`),不抓別人照片。
- 排名叫「推薦指數」,公式公開在 ranking 頁(`tools/score.py`);**沒有真實流量數據前,頁面不准出現「熱門」**。
- 生物月份不准憑記憶填;seed 推出來的格子標「待查證」,等 enrich_spots 查證覆蓋。
- 寫作題目只由 Claude/SS 補進 `內容路線圖.md`(格式 `slug｜分類｜spots｜題目`),路線圖剩 ≤7 題會通知。
- Gemini 免費層**每模型每天 20 次**,SakiDive 與 Sarayuki 共用同一把 key;本機測試會吃掉排程額度,能 mock 就 mock。
- 地圖底圖用 Esri(CARTO 要 key);中文大標 line-height ≥ 1.05。
