#!/usr/bin/env python3
"""Build static articles, news and Phase B spot database/pages. No network, dependencies or git writes.

SAKIDIVE_DIR=/Users/sws/SakiDiveDB python3 tools/build_site.py
SITE_URL defaults to the existing GitHub Pages project URL.
"""
import datetime
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

from covers import cover_svg, og_png
import spot_pages

ROOT = Path(__file__).resolve().parent.parent
SKIP = {'README.md', '沖繩.md', '課程證照資源.md'}
# All 22 existing filenames, including the three excluded index documents.
LEGACY_SLUGS = {
 '慶良間群島深度攻略.md': 'kerama-guide',
 '青之洞窟深度攻略.md': 'okinawa-blue-cave-guide',
 '砂邊-Sunabe-深度攻略.md': 'sunabe-guide',
 '帛琉潛旅攻略.md': 'palau-guide',
 '印尼-Bunaken-與-Lembeh-微距潛點深度攻略.md': 'bunaken-lembeh-guide',
 '菲律賓-Dumaguete-與-Apo-Reef-深度攻略.md': 'dumaguete-apo-reef-guide',
 '船宿潛水攻略.md': 'liveaboard-guide',
 '泰坦砲彈魚.md': 'titan-triggerfish',
 '潛水員如何參與珊瑚復育.md': 'coral-restoration',
 '與鬼蝠魟-鯨鯊同游的守則與亞洲熱門潛點.md': 'manta-whale-shark-etiquette',
 'SSI-vs-PADI-vs-AIDA-vs-Molchanovs.md': 'diving-certifications-compared',
 '台灣-沖繩-菲律賓-scuba-考證費用行情表.md': 'scuba-course-costs',
 '中性浮力練習與安全界線.md': 'neutral-buoyancy-practice',
 '平壓.md': 'equalization-guide',
 '新手潛水電腦選擇重點.md': 'first-dive-computer',
 '新手裝備選購.md': 'beginner-diving-gear',
 '減壓病預防-警訊與就醫原則.md': 'decompression-sickness-safety',
 '潛水行前安全檢查清單.md': 'pre-dive-safety-checklist',
 '裝備保養.md': 'diving-gear-care',
 '沖繩.md': 'okinawa-overview', '課程證照資源.md': 'certification-resources',
 'README.md': 'equipment-overview',
}
LEGACY_SPOTS = {
    'kerama-guide': ['kerama'],
    'okinawa-blue-cave-guide': ['okinawa-bluecave'],
    'sunabe-guide': ['sunabe'],
    'palau-guide': ['blue-corner'],
    'manta-whale-shark-etiquette': ['ishigaki-manta', 'oslob', 'maldives', 'nusa-penida'],
    'bunaken-lembeh-guide': [],
    'dumaguete-apo-reef-guide': [],
}
# 舊文依資料夾只能分到 spot/course/gear,這裡校正成實際分類
LEGACY_CATEGORIES = {
    'titan-triggerfish': 'ocean', 'coral-restoration': 'ocean', 'manta-whale-shark-etiquette': 'ocean',
    'neutral-buoyancy-practice': 'beginner', 'equalization-guide': 'safety',
    'decompression-sickness-safety': 'safety', 'pre-dive-safety-checklist': 'safety',
}

CATEGORIES = {'spot': '潛旅', 'beginner': '新手', 'gear': '裝備', 'safety': '安全', 'ocean': '保育', 'course': '課程', 'life': '生活'}
FOLDERS = {'01_潛水點': 'spot', '02_課程證照': 'course', '03_技術裝備': 'gear'}
SITE_URL = os.environ.get('SITE_URL', 'https://sssunwl.github.io/diveinout').rstrip('/')
SUPER = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = data if isinstance(data, bytes) else data.encode('utf-8')
    if not path.exists() or path.read_bytes() != content:
        path.write_bytes(content)


def safe_url(url):
    return url if urlsplit(url).scheme in ('http', 'https') or url.startswith('#') else '#'


