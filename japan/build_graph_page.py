"""japan/data/graph.json + japan/graph.template.html -> docs/index.html (GitHub Pages, one self-contained file)."""
import json, pathlib

here = pathlib.Path(__file__).parent
data = json.loads((here / "data" / "graph.json").read_text())
tpl = (here / "graph.template.html").read_text()
assert "/*__DATA__*/null" in tpl
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")   # keep </script> safe
out = here.parent / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(tpl.replace("/*__DATA__*/null", payload))
print("wrote", out, round(out.stat().st_size / 1024), "KB")
