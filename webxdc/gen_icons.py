#!/usr/bin/env python3
"""gen_icons.py — draw the `icon.png` of every app in this directory, from source.

Why a generator instead of three PNGs found or hand-drawn: the packages under
`webxdc/` shipped no icon at all, so messengers fell back to a generic default.
A bitmaps with no source cannot be reviewed, cannot be rebuilt, and silently
drift from whatever produced them — which is exactly why `with_bar()` was
deleted from `projects/presskit-reassembler/dist/gfx/gen_gfx.py` rather than
wired up (REVIEW.md PY-8). Here the image *is* the code: shapes on a coordinate
grid, no third-party asset, no binary blob to trust, and

    python3 gen_icons.py --check

proves the committed files still match what this script renders.

No dependencies: `math`, `struct`, `zlib` only, so it runs anywhere
`webxdc_tool.py` runs — unlike the presskit generator, which needs `pyfiglet`
and `Pillow`.

Size and format follow https://webxdc.org/docs/spec/format.html — "a square at
reasonable width/height, usually between 128 x 128 and 512 x 512 pixel", so
256x256 RGBA. Corners get a soft plate radius but no shaped cut-out: several
implementations mask icons themselves and double-masking looks wrong.

Every colour is lifted from the app's own stylesheet — check the hexes in
`<app>/index.html` before changing any, so an icon keeps matching its UI:

    cyberchef   #21252b bg, #abb2bf / #eee ink, #61afef blue, #98c379 green, #e5c07b yellow
    shamir      #0a0c10 bg, #5ce4a0 green, #232838 dim, #e0af68 gold
    radar-scope #001100 bg, #00ff41 / #00aa2a phosphor, #00ccff #ffaa00 #ff3344 contacts

Usage:
    python3 gen_icons.py             # write webxdc/<app>/icon.png for all three
    python3 gen_icons.py --check     # exit 1 if a committed icon is not reproducible
    python3 gen_icons.py --out DIR   # render elsewhere (preview without touching the tree)
"""
from __future__ import annotations

import argparse
import math
import os
import struct
import sys
import zlib

SIZE = 256   # icon edge, final pixels
SS = 3       # supersample factor: rasterise at SIZE*SS, box-filter down to SIZE
HERE = os.path.dirname(os.path.abspath(__file__))


def rgb(hexstr: str):
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    """Blend c1 toward c2 by t (0..1).

    Falloffs (the radar sweep, dim graticules) are resolved against a known
    background *here*, at draw time, so every paint on the canvas is opaque and
    the rasteriser needs no per-pixel compositing."""
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


