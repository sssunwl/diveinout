"""Phase B data merging and static pages; standard library only."""
import json
import re
from html import escape as e
from urllib.parse import quote
from seed_monthly import seed_monthly
from score import calculate, PARTS, EXPLANATION, month_score

COUNTRIES = dict(zip('japan taiwan philippines palau indonesia thailand malaysia maldives egypt'.split(), '日本 台灣 菲律賓 帛琉 印尼 泰國 馬來西亞 馬爾地夫 埃及'.split()))
AREA_NAMES = dict(zip('okinawa-main ishigaki yonaguni kerama miyako kenting green-island xiaoliuqiu lanyu northeast-coast cebu bohol anilao coron palau bali komodo raja-ampat similan sipadan maldives red-sea'.split(), '沖繩本島 石垣島 與那國島 慶良間群島 宮古島 墾丁 綠島 小琉球 蘭嶼 東北角 宿霧 薄荷島 阿尼洛 科隆 帛琉 峇里島 科莫多 四王群島 斯米蘭 詩巴丹 馬爾地夫 紅海'.split()))
def region(area):
    return 'okinawa' if area.startswith(('okinawa-', 'kerama', 'miyako', 'ishigaki', 'yonaguni', 'kume')) else area

def load(root, db, articles):
    data = json.loads((root/'data/spots_seed.json').read_text())
    creatures = json.loads((root/'creatures.json').read_text())['creatures']
    spots = {}
    for s in data['spots']:
        seed_monthly(s, creatures)
        s.update(waterTemp={}, visibility='', sources=[], checked='', article='')
        spots[s['id']] = s
    for path in sorted((db/'data/spots').glob('*.json')):
        override = json.loads(path.read_text())
        sid = override['id']
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', sid):
            raise ValueError('Invalid spot id: '+sid)
        merged = {**spots.get(sid, {}), **override}
        if 'monthly' in override:
            merged['monthlySeed'] = override.get('monthlySeed', False)
            if 'monthlyNote' not in override: merged['monthlyNote'] = ''
        for key, default in [('monthly', {}), ('monthlyNote', ''), ('monthlySeed', False), ('sources', []), ('checked', ''), ('waterTemp', {}), ('visibility', ''), ('tags', []), ('warn', False), ('note', ''), ('see', '')]:
            merged.setdefault(key, default)
        merged['monthly'] = {str(m): merged['monthly'].get(str(m), []) for m in range(1,13)}
        spots[sid] = merged
    areas = []
    for aid in sorted({s['area'] for s in spots.values()}):
        rows = [s for s in spots.values() if s['area']==aid]
        areas.append(dict(id=aid, name=next((s['areaName'] for s in rows if s.get('areaName')), AREA_NAMES.get(aid,aid)), country=rows[0]['country'], region=region(aid), lat=sum(s['lat'] for s in rows)/len(rows), lng=sum(s['lng'] for s in rows)/len(rows)))
    for s in spots.values():
        s['article'] = next((a['slug'] for a in articles if s['id'] in a['spots']), '')
    data.update(schemaVersion=3, spots=calculate(list(spots.values())))
    return data, areas, creatures

CSS = '''<style>
.spot-intro{padding:45px 0 20px}.spot-intro h1{margin-bottom:12px}.crumb{font-size:13px;color:var(--dim)}.facts{display:flex;flex-wrap:wrap;gap:8px}.fact{border:1px solid var(--edge);border-radius:30px;padding:4px 12px;font-size:13px}.spot-map{height:280px;border:1px solid var(--edge);border-radius:12px;margin-top:26px;z-index:0}.calendar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.calendar details{margin:0;padding:12px;min-width:0;background:var(--card)}.calendar summary{list-style:none}.calendar summary strong{display:block}.calendar small{display:block;font-size:10px;color:#ffd27d;text-align:right}.icons{display:flex;flex-wrap:wrap;min-height:48px;gap:4px}.icons svg{width:36px;height:36px;color:var(--accent)}.p-low{opacity:.4}.p-mid{opacity:.7}.p-high{opacity:1}.calendar a{font-size:12px;display:block}.calendar p{font-size:12px}.score-parts{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.score-part{font-size:12px}.score-part progress{width:100%;accent-color:var(--accent);display:block}.warning-box{border:1px solid #ffd27d;padding:18px;border-radius:10px;color:#ffd27d}.rank-row{display:grid;grid-template-columns:48px minmax(0,1fr) 70px;gap:14px;padding:22px 0;border-bottom:1px solid var(--edge)}.rank-row h2{font-size:22px;margin:0}.rank-row .score-parts{grid-column:2/4}.rank-number,.rank-total{font:28px ui-monospace,monospace;color:var(--accent)}.rank-total{text-align:right}.rank-controls{display:flex;flex-wrap:wrap;gap:16px}.rank-controls label{font-size:13px}.rank-controls select{display:block;max-width:100%;padding:9px;background:#0b202a;color:var(--ink);border:1px solid var(--edge);border-radius:8px}.spot-copy{overflow-wrap:anywhere}.leaflet-container{background:#192b31}.rank-row small{color:var(--dim)}
@media(max-width:600px){.calendar{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.calendar details{padding:8px}.icons svg{width:27px;height:27px}.score-parts{gap:6px}.score-part{font-size:10px}.rank-row{gap:8px;grid-template-columns:30px minmax(0,1fr) 48px}.rank-total,.rank-number{font-size:23px}.spot-map{height:230px}}
</style>'''

