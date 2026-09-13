"""Inject the generated tables (results/tables.md sections) into README.md between
<!-- TABLE:<name> --> ... <!-- /TABLE:<name> --> markers. usage: fill_readme.py"""
import re
import common as C

tables = (C.RESULTS / "tables.md").read_text()
sections = {}
cur = None
for line in tables.splitlines():
    if line.startswith("## "):
        cur = line[3:].strip(); sections[cur] = []
    elif cur is not None:
        sections[cur].append(line)
MAP = {"e1": "E1 truth", "baselines": "Baselines re-scored", "e2": "E2 detectors", "e3_loop3": "E3 fits: loop3", "e3_loop3_plus": "E3 fits: loop3_plus",
       "e3_loop3_1024": "E3 fits: loop3_1024", "e3_seg2_1024": "E3 fits: seg2_1024", "e3_sam_even3_k": "E3 fits: sam_even3_k", "e3_sam_zoom_lo_k": "E3 fits: sam_zoom_lo_k", "e4": "E4 camera"}
readme = (C.HERE / "README.md").read_text()
for key, sec in MAP.items():
    body = "\n".join(l for l in sections.get(sec, []) if l.strip()).strip()
    pat = re.compile(rf"(<!-- TABLE:{key} -->)(.*?)(<!-- /TABLE:{key} -->)", re.S)
    if pat.search(readme):
        readme = pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", readme)
(C.HERE / "README.md").write_text(readme)
print("filled", [k for k in MAP if f"<!-- TABLE:{k} -->" in readme])
