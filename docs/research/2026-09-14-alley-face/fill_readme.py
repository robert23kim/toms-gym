"""Inject results/tables.md sections into README.md between <!-- TABLE:<name> --> markers. usage: fill_readme.py"""
import re
import af

tables = (af.RESULTS / "tables.md").read_text()
sections, cur = {}, None
for line in tables.splitlines():
    if line.startswith("## "):
        cur = line[3:].strip(); sections[cur] = []
    elif cur is not None:
        sections[cur].append(line)
MAP = {"e1": "E1 constellation", "timeline": "E1 visibility timeline", "e2": "E2 candidates", "e3": "E3 finding the face", "e4": "E4 aligning the face", "e5": "E5 persistence", "e6": "E6 heatmap model"}
readme = (af.HERE / "README.md").read_text()
for key, sec in MAP.items():
    body = "\n".join(l for l in sections.get(sec, []) if l.strip()).strip()
    pat = re.compile(rf"(<!-- TABLE:{key} -->)(.*?)(<!-- /TABLE:{key} -->)", re.S)
    if pat.search(readme):
        readme = pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", readme)
(af.HERE / "README.md").write_text(readme)
print("filled", [k for k in MAP if f"<!-- TABLE:{k} -->" in readme])
