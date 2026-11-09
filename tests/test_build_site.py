import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_site as b
import covers


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = []; self.fragments = []; self.hrefs = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'a':
            self.hrefs.append(a.get('href', ''))
            if a.get('href', '').startswith('#src-'): self.fragments.append(a['href'][1:])


class BuildTests(unittest.TestCase):
    def test_flat_yaml(self):
        data, body = b.parse_frontmatter('---\ntitle: "海: 旅"\nslug: sea\ncategory: spot\nspots: [kerama, anilao]\ndate: 2026-11-09\n---\n# 海\n')
        self.assertEqual(data['spots'], ['kerama', 'anilao'])
        self.assertEqual(body, '# 海\n')

    def test_markdown_and_html_escape(self):
        text = '# 標題\n\n**粗體** [連結](https://example.org)\n\n- 第一\n  - 第二\n\n> 引用\n\n| A | B |\n|---|---|\n| 一 | 二 |\n\n<script>alert(1)</script>'
        rendered = b.markdown(text)
        for tag in ('<h1>', '<strong>', '<ul>', '<blockquote>', '<table>'):
            self.assertIn(tag, rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertNotIn('<script>', rendered)
        self.assertEqual(rendered.count('<ul>'), 2)

    def test_legacy_sources(self):
        body, sources = b.sources_section('文字[來源 12](https://example.org/a_(b))（抓取：2026-09-07）\n\n## 來源\n\n- [來源 12：官方](https://example.org/a_(b))')
        self.assertIn('<sup><a href="#src-12">12</a></sup>', body)
        self.assertNotIn('抓取', body)
        self.assertIn('id="src-12"', sources)
        self.assertIn('https://example.org/a_(b)', sources)
        self.assertEqual(sources.count('id="src-12"'), 1)

    def test_new_multidigit_citation(self):
        body, sources = b.sources_section('文字[¹²](#src-12)\n\n## 來源\n- [來源 12：官方](https://example.org)')
        self.assertIn('<sup><a href="#src-12">¹²</a></sup>', body)
        self.assertIn('id="src-12"', sources)

    def test_slug_map(self):
        self.assertEqual(len(b.LEGACY_SLUGS), 22)
        self.assertEqual(len(set(b.LEGACY_SLUGS.values())), 22)

    def test_cover_short_title_and_subtitle(self):
        short, subtitle = covers.cover_titles('慶良間群島深度攻略（船潛選擇、季節、生態與行前）')
        self.assertEqual(short, '慶良間群島深度攻略')
        self.assertEqual(subtitle, '船潛選擇、季節、生態與行前')
        self.assertEqual(covers.cover_titles('珊瑚復育：亞洲案例'), ('珊瑚復育', '亞洲案例'))
        self.assertEqual(covers.cover_titles('潛水：入門知識'), ('潛水：入門知識', ''))
        self.assertEqual(covers.cover_titles('Short title (subtitle)'), ('Short title', 'subtitle'))
        _, subtitle = covers.cover_titles('長篇潛水標題：' + '海' * 40)
        self.assertEqual(len(subtitle), 26)
        self.assertTrue(subtitle.endswith('…'))

    def test_cover_punctuation_wrapping(self):
        for punctuation in covers.NO_START:
            lines = covers.title_lines('海' * 11 + punctuation + '亞洲案例')
            self.assertTrue(all(line[0] not in covers.NO_START for line in lines))
            self.assertTrue(all(line[-1] not in covers.NO_END for line in lines))
        for punctuation in covers.NO_END:
            lines = covers.title_lines('海' * 10 + punctuation + '亞洲案例')
            self.assertTrue(all(line[-1] not in covers.NO_END for line in lines))
        self.assertEqual(len(covers.title_lines('海' * 40)), 2)

    def test_category_art_and_determinism(self):
        namespace = {'s': 'http://www.w3.org/2000/svg'}
        self.assertEqual(len(set(covers.ICONS.values())), 7)
        for category, color in covers.COLORS.items():
            svg = covers.cover_svg('test-cover', '珊瑚復育：亞洲案例與行前準備', category)
            self.assertEqual(svg, covers.cover_svg('test-cover', '珊瑚復育：亞洲案例與行前準備', category))
            root = ET.fromstring(svg)
            icon = root.find('.//s:g[@data-category-icon]', namespace)
            self.assertEqual(icon.attrib['stroke'], color)
            self.assertEqual(icon.attrib['stroke-width'], '3.5')
            stop = root.find('.//s:linearGradient[@id="sea"]/s:stop', namespace)
            self.assertGreaterEqual(float(stop.attrib['stop-opacity']), .55)
            self.assertEqual(stop.attrib['stop-color'], color)
            self.assertNotEqual(svg, covers.cover_svg('another-slug', '珊瑚復育：亞洲案例與行前準備', category))

    def test_build_fixture_and_stability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root/'db'; out = root/'out'
            for folder in b.FOLDERS: (db/folder).mkdir(parents=True)
            (db/'00_每日簡報').mkdir()
            (db/'01_潛水點/慶良間群島深度攻略.md').write_text('# 舊文章\n\n海的故事[來源 1](https://example.org)（抓取：2026-09-07）')
            (db/'01_潛水點/沖繩.md').write_text('# 索引')
            (db/'03_技術裝備/new.md').write_text('---\ntitle: 新文章\nslug: new-article\ncategory: safety\nspots: [kerama]\ndate: 2026-11-09\nsummary: 新摘要\nwords: 1000\n---\n# 新文章\n\n內容[¹](#src-1)\n\n## 來源\n- [來源 1：官方](https://example.org)')
            (db/'00_每日簡報/2026-11-09.md').write_text('## 🔑 今日重點\n\n* **標題**：正文\n  → 對我方啟示: 不公開的編輯筆記\n  [官方](https://example.org) 抓取:2026-11-09\n\n## 其他\n忽略')
            with patch.object(b, 'first_commit_date', return_value='2026-09-07'):
                b.build(db, out)
                before = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
                b.build(db, out)
                after = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            articles = json.loads((out/'articles/index.json').read_text())
            self.assertEqual([a['slug'] for a in articles], ['new-article', 'kerama-guide'])
            self.assertFalse(articles[0]['legacy']); self.assertTrue(articles[1]['legacy'])
            self.assertEqual(articles[1]['spots'], ['kerama'])
            self.assertIn('../../spots/kerama/', (out/'articles/kerama-guide/index.html').read_text())
            for article in articles:
                page = (out/'articles'/article['slug']/'index.html').read_text()
                parser = Links(); parser.feed(page)
                self.assertTrue(all(f in parser.ids for f in parser.fragments))
                self.assertIn('application/ld+json', page)
                self.assertIn('og-default.png', page)
            weekly = json.loads((out/'news/latest.json').read_text())
            self.assertEqual(weekly['items'][0]['title'], '標題')
            self.assertNotIn('編輯筆記', (out/'news/index.html').read_text())
            self.assertEqual(weekly['items'][0]['source_url'], 'https://example.org')
            self.assertEqual((out/'assets/og-default.png').read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
            ET.parse(out/'sitemap.xml')


    def test_spot_schema_scores_and_pages(self):
        import spot_pages
        import score
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'db'; out=Path(tmp)/'out'; db.mkdir()
            b.build(db,out)
            data=json.loads((out/'spots.json').read_text())
            areas=json.loads((out/'areas.json').read_text())
            spots={s['id']:s for s in data['spots']}
            okinawa={a['id'] for a in areas if a['region']=='okinawa'}
            self.assertEqual(sum(s['area'] in okinawa for s in spots.values()),9)
            self.assertEqual(len(list((out/'spots').glob('*/index.html'))),30)
            for sid in spots:
                page=(out/'spots'/sid/'index.html').read_text()
                self.assertEqual(page.count('data-month='),12)
                self.assertEqual(page.count('<small>待查證</small>'),12)
            # Global maximum is 5 species. Kenting: 5/5*30+12/12*20+20+0+0=70.
            self.assertEqual(spots['kenting']['score']['total'],70)
            self.assertEqual(spots['kenting']['score']['parts'],dict(diversity=30,season=20,beginner=20,signature=0,trust=0))
            # Nusa Penida: 3/5*30+7/12*20+12+15+0=56.666..., rounds to 57.
            self.assertEqual(spots['nusa-penida']['score']['total'],57)
            self.assertAlmostEqual(sum(spots['nusa-penida']['score']['parts'].values()),56+2/3)
            self.assertNotIn('熱門',(out/'ranking/index.html').read_text())
            self.assertEqual(data['spots'],sorted(data['spots'],key=lambda x:(-x['score']['total'],x['id'])))
            for a in areas:
                rows=[s for s in spots.values() if s['area']==a['id']]
                self.assertAlmostEqual(a['lat'],sum(s['lat'] for s in rows)/len(rows))
            enrich=db/'data/spots';enrich.mkdir(parents=True)
            (enrich/'kenting.json').write_text(json.dumps(dict(id='kenting',see='查證內容',monthly={'1':[{'c':'turtle','p':'high'}]},sources=[{'url':'https://example.org','title':'來源','checked':'2026-11-09'}])))
            new={**spots['kenting'],'id':'kume-test','country':'japan','area':'kume-test','areaName':'久米測試區','lat':26,'lng':127}
            (enrich/'kume-test.json').write_text(json.dumps(new))
            b.build(db,out)
            updated=json.loads((out/'spots.json').read_text())['spots']
            k=next(s for s in updated if s['id']=='kenting')
            self.assertEqual(k['see'],'查證內容');self.assertFalse(k['monthlySeed'])
            self.assertEqual(k['monthly']['1'],[{'c':'turtle','p':'high'}]);self.assertEqual(k['monthly']['2'],[])
            self.assertEqual(k['name'],spots['kenting']['name'])
            a=next(a for a in json.loads((out/'areas.json').read_text()) if a['id']=='kume-test')
            self.assertEqual((a['name'],a['region']),('久米測試區','okinawa'))
            self.assertTrue((out/'spots/kume-test/index.html').exists())
            before={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
            b.build(db,out)
            self.assertEqual(before,{str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})

    def test_score_trust_and_rounding(self):
        import datetime
        import score
        s=dict(id='test',months=[1],levelMin='advanced',tags=['manta','whaleshark','turtle','mola','hammer'],monthly={},sources=[{}, {}, {}],checked='2026-05-13')
        score.calculate([s],datetime.date(2026,11,9))
        self.assertEqual(s['score']['parts']['trust'],10)
        self.assertEqual(s['score']['parts']['signature'],20)
        s['checked']='2026-05-12'
        score.calculate([s],datetime.date(2026,11,9))
        self.assertEqual(s['score']['parts']['trust'],5)


if __name__ == '__main__': unittest.main()
