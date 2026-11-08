import json, time
from pytrends.request import TrendReq
p = TrendReq(hl='th-TH', tz=-420)
out = {}
p.build_payload(['น้ำท่วม'], geo='TH', timeframe='today 5-y')
s = p.interest_over_time()['น้ำท่วม']; out['five_y'] = {str(k.date()): int(v) for k, v in s.items()}
print(s.resample('ME').max().tail(40).to_string())
json.dump(out, open('raw.json', 'w'), ensure_ascii=False)
