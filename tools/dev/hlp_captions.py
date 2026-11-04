r"""List the text records that contain pictures for a WinHelp 3.1 .HLP (|TOPIC + |Phrases).
Usage: hlp_captions.py KAISER.HLP > recs.json   (input for map_pictures.py)"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hlp_bitmaps import R, internal, read_dir, unlz77  # noqa: E402

d = open(sys.argv[1], "rb").read()
files = read_dir(d)
sysf = internal(d, files["|SYSTEM"])
_magic, minor, _major, _date, flags = struct.unpack_from("<HHHIH", sysf, 0)
compressed = minor > 16 and (flags & 0xC)
bsize = 2048 if flags & 8 else 4096

# phrases
ph = internal(d, files["|Phrases"])
n, _hundred = struct.unpack_from("<HH", ph, 0)
if minor > 16:
    dsize = struct.unpack_from("<I", ph, 4)[0]
    offs = struct.unpack_from(f"<{n + 1}H", ph, 8)
    blob = unlz77(ph[8 + 2 * (n + 1):])[:dsize]
    base = 2 * (n + 1)
else:
    offs = struct.unpack_from(f"<{n + 1}H", ph, 4)
    blob, base = ph[4 + 2 * (n + 1):], 2 * (n + 1)
phrases = [blob[offs[k] - base:offs[k + 1] - base] for k in range(n)]

# topic blocks into a linear buffer addressed by (block << 14) | offset
tp = internal(d, files["|TOPIC"])
buf = bytearray()
for k in range(0, len(tp), bsize):
    blk = tp[k:k + bsize]
    data = blk[:12] + (unlz77(blk[12:]) if compressed else blk[12:])
    buf += data[:0x4000].ljust(0x4000, b"\0")


def expand(text, size2):
    if size2 <= len(text):
        return text
    out, i = bytearray(), 0
    while i < len(text):
        c = text[i]
        if 0 < c < 0x10 and i + 1 < len(text):
            idx = 256 * (c - 1) + text[i + 1]
            out += phrases[idx >> 1]
            if idx & 1:
                out += b" "
            i += 2
        else:
            out.append(c); i += 1
    return bytes(out)


pos, result = 12, []
seen = set()
while pos not in seen and pos + 21 <= len(buf):
    seen.add(pos)
    bs, dl2, _prev, nxt, dl1 = struct.unpack_from("<IIiiI", buf, pos)
    rtype = buf[pos + 20]
    ld1 = bytes(buf[pos + 21:pos + dl1])
    ld2 = expand(bytes(buf[pos + dl1:pos + bs]), dl2)
    if rtype in (0x20, 0x23):
        text = ld2.decode("cp1252", "replace")
        text = re.sub(r"\s+", " ", text.replace("\0", " ")).strip()
        pics = []
        for m in re.finditer(rb"[\x86\x87\x88](?:\x03|\x22)", ld1):
            r = R(ld1, m.end())
            try:
                r.culong()
                if ld1[m.start() + 1] == 0x22:
                    r.cushort()
                emb, num = struct.unpack_from("<hh", ld1, r.p)
            except (IndexError, struct.error):
                continue
            if emb == 0 and 0 <= num < 400:
                pics.append(num)
        if pics:
            result.append({"pics": list(dict.fromkeys(pics)), "text": text})
    if nxt in (-1, 0) or nxt == pos:
        break
    pos = nxt
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=0))
