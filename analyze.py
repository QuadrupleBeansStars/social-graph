"""posts.jsonl -> data/viz.json : monthly brand volume/sentiment + monthly term co-occurrence graphs"""
import json, collections, warnings; warnings.filterwarnings("ignore")
import json, collections, itertools, datetime as D, re
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus import thai_stopwords, thai_words
from pythainlp.util import dict_trie
import networkx as nx

BRANDS = {
    "Starbucks": ["starbucks", "สตาบัค", "สตาร์บัค", "สตาร์บัคส์", "สตาบัก", "sbux"],
    "Café Amazon": ["amazon", "อเมซอน", "อะเมซอน", "แอมะซอน"],
    "Inthanin": ["อินทนิล", "inthanin"],
    "7-Eleven / All Café": ["all cafe", "ออลคาเฟ่", "เซเว่น", "7-11", "7-eleven"],
    "Black Canyon": ["black canyon", "แบล็คแคนยอน"],
    "True Coffee": ["true coffee", "ทรูคอฟฟี่"],
    "Doi Chaang": ["ดอยช้าง", "doi chaang"],
    "Punthai": ["พันธุ์ไทย", "punthai"],
    "Luckin": ["luckin", "ลัคอิน"],
    "Mixue / Chinese chains": ["mixue", "มี่เสวี่ย", "มิกซ์เซว่", "chagee", "ชาจี", "cotti", "luckin"],
}
POS = "อร่อย ชอบ ดี ถูก คุ้ม หอม เข้ม ประทับใจ สะดวก น่ารัก แนะนำ เยี่ยม สุดยอด ฟิน ละมุน กลมกล่อม เร็ว สบาย สวย".split()
NEG = "แพง ไม่อร่อย แย่ ช้า เสีย หวานเกิน จืด เปรี้ยว ผิดหวัง ห่วย ไม่ชอบ รอนาน งก บ่น ขม เหม็น โกง ปิด ขาดทุน ลด หาย เจ๊ง".split()
STOP = set(thai_stopwords()) | set("ครับ ค่ะ คะ นะ จ้า ค่า เลย ก็ ที่ แต่ คือ มี ไป มา ได้ ให้ จะ ไม่ เป็น ว่า กับ แล้ว ของ และ ใน คน ร้าน กิน ซื้อ ทาน อัน ตัว เอง กัน ยัง ตอน เคย อยู่ ทำ แบบ ขอ ถาม ดู รู้ อะไร เท่า ไหร่ จริง ๆ นะคะ ขอบคุณ ผม เรา คุณ ครับผม ค่ะ ด้วย มาก ๆ ก่อน หลัง บาง อย่าง ตาม ส่วน เพราะ ถ้า เห็น บอก คิด ว่า แค่ นี้ นั้น ไง หรอ เหรอ คับ จ้ะ คะ ฮะ ค่า เนอะ อ่ะ อะ".split())

def month(r):
    t = r["time"]
    if isinstance(t, str): return t[:7]
    return D.datetime.utcfromtimestamp(t).strftime("%Y-%m") if t else None

TRIE = dict_trie(set(thai_words()) | {k for ks in BRANDS.values() for k in ks} | {"ปตท.","แฟรนไชส์","ไตรมาส"})
rows = [json.loads(l) for l in open("data/posts.jsonl")]
tt = {r["topic_id"]: month(r) for r in rows if r["kind"] == "topic"}
data = []
for r in rows:
    m = month(r) or tt.get(r["topic_id"])
    if not m or m < "2025-11" or not r["text"]: continue
    low = r["text"].lower()
    brands = [b for b, ks in BRANDS.items() if any(k in low for k in ks)]
    toks = [w.strip().lower() for w in word_tokenize(r["text"], engine="newmm", custom_dict=TRIE, keep_whitespace=False)]
    ALLK = {k for ks in BRANDS.values() for k in ks} | {"cafe","caf","คาเฟ่อเมซอน","สตาร์บัคส์"}
    toks = [w for w in toks if w not in ALLK and len(w) > 1 and w not in STOP and not re.fullmatch(r"[\d\W_]+", w)]
    sent = sum(w in POS for w in toks) - sum(w in NEG for w in toks) - 2 * ("ไม่อร่อย" in low)
    data.append({"m": m, "brands": brands, "toks": set(toks), "s": (sent > 0) - (sent < 0), "kind": r["kind"], "tid": r["topic_id"]})
