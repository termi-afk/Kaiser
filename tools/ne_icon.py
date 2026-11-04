r"""Extract the first icon group of a Win16 (NE) or Win32/64 (PE) executable as a .ico file.
Usage: ne_icon.py program.exe out.ico"""
import struct
import sys


def ne_resources(d):
    ne = struct.unpack_from("<I", d, 0x3C)[0]
    rt = ne + struct.unpack_from("<H", d, ne + 0x24)[0]
    shift = struct.unpack_from("<H", d, rt)[0]
    p, res = rt + 2, {}
    while True:
        tid = struct.unpack_from("<H", d, p)[0]
        if tid == 0:
            break
        cnt = struct.unpack_from("<H", d, p + 2)[0]
        p += 8
        for _ in range(cnt):
            off, ln, _fl, rid = struct.unpack_from("<HHHH", d, p)
            p += 12
            res.setdefault(tid & 0x7FFF, []).append((rid & 0x7FFF, d[off << shift:(off << shift) + (ln << shift)]))
    return res


def pe_resources(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec, = struct.unpack_from("<H", d, pe + 6)
    optsize, = struct.unpack_from("<H", d, pe + 20)
    opt = pe + 24
    magic, = struct.unpack_from("<H", d, opt)
    ddir = opt + (96 if magic == 0x10B else 112)
    rva, _size = struct.unpack_from("<II", d, ddir + 2 * 8)
    secs = []
    for k in range(nsec):
        s = opt + optsize + 40 * k
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", d, s + 8)
        secs.append((vaddr, max(vsize, rawsize), rawptr))

    def off(r):
        for va, sz, raw in secs:
            if va <= r < va + sz:
                return raw + r - va
        raise ValueError(r)

    base = off(rva)

    def entries(o):
        nn, ni = struct.unpack_from("<HH", d, o + 12)
        for k in range(nn + ni):
            name, ptr = struct.unpack_from("<II", d, o + 16 + 8 * k)
            yield name, ptr

    res = {}
    for tid, p1 in entries(base):
        if not p1 & 0x80000000 or tid & 0x80000000:
            continue
        for rid, p2 in entries(base + (p1 & 0x7FFFFFFF)):
            if not p2 & 0x80000000:
                continue
            for _lang, p3 in entries(base + (p2 & 0x7FFFFFFF)):
                drva, dsize = struct.unpack_from("<II", d, base + p3)
                res.setdefault(tid, []).append((rid & 0x7FFFFFFF, d[off(drva):off(drva) + dsize]))
                break
    return res


def main(exe, out):
    d = open(exe, "rb").read()
    hdr = d[struct.unpack_from("<I", d, 0x3C)[0]:][:2]
    res = ne_resources(d) if hdr == b"NE" else pe_resources(d)
    icons = dict(res.get(3, []))
    group = res[14][0][1]
    n = struct.unpack_from("<H", group, 4)[0]
    ents = []
    for i in range(n):
        w, h, cc, _r, planes, bpp, size, nid = struct.unpack_from("<BBBBHHIH", group, 6 + i * 14)
        data = icons[nid]
        if not bpp and data[:4] == b"\x28\0\0\0":
            bpp = struct.unpack_from("<H", data, 14)[0]
        ents.append((w, h, cc, planes or 1, bpp, data))
    blob = struct.pack("<HHH", 0, 1, len(ents))
    pos, body = 6 + 16 * len(ents), b""
    for w, h, cc, pl, bpp, data in ents:
        blob += struct.pack("<BBBBHHII", w, h, cc, 0, pl, bpp, len(data), pos + len(body))
        body += data
    open(out, "wb").write(blob + body)
    print(f"{exe} -> {out}: {len(ents)} image(s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
