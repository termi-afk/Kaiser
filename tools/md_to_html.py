r"""Convert the Kaiser 1.23 manual (docs/manual.md of LarsGehrmann/Kaiser-decompile, generated
from the 1.23 KAISER.HLP) into one standalone HTML page with its pictures.

Usage: md_to_html.py manual.md out.html [image_subdir]
{bmc bmN.bmp} / {bml ...} / {bmr ...} become <img src="image_subdir/bmN.png"> when that file
exists next to out.html, otherwise they are dropped."""
import html
import os
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
imgdir = sys.argv[3] if len(sys.argv) > 3 else "bilder"
base = os.path.dirname(os.path.abspath(dst))
lines = open(src, encoding="utf-8").read().splitlines()
PIC = re.compile(r"\{bm([clr]) (bm\d+)\.\w+\}")


def pic(m):
    rel = f"{imgdir}/{m.group(2)}.png"
    if not os.path.exists(os.path.join(base, rel)):
        return ""
    cls = {"c": "pc", "l": "pl", "r": "pr"}[m.group(1)]
    return f'<img class="{cls}" src="{rel}" alt="">'


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((#[^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<i>\1</i>", t)
    return PIC.sub(pic, t)


def is_row(ln):
    return ln.rstrip().endswith("|")


def cells(ln):
    return [c.strip() for c in ln.rstrip()[:-1].split("|")]


out, toc, i = [], [], 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("<a id="):
        out.append(ln)
    elif m := re.match(r"^(#{1,4}) (.*)", ln):
        lvl, text = len(m.group(1)), m.group(2)
        hid = f"h{len(toc)}"
        if lvl == 2:
            toc.append((hid, text))
        out.append(f'<h{lvl} id="{hid}">{inline(text)}</h{lvl}>')
    elif is_row(ln):
        rows = []
        while i < len(lines) and is_row(lines[i]):
            c = cells(lines[i])
            # helpdeco split some rows in two lines: "{bmc bm9.bmp} |" + "Demographische Daten |"
            if len(c) == 1 and i + 1 < len(lines) and is_row(lines[i + 1]) and len(cells(lines[i + 1])) == 1:
                c = c + cells(lines[i + 1]); i += 1
            if not re.fullmatch(r"[-: ]*", "".join(c)):
                rows.append(c)
            i += 1
        out.append("<table>" + "".join(
            "<tr>" + "".join(f"<td>{inline(x)}</td>" for x in r) + "</tr>" for r in rows) + "</table>")
        continue
    elif ln.startswith("- "):
        items = []
        while i < len(lines) and lines[i].startswith("- "):
            items.append(f"<li>{inline(lines[i][2:])}</li>")
            i += 1
        out.append("<ul>" + "".join(items) + "</ul>")
        continue
    elif ln.strip() == "---":
        out.append("<hr>")
    elif ln.startswith("Automatisch erzeugt von"):
        pass
    elif ln.strip():
        out.append(f"<p>{inline(ln)}</p>")
    i += 1

nav = "".join(f'<li><a href="#{h}">{inline(t)}</a></li>' for h, t in toc)
page = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kaiser 1.23 Hilfe</title>
<style>
:root {{ --bg:#fffbea; --fg:#2b2416; --muted:#6b5d3f; --accent:#7a1f12; --line:#e3d7a8; --panel:#fff4c4; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1d1a12; --fg:#efe6cc; --muted:#b5a882; --accent:#f0a070; --line:#3d3524; --panel:#2a2518; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 Georgia, "Times New Roman", serif; }}
.wrap {{ display:grid; grid-template-columns: 260px 1fr; max-width:1200px; margin:0 auto; }}
nav {{ position:sticky; top:0; height:100vh; overflow:auto; padding:20px 16px; border-right:1px solid var(--line); background:var(--panel); font:14px/1.4 system-ui, sans-serif; }}
nav h2 {{ font-size:15px; margin:0 0 10px; color:var(--accent); }}
nav ul {{ list-style:none; margin:0; padding:0; }} nav li {{ margin:3px 0; }}
main {{ padding:24px 32px 80px; min-width:0; }}
h1 {{ color:var(--accent); font-size:28px; }} h2 {{ color:var(--accent); border-bottom:1px solid var(--line); padding-bottom:4px; margin-top:40px; clear:both; }}
a {{ color:var(--accent); }} p {{ margin:6px 0; }}
p > i:only-child {{ color:var(--muted); font-size:13px; }}
img {{ image-rendering:pixelated; vertical-align:middle; }}
img.pl {{ float:left; margin:2px 12px 6px 0; }} img.pr {{ float:right; margin:2px 0 6px 12px; }}
hr {{ clear:both; border:0; border-top:1px solid var(--line); }}
table {{ border-collapse:collapse; margin:10px 0; display:block; overflow-x:auto; clear:both; }}
td {{ border:1px solid var(--line); padding:3px 10px; vertical-align:middle; }}
@media (max-width: 760px) {{ .wrap {{ display:block; }} nav {{ position:static; height:auto; border-right:0; border-bottom:1px solid var(--line); }} main {{ padding:16px; }} }}
</style></head><body><div class="wrap">
<nav><h2>Inhalt</h2><ul>{nav}</ul></nav>
<main>{''.join(out)}
<hr><p><small>Kaiser 1.23 &copy; Stefan Maday. Text aus KAISER.HLP 1.23 (umgewandelt von
<a href="https://github.com/LarsGehrmann/Kaiser-decompile">Kaiser-decompile</a>), Bilder aus KAISER.HLP 1.22a
und KAISER.EXE 1.23.</small></p>
</main></div></body></html>"""
open(dst, "w", encoding="utf-8").write(page)
print("wrote", dst, len(page))
