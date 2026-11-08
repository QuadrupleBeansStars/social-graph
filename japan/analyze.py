"""Pantip Japan travel posts + JNTO Thai arrivals -> data/viz.json"""
import json, re, collections, itertools, datetime as D, warnings
warnings.filterwarnings("ignore")
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus import thai_stopwords, thai_words
from pythainlp.util import dict_trie
import networkx as nx

OFF = {"การ์ตูนญี่ปุ่น", "Disneyland", "อาหารญี่ปุ่น", "คนไทยในญี่ปุ่น"}
START, FULL_END = "2025-01", "2026-09"   # Oct-Nov 2026 over-sampled (main tag only reaches back 3 weeks)

PLACES = {  # canonical -> spellings
 "Tokyo": ["โตเกียว", "tokyo"], "Osaka": ["โอซาก้า", "โอซาก้า", "osaka", "นัมบะ", "namba", "umeda", "อุเมดะ"],
 "Kyoto": ["เกียวโต", "kyoto", "อาราชิยาม่า", "arashiyama", "ฟูชิมิ"], "Nara": ["นารา", "nara"],
 "Hokkaido": ["ฮอกไกโด", "hokkaido"], "Sapporo": ["ซัปโปโร", "ซัปโปะโระ", "sapporo"], "Otaru": ["โอตารุ", "otaru"],
 "Hakodate": ["ฮาโกดาเตะ", "hakodate"], "Biei/Furano": ["บิเอ", "biei", "ฟุราโน่", "furano"],
 "Fukuoka": ["ฟุกุโอกะ", "fukuoka", "hakata", "ฮากาตะ"], "Kyushu": ["คิวชู", "kyushu", "beppu", "เบปปุ", "yufuin", "ยูฟุอิน"],
 "Okinawa": ["โอกินาว่า", "okinawa"], "Nagoya": ["นาโกย่า", "nagoya"], "Takayama": ["ทาคายาม่า", "takayama"],
 "Shirakawa-go": ["ชิราคาวาโกะ", "shirakawa"], "Kanazawa": ["คานาซาว่า", "kanazawa"],
 "Fuji/Kawaguchiko": ["ฟูจิ", "fuji", "คาวากุจิโกะ", "kawaguchiko"], "Hakone": ["ฮาโกเน่", "hakone"],
 "Hiroshima": ["ฮิโรชิม่า", "hiroshima", "มิยาจิม่า"], "Tohoku/Sendai": ["โทโฮคุ", "tohoku", "เซนได", "sendai"],
 "Kamakura": ["คามาคุระ", "kamakura"], "Yokohama": ["โยโกฮาม่า", "yokohama"], "Nikko": ["นิกโก้", "nikko"],
}
THEMES = {  # seasonal / interest themes
 "sakura": ["ซากุระ", "sakura", "ฮานามิ"], "autumn leaves": ["ใบไม้เปลี่ยนสี", "ใบไม้แดง", "โมมิจิ", "momiji", "koyo"],
 "snow": ["หิมะ", "snow", "สกี", "ski"], "onsen": ["ออนเซ็น", "onsen"], "lavender/flowers": ["ลาเวนเดอร์", "ทุ่งดอกไม้"],
 "JR pass": ["jr pass", "เจอาร์พาส", "jrpass"], "shinkansen": ["ชินคันเซ็น", "shinkansen"], "rent a car": ["เช่ารถ", "ขับรถ"],
 "budget/yen": ["งบ", "เยน", "ค่าใช้จ่าย", "แลกเงิน"], "hotel": ["โรงแรม", "ที่พัก", "hotel"],
 "shopping": ["ช้อป", "shopping", "ดองกี้", "donki", "uniqlo"], "food": ["ราเมง", "ซูชิ", "อาหาร", "ร้านอาหาร", "wagyu", "เนื้อวากิว"],
 "USJ/Disney": ["usj", "universal", "ยูนิเวอร์แซล", "disney", "ดิสนีย์"], "matcha": ["มัทฉะ", "matcha"],
 "immigration/visa": ["ตม.", "ตม ", "วีซ่า", "visa", "jesta", "visit japan web"],
}
PLAN = re.compile(r"\?|ไหม|มั้ย|ยังไง|อย่างไร|แนะนำ|สอบถาม|ขอคำ|ช่วย|รบกวน|ดีไหม|ควร|แพลน|ปรึกษา|หรือเปล่า|ได้ไหม|บ้างคะ|บ้างครับ")
REVIEW = re.compile(r"รีวิว|review|พาเที่ยว|เที่ยว.*วัน|ทริป|trip|บันทึก|เล่า|ไปมาแล้ว|day ?\d|วันที่ ?\d|ep\.?\s?\d|\[cr\]|cr\b", re.I)
TH_M = {"ม.ค": 1, "มกรา": 1, "ก.พ": 2, "กุมภา": 2, "มี.ค": 3, "มีนา": 3, "เม.ย": 4, "เมษา": 4, "พ.ค": 5, "พฤษภา": 5,
        "มิ.ย": 6, "มิถุนา": 6, "ก.ค": 7, "กรกฎา": 7, "ส.ค": 8, "สิงหา": 8, "ก.ย": 9, "กันยา": 9, "ต.ค": 10, "ตุลา": 10,
        "พ.ย": 11, "พฤศจิกา": 11, "ธ.ค": 12, "ธันวา": 12}
