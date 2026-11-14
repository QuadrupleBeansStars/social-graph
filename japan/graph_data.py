"""Pantip Japan threads -> data/graph.json : two-tier place co-mention graph (cities + landmarks).

Unit of analysis = thread (topic + all comments). Edges = places mentioned in the same thread.
Per node: thread count, season split, top distinctive terms (TF-IDF), top threads, neighbours.
"""
import json, re, math, random, collections, itertools, datetime as D, warnings, pathlib
warnings.filterwarnings("ignore")
import networkx as nx
try:
    from pythainlp.tokenize import word_tokenize
    from pythainlp.corpus import thai_stopwords, thai_words
    from pythainlp.util import dict_trie
    HAVE_TH = True
except ImportError:          # no Thai tokenizer: fall back to curated Thai/English topic lexicon
    HAVE_TH = False
import gazetteer as G

OFF = {"การ์ตูนญี่ปุ่น", "Disneyland"}          # off-topic tags (cartoons, overseas Disney); food / Thais-in-Japan kept
START, END = "2025-01", "2026-11"
OVERSAMPLED = {"2026-10", "2026-11"}   # main tag only reaches ~3 weeks back -> downsample to typical monthly density
CAP, SEED = 25, 7
MIN_NODE, MIN_EDGE = 5, 3     # min threads per node / per edge to be drawn

TH_M = {"ม.ค": 1, "มกรา": 1, "ก.พ": 2, "กุมภา": 2, "มี.ค": 3, "มีนา": 3, "เม.ย": 4, "เมษา": 4, "พ.ค": 5, "พฤษภา": 5,
        "มิ.ย": 6, "มิถุนา": 6, "ก.ค": 7, "กรกฎา": 7, "ส.ค": 8, "สิงหา": 8, "ก.ย": 9, "กันยา": 9, "ต.ค": 10, "ตุลา": 10,
        "พ.ย": 11, "พฤศจิกา": 11, "ธ.ค": 12, "ธันวา": 12}
EN_M = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
MRE = re.compile(r"(" + "|".join(sorted(map(re.escape, TH_M), key=len, reverse=True)) + r"|\b(?:" + "|".join(EN_M) + r")[a-z]*\b)", re.I)
SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer"}
season = lambda mo: SEASONS.get(mo, "Autumn")

def trip_month(text):
    m = MRE.search(text)
    if not m: return None
    k = m.group(1).lower()
    return next((v for kk, v in TH_M.items() if k.startswith(kk.lower())), None) or EN_M.get(k[:3])

ALIASES = {a for _, als in G.CITIES.values() for a in als} | {a for _, _, als in G.LANDMARKS.values() for a in als}
LEXICON = {  # curated Thai/English topic words used when pythainlp is unavailable
    "ราคา": "price", "แพง": "price", "ถูก": "price", "บัตร": "tickets", "ตั๋ว": "tickets", "จอง": "booking", "klook": "booking",
    "รถไฟ": "train", "ชินคันเซ็น": "train", "jr": "train", "pass": "pass", "รถเมล์": "bus", "บัส": "bus", "แท็กซี่": "taxi", "taxi": "taxi",
    "เช่ารถ": "rent a car", "ขับรถ": "rent a car", "สนามบิน": "airport", "โรงแรม": "hotel", "ที่พัก": "hotel", "hotel": "hotel",
    "อาหาร": "food", "ร้านอาหาร": "food", "ราเมน": "ramen", "ราเมง": "ramen", "ซูชิ": "sushi", "ปู": "crab", "วากิว": "wagyu", "ขนม": "sweets",
    "ช้อป": "shopping", "shopping": "shopping", "donki": "shopping", "ดองกี้": "shopping", "ซื้อของ": "shopping", "ภาษี": "tax refund", "tax": "tax refund",
    "หิมะ": "snow", "สกี": "ski", "ski": "ski", "snow": "snow", "ซากุระ": "sakura", "sakura": "sakura", "ใบไม้": "autumn leaves", "momiji": "autumn leaves",
    "ออนเซ็น": "onsen", "onsen": "onsen", "คนเยอะ": "crowded", "แน่น": "crowded", "คิว": "queue", "รอ": "queue", "หนาว": "cold", "ร้อน": "hot", "ฝน": "rain",
    "เด็ก": "kids", "ครอบครัว": "family", "เดินทางคนเดียว": "solo", "คนเดียว": "solo", "ฮันนีมูน": "honeymoon", "ผู้สูงอายุ": "seniors",
    "แผน": "itinerary", "แพลน": "itinerary", "itinerary": "itinerary", "วีซ่า": "visa", "visa": "visa", "ตม": "immigration", "สวย": "scenic", "วิว": "view",
    "ถ่ายรูป": "photos", "รีวิว": "review", "งบ": "budget", "เยน": "yen", "wifi": "wifi", "sim": "sim/wifi", "esim": "sim/wifi", "ซิม": "sim/wifi",
}
if HAVE_TH:
    TRIE = dict_trie(set(thai_words()) | {a for a in ALIASES if not a.isascii()})
    STOP0 = set(thai_stopwords())