# ---------------------------------------------------------------------------
# raster core
# ---------------------------------------------------------------------------
class Canvas:
    """Opaque paint-over-canvas raster. Shapes are drawn in canvas units
    (= final pixels x SS); call `s(px)` to convert."""

    def __init__(self, size=SIZE, ss=SS, bg=(0, 0, 0)):
        self.n, self.ss = size, ss
        self.w = self.h = size * ss
        self.px = bytearray(self.w * self.h * 4)
        self.rect(0, 0, self.w - 1, self.h - 1, bg)

    def s(self, v):
        return int(v * self.ss)

    # -- primitives ----------------------------------------------------
    def row(self, y, x0, x1, c):
        """Paint x0..x1 inclusive on row y. The one hot loop; slice-assigned."""
        if not 0 <= y < self.h or x1 < 0 or x0 >= self.w:
            return
        x0 = max(x0, 0)
        x1 = min(x1, self.w - 1)
        if x1 < x0:
            return
        i = (y * self.w + x0) * 4
        self.px[i:i + 4 * (x1 - x0 + 1)] = bytes((c[0], c[1], c[2], 255)) * (x1 - x0 + 1)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(min(y0, y1)), int(max(y0, y1)) + 1):
            self.row(y, int(x0), int(x1), c)

    def rrect(self, x0, y0, x1, y1, r, c):
        """Rounded rectangle: per-row chord length from the corner-circle equation."""
        x0, y0, x1, y1, r = int(x0), int(y0), int(x1), int(y1), int(r)
        for y in range(y0, y1 + 1):
            dy = 0
            if y < y0 + r:
                dy = y0 + r - y
            elif y > y1 - r:
                dy = y - (y1 - r)
            if dy == 0:
                self.row(y, x0, x1, c)
            elif dy <= r:
                inset = r - math.isqrt(r * r - dy * dy)
                self.row(y, x0 + inset, x1 - inset, c)

    def disc(self, cx, cy, r, c):
        cx, cy, r = int(cx), int(cy), int(r)
        for y in range(cy - r, cy + r + 1):
            d = r * r - (y - cy) ** 2
            if d >= 0:
                dx = math.isqrt(d)
                self.row(y, cx - dx, cx + dx, c)

    def ring(self, cx, cy, r, t, c):
        """Annulus, outer radius r, thickness t."""
        cx, cy, r, t = int(cx), int(cy), int(r), max(1, int(t))
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            out = r * r - dy * dy
            if out < 0:
                continue
            xo = math.isqrt(out)
            inn = (r - t) * (r - t) - dy * dy
            if inn <= 0:
                self.row(y, cx - xo, cx + xo, c)
            else:
                xi = math.isqrt(inn)
                self.row(y, cx - xo, cx - xi - 1, c)
                self.row(y, cx + xi + 1, cx + xo, c)

    def poly(self, pts, c):
        """Even-odd scanline fill of a polygon in (x, y) canvas units."""
        pts = [(float(x), float(y)) for x, y in pts]
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(min(ys)), int(max(ys)) + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.row(y, int(round(xs[i])), int(round(xs[i + 1])) - 1, c)

    def seg(self, x0, y0, x1, y1, t, c):
        """Thick line = quad + round caps, so joins stay smooth at any angle."""
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln * t / 2.0, dx / ln * t / 2.0
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                   (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)
        self.disc(x0, y0, t / 2, c)
        self.disc(x1, y1, t / 2, c)

    def wedge(self, cx, cy, r, a0, a1, c):
        """Filled sector, degrees, 0 = east, counter-clockwise (y is flipped).

        Drawn as a fan polygon with the arc sampled at ~1 degree: the chord error
        at r = SIZE*SS is under a tenth of a pixel, and it costs one scanline
        fill instead of a per-pixel atan2 sweep over the bounding box — which
        matters because the radar afterglow is 46 wedges."""
        cx, cy, r = int(cx), int(cy), int(r)
        steps = max(1, int(abs(a1 - a0)))
        pts = [(cx, cy)]
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
        self.poly(pts, c)

    # -- output --------------------------------------------------------
    def downsample(self):
        """Box-filter SS x SS blocks: averaging hard-edged high-res pixels is the
        anti-aliasing, so no per-shape coverage maths is needed."""
        n, ss, w, px = self.n, self.ss, self.w, self.px
        out = bytearray(n * n * 4)
        ss2 = ss * ss
        for y in range(n):
            for x in range(n):
                rs = gs = bs = 0
                for sy in range(ss):
                    base = ((y * ss + sy) * w + x * ss) * 4
                    blk = px[base:base + ss * 4]
                    for k in range(0, ss * 4, 4):
                        rs += blk[k]
                        gs += blk[k + 1]
                        bs += blk[k + 2]
                o = (y * n + x) * 4
                out[o:o + 3] = bytes((rs // ss2, gs // ss2, bs // ss2))
                out[o + 3] = 255
        return bytes(out)

    def png(self):
        return png_encode(self.n, self.downsample())


# ---------------------------------------------------------------------------
# PNG I/O. One IHDR + one IDAT + one IEND, no tIME or tEXt chunk: the encoder is
# a pure function of the pixels, so two runs are byte-identical and `git status`
# stays clean after a rebuild.
# ---------------------------------------------------------------------------
def png_encode(size: int, rgba: bytes) -> bytes:
    stride = size * 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)                                   # filter type 0 (None)
        raw += rgba[y * stride:(y + 1) * stride]
    out = bytearray(b"\x89PNG\r\n\x1a\n")

    def chunk(tag: bytes, data: bytes):
        out.extend(struct.pack(">I", len(data)) + tag + data)
        out.extend(struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    chunk(b"IEND", b"")
    return bytes(out)


def png_decode_rgba(data: bytes):
    """Minimal PNG reader for `--check`: 8-bit RGB/RGBA, filters 0-4, no
    interlacing or palette. Pixels are what matters for reproducibility, which
    is why `--check` compares decoded pixels and not file bytes: a different
    zlib build may encode the same image to different bytes, and that is not
    drift."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    i, ihdr, idat = 8, None, bytearray()
    while i + 12 <= len(data):
        (ln,) = struct.unpack(">I", data[i:i + 4])
        tag, body = data[i + 4:i + 8], data[i + 8:i + 8 + ln]
        if tag == b"IHDR":
            ihdr = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        i += 12 + ln
    if ihdr is None:
        raise ValueError("no IHDR chunk")
    w, h, depth, ctype, comp, filt, interlace = struct.unpack(">IIBBBBB", ihdr[:13])
    if (depth, comp, filt, interlace) != (8, 0, 0, 0):
        raise ValueError(f"unsupported PNG (depth={depth}, comp={comp}, filter={filt}, interlace={interlace})")
    nch = {2: 3, 6: 4}.get(ctype)
    if nch is None:
        raise ValueError(f"unsupported colour type {ctype}; need RGB (2) or RGBA (6)")
    stride = w * nch
    raw = zlib.decompress(bytes(idat))
    out = bytearray(w * h * 4)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        f = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if f == 1:
            for x in range(nch, stride):
                line[x] = (line[x] + line[x - nch]) & 0xFF
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif f == 3:
            for x in range(stride):
                a = line[x - nch] if x >= nch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif f == 4:
            for x in range(stride):
                a = line[x - nch] if x >= nch else 0
                c, p = (prev[x - nch] if x >= nch else 0), prev[x]
                pa, pb, pc = abs(p - c), abs(a - c), abs(a + p - 2 * c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else p)
                line[x] = (line[x] + pred) & 0xFF
        elif f != 0:
            raise ValueError(f"unknown PNG filter {f}")
        for x in range(w):
            o, s0 = (y * w + x) * 4, x * nch
            out[o:o + 3] = line[s0:s0 + 3]
            out[o + 3] = 255 if nch == 3 else line[s0 + 3]
        prev = line
    return w, h, bytes(out)


# ---------------------------------------------------------------------------
# shared furniture
# ---------------------------------------------------------------------------
def plate(cv: Canvas, bg: str, edge: str, radius=52, inset=12, thick=4):
    """Square with softened corners, plus a one-colour border: the three apps
    read as one family in a chat list."""
    s, w = cv.s, cv.w - 1
    cv.rrect(0, 0, w, w, s(radius), rgb(bg))
    cv.rrect(s(inset), s(inset), s(256 - inset), s(256 - inset), s(radius - 6), rgb(edge))
    cv.rrect(s(inset + thick), s(inset + thick), s(255 - inset - thick), s(255 - inset - thick),
             s(radius - 6 - thick), rgb(bg))


# ---------------------------------------------------------------------------
# the three icons
# ---------------------------------------------------------------------------
def icon_cyberchef() -> Canvas:
    """Toque + cleaver: what the app actually is — an offline CyberChef build,
    416 recipes, i.e. a kitchen. Both motifs are polygons, so the icon stays
    legible at the 32-48px the messenger list views actually use."""
    bg, ink, steel, blue, wood = "#21252b", "#eee", "#abb2bf", "#61afef", "#e5c07b"
    cv = Canvas(bg=rgb(bg))
    s = cv.s
    plate(cv, bg, blue)

    hat = rgb(ink)
    for cx, r in ((90, 28), (128, 34), (166, 28)):            # the three puffs
        cv.disc(s(cx), s(78), s(r), hat)
    cv.disc(s(108), s(72), s(24), hat)                         # fuse them, no valleys
    cv.disc(s(148), s(72), s(24), hat)
    cv.rect(s(96), s(86), s(160), s(126), hat)                 # band, narrower than the puffs
    cv.rect(s(96), s(121), s(160), s(126), rgb(steel))        # band shadow

    # cleaver, tilted -14deg about its own centre, drawn in a local frame
    ang = math.radians(-14)
    ox, oy = s(126), s(178)
    ca, sa = math.cos(ang), math.sin(ang)

    def xf(pts):
        return [(ox + s(x * ca - y * sa), oy + s(x * sa + y * ca)) for x, y in pts]

    cv.poly(xf([(-46, -6), (14, -22), (34, -22), (34, 20), (-40, 20)]), rgb(steel))   # blade
    cv.poly(xf([(-40, 20), (34, 20), (34, 14), (-36, 14)]), rgb(ink))                  # cutting edge
    cv.seg(*xf([(34, -4), (58, -4)])[0], *xf([(34, -4), (58, -4)])[1], s(20), rgb(wood))  # handle
    for hx in (42, 52):
        cv.disc(*xf([(hx, -4)])[0], s(3), rgb(bg))                                        # rivets
    return cv


def icon_shamir() -> Canvas:
    """Five shares around one secret, three of them lit: k-of-n at a glance."""
    bg, lit, dim, gold = "#0a0c10", "#5ce4a0", "#232838", "#e0af68"
    cv = Canvas(bg=rgb(bg))
    s = cv.s
    plate(cv, bg, lit)

    cx, cy, r_out, r_in = s(128), s(132), s(104), s(56)
    for i in range(5):
        a0 = 126 - 72 * i                                     # start at the top, go CW
        cv.wedge(cx, cy, r_out, a0, a0 + 66, rgb(lit if i < 3 else dim))
        cv.disc(cx, cy, r_in, rgb(bg))                        # punch the ring once the sector is down

    cv.disc(cx, cy, s(34), rgb(gold))                          # the secret, as a keyhead
    cv.disc(cx, cy, s(13), rgb(bg))
    cv.poly([(cx - s(5), cy), (cx + s(5), cy), (cx + s(3), cy + s(20)), (cx - s(3), cy + s(20))],
            rgb(gold))
    return cv


def icon_radar() -> Canvas:
    """ADS-B plot scope: graticule, phosphor sweep, three contacts."""
    bg, on, off, cyan, amber, red = "#001100", "#00ff41", "#00aa2a", "#00ccff", "#ffaa00", "#ff3344"
    cv = Canvas(bg=rgb(bg))
    s = cv.s
    plate(cv, bg, off)

    cx, cy, r = s(128), s(132), s(104)
    cv.disc(cx, cy, r, mix(rgb(bg), rgb(on), 0.07))           # scope face
    head = 118                                                 # sweep leading edge, degrees
    for i in range(46):                                        # 46 slices, exponential afterglow
        cv.wedge(cx, cy, r, head - i - 1, head - i, mix(rgb(bg), rgb(on), 0.55 * math.exp(-i / 16.0)))
    for ring in (96, 70, 44):
        cv.ring(cx, cy, s(ring), s(3), rgb(off))
    cv.ring(cx, cy, r, s(4), rgb(on))
    cv.seg(cx - r, cy, cx + r, cy, s(2), mix(rgb(bg), rgb(off), 0.85))
    cv.seg(cx, cy - r, cx, cy + r, s(2), mix(rgb(bg), rgb(off), 0.85))
    cv.seg(cx, cy, cx + r * math.cos(math.radians(head)), cy - r * math.sin(math.radians(head)),
           s(4), rgb(on))

    for bx, by, col, alert in ((-52, -34, cyan, 0), (38, 46, amber, 0), (60, -60, red, 1)):
        cv.disc(cx + s(bx), cy + s(by), s(8), rgb(col))
        if alert:
            cv.ring(cx + s(bx), cy + s(by), s(17), s(3), rgb(col))
    cv.disc(cx, cy, s(5), rgb(on))
    return cv


ICONS = {"cyberchef": icon_cyberchef, "shamir": icon_shamir, "radar-scope": icon_radar}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render or verify the webxdc app icons.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="compare each committed icon with a fresh render; exit 1 on drift")
    ap.add_argument("--out", default=HERE, help="root to write into (default: this directory)")
    args = ap.parse_args(argv)

    rc = 0
    for app, fn in sorted(ICONS.items()):
        want = fn().png()
        path = os.path.join(args.out, app, "icon.png")
        if args.check:
            if not os.path.isfile(path):
                print(f"[MISSING] {app}/icon.png — run: python3 gen_icons.py")
                rc = 1
                continue
            got = open(path, "rb").read()
            try:
                same = png_decode_rgba(got)[2] == png_decode_rgba(want)[2]
            except ValueError as e:
                print(f"[FAIL] {app}/icon.png — {e}")
                rc = 1
                continue
            if not same:
                print(f"[DRIFT] {app}/icon.png — pixels differ from the generator;"
                      f" re-run python3 gen_icons.py")
                rc = 1
            else:
                note = "" if len(got) == len(want) else f"  (re-encoded by another zlib: {len(got)} vs {len(want)} bytes)"
                print(f"[OK] {app}/icon.png — {len(got)} bytes, reproducible{note}")
            continue
        if not os.path.isdir(os.path.dirname(path)):
            print(f"[SKIP] no such app directory: {os.path.dirname(path)}")
            continue
        with open(path, "wb") as fh:
            fh.write(want)
        print(f"wrote {os.path.relpath(path, HERE)} ({len(want)} bytes, {SIZE}x{SIZE} RGBA)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