titles = {r["topic_id"]: r["text"] for r in rows if r["kind"] == "topic"}

months = sorted({d["m"] for d in data})
# brand mentions + sentiment by month
bm = {b: {m: [0, 0, 0] for m in months} for b in BRANDS}
for d in data:
    for b in d["brands"]: bm[b][d["m"]][d["s"] + 1] += 1
peak = {}
for b in BRANDS:
    c = collections.Counter((d["m"], d["tid"]) for d in data if b in d["brands"])
    if not c: continue
    bymonth = collections.Counter()
    for (m, t), n in c.items(): bymonth[m] += n
    pm = bymonth.most_common(1)[0][0]
    tid = max(((t, n) for (m, t), n in c.items() if m == pm), key=lambda x: x[1])[0]
    peak[b] = {"m": pm, "title": titles.get(tid, "")[:70], "tid": tid}
# overall volume
vol = collections.Counter((d["m"], d["kind"]) for d in data)

# co-occurrence: brands as nodes + top terms, per quarter-ish (2-month windows) and overall
def graph(sub, top=45, min_w=3):
    df = collections.Counter(t for d in sub for t in d["toks"])
    for d in sub:
        for b in d["brands"]: df["#" + b] += 1
    keep = {t for t, _ in df.most_common(top)} | {"#" + b for b in BRANDS if df["#" + b] >= 3}
    E = collections.Counter()
    for d in sub:
        nodes = sorted((d["toks"] | {"#" + b for b in d["brands"]}) & keep)
        for a, b in itertools.combinations(nodes, 2): E[(a, b)] += 1
    G = nx.Graph(); G.add_nodes_from(keep)
    for (a, b), w in E.items():
        if w >= min_w: G.add_edge(a, b, weight=w)
    G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
    comm = nx.community.louvain_communities(G, weight="weight", seed=1) if len(G) else []
    cid = {n: i for i, c in enumerate(comm) for n in c}
    btw = nx.betweenness_centrality(G, weight=None) if len(G) else {}
    return {"nodes": [{"id": n, "n": df[n], "c": cid.get(n, 0), "brand": n.startswith("#"), "btw": round(btw.get(n, 0), 3)} for n in G],
            "links": [{"source": a, "target": b, "w": d["weight"]} for a, b, d in G.edges(data=True)]}

periods = [("All", months)] + [(f"{months[i]} → {months[min(i+1, len(months)-1)]}", months[i:i+2]) for i in range(0, len(months), 2)]
graphs = {name: graph([d for d in data if d["m"] in ms], min_w=4 if name == "All" else 2) for name, ms in periods}

# brand-specific top associated terms (lift)
tot = collections.Counter(t for d in data for t in d["toks"]); N = len(data)
assoc = {}
for b in BRANDS:
    sub = [d for d in data if b in d["brands"]]
    if len(sub) < 15: continue
    c = collections.Counter(t for d in sub for t in d["toks"])
    assoc[b] = [(t, n, round(n / len(sub) / (tot[t] / N), 1)) for t, n in c.most_common(400) if n >= 5 and t not in sum(BRANDS.values(), [])]
    assoc[b] = sorted(assoc[b], key=lambda x: -x[2])[:15]

out = {"months": months, "volume": {k: [vol[(m, k)] for m in months] for k in ("topic", "comment")},
       "brands": {b: v for b, v in bm.items() if sum(sum(x) for x in v.values()) >= 10},
       "graphs": graphs, "assoc": assoc, "peak": peak, "n_rows": N, "n_threads": len(tt)}
json.dump(out, open("data/viz.json", "w"), ensure_ascii=False)
print(N, months)
for b, v in out["brands"].items(): print(b, [sum(v[m]) for m in months])
for b, a in assoc.items(): print(b, a[:10])
for k, g in graphs.items(): print(k, len(g["nodes"]), len(g["links"]))
