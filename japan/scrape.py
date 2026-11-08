"""Pantip Japan travel: latest 50 topics per tag (since 2025) + all comments -> data/posts.jsonl"""
import collections, json, re, time, html, requests, sys
TAGS = ["ประเทศญี่ปุ่น","โตเกียว","โอซาก้า","ฮอกไกโด","เกียวโต","ฟุกุโอกะ","โอกินาว่า",
 "Japan","Tokyo","Osaka","Hokkaido","Kyoto","Fukuoka","Nagoya","Sapporo","Okinawa","Hiroshima","Nara",
 "ซัปโปโร","นารา","ฮิโรชิม่า","คานาซาว่า","ชิราคาวาโกะ","คามาคุระ","นิกโก้","โยโกฮาม่า","ฮาโกเน่","ฟูจิ",
 "ออนเซ็น","ยูนิเวอร์แซล สตูดิโอ เจแปน","Universal Studios Japan","Tokyo Disneyland","สายการบิน","ตั๋วเครื่องบิน",
 "เที่ยวต่างประเทศ","Backpacker","บันทึกนักเดินทาง","วีซ่า","ร้านอาหารญี่ปุ่น","อาหารญี่ปุ่น","ช้อปปิ้ง","Blue Planet"]
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (research script)"
clean = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()
JP = re.compile(r"ญี่ปุ่น|japan|โตเกียว|tokyo|โอซาก้า|osaka|เกียวโต|kyoto|ฮอกไกโด|hokkaido|ซัปโปโร|ฟุกุโอกะ|โอกินาว่า|นาโกย่า|ฟูจิ|นารา|ฮิโรชิม่า|คานาซาว่า|ทาคายาม่า|ชิราคาวาโกะ|คามาคุระ|ฮาโกเน่|เยน|jr pass|ออนเซ็น|ซากุระ|usj|disney", re.I)
def tag_topics(tag):
    h = S.get(f"https://pantip.com/tag/{requests.utils.quote(tag)}", timeout=30).text
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    try: return (json.loads(m.group(1))["props"]["initialProps"]["pageProps"].get("topics") or {}).get("data") or []
    except Exception: return []
def comments(tid):
    r = S.get("https://pantip.com/forum/topic/render_comments", params={"tid": tid, "param": "", "type": 3},
              headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"https://pantip.com/topic/{tid}"}, timeout=30)
    out = []
    for c in json.loads(r.content.decode("utf-8-sig")).get("comments", []) or []:
        out.append(c); out += c.get("replies", []) or []
    return out
topics = {}
for tag in TAGS:
    ts = tag_topics(tag)
    generic = tag not in TAGS[:28]  # generic travel tags: keep only Japan-related titles
    keep = [t for t in ts if (t.get("created_time") or "") >= "2025-01-01" and (not generic or JP.search(t["title"]) or any(JP.search(x.get("name","")) for x in t.get("tags",[]) if isinstance(x,dict)))]
    print(f"{tag:28} got={len(ts):3} kept={len(keep):3} oldest={min((t.get('created_time','')[:10] for t in ts if t.get('created_time')), default='-')}", flush=True)
    for t in keep: topics.setdefault(t["topic_id"], {**t, "src": []})["src"].append(tag)
    time.sleep(1)
seen = set(TAGS); found = collections.Counter(x.get("name") for t in topics.values() for x in t.get("tags", []) if isinstance(x, dict))
extra = [n for n, c in found.most_common() if n and n not in seen and c >= 2 and JP.search(n)]
print("discovered:", extra, flush=True)
for tag in extra:
    ts = tag_topics(tag); keep = [t for t in ts if (t.get("created_time") or "") >= "2025-01-01"]
    print(f"{tag:28} got={len(ts):3} kept={len(keep):3}", flush=True)
    for t in keep: topics.setdefault(t["topic_id"], {**t, "src": []})["src"].append(tag)
    time.sleep(1)
print("unique topics", len(topics), flush=True)
with open("data/posts.jsonl", "w") as f:
    for i, (tid, t) in enumerate(topics.items()):
        f.write(json.dumps({"kind": "topic", "topic_id": tid, "time": t.get("created_time"), "text": t["title"], "type": t.get("topic_type"),
            "user": (t.get("author") or {}).get("id"), "views": t.get("views_count"), "n_comments": t.get("comments_count"),
            "tags": [x.get("name") for x in t.get("tags", []) if isinstance(x, dict)], "src": t["src"]}, ensure_ascii=False) + "\n")
        if t.get("comments_count"):
            try:
                for c in comments(tid):
                    f.write(json.dumps({"kind": "comment", "topic_id": tid, "time": int(c.get("created_time") or 0),
                        "text": clean(c.get("message")), "user": (c.get("user") or {}).get("mid")}, ensure_ascii=False) + "\n")
            except Exception as e: print("err", tid, e)
            time.sleep(0.6)
        if i % 50 == 0: print(i, "/", len(topics), flush=True)
print("done")
