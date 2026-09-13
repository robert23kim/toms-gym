"""Paste results/summary.md between the <!-- TABLE --> markers of README.md."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
readme = HERE / "README.md"
table = (HERE / "results" / "summary.md").read_text().strip()
txt = readme.read_text()
a, b = txt.index("<!-- TABLE -->"), txt.index("<!-- /TABLE -->")
readme.write_text(txt[:a] + "<!-- TABLE -->\n" + table + "\n" + txt[b:])
print("filled", readme)
