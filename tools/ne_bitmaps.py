r"""Extract RT_BITMAP resources from a Win16 NE executable as PNG.  Usage: ne_bitmaps.py EXE outdir"""
import io, os, struct, sys
from PIL import Image


def resources(d):
    ne = struct.unpack_from('<I', d, 0x3c)[0]
    rt = ne + struct.unpack_from('<H', d, ne + 0x24)[0]
    shift = struct.unpack_from('<H', d, rt)[0]; p = rt + 2
    res = {}
    while True:
        tid = struct.unpack_from('<H', d, p)[0]
        if tid == 0:
            break
        cnt = struct.unpack_from('<H', d, p + 2)[0]; p += 8
        for _ in range(cnt):
            off, ln, _fl, rid = struct.unpack_from('<HHHH', d, p); p += 12
            res.setdefault(tid, []).append((rid, d[off << shift:(off << shift) + (ln << shift)]))
    return res, rt


def name_of(d, rt, rid):
    if rid & 0x8000:
        return str(rid & 0x7fff)
    n = d[rt + rid]
    return d[rt + rid + 1: rt + rid + 1 + n].decode('latin1')


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    os.makedirs(sys.argv[2], exist_ok=True)
    res, rt = resources(d)
    for rid, b in res.get(0x8002, []):
        hdr = struct.unpack_from('<I', b, 0)[0]
        bpp = struct.unpack_from('<H', b, 14)[0]
        ncol = struct.unpack_from('<I', b, 32)[0] or (1 << bpp if bpp <= 8 else 0)
        off = 14 + hdr + 4 * ncol
        bmp = b'BM' + struct.pack('<IHHI', 14 + len(b), 0, 0, off) + b
        im = Image.open(io.BytesIO(bmp)); im.load()
        nm = name_of(d, rt, rid)
        im.convert('RGB').save(os.path.join(sys.argv[2], f'{nm}.png'))
        print(nm, im.size, end='; ')
