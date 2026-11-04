r"""Extract the embedded bitmaps (|bm0, |bm1, ...) from a WinHelp 3.1 .HLP file as PNG.
Usage: hlp_bitmaps.py KAISER.HLP outdir        (format notes: helpdeco's helpfile.txt)"""
import os
import struct
import sys

from PIL import Image


def read_dir(d):
    magic, dirstart = struct.unpack_from("<II", d, 0)
    assert magic == 0x00035F3F, hex(magic)
    bt = dirstart + 9  # skip FILEHEADER
    (bmagic, flags, pagesize) = struct.unpack_from("<HHH", d, bt)
    assert bmagic == 0x293B
    root, _neg1, total, nlevels = struct.unpack_from("<hhhh", d, bt + 26)
    pages = bt + 38
    page = root
    for _ in range(nlevels - 1):  # descend leftmost
        page = struct.unpack_from("<h", d, pages + page * pagesize + 4)[0]
    files = {}
    while page != -1:
        p = pages + page * pagesize
        _unused, n, _prev, nxt = struct.unpack_from("<HHhh", d, p)
        q = p + 8
        for _ in range(n):
            e = d.index(b"\0", q)
            name = d[q:e].decode("latin1")
            files[name] = struct.unpack_from("<I", d, e + 1)[0]
            q = e + 5
        page = nxt
    return files


def internal(d, off):
    _reserved, used, _fl = struct.unpack_from("<IIB", d, off)
    return d[off + 9: off + 9 + used]


class R:
    def __init__(self, b, p):
        self.b, self.p = b, p

    def byte(self):
        v = self.b[self.p]; self.p += 1; return v

    def cushort(self):
        if self.b[self.p] & 1:
            v = struct.unpack_from("<H", self.b, self.p)[0] >> 1; self.p += 2
        else:
            v = self.b[self.p] >> 1; self.p += 1
        return v

    def culong(self):
        if self.b[self.p] & 1:
            v = struct.unpack_from("<I", self.b, self.p)[0] >> 1; self.p += 4
        else:
            v = struct.unpack_from("<H", self.b, self.p)[0] >> 1; self.p += 2
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.p)[0]; self.p += 4; return v


def unrle(b):
    out, i = bytearray(), 0
    while i < len(b):
        n = b[i]; i += 1
        if n & 0x80:
            out += b[i:i + (n & 0x7F)]; i += n & 0x7F
        else:
            out += bytes([b[i]]) * n; i += 1
    return bytes(out)


def unlz77(b):
    out, i = bytearray(), 0
    while i < len(b):
        flags = b[i]; i += 1
        for bit in range(8):
            if i >= len(b):
                break
            if flags & (1 << bit):
                w = struct.unpack_from("<H", b, i)[0]; i += 2
                off, ln = (w & 0x0FFF) + 1, (w >> 12) + 3
                for _ in range(ln):
                    out.append(out[-off])
            else:
                out.append(b[i]); i += 1
    return bytes(out)


def picture(b, off):
    r = R(b, off)
    ptype, packing = r.byte(), r.byte()
    if ptype not in (5, 6):
        return None, f"type {ptype}"
    r.culong(); r.culong()  # dpi
    planes, bpp = r.cushort(), r.cushort()
    w, h = r.culong(), r.culong()
    used, _imp = r.culong(), r.culong()
    csize, _hs = r.culong(), r.culong()
    coff, _hoff = r.u32(), r.u32()
    pal = None
    if ptype == 6 and bpp <= 8:
        n = used or (1 << bpp)
        pal = [tuple(b[r.p + 4 * k: r.p + 4 * k + 3][::-1]) for k in range(n)]
    data = b[off + coff: off + coff + csize]
    if packing in (2, 3):
        data = unlz77(data)
    if packing in (1, 3):
        data = unrle(data)
    if ptype == 5:  # DDB: top-down rows padded to 16 bit, monochrome/planar unusual
        stride = ((w * bpp + 15) // 16) * 2
        rows = range(h)
        if bpp == 1:
            pal = [(0, 0, 0), (255, 255, 255)]
    else:
        stride = ((w * bpp + 31) // 32) * 4
        rows = range(h - 1, -1, -1)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y_out, y in enumerate(rows):
        row = data[y_out * stride:(y_out + 1) * stride]
        for x in range(w):
            if bpp == 24:
                bb, g, rr = row[3 * x:3 * x + 3]; px[x, y] = (rr, g, bb)
            else:
                bit = x * bpp
                v = (row[bit // 8] >> (8 - bpp - bit % 8)) & ((1 << bpp) - 1)
                px[x, y] = pal[v] if pal and v < len(pal) else (v, v, v)
    return img, f"{w}x{h}x{bpp} type{ptype} pack{packing}"


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    files = read_dir(d)
    for name, off in sorted(files.items()):
        if not name.startswith("|bm"):
            continue
        b = internal(d, off)
        magic, n = struct.unpack_from("<HH", b, 0)
        offs = struct.unpack_from(f"<{n}I", b, 4)
        img, info = picture(b, offs[0])
        print(name, hex(magic), n, info)
        if img:
            img.save(os.path.join(out, name[1:] + ".png"))


if __name__ == "__main__":
    main()
