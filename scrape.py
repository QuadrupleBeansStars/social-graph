"""Scrape Pantip coffee-chain tags: latest topics per tag + their comments -> data/posts.jsonl"""
import json, re, time, html, pathlib, requests

TAGS = ["คาเฟ่ (Cafe)", "เครื่องดื่ม", "ธุรกิจแฟรนไชน์", "ชา (Tea)", "เครื่องชงกาแฟ", "Starbucks", "คาเฟ่อเมซอน", "Cafe Amazon", "อินทนิล", "Black Canyon", "All Cafe",
        "ทรูคอฟฟี่", "ดอยช้าง", "Pacamara", "กาแฟพันธุ์ไทย", "Tim Hortons", "Arabitia", "% Arabica",
        "ร้านกาแฟ", "กาแฟ", "คาเฟ่", "Luckin Coffee", "Kudsan", "D'Ark", "Bluekoff"]
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (research script)"
OUT = pathlib.Path("data"); OUT.mkdir(exist_ok=True)
clean = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()

def tag_topics(tag):
    h = S.get(f"https://pantip.com/tag/{requests.utils.quote(tag)}", timeout=30).text
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if not m: return []
    t = json.loads(m.group(1))["props"]["initialProps"]["pageProps"].get("topics") or {}
    return t.get("data") or []

def comments(tid):
    r = S.get("https://pantip.com/forum/topic/render_comments", params={"tid": tid, "param": "", "type": 3},
              headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"https://pantip.com/topic/{tid}"}, timeout=30)
    out = []
    for c in json.loads(r.content.decode("utf-8-sig")).get("comments", []) or []:
        out.append(c)
        out += c.get("replies", []) or []
    return out

topics = {}
for tag in TAGS:
    ts = tag_topics(tag); print(tag, len(ts), flush=True)
    for t in ts:
        topics.setdefault(t["topic_id"], {**t, "tags_src": []})["tags_src"].append(tag)
    time.sleep(1)

with open(OUT / "posts.jsonl", "w") as f:
    for i, (tid, t) in enumerate(topics.items()):
        f.write(json.dumps({"kind": "topic", "topic_id": tid, "time": t["created_time"], "text": t["title"],
                            "user": (t.get("author") or {}).get("id"), "views": t.get("views_count"),
                            "tags": [x.get("name") for x in t.get("tags", []) if isinstance(x, dict)] or t["tags_src"],
                            "tags_src": t["tags_src"]}, ensure_ascii=False) + "\n")
        if t.get("comments_count"):
            try:
                for c in comments(tid):
                    f.write(json.dumps({"kind": "comment", "topic_id": tid, "time": int(c.get("created_time") or 0),
                                        "text": clean(c.get("message")), "user": (c.get("user") or {}).get("mid"),
                                        "emo": c.get("emo_score")}, ensure_ascii=False) + "\n")
            except Exception as e: print("err", tid, e)
            time.sleep(0.7)
        if i % 25 == 0: print(i, "/", len(topics), flush=True)
print("done", len(topics))