def inline(text):
    # Escape all raw HTML; only this renderer can create markup.
    pattern = r'\[([^\]]+)\]\((https?://[^\s]+?|#[^\s)]+)\)(?=\s|[。，、；：！？）,.!?;:]|$)|\[([^\]]+)\]\((https?://[^\s]+?|#[^\s)]+)\)|(`[^`]+`)|([⁰¹²³⁴⁵⁶⁷⁸⁹]+)'
    def token(match):
        label, url = (match[1], match[2]) if match[1] is not None else (match[3], match[4])
        if label is not None:
            link = f'<a href="{html.escape(safe_url(url), quote=True)}">{html.escape(label)}</a>'
            return '<sup>' + link + '</sup>' if re.fullmatch(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+', label) else link
        if match[5]:
            return '<code>' + html.escape(match[5][1:-1]) + '</code>'
        digits = match[6].translate(SUPER)
        # Each source digit is an independent superscript citation.
        return ''.join(f'<sup><a href="#src-{n}">{n}</a></sup>' for n in digits)
    parts, last = [], 0
    for match in re.finditer(pattern, text):
        parts.append(html.escape(text[last:match.start()]))
        parts.append(token(match))
        last = match.end()
    parts.append(html.escape(text[last:]))
    rendered = ''.join(parts)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', rendered)


def markdown(text):
    """Small block renderer: headings, paragraphs, nested lists, tables, quotes."""
    lines, output, i = text.splitlines(), [], 0
    def list_at(line):
        return re.match(r'^(\s*)([-*+] |\d+[.)] )\s*(.*)$', line)
    def render_list(start, indent):
        first = list_at(lines[start])
        tag = 'ol' if first[2][0].isdigit() else 'ul'
        result = [f'<{tag}>']
        j = start
        while j < len(lines):
            match = list_at(lines[j])
            if not match or len(match[1]) != indent:
                break
            current_tag = 'ol' if match[2][0].isdigit() else 'ul'
            if current_tag != tag:
                break
            result.append('<li>' + inline(match[3]))
            j += 1
            while j < len(lines):
                child = list_at(lines[j])
                if child and len(child[1]) > indent:
                    rendered, j = render_list(j, len(child[1]))
                    result.append(rendered)
                elif lines[j].strip() and len(lines[j])-len(lines[j].lstrip()) > indent:
                    result.append(' ' + inline(lines[j].strip()))
                    j += 1
                else:
                    break
            result.append('</li>')
        return ''.join(result) + f'</{tag}>', j
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        heading = re.match(r'^(#{1,6})\s+(.*)', line)
        if heading:
            level = len(heading[1])
            output.append(f'<h{level}>{inline(heading[2])}</h{level}>')
            i += 1
        elif i+1 < len(lines) and '|' in line and re.fullmatch(r'[\s|:\-]+', lines[i+1]) and '-' in lines[i+1]:
            rows = [line]
            i += 2
            while i < len(lines) and '|' in lines[i] and lines[i].strip():
                rows.append(lines[i].strip()); i += 1
            table = []
            for n, row in enumerate(rows):
                cell = 'th' if n == 0 else 'td'
                table.append('<tr>' + ''.join(f'<{cell}>{inline(x.strip())}</{cell}>' for x in row.strip('|').split('|')) + '</tr>')
            output.append('<div class="table-scroll"><table>' + ''.join(table) + '</table></div>')
        elif list_at(lines[i]):
            rendered, i = render_list(i, len(list_at(lines[i])[1])); output.append(rendered)
        elif line.startswith('>'):
            quoted = []
            while i < len(lines) and lines[i].lstrip().startswith('>'):
                quoted.append(re.sub(r'^\s*> ?', '', lines[i])); i += 1
            output.append('<blockquote>' + markdown('\n'.join(quoted)) + '</blockquote>')
        elif re.fullmatch(r'[-*_]{3,}', line):
            output.append('<hr>'); i += 1
        else:
            para = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^\s*(#{1,6}\s|>|[-*+] |\d+[.)] )', lines[i]):
                if i+1 < len(lines) and '|' in lines[i] and re.fullmatch(r'[\s|:\-]+', lines[i+1]):
                    break
                para.append(lines[i].strip()); i += 1
            output.append('<p>' + inline(' '.join(para)) + '</p>')
    return '\n'.join(output)


def parse_frontmatter(text):
    """The flat YAML schema used by the pipeline, including quoted/flow lists.

    Also accepts bare YAML scalars and indented spots lists; rejects unsupported data.
    """
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---\n', 4)
    if end < 0:
        raise ValueError('Unclosed frontmatter')
    data, current = {}, None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line.startswith('  - ') and current == 'spots':
            data['spots'].append(line[4:].strip().strip('"\'')); continue
        key, sep, value = line.partition(':')
        if not sep:
            raise ValueError('Invalid frontmatter line: ' + line)
        key, value = key.strip(), value.strip()
        current = key
        if key == 'spots' and not value:
            data[key] = []; continue
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            if value.startswith('[') and value.endswith(']'):
                parsed = [x.strip().strip('"\'') for x in value[1:-1].split(',') if x.strip()]
            elif value.startswith("'") and value.endswith("'"):
                parsed = value[1:-1].replace("''", "'")
            else:
                parsed = value
        data[key] = parsed
    return data, text[end+5:]


def plain(text):
    text = re.sub(r'\[來源\s*\d+[^\]]*\]\((https?://[^\s]+)\)', '', text)
    text = re.sub(r'（抓取[：:]\s*\d{4}-\d{2}-\d{2}）', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return re.sub(r'[#*_>`⁰¹²³⁴⁵⁶⁷⁸⁹]', '', text).strip()


def sources_section(body):
    """Collect and deduplicate old inline citations and new source lists."""
    parts = re.split(r'^##\s+來源[^\n]*\n', body, maxsplit=1, flags=re.M)
    prose, tail = parts[0], parts[1] if len(parts) > 1 else ''
    sources = {}
    def collect(match):
        number, label, url = match[1], match[2] or '', match[3]
        sources.setdefault(number, (label.strip(' ：:'), url))
        return f'[CITE{number}](#src-{number})'
    pattern = r'\[來源\s*(\d+)([^\]]*)\]\((https?://[^\s]+)\)'
    re.sub(pattern, collect, tail)
    prose = re.sub(pattern, collect, prose)
    prose = re.sub(r'（抓取[：:]\s*\d{4}-\d{2}-\d{2}）', '', prose)
    rendered = markdown(prose)
    rendered = re.sub(r'<a href="#src-(\d+)">CITE\d+</a>', r'<sup><a href="#src-\1">\1</a></sup>', rendered)
    rows = ''.join(f'<li id="src-{number}"><a href="{html.escape(safe_url(url), quote=True)}">{html.escape(label or "來源 " + number)}</a></li>' for number, (label, url) in sorted(sources.items(), key=lambda x: int(x[0])))
    return rendered, ('<details class="sources"><summary>來源與參考資料 · ' + str(len(sources)) + '</summary><ol>' + rows + '</ol></details>') if rows else ''


def first_commit_date(db, path):
    # Read-only git query; never changes the index, worktree or refs.
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(db), 'log', '--follow', '--format=%cI', '--', str(path.relative_to(db))], capture_output=True, text=True, check=True)
    dates = result.stdout.splitlines()
    if not dates:
        raise ValueError(f'Legacy article has no commit date: {path}')
    return datetime.datetime.fromisoformat(dates[-1].replace('Z', '+00:00')).date().isoformat()


def read_articles(db):
    articles = []
    for folder, category in FOLDERS.items():
        for path in sorted((db / folder).rglob('*.md')):
            if path.name in SKIP:
                continue
            text = path.read_text(encoding='utf-8')
            data, body = parse_frontmatter(text)
            legacy = not bool(data)
            title_match = re.search(r'^# (.+)', body, re.M)
            title = data.get('title') or (title_match[1] if title_match else path.stem)
            slug = data.get('slug') or LEGACY_SLUGS.get(path.name) or 'legacy-' + hashlib.sha1(path.name.encode()).hexdigest()[:8]
            # Old-format pipeline articles may have a Unicode filename slug.
            if not re.fullmatch(r'[\w-]+', slug) or slug in ('.', '..'):
                raise ValueError('Unsafe slug: ' + slug)
            category = data.get('category', LEGACY_CATEGORIES.get(slug, FOLDERS[folder]))
            if category not in CATEGORIES:
                raise ValueError('Unknown category: ' + category)
            body = re.sub(r'^# .+\n?', '', body, count=1, flags=re.M).lstrip()
            paragraphs = [plain(x) for x in body.split('\n\n') if x.strip() and not x.startswith(('#', '-', '*', '>'))]
            summary = str(data.get('summary') or (paragraphs[0] if paragraphs else plain(body)))[:80]
            date = str(data.get('date') or first_commit_date(db, path))
            datetime.date.fromisoformat(date)
            words = data.get('words') or len(re.sub(r'\s+', '', plain(body)))
            spots = data.get('spots', LEGACY_SPOTS.get(slug, []) if legacy else [])
            if not isinstance(spots, list) or any(not re.fullmatch(r'[a-z0-9-]+', x) for x in spots):
                raise ValueError('Invalid spots: ' + str(spots))
            capture = re.search(r'抓取[：:]\s*(\d{4}-\d{2}-\d{2})', text)
            rendered, sources = sources_section(body)
            articles.append(dict(slug=slug, title=title, category=category, date=date, summary=summary,
                                 words=int(words), spots=spots, cover=f'assets/covers/{slug}.svg', legacy=legacy,
                                 body=rendered, sources=sources, captured=capture[1] if capture else date))
    if len({a['slug'] for a in articles}) != len(articles):
        raise ValueError('Duplicate article slug')
    return sorted(articles, key=lambda a: (a['date'], a['slug']), reverse=True)


CSS = '''
:root{--ink:#e9fbff;--dim:#8fb3bf;--accent:#2ff3e0;--pop:#ff5470;--edge:rgba(47,243,224,.28);--card:rgba(255,255,255,.045)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 95% 0,rgba(47,243,224,.10),transparent 45%),#020a10;color:var(--ink);font-family:"PingFang TC","Noto Sans TC",sans-serif;line-height:1.8}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
nav{display:flex;flex-wrap:wrap;gap:24px;padding:24px 0;border-bottom:1px solid var(--edge)}.wrap{width:min(1120px,calc(100% - 40px));margin:auto}.lab{font:12px ui-monospace,monospace;letter-spacing:.18em;color:var(--accent);text-transform:uppercase}.intro{padding:64px 0 32px}h1,h2,h3{line-height:1.2;letter-spacing:0;overflow-wrap:anywhere}h1{font-size:clamp(32px,5vw,62px);max-width:900px;margin:18px 0 24px}h2{font-size:27px;margin-top:42px}h3{font-size:21px}.dim,.meta,time{color:var(--dim)}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}.card{min-width:0;background:var(--card);border:1px solid var(--edge);border-radius:12px;overflow:hidden}.card .copy{padding:22px}.card h3{margin:10px 0 16px}.card p{color:var(--dim);font-size:14px}.card img{width:100%;height:auto;aspect-ratio:1200/630;object-fit:contain;display:block}.chips{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 30px}.chips button{border:1px solid var(--edge);border-radius:99px;color:var(--ink);background:transparent;padding:9px 18px;font:inherit;cursor:pointer}.chips button[aria-pressed=true]{background:var(--accent);color:#020a10}.article{max-width:720px;margin:0 auto;font-size:17px;line-height:1.8;overflow-wrap:anywhere}.article h1{font-size:clamp(28px,5vw,42px)}.article img{max-width:100%}.cover{width:100%;display:block;margin:42px auto 28px;border-radius:12px}.article blockquote{border-left:2px solid var(--accent);margin-left:0;padding:2px 20px;color:var(--dim)}li{margin:9px 0}sup{font-size:.7em;margin-left:2px}sup a{padding:3px}details{border:1px solid var(--edge);border-radius:10px;padding:18px;margin:36px 0}summary{color:var(--accent);cursor:pointer}.sources li{scroll-margin-top:24px}.sources li:target{background:rgba(47,243,224,.15)}.sources a{overflow-wrap:anywhere}.table-scroll{max-width:100%;overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid var(--edge);padding:10px;min-width:85px}th{background:var(--card)}.related{margin-top:48px}.spot-card{display:block;padding:20px;border:1px solid var(--edge);border-radius:10px;margin:10px 0}.legacy{color:var(--accent);font-size:13px}footer{padding:65px 0;color:var(--dim);font-size:12px}[hidden]{display:none!important}@media(max-width:700px){.grid{grid-template-columns:1fr}.intro{padding-top:34px}.wrap{width:calc(100% - 32px)}.article{font-size:16px}nav{gap:18px}.cover{margin-top:24px}.card h3{font-size:22px}h1{line-height:1.2}}
'''


def shell(title, summary, route, content, structured=None):
    # Relative paths allow local preview and project-path GitHub Pages deployment.
    depth = len([x for x in route.split('/') if x])
    prefix = '../' * depth
    absolute = SITE_URL + '/' + route
    ld = '<script type="application/ld+json">' + json.dumps(structured, ensure_ascii=False).replace('<', '\\u003c') + '</script>' if structured else ''
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} ｜ DiveInOut</title>
<meta name="description" content="{html.escape(summary, quote=True)}"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(summary, quote=True)}"><meta property="og:image" content="{SITE_URL}/assets/og-default.png"><link rel="canonical" href="{html.escape(absolute, quote=True)}">{ld}<style>{CSS}</style></head>
<body><div class="wrap"><nav aria-label="主要導覽"><a class="lab" href="{prefix}">← DiveInOut</a><a href="{prefix}articles/">文章</a><a href="{prefix}news/">情報</a><a href="{prefix}spots/">潛點地圖</a><a href="{prefix}ranking/">排名</a></nav><main>{content}</main><footer><span class="lab">DiveInOut / Pan-Asia Dive Mag</span><p>價格、季節及規範可能變動，出發前請向當地專業人員覆核。</p></footer></div></body></html>'''


def card(article, prefix='../'):
    return f'''<article class="card" data-category="{article['category']}"><a href="{prefix}articles/{article['slug']}/"><img src="{prefix}{article['cover']}" width="1200" height="630" loading="lazy" alt="{html.escape(article['title'], quote=True)}"></a><div class="copy"><span class="lab">{CATEGORIES[article['category']]}</span><h3><a href="{prefix}articles/{article['slug']}/">{html.escape(article['title'])}</a></h3><p>{html.escape(article['summary'])}</p><time datetime="{article['date']}">{article['date']}</time></div></article>'''


def news_items(text):
    match = re.search(r'^##[^\n]*今日重點[^\n]*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not match:
        return []
    blocks = re.split(r'^\s*[*-]\s+', match[1], flags=re.M)
    items = []
    for block in blocks:
        if not block.strip():
            continue
        title_match = re.match(r'\*\*(.+?)\*\*\s*[:：]?\s*', block)
        title = title_match[1] if title_match else plain(block.splitlines()[0])
        rest = block[title_match.end():] if title_match else block
        links = re.findall(r'\[([^\]]+)\]\((https?://[^\s]+)\)', block)
        summary = rest.split('→')[0]
        summary = re.sub(r'\[[^\]]*\]\([^)]+\)', '', summary)
        summary = re.sub(r'抓取[：:]\s*[\d-]+', '', summary)
        summary = re.sub(r'\s+', ' ', plain(summary)).strip()
        name, url = links[-1] if links else ('來源未提供', '')
        items.append(dict(title=title, summary=summary, source_name=name, source_url=safe_url(url) if url else '', category='本週情報', emoji='🌊'))
    return items


def build(db, out=ROOT):
    if not db.is_dir():
        raise ValueError('SAKIDIVE_DIR does not exist: ' + str(db))
    articles = read_articles(db)
    spot_data, areas, creatures = spot_pages.load(ROOT, db, articles)
    write(out / 'spots.json', json.dumps(spot_data, ensure_ascii=False, indent=2)+'\n')
    write(out / 'areas.json', json.dumps(areas, ensure_ascii=False, indent=2)+'\n')
    write(out / 'assets/creatures.svg', (ROOT / 'assets/creatures.svg').read_text())
    spot_pages.generate(spot_data, areas, creatures, articles, out, write, shell, SITE_URL)
    spots = {s['id']: s for s in spot_data['spots']}
    for a in articles:
        write(out / a['cover'], cover_svg(a['slug'], a['title'], a['category']))
        related = [x for x in articles if x['category'] == a['category'] and x['slug'] != a['slug']][:3]
        spot_cards = ''
        if a['spots']:
            spot_cards = '<h2>相關潛點</h2>' + ''.join(f'<a class="spot-card" href="../../spots/{sid}/">{html.escape(spots.get(sid, {}).get("name", sid))} →</a>' for sid in a['spots'])
        legacy = f'<p class="legacy">深度攻略・資料抓取於 {a["captured"]}</p>' if a['legacy'] else ''
        content = f'''<img class="cover" src="../../{a['cover']}" width="1200" height="630" alt="{html.escape(a['title'], quote=True)}"><article class="article">{legacy}<div class="lab">{CATEGORIES[a['category']]} / {a['date']} / {a['words']} 字 / 約 {math.ceil(a['words']/400)} 分鐘</div><h1>{html.escape(a['title'])}</h1>{a['body']}{spot_cards}</article><section class="related"><h2>繼續閱讀 · {CATEGORIES[a['category']]}</h2><div class="grid">{''.join(card(x, '../../') for x in related)}</div></section><div class="article">{a['sources']}</div><script>