EN_M = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
MRE = re.compile(r"(" + "|".join(sorted(map(re.escape, TH_M), key=len, reverse=True)) + r"|\b(?:" + "|".join(EN_M) + r")[a-z]*\b)", re.I)

def trip_month(text):
    m = MRE.search(text)
    if not m: return None
    k = m.group(1).lower()
    return next((v for kk, v in TH_M.items() if k.startswith(kk.lower())), None) or EN_M.get(k[:3])

def season(mo): return {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
                        6: "Summer", 7: "Summer", 8: "Summer"}.get(mo, "Autumn")

ALLK = {k for d in (PLACES, THEMES) for ks in d.values() for k in ks}
TRIE = dict_trie(set(thai_words()) | ALLK)
STOP = set(thai_stopwords()) | set("""ครับ ค่ะ คะ นะ จ้า ค่า เลย ก็ ที่ แต่ คือ มี ไป มา ได้ ให้ จะ ไม่ เป็น ว่า กับ แล้ว ของ และ ใน คน อัน ตัว เอง กัน ยัง ตอน เคย อยู่ ทำ แบบ ขอ ถาม ดู รู้ อะไร เท่า ไหร่ จริง นะคะ ขอบคุณ ผม เรา คุณ ครับผม ด้วย มาก ก่อน หลัง บาง อย่าง ตาม ส่วน เพราะ ถ้า เห็น บอก คิด แค่ นี้ นั้น ไง หรอ เหรอ คับ จ้ะ ฮะ เนอะ อ่ะ อะ ญี่ปุ่น japan เที่ยว วัน ไหม มั้ย ดี ช่วง ลอง เดือน ปี ครั้ง เดินทาง ที่นี่ ตรงนี้ คนไทย ประเทศ ประเทศไทย ไทย ค่ะ""".split())

def find(d, low): return [k for k, ks in d.items() if any(s in low for s in ks)]
def month_of(r):
    t = r["time"]
    if isinstance(t, str): return t[:7]
    return D.datetime.utcfromtimestamp(t).strftime("%Y-%m") if t else None

rows = [json.loads(l) for l in open("data/posts.jsonl")]
T = {r["topic_id"]: r for r in rows if r["kind"] == "topic"}
travel = {k for k, t in T.items() if set(t["src"]) - OFF}
data = []
for r in rows:
    if r["topic_id"] not in travel or not r["text"]: continue
    m = month_of(r) or month_of(T[r["topic_id"]])
    if not m or m < START: continue
    low = r["text"].lower()
    toks = [w.strip().lower() for w in word_tokenize(r["text"], engine="newmm", custom_dict=TRIE, keep_whitespace=False)]
    toks = {w for w in toks if w not in ALLK and w not in STOP and len(w) > 1 and not re.fullmatch(r"[\d\W_a-z]{1,2}|[\d\W_]+", w)}
    data.append({"m": m, "kind": r["kind"], "tid": r["topic_id"], "places": find(PLACES, low), "themes": find(THEMES, low), "toks": toks})

months = [m for m in sorted({d["m"] for d in data})]
arr = json.load(open("data/jnto_thai_arrivals.json"))

# 1. volume
vol = {k: [sum(1 for d in data if d["m"] == m and d["kind"] == k) for m in months] for k in ("topic", "comment")}

# 2. planning vs review (topics)
intent = {m: collections.Counter() for m in months}
tr_lead = []  # (post month, trip month) for planning topics naming a month
topic_rows = []
for tid in travel:
    t = T[tid]; m = month_of(t)
    if not m or m < START: continue
    title = t["text"]
    kind = "review" if REVIEW.search(title) and not PLAN.search(title) else "planning" if PLAN.search(title) else "other"
    intent[m][kind] += 1
    tm = trip_month(title)
    if kind == "planning" and tm:
        pm = int(m[5:]); lead = (tm - pm) % 12
        tr_lead.append({"post": m, "trip": tm, "lead": lead, "title": title[:80]})
    topic_rows.append({"m": m, "kind": kind, "title": title[:90], "tid": tid, "views": t.get("views"), "nc": t.get("n_comments")})