def breakdown(s):
    return '<div class="score-parts">'+''.join(f'<div class="score-part">{label}<br>{s["score"]["parts"][key]:.1f} / {maximum}<progress aria-label="{label}" value="{s["score"]["parts"][key]}" max="{maximum}"></progress></div>' for key,(label,maximum) in PARTS.items())+'</div>'

def generate(data, areas, creatures, articles, out, write, shell, site_url):
    byarea = {a['id']:a for a in areas}; cr = {c['id']:c for c in creatures}; ar = {a['slug']:a for a in articles}
    for s in data['spots']:
        area = byarea[s['area']]; country = COUNTRIES.get(s['country'],s['country'])
        calendar = []
        for m in range(1,13):
            rows = s['monthly'].get(str(m), [])
            icons = ''.join(f'<svg class="p-{e(x["p"])}" viewBox="0 0 100 100" role="img" aria-label="{e(cr.get(x["c"],{}).get("name",x["c"]))}"><use href="../../assets/creatures.svg#{e((cr[x["c"]].get("svg") or x["c"]))}"></use></svg>' for x in rows if x['c'] in cr)
            icons += ''.join('<span class="fact">'+e(cr.get(x['c'],{}).get('name',x['c']))+'</span>' for x in rows if x['c'] not in cr)
            links = ''.join(f'<a href="../../creatures/#{quote(x["c"])}">{e(cr.get(x["c"],{}).get("name",x["c"]))} · {dict(high="高",mid="中",low="低")[x["p"]]}</a>' for x in rows)
            calendar.append(f'<details data-month="{m}"><summary><strong>{m} 月</strong><span class="icons">{icons}</span>{"<small>待查證</small>" if s.get("monthlySeed") else ""}</summary>{links or "<p>尚無生物月份資料</p>"}</details>')
        a = ar.get(s['article'])
        intro = f'<p>{e(a["summary"])}</p><a href="../../articles/{a["slug"]}/">讀完整介紹 →</a>' if a else f'<p>{e(s["see"])}</p><p>{e(s["note"])}</p>'
        water = ''
        if s.get('waterTemp'):
            temp = s['waterTemp']; water += '<h2>水溫</h2><p>'+e(' / '.join(f'{m}月 {v}°C' for m,v in temp.items()) if isinstance(temp,dict) else str(temp))+'</p>'
        if s.get('visibility'): water += '<h2>能見度</h2><p>'+e(str(s['visibility']))+'</p>'
        related = ''.join(f'<a class="spot-card" href="../{x["id"]}/">{e(x["name"])} →</a>' for x in data['spots'] if x['area']==s['area'] and x['id']!=s['id'])
        sources = ''.join(f'<li><a href="{e(x["url"] if x["url"].startswith(("https://","http://")) else "#",quote=True)}">{e(x.get("title",x["url"]))}</a> · {e(x.get("checked", ""))}</li>' for x in s['sources'])
        content = CSS+f'''<header class="spot-intro"><div class="crumb"><a href="../?c={s['country']}">{e(country)}</a> › <a href="../?c={s['country']}&amp;r={s['area']}">{e(area['name'])}</a> › {e(s['name'])}</div><div class="lab">Dive spot / 潛點介紹</div><h1>{e(s['name'])}</h1><p class="dim">{e(s['place'])}</p><div class="facts"><span class="fact">{e(s['level'])}</span><span class="fact">{e(s['type'])}</span><span class="fact">最佳月份：{'、'.join(map(str,s['months']))} 月</span></div></header><div id="spotMap" class="spot-map" aria-label="潛點位置地圖"></div><section><h2>1–12 月生物月曆</h2><p class="dim">{e(s['monthlyNote'])} · 圖示深淺代表機率：高／中／低。點月份展開生物清單；未列出不代表不會出現。</p><div class="calendar">{''.join(calendar)}</div></section><div class="spot-copy">{water}<h2>潛點介紹</h2>{intro}<h2>推薦指數 · {s['score']['total']} / 100</h2>{breakdown(s)}<p><a href="../../ranking/">查看排名與計算方式 →</a></p>{('<h2>注意事項</h2><div class="warning-box">出發前請覆核季節與規範<p>'+e(s['note'])+'</p></div>') if s['warn'] else ''}<h2>同地區其他潛點</h2>{related or '<p class="dim">目前尚無其他收錄潛點。</p>'}<h2>來源與最後查證日</h2><p class="dim">最後查證：{e(s['checked'] or '尚未查證')}</p>{'<ul>'+sources+'</ul>' if sources else '<p class="dim">現有 seed 資料，來源待補、月份待查證。</p>'}</div>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>const map=L.map('spotMap',{{scrollWheelZoom:false}}).setView([{s['lat']},{s['lng']}],9);L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}',{{attribution:'Tiles © Esri',maxZoom:16}}).addTo(map);L.marker([{s['lat']},{s['lng']}]).addTo(map);</script>'''
        structured = {'@context':'https://schema.org','@type':'TouristAttraction','name':s['name'],'description':s['see'],'url':site_url+'/spots/'+s['id']+'/', 'geo':{'@type':'GeoCoordinates','latitude':s['lat'],'longitude':s['lng']}}
        write(out/'spots'/s['id']/'index.html',shell(s['name'],s['see'],'spots/'+s['id']+'/',content,structured))
    options = lambda rows: ''.join(f'<option value="{e(k)}">{e(v)}</option>' for k,v in rows)
    controls = '<div class="rank-controls"><label>國家<select id="country"><option value="">全部國家</option>'+options((c,COUNTRIES.get(c,c)) for c in sorted({s['country'] for s in data['spots']}))+'</select></label><label>地區<select id="area"><option value="">全部地區</option><option value="okinawa">沖繩全部</option>'+options((a['id'],a['name']) for a in areas)+'</select></label><label>程度<select id="beginner"><option value="">全部程度</option><option value="beginner">新手</option></select></label><label>月份<select id="month"><option value="">全年推薦指數</option>'+options((str(m),f'{m} 月') for m in range(1,13))+'</select></label></div>'
    rows = ''.join(f'<article class="rank-row" data-id="{s["id"]}"><span class="rank-number">{i}</span><div><h2><a href="../spots/{s["id"]}/">{e(s["name"])}</a></h2><small>{e(COUNTRIES.get(s["country"],s["country"]))} · {e(byarea[s["area"]]["name"])}</small><div class="month-value"></div></div><strong class="rank-total">{s["score"]["total"]}</strong>{breakdown(s)}</article>' for i,s in enumerate(data['spots'],1))
    payload=json.dumps([dict(id=s['id'],country=s['country'],area=s['area'],region=region(s['area']),beginner=s['levelMin'],total=s['score']['total'],months=[month_score(s,m) for m in range(1,13)]) for s in data['spots']],ensure_ascii=False).replace('<','\\u003c')
    script='''<script>const spots=PAYLOAD,ids=['country','area','beginner','month'],controls=Object.fromEntries(ids.map(id=>[id,document.getElementById(id)])),rows=new Map([...document.querySelectorAll('.rank-row')].map(x=>[x.dataset.id,x]));function render(){const c=controls.country.value,a=controls.area.value,b=controls.beginner.value,m=Number(controls.month.value);[...controls.area.options].forEach(o=>{o.hidden=!!(c&&o.value&& !spots.some(s=>s.country===c&&(s.area===o.value||s.region===o.value)))});const selected=spots.filter(s=>(!c||s.country===c)&&(!a||s.area===a||s.region===a)&&(!b||s.beginner===b)).sort((a,b)=>(m?b.months[m-1]-a.months[m-1]:b.total-a.total)||(a.id<b.id?-1:1));rows.forEach(r=>r.hidden=true);selected.forEach((s,i)=>{const row=rows.get(s.id);row.hidden=false;row.querySelector('.rank-number').textContent=i+1;row.querySelector('.month-value').textContent=m?m+' 月生物加權：'+s.months[m-1]:'';document.getElementById('ranks').append(row)});document.getElementById('rankCount').textContent=selected.length+' 個潛點';}ids.forEach(id=>controls[id].addEventListener('change',()=>{if(id==='country')controls.area.value='';render()}));render();</script>'''.replace('PAYLOAD',payload)
    content=CSS+'<header class="intro"><div class="lab">Dive rankings / 推薦指數</div><h1>下一潛，去哪裡？</h1><h2>排名怎麼算</h2><p>'+EXPLANATION+'</p><p class="dim">多樣性＝全年不同物種數 ÷ 全站最大值 × 30；季節＝最佳月份數 ÷ 12 × 20；程度：新手 20、AOWD 12、進階 5；招牌生物：鬼蝠魟、鯨鯊、海龜、翻車魚、錘頭鯊各 5，上限 20；來源 ≥3 且最後查證在建站日 180 天內得 10，來源 ≥1 得 5，其餘 0。總分四捨五入，同分依 id 排序。月份排名依該月生物加權：高 2、中 1、低 0.5；右側仍顯示全年推薦指數，下方五項為全年分數。</p></header>'+controls+'<p id="rankCount" aria-live="polite"></p><div id="ranks">'+rows+'</div>'+script
    write(out/'ranking/index.html',shell('潛點推薦排名',EXPLANATION,'ranking/',content))