else:
    STOP0 = set()
STOP = STOP0 | set("""ครับ ค่ะ คะ นะ จ้า ค่า เลย ก็ ที่ แต่ คือ มี ไป มา ได้ ให้ จะ ไม่ เป็น ว่า กับ แล้ว ของ และ ใน คน อัน ตัว เอง กัน ยัง ตอน เคย อยู่ ทำ แบบ ขอ ถาม ดู รู้ อะไร เท่า ไหร่ จริง นะคะ ขอบคุณ ผม เรา คุณ ครับผม ด้วย มาก ก่อน หลัง บาง อย่าง ตาม ส่วน เพราะ ถ้า เห็น บอก คิด แค่ นี้ นั้น ไง หรอ เหรอ คับ จ้ะ ฮะ เนอะ อ่ะ อะ ญี่ปุ่น japan เที่ยว วัน ไหม มั้ย ดี ช่วง ลอง เดือน ปี ครั้ง เดินทาง ที่นี่ ตรงนี้ คนไทย ประเทศ ประเทศไทย ค่ะ ไป-กลับ แล้วก็ ครับผม เค้า ไหน นึง นิด หน่อย เยอะ อีก แถว ใช่ ได้ครับ ได้ค่ะ จาก ถึง""".split())

def tokens(text):
    if not HAVE_TH:
        low = text.lower()
        return sorted({v for k, v in LEXICON.items() if k in low})
    out = []
    for w in word_tokenize(text, engine="newmm", custom_dict=TRIE, keep_whitespace=False):
        w = w.strip().lower()
        if len(w) < 2 or w in STOP or w in ALIASES or re.fullmatch(r"[\d\W_]+", w): continue
        out.append(w)
    return out

def month_of(t):
    if isinstance(t, str): return t[:7]
    return D.datetime.utcfromtimestamp(t).strftime("%Y-%m") if t else None

def build():
    rows = [json.loads(l) for l in open("data/posts.jsonl")]
    threads = collections.defaultdict(list)
    for r in rows: threads[r["topic_id"]].append(r)
    T = {}
    for tid, v in threads.items():
        top = next((r for r in v if r["kind"] == "topic"), None)
        if not top or OFF & set(top.get("tags") or []): continue
        m = month_of(top["time"])
        if not (START <= m <= END): continue
        text = " ".join(r["text"] for r in v)
        lms = set().union(*(G.find_landmarks(r["text"]) for r in v))
        cts = set().union(*(G.find_cities(r["text"]) for r in v)) | {G.LANDMARKS[l][0] for l in lms}
        tm = trip_month(top["text"]) or trip_month(text) or int(m[5:])
        T[tid] = dict(title=top["text"], views=top.get("views") or 0, n=len(v) - 1, month=m, season=season(tm),
                      cities=cts, lms=lms, toks=tokens(text) if (cts or lms) else [])
    # fair season comparison: cap over-sampled months at the typical monthly density (seeded random)
    rng = random.Random(SEED)
    by_m = collections.defaultdict(list)
    for tid, t in T.items(): by_m[t["month"]].append(tid)
    drop = set()
    for m in OVERSAMPLED:
        ids = sorted(by_m.get(m, []))
        if len(ids) > CAP: drop |= set(ids) - set(rng.sample(ids, CAP))
    return {tid: t for tid, t in T.items() if tid not in drop}

