import json, time
from pytrends.request import TrendReq
p = TrendReq(hl='th-TH', tz=-420)
out = json.load(open('raw.json'))
EV = {"2024 North": "2024-08-01 2024-11-30", "2025 Hat Yai": "2025-11-01 2025-12-31", "2026 Sep": "2026-08-15 2026-11-07"}
def go(kw, tf, key):
    for i in range(4):
        try:
            p.build_payload(kw, geo='TH', timeframe=tf); return p
        except Exception as e: print('retry', key, e); time.sleep(20 * (i + 1))
for name, tf in EV.items():
    go(['น้ำท่วม'], tf, name)
    s = p.interest_over_time()['น้ำท่วม']; out[f'daily:{name}'] = {str(k.date()): int(v) for k, v in s.items()}; time.sleep(6)
    r = p.interest_by_region(resolution='REGION', inc_low_vol=True)['น้ำท่วม']
    out[f'region:{name}'] = {k: int(v) for k, v in r.items() if v > 0}; time.sleep(6)
    rq = p.related_queries()['น้ำท่วม']
    out[f'rising:{name}'] = rq['rising'].head(15).values.tolist() if rq['rising'] is not None else []
    out[f'top:{name}'] = rq['top'].head(15).values.tolist() if rq['top'] is not None else []
    print(name, sorted(out[f'region:{name}'].items(), key=lambda x: -x[1])[:6]); print(out[f'rising:{name}'][:10]); time.sleep(8)
# business-relevant demand terms over 5y (max 5 per payload; anchor น้ำท่วม in both)
G = [['น้ำท่วม', 'ประกันน้ำท่วม', 'กระสอบทราย', 'ปั๊มน้ำ', 'บริจาค'], ['น้ำท่วม', 'ซ่อมรถน้ำท่วม', 'เรือ', 'ทำความสะอาดบ้าน', 'เยียวยาน้ำท่วม']]
for i, g in enumerate(G):
    go(g, 'today 5-y', f'g{i}'); df = p.interest_over_time()
    for k in g[1:]: out[f'demand:{k}'] = {str(d.date()): int(v) for d, v in df[k].items()}
    out[f'anchor{i}'] = {str(d.date()): int(v) for d, v in df['น้ำท่วม'].items()}
    print(g, df[g].resample('ME').max().tail(16).to_string()); time.sleep(8)
json.dump(out, open('raw.json', 'w'), ensure_ascii=False)
