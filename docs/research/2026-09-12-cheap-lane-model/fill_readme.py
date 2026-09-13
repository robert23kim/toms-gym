"""Insert results/summary.md's main table between <!-- TABLE --> markers in README.md
(idempotent: the block is replaced on every run)."""
import re
from pathlib import Path

readme = Path("README.md"); md = readme.read_text()
table = Path("results/summary.md").read_text().split("\n\\* SAM")[0].strip()
note = "\n\n\\* SAM per-frame means are over the throw frames each method scored: loop 1's video mode covers the whole throw including occluded frames; loop 2's gate + carry reports accepted frames only."
block = f"<!-- TABLE -->\n{table}{note}\n<!-- /TABLE -->"
if "<!-- /TABLE -->" in md:
    md = re.sub(r"<!-- TABLE -->.*?<!-- /TABLE -->", lambda m: block, md, flags=re.S)
else:
    md = md.replace("<!-- TABLE -->", block)
readme.write_text(md)
print("table rows:", table.count("\n") - 1)