def top_terms(T, key, name, k=12):
    """TF-IDF over thread docs: terms distinctive to threads mentioning `name`."""
    docs = [t for t in T.values() if name in t[key] and t["toks"]]
    df_all = collections.Counter(w for t in T.values() for w in set(t["toks"]))
    N = len(T)
    tf = collections.Counter(w for t in docs for w in set(t["toks"]))
    sc = {w: c * math.log(N / (1 + df_all[w])) for w, c in tf.items() if c >= 3}
    return [w for w, _ in sorted(sc.items(), key=lambda x: -x[1])[:k]]

def graph(T, key, nodes):
    cnt = collections.Counter(n for t in T.values() for n in t[key])
    keep = {n for n in nodes if cnt[n] >= MIN_NODE}
    E = collections.Counter()
    for t in T.values():
        for a, b in itertools.combinations(sorted(t[key] & keep), 2): E[(a, b)] += 1
    E = {e: w for e, w in E.items() if w >= MIN_EDGE}
    return cnt, keep, E

if __name__ == "__main__":
    T = build()
    print("threads kept:", len(T))
    cnt, keep, E = graph(T, "cities", G.CITIES)
    g = nx.Graph(); g.add_nodes_from(keep)
    for (a, b), w in E.items():
        # Jaccard-ish normalisation so Tokyo/Osaka hubs do not dominate everything
        g.add_edge(a, b, weight=w, lift=w / math.sqrt(cnt[a] * cnt[b]))
    comms = nx.community.louvain_communities(g, weight="lift", seed=7)
    print(f"city graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges, {len(comms)} communities")
    for c in sorted(comms, key=len, reverse=True): print("  community:", sorted(c, key=lambda n: -cnt[n]))
    print("top edges by thread count:", sorted(E.items(), key=lambda x: -x[1])[:12])
    print("top edges by lift (min 4 threads):", sorted(((e, round(g.edges[e]["lift"], 2), w) for e, w in E.items() if w >= 4), key=lambda x: -x[1])[:12])
    pr = nx.pagerank(g, weight="weight"); print("pagerank:", [(n, round(s, 3)) for n, s in sorted(pr.items(), key=lambda x: -x[1])[:8]])
    bc = nx.betweenness_centrality(g, weight=None); print("betweenness:", [(n, round(s, 3)) for n, s in sorted(bc.items(), key=lambda x: -x[1])[:6]])
    for name in ["Osaka", "Hokkaido", "Fukuoka"]:
        nb = sorted(((b if a == name else a, w) for (a, b), w in E.items() if name in (a, b)), key=lambda x: -x[1])[:6]
        ssn = collections.Counter(t["season"] for t in T.values() if name in t["cities"])
        print(f"\n[{name}] threads={cnt[name]} seasons={dict(ssn)}\n  neighbours={nb}\n  terms={top_terms(T, 'cities', name)}")
    lc, lkeep, LE = graph(T, "lms", G.LANDMARKS)
    print(f"\nlandmark graph: {len(lkeep)} nodes, {len(LE)} edges (min node {MIN_NODE}, min edge {MIN_EDGE})")
    print("top landmark edges:", sorted(LE.items(), key=lambda x: -x[1])[:10])
    print("Osaka landmarks:", [(l, lc[l]) for l in sorted(lkeep, key=lambda x: -lc[x]) if G.LANDMARKS[l][0] == "Osaka"])
    print("Dotonbori terms:", top_terms(T, "lms", "Dotonbori"))
    print("season totals:", collections.Counter(t["season"] for t in T.values()))


# ---------------------------------------------------------------- export for the web page
def communities(T, key, nodes, ids=None):
    sub = {t: v for t, v in T.items() if ids is None or t in ids}
    cnt, keep, E = graph(sub, key, nodes)
    g = nx.Graph(); g.add_nodes_from(keep)
    for (a, b), w in E.items(): g.add_edge(a, b, lift=w / math.sqrt(cnt[a] * cnt[b]))
    return [sorted(c) for c in nx.community.louvain_communities(g, weight="lift", seed=7)], g