# 3. place x trip-season (by trip month if named, else post month) using all posts
full_ = [d for d in data if d["m"] <= FULL_END]
ps = collections.defaultdict(collections.Counter); ts_ = collections.defaultdict(collections.Counter)
tripm = {tid: trip_month(T[tid]["text"]) for tid in travel}
for d in full_:
    mo = tripm.get(d["tid"]) or int(d["m"][5:])
    s = season(mo)
    for p in d["places"]: ps[p][s] += 1
    for th in d["themes"]: ts_[th][s] += 1

# 4. seasonal networks (by post-month season, full-coverage months only + all)
def graph(sub, top=40, min_w=3):
    df = collections.Counter()
    for d in sub:
        df.update(d["toks"]); df.update("@" + p for p in d["places"]); df.update("#" + t for t in d["themes"])
    ent = [k for k in df if k[0] in "@#" and df[k] >= 4]
    words = [k for k, _ in df.most_common(300) if k[0] not in "@#"][:top]
    keep = set(ent) | set(words)
    E = collections.Counter()
    for d in sub:
        nodes = sorted((d["toks"] | {"@" + p for p in d["places"]} | {"#" + t for t in d["themes"]}) & keep)
        for a, b in itertools.combinations(nodes, 2): E[(a, b)] += 1
    G = nx.Graph()
    for (a, b), w in E.items():
        if w >= min_w: G.add_edge(a, b, weight=w)
    if not len(G): return {"nodes": [], "links": []}
    comm = nx.community.louvain_communities(G, weight="weight", seed=1)
    cid = {n: i for i, c in enumerate(comm) for n in c}
    return {"nodes": [{"id": n, "n": df[n], "c": cid[n], "t": "place" if n[0] == "@" else "theme" if n[0] == "#" else "word"} for n in G],
            "links": [{"source": a, "target": b, "w": dd["weight"]} for a, b, dd in G.edges(data=True)]}

full = [d for d in data if d["m"] <= FULL_END]
graphs = {"All": graph(full, min_w=5)}
for s in ["Winter", "Spring", "Summer", "Autumn"]:
    graphs[s] = graph([d for d in full if season(int(d["m"][5:])) == s], min_w=3)

import numpy as np
fm = [m for m in months if m <= FULL_END]
post = np.array([sum(1 for d in full_ if d["m"] == m) for m in fm], float)
arv = np.array([arr[m] for m in fm], float)
season_n = collections.Counter(season(tripm.get(d["tid"]) or int(d["m"][5:])) for d in full_)
lagc = {}
for L in range(-3, 4):  # L>0: posts lead arrivals by L months
    a, b = (post[:len(post)-L], arv[L:]) if L >= 0 else (post[-L:], arv[:len(arv)+L])
    lagc[L] = round(float(np.corrcoef(a, b)[0, 1]), 2)
print("lag corr (posts lead arrivals by L months):", lagc)
out = {"months": months, "full_end": FULL_END, "arrivals": arr, "volume": vol,
       "intent": {m: dict(intent[m]) for m in months}, "lead": tr_lead,
       "place_season": {p: dict(c) for p, c in ps.items() if sum(c.values()) >= 8},
       "theme_season": {p: dict(c) for p, c in ts_.items() if sum(c.values()) >= 8},
       "graphs": graphs, "lagc": lagc, "season_n": dict(season_n), "n_rows": len(data), "n_threads": len(topic_rows),
       "top_threads": sorted(topic_rows, key=lambda x: -(x["nc"] or 0))[:12]}
json.dump(out, open("data/viz.json", "w"), ensure_ascii=False)

print("rows", len(data), "threads", len(topic_rows))
print("vol", list(zip(months, vol["topic"], vol["comment"])))
print("intent", {m: dict(intent[m]) for m in months})
print("leads", collections.Counter(x["lead"] for x in tr_lead), len(tr_lead))
print("trip months", collections.Counter(x["trip"] for x in tr_lead))
for p, c in sorted(out["place_season"].items(), key=lambda x: -sum(x[1].values())): print(p, dict(c))
for p, c in sorted(out["theme_season"].items(), key=lambda x: -sum(x[1].values())): print(p, dict(c))
for k, g in graphs.items(): print(k, len(g["nodes"]), len(g["links"]), sorted([n["id"] for n in g["nodes"] if n["t"] != "word"]))
