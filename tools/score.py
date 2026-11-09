"""Published recommendation formula. Round halves upward, never banker rounding."""
import datetime
import math

PARTS = {'diversity': ('生物多樣性', 30), 'season': ('可潛季節', 20), 'beginner': ('新手友善', 20), 'signature': ('招牌生物', 20), 'trust': ('資料可信度', 10)}
EXPLANATION = '推薦指數是 DiveInOut 依公開資料計算的分數,滿分 100:生物多樣性 30、可潛季節 20、新手友善 20、招牌生物 20、資料可信度 10。目前沒有使用瀏覽數,所以這不是人氣排行;資料標『待查證』的潛點,分數會隨查證更新。'
def species(s):
    return {x['c'] for rows in s.get('monthly', {}).values() for x in rows}
def month_score(s, month):
    return sum({'high': 2, 'mid': 1, 'low': .5}[x['p']] for x in s.get('monthly', {}).get(str(month), []))
def calculate(spots, today=None):
    today = today or datetime.date.today()
    maximum = max((len(species(s)) for s in spots), default=0)
    for s in spots:
        try: recent = 0 <= (today-datetime.date.fromisoformat(s.get('checked', ''))).days <= 180
        except (ValueError, TypeError): recent = False
        sources = len(s.get('sources', []))
        signature = set(s.get('tags', [])) | species(s)
        parts = dict(diversity=len(species(s))/maximum*30 if maximum else 0, season=len(set(s['months']))/12*20, beginner={'beginner':20,'intermediate':12,'advanced':5}[s['levelMin']], signature=min(20,5*len(signature & {'manta','whaleshark','turtle','mola','hammer'})), trust=10 if sources>=3 and recent else 5 if sources else 0)
        s['score'] = {'total': math.floor(sum(parts.values())+.5), 'parts': parts}
    return sorted(spots, key=lambda s: (-s['score']['total'], s['id']))
