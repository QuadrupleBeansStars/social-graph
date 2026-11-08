import json
from pytrends.request import TrendReq
p = TrendReq(hl='th-TH', tz=-420)
p.build_payload(['น้ำท่วม'], geo='TH', timeframe='2026-09-01 2026-09-30')
s = p.interest_over_time()['น้ำท่วม']
json.dump({str(k.date()): int(v) for k, v in s.items()}, open('daily_sep2026.json', 'w'))
for k, v in s.items(): print(k.date(), f"{v:3d}", "█" * (v // 2))
