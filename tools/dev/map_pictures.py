r"""Map the picture numbers of the 1.23 manual (manual.md, from helpdeco of the 1.23 KAISER.HLP)
to the picture numbers of the 1.22a KAISER.HLP, by aligning both picture sequences in document
order with a text-similarity score.  Usage: map_pictures.py manual.md recs122.json map.json"""
import json
import re
import sys

md, recs_path, out = sys.argv[1:4]
recs = json.load(open(recs_path, encoding="utf-8"))
words = lambda t: {w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß]{4,}", t)}

# 1.22a: sequence of (pic, words of its record)
s1 = [(p, words(r["text"])) for r in recs for p in r["pics"]]

# 1.23: sequence of (pic, words right after it)
s2 = []
lines = open(md, encoding="utf-8").read().splitlines()
tag = re.compile(r"\{bm[clr] bm(\d+)\.\w+\}")
for n, ln in enumerate(lines):
    for m in tag.finditer(ln):
        after = tag.sub(" ", ln[m.end():] + " " + " ".join(lines[n + 1:n + 3]))
        ctx = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß]{4,}", after)][:5]
        s2.append((int(m.group(1)), [w.lower() for w in ctx]))


def sim(a, b):
    return sum(w in b for w in a) / len(a) if a else 0.0


# Needleman-Wunsch (maximize; gaps free)
A, B = len(s2), len(s1)
S = [[0.0] * (B + 1) for _ in range(A + 1)]
for i in range(1, A + 1):
    for j in range(1, B + 1):
        sc = sim(s2[i - 1][1], s1[j - 1][1])
        S[i][j] = max(S[i - 1][j], S[i][j - 1], S[i - 1][j - 1] + (sc if sc >= 0.4 else -1))
i, j, pairs = A, B, []
while i and j:
    sc = sim(s2[i - 1][1], s1[j - 1][1])
    if sc >= 0.4 and S[i][j] == S[i - 1][j - 1] + sc:
        pairs.append((s2[i - 1][0], s1[j - 1][0])); i -= 1; j -= 1
    elif S[i][j] == S[i - 1][j]:
        i -= 1
    else:
        j -= 1
votes = {}
for a, b in pairs:
    votes.setdefault(a, {}).setdefault(b, 0)
    votes[a][b] += 1
mapping = {f"bm{a}": f"bm{max(v, key=v.get)}" for a, v in sorted(votes.items())}
json.dump(mapping, open(out, "w"), indent=0)
missing = sorted({a for a, _ in s2} - {int(k[2:]) for k in mapping})
print(f"mapped {len(mapping)} of {len({a for a, _ in s2})}; unmapped 1.23 pictures: {missing}")