function revealSource(){{const id=location.hash.slice(1);if(!id.startsWith('src-'))return;const target=document.getElementById(id);if(!target)return;const details=target.closest('details');if(details)details.open=true;target.scrollIntoView({{block:'center'}});}}
addEventListener('hashchange',revealSource);revealSource();
</script>''' 
        structured = {'@context': 'https://schema.org', '@type': 'Article', 'headline': a['title'], 'description': a['summary'], 'datePublished': a['date'], 'image': SITE_URL+'/assets/og-default.png', 'mainEntityOfPage': SITE_URL+'/articles/'+a['slug']+'/', 'author': {'@type': 'Organization', 'name': 'DiveInOut'}, 'publisher': {'@type': 'Organization', 'name': 'DiveInOut'}}
        write(out / 'articles' / a['slug'] / 'index.html', shell(a['title'], a['summary'], f'articles/{a["slug"]}/', content, structured))
    keys = ('slug', 'title', 'category', 'date', 'summary', 'words', 'spots', 'cover', 'legacy')
    write(out / 'articles/index.json', json.dumps([{k: a[k] for k in keys} for a in articles], ensure_ascii=False, indent=2)+'\n')
    chips = '<button type="button" data-filter="all" aria-pressed="true">全部</button>' + ''.join(f'<button type="button" data-filter="{key}" aria-pressed="false">{value}</button>' for key, value in CATEGORIES.items())
    script = '''<script>document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));let count=0;document.querySelectorAll('[data-category]').forEach(c=>{c.hidden=b.dataset.filter!=='all'&&c.dataset.category!==b.dataset.filter;if(!c.hidden)count++});document.getElementById('count').textContent=count+' 篇文章';}));</script>'''
    content = f'<header class="intro"><div class="lab">Stories / 潛旅日常</div><h1>每一次下潛之前。</h1><p class="dim">從亞洲潛旅到裝備與海洋，慢慢讀，安心下水。</p></header><div class="chips" aria-label="文章分類">{chips}</div><p class="dim" id="count" aria-live="polite">{len(articles)} 篇文章</p><div class="grid">'+''.join(card(a) for a in articles)+'</div>'+script
    write(out / 'articles/index.html', shell('文章', '亞洲潛旅、新手知識與裝備文章。', 'articles/', content))
    brief_sections, latest = [], None
    for path in sorted((db / '00_每日簡報').glob('*.md'), reverse=True):
        items = news_items(path.read_text())
        if not items:
            continue
        date = path.stem
        datetime.date.fromisoformat(date)
        if latest is None:
            latest = dict(week_of=date, updated=date, items=items)
        cards = ''.join('<article class="card"><div class="copy"><span class="lab">NEWS</span><h3>'+html.escape(item['title'])+'</h3><p>'+html.escape(item['summary'])+'</p>'+ (f'<a href="{html.escape(item["source_url"], quote=True)}" rel="noopener">來源：{html.escape(item["source_name"])} ↗</a>' if item['source_url'] else '<span class="dim">來源未提供</span>')+'</div></article>' for item in items)
        brief_sections.append(f'<section id="brief-{date}"><h2>{date} · 今日重點</h2><div class="grid">{cards}</div></section>')
    write(out / 'news/index.html', shell('每週情報', '潛旅、海洋與潛水安全的每週簡報重點。', 'news/', '<header class="intro"><div class="lab">News / 海面情報</div><h1>從海面，讀懂海裡。</h1><p class="dim">每週簡報重點與原始來源，依日期收錄。</p></header>'+''.join(brief_sections)))
    write(out / 'news/latest.json', json.dumps(latest or dict(week_of='', updated='', items=[]), ensure_ascii=False, indent=2)+'\n')
    write(out / 'assets/og-default.png', og_png())
    routes = ['', 'articles/', 'news/', 'spots/', 'creatures/', 'ranking/'] + ['articles/'+a['slug']+'/' for a in articles]
    routes += [str(path.parent.relative_to(out))+'/' for path in sorted((out/'spots').glob('*/index.html'))]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(SITE_URL+'/'+route)+'</loc></url>' for route in routes)+'</urlset>\n'
    write(out / 'sitemap.xml', sitemap)
    write(out / 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n')
    print(f'Built {len(articles)} articles, {len(brief_sections)} briefs; {sum(a["legacy"] for a in articles)} legacy articles.')


if __name__ == '__main__':
    build(Path(os.environ.get('SAKIDIVE_DIR', str(ROOT.parent/'SakiDiveDB'))).resolve())