def export(T, out="data/graph.json"):
    import math as _m
    N = len(T)
    df = collections.Counter(w for t in T.values() for w in set(t["toks"]))
    comms, g = communities(T, "cities", G.CITIES)
    comm_of = {n: i for i, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}
    months = sorted({t["month"] for t in T.values()})
    seas_months = collections.defaultdict(set)
    for m in months: seas_months[season(int(m[5:]))].add(m)
    tids = sorted(T, key=lambda x: -T[x]["n"])
    idx = {tid: i for i, tid in enumerate(tids)}
    cities = [dict(id=k, region=v[0], comm=comm_of.get(k, -1)) for k, v in G.CITIES.items()]
    lms = [dict(id=k, parent=v[0], type=v[1]) for k, v in G.LANDMARKS.items()]
    threads = []
    for tid in tids:
        t = T[tid]
        keep_terms = sorted(set(t["toks"]), key=lambda w: df[w])[:25]    # rarest-first cap per thread
        threads.append(dict(id=tid, title=t["title"][:110], month=t["month"], season=t["season"], views=t["views"], n=t["n"],
                            cities=sorted(t["cities"]), lms=sorted(t["lms"]), terms=keep_terms))
    out_d = dict(
        meta=dict(threads=N, months=months, season_months={k: len(v) for k, v in seas_months.items()},
                  window=[months[0], months[-1]], cap=dict(months=sorted(OVERSAMPLED), per_month=CAP),
                  min_node=MIN_NODE, min_edge=MIN_EDGE, tokenizer="pythainlp" if HAVE_TH else "lexicon"),
        cities=cities, landmarks=lms, threads=threads,
        idf={w: round(_m.log(N / (1 + c)), 3) for w, c in df.items()})
    pathlib.Path(out).write_text(json.dumps(out_d, ensure_ascii=False, separators=(",", ":")))
    return out_d


if __name__ == "__main__":
    d = export(T)
    print("\nEXPORT: data/graph.json", round(pathlib.Path("data/graph.json").stat().st_size / 1024), "KB;",
          "threads", d["meta"]["threads"], "| months per season", d["meta"]["season_months"], "| tokenizer", d["meta"]["tokenizer"])
    # robustness: do the communities survive a strict 12-month window (Oct25-Sep26) and each season alone?
    full, _ = communities(T, "cities", G.CITIES)
    win = {t for t, v in T.items() if "2025-10" <= v["month"] <= "2026-09"}
    c12, _ = communities(T, "cities", G.CITIES, win)
    def same(a, b):
        A = {frozenset(c) for c in a}; B = {frozenset(c) for c in b}
        return len(A & B), len(A), len(B)
    print("robustness 12-month window: threads", len(win), "communities", [len(c) for c in c12], "| identical to full:", same(full, c12))
    from sklearn.metrics import adjusted_rand_score as ari
    nodes = sorted({n for c in full for n in c} & {n for c in c12 for n in c})
    lab = lambda cs: [next(i for i, c in enumerate(cs) if n in c) for n in nodes]
    print("  adjusted Rand vs full (1.0 = same partition):", round(ari(lab(full), lab(c12)), 2))
    for s in ["Spring", "Summer", "Autumn", "Winter"]:
        ids = {t for t, v in T.items() if v["season"] == s}
        cs, gg = communities(T, "cities", G.CITIES, ids)
        nodes2 = sorted({n for c in full for n in c} & {n for c in cs for n in c})
        l2 = lambda c_: [next(i for i, c in enumerate(c_) if n in c) for n in nodes2]
        print(f"  {s}: threads={len(ids)} nodes={gg.number_of_nodes()} edges={gg.number_of_edges()} ARI vs full={round(ari(l2(full), l2(cs)), 2)}")
    # per-season rate fairness
    sm = d["meta"]["season_months"]; cs_ = collections.Counter(t["season"] for t in T.values())
    print("threads per month by season:", {s: round(cs_[s] / sm[s], 1) for s in sm})
