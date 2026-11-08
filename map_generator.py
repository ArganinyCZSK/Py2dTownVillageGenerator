from __future__ import division, print_function

import bisect
import copy
import json
import math
import os
import random
import struct
import sys
import unicodedata
import zlib
from optparse import OptionParser

PY3 = sys.version_info[0] >= 3
TAU = 2 * math.pi
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "type": "random",
    "name": "",
    "width": 1400, "height": 1000,
    "size": 100,
    "main_roads": 0,
    "streets": 100,
    "house_density": 100,
    "house_size": 100,
    "yards": 38,
    "fence_yards": 40,
    "brick_yards": 15,
    "pastures": 30,
    "gardens": 6,
    "walls": 1,
    "towers": 0,
    "lamps": 1, "lamp_spacing": 100,
    "center": 1,
    "church": 1,
    "dirt_roads": 100, "fields": 100, "forests": 100, "trees": 100,
    "texture": 1, "shadows": 1, "glow": 1, "title": 1, "legend": 1, "scalebar": 1,
}
LOOK_KEYS = ["texture", "shadows", "glow", "title", "legend", "scalebar"]

C = {
    "grass": (128, 166, 94),
    "grass_var": [(118, 157, 86), (136, 172, 100), (124, 160, 90), (142, 176, 104)],
    "fields": [(214, 196, 120), (196, 186, 104), (170, 182, 96), (150, 170, 88),
               (190, 160, 110), (222, 206, 140), (160, 140, 96)],
    "dirt": (181, 145, 98), "dirt_out": (138, 104, 66),
    "street": (204, 201, 192), "street_out": (112, 110, 104),
    "main": (228, 224, 212), "main_out": (88, 86, 82),
    "plaza": (214, 202, 178), "plaza_out": (130, 120, 100),
    "wall": (126, 120, 110), "wall_dark": (84, 80, 74), "tower": (104, 99, 91),
    "yard_wall": (150, 141, 124),
    "fence": (139, 100, 58), "fence_post": (92, 62, 32),
    "brick": (172, 80, 58), "brick_dark": (112, 46, 32), "brick_mortar": (214, 168, 140),
    "pasture": (152, 184, 104), "lawn": (138, 178, 96), "bush": (62, 112, 56),
    "roofs_town": [(170, 74, 52), (182, 92, 60), (150, 64, 48), (196, 110, 70),
                   (120, 112, 108), (160, 84, 58), (140, 130, 122)],
    "roofs_village": [(168, 76, 54), (150, 92, 62), (184, 104, 66), (176, 150, 96),
                      (128, 100, 76), (160, 70, 50)],
    "special_roof": (96, 104, 124),
    "tree": [(58, 98, 52), (66, 110, 58), (50, 88, 46), (74, 116, 60)],
    "green": (150, 186, 110),
    "water": (104, 152, 196), "water_out": (70, 110, 150),
    "lamp": (255, 236, 140), "lamp_glow": (255, 226, 110),
    "text": (40, 36, 30), "text2": (90, 80, 66),
    "panel": (248, 244, 233), "panel_out": (120, 110, 90),
}

NAME_A = ["Oak", "Ash", "Elm", "Mill", "Stone", "Brook", "Thorn", "Wolf", "Raven", "Green",
          "Black", "White", "Red", "Fair", "King", "Bridge", "Wind", "Iron", "Marsh", "Hawk",
          "Deer", "Silver", "Clay", "Willow", "Hazel", "Rook", "Barley", "Holly", "Cold", "Swan"]
NAME_B = ["ford", "bury", "ton", "wick", "field", "ham", "stead", "by", "dale", "brook",
          "worth", "ley", "more", "haven", "gate", "bridge", "hollow", "cross", "well", "combe"]
RIVERS = ["Avon", "Severn", "Trent", "Wye", "Tamar", "Ouse", "Dee", "Tees", "Eden", "Exe"]

APP_TITLE = "Village & Town Map Generator"
AUTHOR = "ArganinyCZSK / Jan Hepp"
LICENSE = "CC BY (Creative Commons Attribution)"
DISCORD = "https://discord.gg/gn85hyddQC"


def make_name(r, town):
    n = r.choice(NAME_A) + r.choice(NAME_B)
    roll = r.random()
    if town:
        if roll < 0.25:
            n = n + " upon " + r.choice(RIVERS)
        elif roll < 0.4:
            n = r.choice(["Kings", "Market", "Castle", "Port"]) + " " + n
    elif roll < 0.35:
        n = r.choice(["Little", "Lower", "Upper", "Nether", "Great"]) + " " + n
    return n


def to_unicode(s):
    if not PY3 and isinstance(s, str):
        return s.decode("utf-8", "replace")
    return s


def to_ascii(s):
    s = unicodedata.normalize("NFKD", to_unicode(s))
    return str(s.encode("ascii", "ignore").decode("ascii"))


def ascii_name(s):
    out = "".join([ch if ch.isalnum() else "_" for ch in to_ascii(s)]).strip("_")
    return str(out) or "map"


def fs_text(s):
    if not PY3 and isinstance(s, str):
        return s.decode(sys.getfilesystemencoding() or "mbcs", "replace")
    return s


def shade(col, f):
    return tuple([max(0, min(255, int(c * f))) for c in col[:3]])


def mix(a, b, t):
    return tuple([int(a[i] * (1 - t) + b[i] * t) for i in range(3)])


def hexcol(c):
    return "#%02x%02x%02x" % (int(c[0]), int(c[1]), int(c[2]))


def local_rect(cx, cy, ang, u0, u1, v0, v1):
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    return [(cx + ux * u + vx * v, cy + uy * u + vy * v)
            for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]


def rect_loop(cx, cy, ang, u0, u1, v0, v1, gate_w=7):
    c = local_rect(cx, cy, ang, u0, u1, v0, v1)
    um = (u0 + u1) / 2
    g = local_rect(cx, cy, ang, um - gate_w / 2, um + gate_w / 2, v0, v0)
    return [g[1], c[1], c[2], c[3], c[0], g[0]]


def roads_angle(roads, x, y):
    best, ang = 1e18, 0.0
    for rd in roads:
        for (ax, ay), (bx, by) in zip(rd["pts"], rd["pts"][1:]):
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            if L2 < 1e-9:
                continue
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2))
            d = (ax + t * dx - x) ** 2 + (ay + t * dy - y) ** 2
            if d < best:
                best, ang = d, math.atan2(dy, dx)
    return ang


def point_in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def seg_intersect(p1, p2, p3, p4):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p1, p2, p3, p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    if 0 <= t <= 1 and 0 <= u <= 1:
        return x1 + t * (x2 - x1), y1 + t * (y2 - y1)
    return None


class Polyline(object):
    def __init__(self, pts):
        self.pts = pts
        self.cum = [0.0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + math.hypot(x1 - x0, y1 - y0))
        self.length = self.cum[-1]

    def at(self, s):
        s = max(0.0, min(s, self.length))
        i = max(1, min(bisect.bisect_left(self.cum, s), len(self.pts) - 1))
        s0, s1 = self.cum[i - 1], self.cum[i]
        (x0, y0), (x1, y1) = self.pts[i - 1], self.pts[i]
        t = 0 if s1 == s0 else (s - s0) / (s1 - s0)
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, math.atan2(y1 - y0, x1 - x0)


class Raster(object):
    def __init__(self, w, h, ch=3, bg=0):
        self.w, self.h, self.ch = w, h, ch
        self.buf = self._col(bg) * (w * h)

    def _col(self, col):
        if self.ch == 1:
            return bytearray([col if isinstance(col, int) else int(col[0])])
        return bytearray([int(col[0]), int(col[1]), int(col[2])])

    def get(self, x, y):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.buf[(y * self.w + x) * self.ch]
        return 255

    def _span(self, y, x0, x1, col):
        if y < 0 or y >= self.h:
            return
        if x0 < 0:
            x0 = 0
        if x1 > self.w:
            x1 = self.w
        if x1 <= x0:
            return
        off = (y * self.w + x0) * self.ch
        self.buf[off:off + (x1 - x0) * self.ch] = col * (x1 - x0)

    def _blend_span(self, y, x0, x1, col, a):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0:
            return
        b = self.buf
        ia = 255 - a
        r0, g0, b0 = col[0] * a, col[1] * a, col[2] * a
        i = (y * self.w + x0) * 3
        end = (y * self.w + x1) * 3
        while i < end:
            b[i] = (b[i] * ia + r0) // 255
            b[i + 1] = (b[i + 1] * ia + g0) // 255
            b[i + 2] = (b[i + 2] * ia + b0) // 255
            i += 3

    def _scan_poly(self, pts, fn):
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.ceil(min(ys) - 0.5)))
        y1 = min(self.h - 1, int(math.floor(max(ys) - 0.5)))
        n = len(pts)
        edges = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if ay != by:
                edges.append((ax, ay, by, (bx - ax) / (by - ay)))
        for y in range(y0, y1 + 1):
            sy = y + 0.5
            xs = []
            for ax, ay, by, k in edges:
                if (ay <= sy < by) or (by <= sy < ay):
                    xs.append(ax + (sy - ay) * k)
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                fn(y, int(math.ceil(xs[i] - 0.5)), int(math.ceil(xs[i + 1] - 0.5)))

    def fill_poly(self, pts, col):
        c = self._col(col)
        self._scan_poly(pts, lambda y, a, b: self._span(y, a, b, c))

    def blend_poly(self, pts, col, alpha):
        self._scan_poly(pts, lambda y, a, b: self._blend_span(y, a, b, col, alpha))

    def _scan_ellipse(self, cx, cy, rx, ry, fn):
        if rx <= 0 or ry <= 0:
            return
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            dy = (y + 0.5 - cy) / ry
            if abs(dy) >= 1:
                continue
            dx = rx * math.sqrt(1 - dy * dy)
            fn(y, int(math.ceil(cx - dx - 0.5)), int(math.ceil(cx + dx - 0.5)))

    def fill_ellipse(self, cx, cy, rx, ry, col):
        c = self._col(col)
        self._scan_ellipse(cx, cy, rx, ry, lambda y, a, b: self._span(y, a, b, c))

    def blend_ellipse(self, cx, cy, rx, ry, col, alpha):
        self._scan_ellipse(cx, cy, rx, ry,
                           lambda y, a, b: self._blend_span(y, a, b, col, alpha))

    def glow(self, cx, cy, r, col, alpha):
        b = self.buf
        for y in range(int(cy - r), int(cy + r) + 1):
            if y < 0 or y >= self.h:
                continue
            for x in range(int(cx - r), int(cx + r) + 1):
                if x < 0 or x >= self.w:
                    continue
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
                if d >= 1:
                    continue
                a = int(alpha * (1 - d) * (1 - d))
                ia = 255 - a
                i = (y * self.w + x) * 3
                b[i] = (b[i] * ia + col[0] * a) // 255
                b[i + 1] = (b[i + 1] * ia + col[1] * a) // 255
                b[i + 2] = (b[i + 2] * ia + col[2] * a) // 255

    def stroke(self, pts, width, col, round_joins=True):
        r = width / 2.0
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay)
            if L < 1e-6:
                continue
            nx, ny = -(by - ay) / L * r, (bx - ax) / L * r
            self.fill_poly([(ax + nx, ay + ny), (bx + nx, by + ny),
                            (bx - nx, by - ny), (ax - nx, ay - ny)], col)
        if round_joins and r >= 1:
            for x, y in pts:
                self.fill_ellipse(x, y, r, r, col)

    def rect(self, x0, y0, x1, y1, col):
        self.fill_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col)

    def block(self, x, y, s, col):
        for yy in range(int(y), int(y + s)):
            self._span(yy, int(x), int(x + s), col)

    def save_png(self, path):
        w, h, rb = self.w, self.h, self.w * 3
        raw = b"".join([b"\x00" + bytes(self.buf[y * rb:(y + 1) * rb]) for y in range(h)])

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data +
                    struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

        write_bytes(path, b"\x89PNG\r\n\x1a\n" +
                    chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                    chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))

    def _bgr(self):
        src = self.buf
        out = bytearray(len(src))
        try:
            out[0::3] = src[2::3]
            out[1::3] = src[1::3]
            out[2::3] = src[0::3]
        except Exception:
            for i in range(0, len(src), 3):
                out[i], out[i + 1], out[i + 2] = src[i + 2], src[i + 1], src[i]
        return out

    def save_bmp(self, path):
        w, h, rb = self.w, self.h, self.w * 3
        pad = (4 - rb % 4) % 4
        bgr = self._bgr()
        rows = [bytes(bgr[y * rb:(y + 1) * rb]) + b"\x00" * pad for y in range(h - 1, -1, -1)]
        data = b"".join(rows)
        header = struct.pack("<2sIHHI", b"BM", 54 + len(data), 0, 0, 54)
        info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(data), 2835, 2835, 0, 0)
        write_bytes(path, header + info + data)

    def save_ppm(self, path):
        write_bytes(path, ("P6\n%d %d\n255\n" % (self.w, self.h)).encode("ascii") + bytes(self.buf))


def write_bytes(path, data):
    f = open(path, "wb")
    try:
        f.write(data)
    finally:
        f.close()


_GL = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.###.", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.", "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "a": ".....|.....|.###.|....#|.####|#...#|.####", "b": "#....|#....|####.|#...#|#...#|#...#|####.",
    "c": ".....|.....|.###.|#....|#....|#...#|.###.", "d": "....#|....#|.####|#...#|#...#|#...#|.####",
    "e": ".....|.....|.###.|#...#|#####|#....|.###.", "f": "..##.|.#..#|.#...|###..|.#...|.#...|.#...",
    "g": ".....|.....|.####|#...#|#...#|#...#|.####|....#|.###.",
    "h": "#....|#....|####.|#...#|#...#|#...#|#...#", "i": "..#..|.....|.##..|..#..|..#..|..#..|.###.",
    "j": "...#.|.....|..##.|...#.|...#.|...#.|...#.|#..#.|.##..",
    "k": "#....|#....|#..#.|#.#..|##...|#.#..|#..#.", "l": ".##..|..#..|..#..|..#..|..#..|..#..|.###.",
    "m": ".....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#", "n": ".....|.....|####.|#...#|#...#|#...#|#...#",
    "o": ".....|.....|.###.|#...#|#...#|#...#|.###.",
    "p": ".....|.....|####.|#...#|#...#|#...#|####.|#....|#....",
    "q": ".....|.....|.####|#...#|#...#|#...#|.####|....#|....#",
    "r": ".....|.....|#.##.|##..#|#....|#....|#....", "s": ".....|.....|.####|#....|.###.|....#|####.",
    "t": ".#...|.#...|###..|.#...|.#...|.#..#|..##.", "u": ".....|.....|#...#|#...#|#...#|#..##|.##.#",
    "v": ".....|.....|#...#|#...#|#...#|.#.#.|..#..", "w": ".....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.",
    "x": ".....|.....|#...#|.#.#.|..#..|.#.#.|#...#",
    "y": ".....|.....|#...#|#...#|#...#|#...#|.####|....#|.###.",
    "z": ".....|.....|#####|...#.|..#..|.#...|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": ".###.|#....|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|....#|.###.",
    ".": ".....|.....|.....|.....|.....|.##..|.##..", ",": ".....|.....|.....|.....|.##..|..#..|.#...",
    "-": ".....|.....|.....|.###.|.....|.....|.....", ":": ".....|.##..|.##..|.....|.##..|.##..|.....",
    "/": "....#|...#.|...#.|..#..|.#...|.#...|#....", "(": "...#.|..#..|.#...|.#...|.#...|..#..|...#.",
    ")": ".#...|..#..|...#.|...#.|...#.|..#..|.#...", "|": "..#..|..#..|..#..|..#..|..#..|..#..|..#..",
    "'": "..#..|..#..|.....|.....|.....|.....|.....", "%": "##..#|##.#.|...#.|..#..|.#...|.#.##|#..##",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....", "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..", "&": ".##..|#..#.|.##..|.#...|#.#.#|#..#.|.##.#",
    "=": ".....|.....|#####|.....|#####|.....|.....", "_": ".....|.....|.....|.....|.....|.....|#####",
    "~": ".....|.....|.#...|#.#.#|...#.|.....|.....",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}
GLYPHS = {}
for _k, _v in _GL.items():
    _rows = _v.split("|")
    GLYPHS[_k] = _rows + ["....."] * (9 - len(_rows))


def text_width(text, s):
    return len(to_ascii(text)) * 6 * s


def raster_text(rs, x, y, text, s, col):
    c = rs._col(col)
    cx = x
    for ch in to_ascii(text):
        rows = GLYPHS.get(ch) or GLYPHS.get(ch.upper()) or GLYPHS[" "]
        for r in range(9):
            row = rows[r]
            for k in range(5):
                if row[k] == "#":
                    rs.block(cx + k * s, y + r * s, s, c)
        cx += 6 * s


class Settlement(object):
    def __init__(self, kind, seed, cfg):
        self.kind, self.seed = kind, seed
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.town = (kind == "town")
        r = self.rng
        self.W, self.H = int(cfg["width"]), int(cfg["height"])
        self.area = self.W * self.H / 1400000.0
        self.cx = self.W / 2 + r.uniform(-60, 60)
        self.cy = self.H / 2 + r.uniform(-40, 40)
        self.R = (r.uniform(290, 340) if self.town else r.uniform(200, 250)) * self.pct("size")

        self.roads, self.houses, self.lamps = [], [], []
        self.fields, self.trees, self.gates, self.gardens = [], [], [], []
        self.wall_poly = None
        self.wall_shrunk = None
        self.plaza = None
        self.green = None
        self.pond = None

        self.occ = Raster(self.W, self.H, 1, 0)
        self.bld = Raster(self.W, self.H, 1, 0)
        self.grid = {}
        self.cell = 8
        self.name = to_unicode(cfg["name"]).strip() or make_name(r, self.town)
        self.generate()

    def pct(self, key):
        return max(0.0, float(self.cfg[key]) / 100.0)

    def count(self, a, b, key):
        return int(round(self.rng.randint(a, b) * self.pct(key)))

    def in_core(self, x, y):
        if self.wall_shrunk:
            return point_in_poly(x, y, self.wall_shrunk)
        return math.hypot(x - self.cx, y - self.cy) < self.R * 0.85

    def outside_core(self, x, y):
        if self.wall_poly:
            return not point_in_poly(x, y, self.wall_poly)
        return math.hypot(x - self.cx, y - self.cy) > self.R * 0.9

    def _register_road(self, pts, rid):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 3))
            for k in range(n + 1):
                x = x0 + (x1 - x0) * k / n
                y = y0 + (y1 - y0) * k / n
                self.grid.setdefault((int(x // self.cell), int(y // self.cell)), set()).add(rid)

    def _hits_road(self, x, y, own):
        ids = self.grid.get((int(x // self.cell), int(y // self.cell)))
        return bool(ids and (ids - set([own])))

    def _walk(self, x, y, ang, step, max_len, curve, rid, bound=None, stop_on_road=True):
        r = self.rng
        pts = [(x, y)]
        length = 0.0
        drift = 0.0
        while length < max_len:
            drift = drift * 0.7 + r.uniform(-curve, curve)
            ang += drift * 0.5
            nx, ny = x + math.cos(ang) * step, y + math.sin(ang) * step
            if not (-40 < nx < self.W + 40 and -40 < ny < self.H + 40):
                pts.append((nx, ny))
                break
            if bound is not None and not bound(nx, ny):
                break
            if stop_on_road and length > 24:
                hit = False
                for k in (1, 2, 3):
                    if self._hits_road(x + (nx - x) * k / 3, y + (ny - y) * k / 3, rid):
                        hit = True
                        break
                if hit:
                    pts.append((nx, ny))
                    break
            pts.append((nx, ny))
            x, y = nx, ny
            length += step
        return pts

    def _add_road(self, pts, w, kind):
        if len(pts) < 2:
            return
        rid = len(self.roads)
        self.roads.append({"pts": pts, "w": w, "kind": kind})
        self._register_road(pts, rid)
        self.occ.stroke(pts, w + 6, 255)

    def _branch(self, parents, count, w, kind, length_rng, bound, curve=0.12,
                dist_rng=(0.0, 1.0)):
        r = self.rng
        made = 0
        tries = 0
        while parents and made < count and tries < count * 25:
            tries += 1
            pl = Polyline(r.choice(parents)["pts"])
            if pl.length < 40:
                continue
            x, y, a = pl.at(r.uniform(15, pl.length - 15))
            d = math.hypot(x - self.cx, y - self.cy) / max(self.R, 1)
            if not (dist_rng[0] <= d <= dist_rng[1]):
                continue
            ang = a + r.choice((-1, 1)) * (math.pi / 2 + r.uniform(-0.35, 0.35))
            if self._hits_road(x + math.cos(ang) * 14, y + math.sin(ang) * 14, -1) and \
                    self._hits_road(x + math.cos(ang) * 22, y + math.sin(ang) * 22, -1):
                continue
            pts = self._walk(x, y, ang, 10, r.uniform(*length_rng), curve, len(self.roads), bound)
            if len(pts) >= 4:
                self._add_road(pts, w, kind)
                made += 1

    def _make_roads(self):
        r = self.rng
        n_main = int(self.cfg["main_roads"]) or (r.randint(4, 5) if self.town
                                                 else r.choice((2, 3, 3, 4)))
        base = r.uniform(0, TAU)
        main_w = 13 if self.town else 10
        for i in range(n_main):
            ang = base + i * TAU / n_main + r.uniform(-0.35, 0.35) * min(1, 4.0 / n_main)
            pts = self._walk(self.cx, self.cy, ang, 12, 5000, 0.07, len(self.roads),
                             stop_on_road=False)
            self._add_road(pts, main_w, "main")
        mains = list(self.roads)

        if self.town:
            self._branch(mains, self.count(18, 26, "streets"), 8, "street", (80, 260),
                         self.in_core, 0.10)
            streets = [rd for rd in self.roads if rd["kind"] == "street"]
            self._branch(streets, self.count(18, 28, "streets"), 7, "street", (50, 160),
                         self.in_core, 0.08)
            self._branch(mains, self.count(2, 4, "streets"), 7, "street", (60, 140),
                         self.outside_core, 0.12, (1.02, 1.35))
            self._branch(mains, self.count(6, 9, "dirt_roads"), 5, "dirt", (150, 420),
                         self.outside_core, 0.22, (1.05, 2.4))
        else:
            cx, cy, R = self.cx, self.cy, self.R
            within = lambda x, y: math.hypot(x - cx, y - cy) < R * 1.05
            self._branch(mains, self.count(6, 10, "streets"), 7, "street", (60, 200), within,
                         0.14, (0.1, 0.85))
            streets = [rd for rd in self.roads if rd["kind"] == "street"]
            self._branch(streets, self.count(0, 3, "dirt_roads"), 5, "dirt", (40, 120), within,
                         0.2, (0.2, 0.9))
            self._branch(list(self.roads), self.count(6, 9, "dirt_roads"), 5, "dirt",
                         (150, 450), lambda x, y: True, 0.24, (0.45, 2.2))

    def _make_wall(self):
        r = self.rng
        n = int(self.cfg["towers"]) or r.randint(13, 18)
        n = max(5, n)
        Rw = self.R * 0.9
        base = r.uniform(0, TAU)
        poly = []
        for i in range(n):
            a = base + i * TAU / n + r.uniform(-0.12, 0.12) * min(1, 15.0 / n)
            rr = Rw * r.uniform(0.9, 1.08)
            poly.append((self.cx + math.cos(a) * rr * 1.05, self.cy + math.sin(a) * rr * 0.95))
        self.wall_poly = poly
        self.wall_shrunk = [(self.cx + (x - self.cx) * 0.94, self.cy + (y - self.cy) * 0.94)
                            for x, y in poly]

    def _finish_wall(self):
        poly = self.wall_poly + [self.wall_poly[0]]
        self.occ.stroke(poly, 16, 255)
        for rd in self.roads:
            if rd["kind"] != "main":
                continue
            for a, b in zip(rd["pts"], rd["pts"][1:]):
                for p, q in zip(poly, poly[1:]):
                    hit = seg_intersect(a, b, p, q)
                    if hit:
                        self.gates.append([hit[0], hit[1],
                                           math.atan2(q[1] - p[1], q[0] - p[0]), rd["w"]])

    def _make_center(self):
        r = self.rng
        if self.town:
            s = r.uniform(42, 55) * min(1.3, max(0.6, self.pct("size")))
            ang = r.uniform(0, math.pi / 2)
            self.plaza = local_rect(self.cx, self.cy, ang, -s, s, -s * r.uniform(0.75, 1), s)
            self.occ.fill_poly(self.plaza, 255)
            if self.cfg["lamps"]:
                for x, y in self.plaza:
                    self.lamps.append((x * 0.85 + self.cx * 0.15, y * 0.85 + self.cy * 0.15))
        else:
            rx, ry = r.uniform(55, 75), r.uniform(32, 44)
            self.green = (self.cx, self.cy, rx, ry)
            px = self.cx + r.uniform(-rx * 0.4, rx * 0.4)
            py = self.cy + r.uniform(-ry * 0.3, ry * 0.3)
            self.pond = (px, py, r.uniform(14, 22), r.uniform(9, 14))
            self.occ.fill_ellipse(self.cx, self.cy, rx, ry, 255)

    def _free(self, cx, cy, ang, u0, u1, v0, v1, n=6):
        ux, uy = math.cos(ang), math.sin(ang)
        vx, vy = -uy, ux
        for i in range(n):
            u = u0 + (u1 - u0) * i / (n - 1)
            for j in range(n):
                v = v0 + (v1 - v0) * j / (n - 1)
                x = cx + ux * u + vx * v
                y = cy + uy * u + vy * v
                if not (4 <= x < self.W - 4 and 4 <= y < self.H - 4):
                    return False
                if self.occ.get(x, y):
                    return False
        return True

    def _density(self, x, y, kind):
        d = math.hypot(x - self.cx, y - self.cy)
        if self.town:
            if self.in_core(x, y):
                p = 0.97
            elif kind == "dirt":
                p = 0.0
            else:
                p = max(0.0, 0.45 * (1 - (d - self.R) / 140))
        else:
            dn = d / max(self.R, 1)
            p = 0.95 if dn < 0.55 else 0.95 * (1 - (dn - 0.55) / 0.6)
            if kind == "dirt":
                p *= 0.35
        return min(1.0, max(0.0, p) * self.pct("house_density"))

    def _yard_type(self):
        r = self.rng.random() * 100
        if r < float(self.cfg["brick_yards"]):
            return "brick"
        if r < float(self.cfg["brick_yards"]) + float(self.cfg["fence_yards"]):
            return "fence"
        return "stone"

    def _place_house(self, cx, cy, ang, w, d, roof, special=None, margin=1.5, yard=None,
                     yard_type="stone"):
        poly = local_rect(cx, cy, ang, -w / 2, w / 2, -d / 2, d / 2)
        self.houses.append({"cx": cx, "cy": cy, "ang": ang, "w": w, "d": d, "roof": roof,
                            "special": special, "yard": yard, "yard_type": yard_type})
        self.occ.fill_poly(local_rect(cx, cy, ang, -w / 2 - margin, w / 2 + margin,
                                      -d / 2 - margin, d / 2 + margin), 255)
        self.bld.fill_poly(poly, 255)

    def _make_specials(self):
        if not self.cfg["church"]:
            return
        r = self.rng
        specials = ["church", "townhall"] if self.town else ["church"]
        for sp in specials:
            for _ in range(300):
                a = r.uniform(0, TAU)
                dist = r.uniform(50, 110) if self.town else r.uniform(55, 100)
                x = self.cx + math.cos(a) * dist
                y = self.cy + math.sin(a) * dist
                ang = r.uniform(0, math.pi)
                if sp == "church":
                    w, d = r.uniform(38, 46), r.uniform(18, 22)
                else:
                    w, d = r.uniform(30, 36), r.uniform(20, 24)
                pad = 0 if self.town else 9
                if self._free(x, y, ang, -w / 2 - pad - 2, w / 2 + pad + 2,
                              -d / 2 - pad - 2, d / 2 + pad + 2, 8):
                    yard = None
                    if pad:
                        yard = [-w / 2 - pad, w / 2 + pad, -d / 2 - pad, d / 2 + pad]
                        self.occ.fill_poly(local_rect(x, y, ang, -w / 2 - pad - 2,
                                                      w / 2 + pad + 2, -d / 2 - pad - 2,
                                                      d / 2 + pad + 2), 255)
                    self._place_house(x, y, ang, w, d, C["special_roof"], sp, 2, yard)
                    break

    def _make_houses(self):
        r = self.rng
        hs = self.pct("house_size")
        if self.town:
            wr, dr, gap, setback = (12 * hs, 21 * hs), (12 * hs, 19 * hs), (0.5, 3), (2.5, 4.5)
            roofs = C["roofs_town"]
        else:
            wr, dr, gap, setback = (15 * hs, 24 * hs), (12 * hs, 18 * hs), (4, 16), (8, 14)
            roofs = C["roofs_village"]
        yard_p = self.pct("yards")
        prio = {"main": 0, "street": 1, "dirt": 2}
        for rd in sorted(self.roads, key=lambda q: prio[q["kind"]]):
            pl = Polyline(rd["pts"])
            for side in (-1, 1):
                s = r.uniform(0, 10)
                while s < pl.length:
                    w = r.uniform(*wr)
                    d = r.uniform(*dr)
                    x, y, a = pl.at(s + w / 2)
                    nx, ny = -math.sin(a) * side, math.cos(a) * side
                    sb = r.uniform(*setback)
                    off = rd["w"] / 2 + 3 + sb + d / 2
                    hx, hy = x + nx * off, y + ny * off
                    ang = a if side == 1 else a + math.pi
                    if r.random() < self._density(hx, hy, rd["kind"]):
                        yard = None
                        if not self.town and r.random() < yard_p:
                            e = r.uniform(6, 12)
                            back = r.uniform(10, 26)
                            yard = [-w / 2 - e, w / 2 + e, -d / 2 - sb + 1.5, d / 2 + back]
                            if not self._free(hx, hy, ang, yard[0] - 2, yard[1] + 2,
                                              yard[2], yard[3] + 2, 8):
                                yard = None
                        if yard or self._free(hx, hy, ang, -w / 2 - 1, w / 2 + 1,
                                              -d / 2 - 1, d / 2 + 1):
                            if yard:
                                self.occ.fill_poly(local_rect(hx, hy, ang, yard[0] - 2,
                                                              yard[1] + 2, yard[2],
                                                              yard[3] + 2), 255)
                            self._place_house(hx, hy, ang, w, d, r.choice(roofs),
                                              margin=(1.0 if self.town else 4), yard=yard,
                                              yard_type=self._yard_type() if yard else "stone")
                            s += w + r.uniform(*gap)
                            continue
                    s += r.uniform(4, 9)

    def _make_gardens(self):
        r = self.rng
        n = int(self.cfg["gardens"]) if self.town else int(int(self.cfg["gardens"]) / 3)
        made = 0
        for _ in range(n * 120):
            if made >= n:
                break
            a = r.uniform(0, TAU)
            dd = self.R * r.uniform(0.15, 0.95 if self.town else 1.1)
            x, y = self.cx + math.cos(a) * dd, self.cy + math.sin(a) * dd
            if self.town and not self.in_core(x, y):
                continue
            w, h = r.uniform(26, 48), r.uniform(20, 36)
            ang = roads_angle(self.roads, x, y)
            if not self._free(x, y, ang, -w / 2 - 2, w / 2 + 2, -h / 2 - 2, h / 2 + 2, 8):
                continue
            bushes = []
            for _ in range(r.randint(3, 7)):
                bushes.append([r.uniform(-w / 2 + 5, w / 2 - 5), r.uniform(-h / 2 + 5, h / 2 - 5),
                               r.uniform(2.5, 5)])
            self.gardens.append({"cx": x, "cy": y, "ang": ang, "w": w, "h": h,
                                 "bushes": bushes})
            self.occ.fill_poly(local_rect(x, y, ang, -w / 2 - 2, w / 2 + 2,
                                          -h / 2 - 2, h / 2 + 2), 255)
            made += 1

    def _make_lamps(self):
        if not self.cfg["lamps"]:
            return
        r = self.rng
        sp = max(0.3, self.pct("lamp_spacing"))
        for rd in self.roads:
            if rd["kind"] == "dirt":
                continue
            pl = Polyline(rd["pts"])
            spacing = (r.uniform(34, 42) if self.town else r.uniform(55, 75)) * sp
            s = r.uniform(5, spacing)
            side = 1
            while s < pl.length:
                x, y, a = pl.at(s)
                s += spacing
                side = -side
                if self.town:
                    ok = self.in_core(x, y)
                else:
                    ok = math.hypot(x - self.cx, y - self.cy) < self.R * 0.8 and \
                        (rd["kind"] == "main" or r.random() < 0.6)
                if not ok:
                    continue
                off = rd["w"] / 2 + 2.5
                lx, ly = x - math.sin(a) * off * side, y + math.cos(a) * off * side
                if self.plaza and point_in_poly(lx, ly, self.plaza):
                    continue
                if 2 < lx < self.W - 2 and 2 < ly < self.H - 2 and not self.bld.get(lx, ly):
                    self.lamps.append((lx, ly))

    def _make_fields(self):
        r = self.rng
        g = r.uniform(0, math.pi)
        inner = self.R * (1.0 if self.town else 0.82)
        target = int(r.randint(30, 45) * self.pct("fields") * self.area)
        tries = int(900 * max(1.0, self.pct("fields")) * max(1.0, self.area))
        for _ in range(tries):
            if len(self.fields) >= target:
                break
            x, y = r.uniform(10, self.W - 10), r.uniform(10, self.H - 10)
            if math.hypot(x - self.cx, y - self.cy) < inner:
                continue
            fw, fh = r.uniform(55, 140), r.uniform(40, 100)
            ang = g + r.choice((0, math.pi / 2)) + r.uniform(-0.15, 0.15)
            if self._free(x, y, ang, -fw / 2 - 3, fw / 2 + 3, -fh / 2 - 3, fh / 2 + 3, 7):
                pasture = r.random() * 100 < float(self.cfg["pastures"])
                self.fields.append({"cx": x, "cy": y, "ang": ang, "w": fw, "h": fh,
                                    "col": C["pasture"] if pasture else r.choice(C["fields"]),
                                    "gap": r.uniform(4, 7), "rot": r.random() < 0.5,
                                    "pasture": pasture})
                self.occ.fill_poly(local_rect(x, y, ang, -fw / 2 - 3, fw / 2 + 3,
                                              -fh / 2 - 3, fh / 2 + 3), 255)

    def _tree_ok(self, x, y, rad):
        if not (2 < x < self.W - 2 and 2 < y < self.H - 2):
            return False
        for dx, dy in ((0, 0), (rad, 0), (-rad, 0), (0, rad), (0, -rad)):
            px, py = x + dx, y + dy
            if 0 <= px < self.W and 0 <= py < self.H and self.occ.get(px, py):
                return False
        return True

    def _make_trees(self):
        r = self.rng
        for _ in range(int(round(r.randint(4, 7) * self.pct("forests") * self.area))):
            fx, fy = r.uniform(0, self.W), r.uniform(0, self.H)
            for _ in range(60):
                if math.hypot(fx - self.cx, fy - self.cy) > self.R * 1.25:
                    break
                fx, fy = r.uniform(0, self.W), r.uniform(0, self.H)
            sig = r.uniform(30, 75)
            for _ in range(r.randint(60, 160)):
                x, y = r.gauss(fx, sig), r.gauss(fy, sig * 0.8)
                rad = r.uniform(5, 9)
                if self._tree_ok(x, y, rad):
                    self.trees.append((x, y, rad, r.choice(C["tree"])))
        n = int((120 if self.town else 260) * self.pct("trees"))
        for _ in range(n * 3):
            if n <= 0:
                break
            a = r.uniform(0, TAU)
            dd = self.R * (r.uniform(0.95, 1.8) if self.town else r.uniform(0.2, 1.4))
            x, y = self.cx + math.cos(a) * dd, self.cy + math.sin(a) * dd
            rad = r.uniform(4, 7)
            if self._tree_ok(x, y, rad):
                self.trees.append((x, y, rad, r.choice(C["tree"])))
                n -= 1

    def generate(self):
        if self.town and self.cfg["walls"]:
            self._make_wall()
        self._make_roads()
        if self.wall_poly:
            self._finish_wall()
        if self.cfg["center"]:
            self._make_center()
        self._make_specials()
        self._make_houses()
        self._make_gardens()
        self._make_lamps()
        self._make_fields()
        self._make_trees()
        self.occ = self.bld = None

    def to_doc(self):
        objs = []

        def add(o):
            o["id"] = len(objs)
            objs.append(o)

        for f in self.fields:
            o = dict(f)
            o["type"] = "field"
            add(o)
        if self.green:
            add({"type": "green", "x": self.green[0], "y": self.green[1],
                 "rx": self.green[2], "ry": self.green[3]})
        if self.pond:
            add({"type": "pond", "x": self.pond[0], "y": self.pond[1],
                 "rx": self.pond[2], "ry": self.pond[3]})
        for g in self.gardens:
            o = dict(g)
            o["type"] = "garden"
            add(o)
        for h in self.houses:
            o = dict(h)
            o["type"] = h["special"] or "house"
            del o["special"]
            add(o)
        for x, y, rad, col in self.trees:
            add({"type": "tree", "x": x, "y": y, "r": rad, "col": col})
        for x, y in self.lamps:
            add({"type": "lamp", "x": x, "y": y})
        per = (5.5, 7.5) if self.town else (3.2, 4.6)
        opts = {}
        for k in LOOK_KEYS:
            opts[k] = int(self.cfg[k])
        return {"format": "mapgen", "version": 1, "width": self.W, "height": self.H,
                "kind": self.kind, "name": self.name, "seed": self.seed,
                "per_house": self.rng.uniform(*per), "roads": self.roads,
                "wall": self.wall_poly, "gates": self.gates, "plaza": self.plaza,
                "objects": objs, "opts": opts}


def generate_doc(cfg=None, kind=None, seed=None):
    c = dict(DEFAULTS)
    if cfg:
        c.update(cfg)
    if seed is None:
        seed = random.randint(0, 999999)
    kind = kind or c.get("type")
    if kind not in ("village", "town"):
        kind = random.Random(seed).choice(("village", "town"))
    return Settlement(kind, seed, c).to_doc()


def house_parts(o):
    cx, cy, a, w, d = o["cx"], o["cy"], o["ang"], o["w"], o["d"]
    poly = local_rect(cx, cy, a, -w / 2, w / 2, -d / 2, d / 2)
    if w >= d:
        h1 = local_rect(cx, cy, a, -w / 2, w / 2, -d / 2, 0)
        h2 = local_rect(cx, cy, a, -w / 2, w / 2, 0, d / 2)
        rg = local_rect(cx, cy, a, -w / 2 + 1, w / 2 - 1, 0, 0)
        ridge = [rg[0], rg[1]]
    else:
        h1 = local_rect(cx, cy, a, -w / 2, 0, -d / 2, d / 2)
        h2 = local_rect(cx, cy, a, 0, w / 2, -d / 2, d / 2)
        rg = local_rect(cx, cy, a, 0, 0, -d / 2 + 1, d / 2 - 1)
        ridge = [rg[0], rg[3]]
    return poly, h1, h2, ridge


def yard_line(o, gate_w=7):
    u0, u1, v0, v1 = o["yard"]
    return rect_loop(o["cx"], o["cy"], o["ang"], u0, u1, v0, v1, gate_w)


def _along(pts, step):
    out = []
    carry = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        s = carry
        while s <= L:
            t = s / L if L else 0
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t, math.atan2(by - ay, bx - ax)))
            s += step
        carry = s - L
    if pts:
        out.append((pts[-1][0], pts[-1][1], 0.0))
    return out


def wall_ops(kind, pts, tag):
    ops = []
    if kind == "fence":
        ops.append((tag, ("line", pts, C["fence"], 1.4)))
        for x, y, a in _along(pts, 6):
            ops.append((tag, ("poly", local_rect(x, y, a, -1.1, 1.1, -1.1, 1.1),
                              C["fence_post"], None, 0)))
    elif kind == "brick":
        ops.append((tag, ("line", pts, C["brick_dark"], 4.6)))
        ops.append((tag, ("line", pts, C["brick"], 3.0)))
        for x, y, a in _along(pts, 4)[1:-1]:
            p = local_rect(x, y, a, 0, 0, -1.4, 1.4)
            ops.append((tag, ("line", [p[0], p[3]], C["brick_mortar"], 0.6)))
    else:
        ops.append((tag, ("line", pts, shade(C["yard_wall"], 0.7), 3.2)))
        ops.append((tag, ("line", pts, C["yard_wall"], 1.8)))
    return ops


WALL_OBJ = {"fence": "fence", "brickwall": "brick", "stonewall": "stone"}
BUILDING_TYPES = ("house", "church", "townhall")


def build_scene(doc, overlay=True):
    W, H = doc["width"], doc["height"]
    opts = doc.get("opts", {})
    ops = []

    def add(op, tag=None):
        ops.append((tag, op))

    add(("bg", C["grass"]))
    if opts.get("texture", 1):
        r = random.Random(int(doc.get("seed", 0) or 0) * 7 + 1)
        for _ in range(int(2500 * W * H / 1400000.0)):
            add(("ellipse", r.uniform(0, W), r.uniform(0, H), r.uniform(4, 22),
                 r.uniform(3, 14), r.choice(C["grass_var"]), None, 0))

    objs = doc["objects"]

    def of(*types):
        return [o for o in objs if o["type"] in types]

    for f in of("field"):
        tag = "o%d" % f["id"]
        col = tuple(f["col"])
        add(("poly", local_rect(f["cx"], f["cy"], f["ang"], -f["w"] / 2, f["w"] / 2,
                                -f["h"] / 2, f["h"] / 2), col, shade(col, 0.8), 1), tag)
        if f.get("pasture"):
            loop = rect_loop(f["cx"], f["cy"], f["ang"], -f["w"] / 2 + 1, f["w"] / 2 - 1,
                             -f["h"] / 2 + 1, f["h"] / 2 - 1, 10)
            ops.extend(wall_ops("fence", loop, tag))
            continue
        dark = shade(col, 0.88)
        if f["rot"]:
            u_len, v_len, ang = f["h"], f["w"], f["ang"] + math.pi / 2
        else:
            u_len, v_len, ang = f["w"], f["h"], f["ang"]
        k = -u_len / 2 + f["gap"]
        while k < u_len / 2 - 1:
            p = local_rect(f["cx"], f["cy"], ang, k, k, -v_len / 2 + 2, v_len / 2 - 2)
            add(("line", [p[0], p[3]], dark, 1), tag)
            k += f["gap"]

    for g in of("green"):
        add(("ellipse", g["x"], g["y"], g["rx"], g["ry"], C["green"],
             shade(C["green"], 0.85), 1), "o%d" % g["id"])
    for p in of("pond"):
        add(("ellipse", p["x"], p["y"], p["rx"], p["ry"], C["water"], C["water_out"], 2),
            "o%d" % p["id"])
    for sm in of("stream"):
        add(("line", sm["pts"], C["water_out"], 4.2), "o%d" % sm["id"])
        add(("line", sm["pts"], C["water"], 2.6), "o%d" % sm["id"])

    wall = doc.get("wall")
    if wall:
        poly = list(wall) + [wall[0]]
        add(("line", poly, C["wall_dark"], 11))
        add(("line", poly, C["wall"], 7))

    for kind in ("dirt", "street", "main"):
        rs = [rd for rd in doc["roads"] if rd["kind"] == kind]
        for rd in rs:
            add(("line", rd["pts"], C[kind + "_out"], rd["w"] + 3))
        for rd in rs:
            add(("line", rd["pts"], C[kind], rd["w"]))

    if doc.get("plaza"):
        add(("poly", doc["plaza"], C["plaza"], C["plaza_out"], 2))

    if wall:
        for x, y in wall:
            add(("ellipse", x, y, 8.5, 8.5, C["tower"], C["wall_dark"], 2))
        for gx, gy, ang, rw in doc.get("gates", []):
            for sgn in (-1, 1):
                off = rw / 2 + 6
                tx, ty = gx + math.cos(ang) * off * sgn, gy + math.sin(ang) * off * sgn
                add(("poly", local_rect(tx, ty, ang, -5, 5, -7, 7), C["tower"],
                     C["wall_dark"], 2))

    for g in of("garden"):
        tag = "o%d" % g["id"]
        add(("poly", local_rect(g["cx"], g["cy"], g["ang"], -g["w"] / 2, g["w"] / 2,
                                -g["h"] / 2, g["h"] / 2), C["lawn"], None, 0), tag)
        ca, sa = math.cos(g["ang"]), math.sin(g["ang"])
        for bu, bv, br in g.get("bushes", []):
            bx, by = g["cx"] + ca * bu - sa * bv, g["cy"] + sa * bu + ca * bv
            add(("ellipse", bx, by, br, br, C["bush"], shade(C["bush"], 0.75), 1), tag)
        loop = rect_loop(g["cx"], g["cy"], g["ang"], -g["w"] / 2, g["w"] / 2,
                         -g["h"] / 2, g["h"] / 2, 6)
        ops.extend(wall_ops("brick", loop, tag))

    houses = of(*BUILDING_TYPES)
    trees = of("tree")
    if opts.get("shadows", 1):
        for h in houses:
            poly = house_parts(h)[0]
            add(("shadow_poly", [(x + 2.5, y + 2.5) for x, y in poly], 80), "o%d" % h["id"])
        for t in trees:
            add(("shadow_ellipse", t["x"] + 2, t["y"] + 2, t["r"], 60), "o%d" % t["id"])

    for h in houses:
        if h.get("yard"):
            ops.extend(wall_ops(h.get("yard_type", "stone"), yard_line(h), "o%d" % h["id"]))

    for w in of(*WALL_OBJ.keys()):
        ops.extend(wall_ops(WALL_OBJ[w["type"]], w["pts"], "o%d" % w["id"]))

    for h in houses:
        tag = "o%d" % h["id"]
        roof = tuple(h["roof"])
        poly, h1, h2, ridge = house_parts(h)
        add(("poly", h1, shade(roof, 1.08), None, 0), tag)
        add(("poly", h2, shade(roof, 0.86), None, 0), tag)
        add(("line", ridge, shade(roof, 0.65), 1), tag)
        add(("outline", poly, shade(roof, 0.5), 1), tag)
        cx, cy, a, w = h["cx"], h["cy"], h["ang"], h["w"]
        if h["type"] == "church":
            tx, ty = cx + math.cos(a) * (w / 2 - 5), cy + math.sin(a) * (w / 2 - 5)
            add(("poly", local_rect(tx, ty, a, -6, 6, -6, 6), shade(roof, 0.75),
                 shade(roof, 0.45), 1), tag)
            cl = local_rect(tx, ty, a, -3.5, 3.5, 0, 0)
            cw = local_rect(tx, ty, a, 0, 0, -3.5, 3.5)
            add(("line", [cl[0], cl[1]], (245, 235, 200), 1.6), tag)
            add(("line", [cw[0], cw[3]], (245, 235, 200), 1.6), tag)
        elif h["type"] == "townhall":
            add(("ellipse", cx, cy, 4.5, 4.5, (225, 200, 120), shade(roof, 0.45), 1), tag)

    for t in trees:
        col = tuple(t["col"])
        x, y, rad = t["x"], t["y"], t["r"]
        add(("ellipse", x, y, rad, rad, col, shade(col, 0.75), 1), "o%d" % t["id"])
        add(("ellipse", x - rad * 0.35, y - rad * 0.35, rad * 0.45, rad * 0.45,
             shade(col, 1.22), None, 0), "o%d" % t["id"])

    lamps = of("lamp")
    if opts.get("glow", 1):
        for l in lamps:
            add(("glow", l["x"], l["y"], 13, C["lamp_glow"], 210), "o%d" % l["id"])
    for l in lamps:
        add(("ellipse", l["x"], l["y"], 2.6, 2.6, C["lamp"], (70, 60, 35), 1), "o%d" % l["id"])

    if overlay:
        for op in build_overlay(doc):
            add(op, "ui")
    return ops


def doc_stats(doc):
    nb = len([o for o in doc["objects"] if o["type"] in BUILDING_TYPES])
    nl = len([o for o in doc["objects"] if o["type"] == "lamp"])
    pop = int(nb * doc.get("per_house", 4) / 10) * 10
    return nb, nl, pop


def build_overlay(doc):
    W, H = doc["width"], doc["height"]
    opts = doc.get("opts", {})
    ops = []
    panel, pout = C["panel"], C["panel_out"]
    town = doc["kind"] == "town"
    nb, nl, pop = doc_stats(doc)

    if opts.get("title", 1):
        if doc.get("source"):
            tail = "from %s" % to_ascii(doc["source"])
        else:
            tail = "seed %s" % doc.get("seed", "-")
        sub = "%s  |  %d buildings  |  pop. ~%d  |  %s" % (
            "Town" if town else "Village", nb, pop, tail)
        tw = max(text_width(doc["name"], 3), text_width(sub, 2))
        ops.append(("panel", 14, 14, 14 + tw + 28, 104, panel, pout))
        ops.append(("text", 28, 24, doc["name"], 3, C["text"]))
        ops.append(("text", 28, 70, sub, 2, C["text2"]))

    if opts.get("legend", 1):
        items = [("house", "House"), ("special", "Church / town hall")]
        if town and doc.get("wall"):
            items.append(("wall", "Town walls"))
        items += [("stone", "Stone wall"), ("brick", "Brick wall"), ("fence", "Wooden fence"),
                  ("lamp", "Street lamp"), ("main", "Main road"), ("street", "Street"),
                  ("dirt", "Dirt track"), ("field", "Field / pasture"), ("tree", "Tree / forest")]
        if [1 for ob in doc["objects"] if ob["type"] in ("pond", "stream")]:
            items.append(("water", "Water"))
        lx, ly = 14, H - 14 - 26 * len(items) - 44
        ops.append(("panel", lx, ly, lx + 300, H - 14, panel, pout))
        ops.append(("text", lx + 14, ly + 10, "Legend", 2, C["text"]))
        y = ly + 40
        for key, label in items:
            sx, sy = lx + 16, y + 9
            box = [(sx, sy - 7), (sx + 22, sy - 7), (sx + 22, sy + 7), (sx, sy + 7)]
            if key == "house":
                ops.append(("poly", box, C["roofs_town"][0], (80, 40, 30), 1))
            elif key == "special":
                ops.append(("poly", box, C["special_roof"], (50, 50, 60), 1))
            elif key == "wall":
                ops.append(("line", [(sx, sy), (sx + 20, sy)], C["wall_dark"], 8))
                ops.append(("line", [(sx, sy), (sx + 20, sy)], C["wall"], 5))
                ops.append(("ellipse", sx + 21, sy, 6, 6, C["tower"], C["wall_dark"], 1))
            elif key in ("stone", "brick", "fence"):
                for _t, wop in wall_ops(key, [(sx + 1, sy), (sx + 21, sy)], None):
                    if key == "fence" and wop[0] == "line":
                        wop = ("line", wop[1], wop[2], 2)
                    ops.append(wop)
            elif key == "lamp":
                ops.append(("glow", sx + 11, sy, 9, C["lamp_glow"], 200))
                ops.append(("ellipse", sx + 11, sy, 3, 3, C["lamp"], (70, 60, 35), 1))
            elif key in ("main", "street", "dirt"):
                wd = {"main": 9, "street": 7, "dirt": 5}[key]
                ops.append(("line", [(sx + 2, sy), (sx + 20, sy)], C[key + "_out"], wd + 3))
                ops.append(("line", [(sx + 2, sy), (sx + 20, sy)], C[key], wd))
            elif key == "field":
                ops.append(("poly", box, C["fields"][0], (150, 130, 80), 1))
                for k in range(sx + 4, sx + 22, 5):
                    ops.append(("line", [(k, sy - 6), (k, sy + 6)], shade(C["fields"][0], 0.85), 1))
            elif key == "tree":
                ops.append(("ellipse", sx + 11, sy, 8, 8, C["tree"][1], C["tree"][2], 1))
            elif key == "water":
                ops.append(("ellipse", sx + 11, sy, 11, 6, C["water"], C["water_out"], 1))
            ops.append(("text", sx + 36, y, label, 2, C["text"]))
            y += 26

    if opts.get("scalebar", 1):
        bx, by = W - 190, H - 40
        ops.append(("panel", bx - 14, by - 84, W - 14, H - 14, panel, pout))
        ops.append(("poly", [(bx, by), (bx + 50, by), (bx + 50, by + 6), (bx, by + 6)],
                    C["text"], None, 0))
        ops.append(("poly", [(bx + 50, by), (bx + 100, by), (bx + 100, by + 6), (bx + 50, by + 6)],
                    panel, C["text"], 1))
        ops.append(("text", bx - 4, by - 26, "0", 2, C["text"]))
        ops.append(("text", bx + 76, by - 26, "100 m", 2, C["text"]))
        nx, ny = W - 45, by - 44
        ops.append(("poly", [(nx, ny - 26), (nx - 9, ny + 4), (nx, ny - 2)], C["text"], None, 0))
        ops.append(("poly", [(nx, ny - 26), (nx + 9, ny + 4), (nx, ny - 2)], (150, 140, 120), None, 0))
        ops.append(("text", nx - 6, ny + 4, "N", 2, C["text"]))
    return ops


def scale_op(op, s):
    t = op[0]

    def P(pts):
        return [(x * s, y * s) for x, y in pts]

    if t == "bg":
        return op
    if t == "ellipse":
        return (t, op[1] * s, op[2] * s, op[3] * s, op[4] * s, op[5], op[6], op[7] * s)
    if t == "poly":
        return (t, P(op[1]), op[2], op[3], op[4] * s)
    if t in ("outline", "line"):
        return (t, P(op[1]), op[2], op[3] * s)
    if t == "shadow_poly":
        return (t, P(op[1]), op[2])
    if t == "shadow_ellipse":
        return (t, op[1] * s, op[2] * s, op[3] * s, op[4])
    if t == "glow":
        return (t, op[1] * s, op[2] * s, op[3] * s, op[4], op[5])
    if t == "panel":
        return (t, op[1] * s, op[2] * s, op[3] * s, op[4] * s, op[5], op[6])
    if t == "text":
        return (t, op[1] * s, op[2] * s, op[3], max(1, int(round(op[4] * s))), op[5])
    return op


def render_raster(doc, scale=1):
    W, H = int(doc["width"] * scale), int(doc["height"] * scale)
    rs = Raster(W, H, 3, C["grass"])
    for _tag, op in build_scene(doc):
        if scale != 1:
            op = scale_op(op, scale)
        t = op[0]
        if t == "bg":
            rs.buf = rs._col(op[1]) * (W * H)
        elif t == "ellipse":
            _, x, y, rx, ry, fill, out, ow = op
            if out and ow:
                rs.fill_ellipse(x, y, rx + ow / 2.0, ry + ow / 2.0, out)
                rs.fill_ellipse(x, y, rx - ow / 2.0, ry - ow / 2.0, fill)
            else:
                rs.fill_ellipse(x, y, rx, ry, fill)
        elif t == "poly":
            _, pts, fill, out, ow = op
            rs.fill_poly(pts, fill)
            if out and ow:
                rs.stroke(list(pts) + [pts[0]], ow, out, ow >= 2)
        elif t == "outline":
            _, pts, out, ow = op
            rs.stroke(list(pts) + [pts[0]], ow, out, False)
        elif t == "line":
            _, pts, col, w = op
            rs.stroke(pts, w, col, w >= 2)
        elif t == "shadow_poly":
            rs.blend_poly(op[1], (0, 0, 0), op[2])
        elif t == "shadow_ellipse":
            _, x, y, rr, a = op
            rs.blend_ellipse(x, y, rr, rr, (0, 0, 0), a)
        elif t == "glow":
            _, x, y, rr, col, a = op
            rs.glow(x, y, rr, col, a)
        elif t == "panel":
            _, x0, y0, x1, y1, fill, out = op
            rs.rect(x0, y0, x1, y1, out)
            rs.rect(x0 + 2 * scale, y0 + 2 * scale, x1 - 2 * scale, y1 - 2 * scale, fill)
        elif t == "text":
            _, x, y, txt, s, col = op
            raster_text(rs, x, y, txt, s, col)
    return rs


def _esc_xml(s):
    return to_unicode(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(doc):
    W, H = doc["width"], doc["height"]
    out = [u'<?xml version="1.0" encoding="UTF-8"?>\n',
           u'<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
           % (W, H, W, H),
           u'<title>%s</title>\n' % _esc_xml(doc["name"]),
           u'<defs><radialGradient id="glow"><stop offset="0" stop-color="%s" stop-opacity="1"/>'
           u'<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient></defs>\n'
           % (hexcol(C["lamp_glow"]), hexcol(C["lamp_glow"]))]

    def pts_s(pts):
        return u" ".join([u"%.1f,%.1f" % (x, y) for x, y in pts])

    cur = [None]
    for tag, op in build_scene(doc):
        if tag != cur[0]:
            if cur[0] is not None:
                out.append(u"</g>\n")
            if tag is not None:
                out.append(u'<g id="%s">' % tag)
            cur[0] = tag
        t = op[0]
        if t == "bg":
            out.append(u'<rect width="%d" height="%d" fill="%s"/>\n' % (W, H, hexcol(op[1])))
        elif t == "ellipse":
            _, x, y, rx, ry, fill, o, ow = op
            st = (u' stroke="%s" stroke-width="%.1f"' % (hexcol(o), ow)) if o and ow else u""
            out.append(u'<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s"%s/>\n'
                       % (x, y, rx, ry, hexcol(fill), st))
        elif t == "poly":
            _, pts, fill, o, ow = op
            st = (u' stroke="%s" stroke-width="%.1f"' % (hexcol(o), ow)) if o and ow else u""
            out.append(u'<polygon points="%s" fill="%s"%s/>\n' % (pts_s(pts), hexcol(fill), st))
        elif t == "outline":
            _, pts, o, ow = op
            out.append(u'<polygon points="%s" fill="none" stroke="%s" stroke-width="%.1f"/>\n'
                       % (pts_s(pts), hexcol(o), ow))
        elif t == "line":
            _, pts, col, w = op
            out.append(u'<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f" '
                       u'stroke-linecap="round" stroke-linejoin="round"/>\n'
                       % (pts_s(pts), hexcol(col), w))
        elif t == "shadow_poly":
            out.append(u'<polygon points="%s" fill="#000" fill-opacity="%.2f"/>\n'
                       % (pts_s(op[1]), op[2] / 255.0))
        elif t == "shadow_ellipse":
            _, x, y, rr, a = op
            out.append(u'<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#000" fill-opacity="%.2f"/>\n'
                       % (x, y, rr, a / 255.0))
        elif t == "glow":
            _, x, y, rr, col, a = op
            out.append(u'<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#glow)" opacity="%.2f"/>\n'
                       % (x, y, rr, a / 255.0))
        elif t == "panel":
            _, x0, y0, x1, y1, fill, o = op
            out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="8" fill="%s" '
                       u'fill-opacity="0.93" stroke="%s" stroke-width="2"/>\n'
                       % (x0, y0, x1 - x0, y1 - y0, hexcol(fill), hexcol(o)))
        elif t == "text":
            _, x, y, txt, s, col = op
            out.append(u'<text x="%.1f" y="%.1f" font-family="Arial, Helvetica, sans-serif" '
                       u'font-size="%.1f" font-weight="bold" fill="%s">%s</text>\n'
                       % (x, y + 7.5 * s, 10 * s, hexcol(col), _esc_xml(txt)))
    if cur[0] is not None:
        out.append(u"</g>\n")
    out.append(u"</svg>\n")
    return u"".join(out).encode("utf-8")


def render_eps(doc):
    W, H = doc["width"], doc["height"]
    grass = C["grass"]
    L = ["%!PS-Adobe-3.0 EPSF-3.0", "%%%%BoundingBox: 0 0 %d %d" % (W, H),
         "%%Title: " + to_ascii(doc["name"]), "%%EndComments",
         "/M {moveto} bind def /Lt {lineto} bind def",
         "1 setlinecap 1 setlinejoin",
         "0 %d translate 1 -1 scale" % H]

    def rgb(c):
        return "%.3f %.3f %.3f setrgbcolor" % (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)

    def path(pts, close):
        s = ["newpath %.1f %.1f M" % (pts[0][0], pts[0][1])]
        for x, y in pts[1:]:
            s.append("%.1f %.1f Lt" % (x, y))
        if close:
            s.append("closepath")
        return " ".join(s)

    def ell(x, y, rx, ry):
        return ("gsave %.1f %.1f translate %.2f %.2f scale newpath 0 0 1 0 360 arc closepath "
                "fill grestore" % (x, y, max(rx, 0.01), max(ry, 0.01)))

    for _tag, op in build_scene(doc):
        t = op[0]
        if t == "bg":
            L.append(rgb(op[1]) + " 0 0 %d %d rectfill" % (W, H))
        elif t == "ellipse":
            _, x, y, rx, ry, fill, o, ow = op
            if o and ow:
                L.append(rgb(o) + " " + ell(x, y, rx + ow / 2.0, ry + ow / 2.0))
                if rx > ow / 2.0 and ry > ow / 2.0:
                    L.append(rgb(fill) + " " + ell(x, y, rx - ow / 2.0, ry - ow / 2.0))
            else:
                L.append(rgb(fill) + " " + ell(x, y, rx, ry))
        elif t == "poly":
            _, pts, fill, o, ow = op
            L.append(rgb(fill) + " " + path(pts, True) + " fill")
            if o and ow:
                L.append(rgb(o) + " %.2f setlinewidth " % ow + path(pts, True) + " stroke")
        elif t == "outline":
            _, pts, o, ow = op
            L.append(rgb(o) + " %.2f setlinewidth " % ow + path(pts, True) + " stroke")
        elif t == "line":
            _, pts, col, w = op
            L.append(rgb(col) + " %.2f setlinewidth " % w + path(pts, False) + " stroke")
        elif t == "shadow_poly":
            L.append(rgb(mix(grass, (0, 0, 0), op[2] / 255.0 * 0.8)) + " " +
                     path(op[1], True) + " fill")
        elif t == "shadow_ellipse":
            _, x, y, rr, a = op
            L.append(rgb(mix(grass, (0, 0, 0), a / 255.0 * 0.8)) + " " + ell(x, y, rr, rr))
        elif t == "glow":
            pass
        elif t == "panel":
            _, x0, y0, x1, y1, fill, o = op
            L.append(rgb(o) + " %.1f %.1f %.1f %.1f rectfill" % (x0, y0, x1 - x0, y1 - y0))
            L.append(rgb(fill) + " %.1f %.1f %.1f %.1f rectfill" % (x0 + 2, y0 + 2,
                                                                     x1 - x0 - 4, y1 - y0 - 4))
        elif t == "text":
            _, x, y, txt, s, col = op
            txt = to_ascii(txt).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            L.append(rgb(col) + " /Helvetica-Bold findfont %.1f scalefont setfont "
                     "gsave %.1f %.1f translate 1 -1 scale 0 0 moveto (%s) show grestore"
                     % (10 * s, x, y + 7.5 * s, txt))
    L.append("showpage")
    L.append("%%EOF")
    return ("\n".join(L) + "\n").encode("ascii")


def _round_doc(o):
    if isinstance(o, float):
        return round(o, 2)
    if isinstance(o, dict):
        d = {}
        for k, v in o.items():
            d[k] = _round_doc(v)
        return d
    if isinstance(o, (list, tuple)):
        return [_round_doc(v) for v in o]
    return o


EXPORT_FORMATS = ["PNG", "BMP", "PPM", "SVG", "EPS", "JSON"]


def export_doc(doc, fmt, folder=SCRIPT_DIR, scale=1):
    base = "map_%s_%s_%s" % (doc["kind"], ascii_name(doc["name"]), doc.get("seed", "x"))
    fmts = EXPORT_FORMATS if fmt.upper() == "ALL" else [fmt.upper()]
    written = []
    raster = None
    for f in fmts:
        name = str(base + "." + f.lower())
        path = os.path.join(folder, name)
        if f in ("PNG", "BMP", "PPM"):
            if raster is None:
                raster = render_raster(doc, scale)
            if f == "PNG":
                raster.save_png(path)
            elif f == "BMP":
                raster.save_bmp(path)
            else:
                raster.save_ppm(path)
        elif f == "SVG":
            write_bytes(path, render_svg(doc))
        elif f == "EPS":
            write_bytes(path, render_eps(doc))
        elif f == "JSON":
            data = json.dumps(_round_doc(doc), indent=1)
            if PY3:
                data = data.encode("utf-8")
            write_bytes(path, data)
        else:
            raise ValueError("Unknown format: %s" % f)
        written.append(name)
    return written


def load_doc(path):
    f = open(path, "rb")
    try:
        data = f.read()
    finally:
        f.close()
    doc = json.loads(data.decode("utf-8"))
    if doc.get("format") != "mapgen":
        raise ValueError("This is not a map file made by this generator.")
    doc.setdefault("opts", {})
    for k in LOOK_KEYS:
        doc["opts"].setdefault(k, 1)
    doc["kind"] = str(doc["kind"])
    for o in doc["objects"]:
        o["type"] = str(o["type"])
    for rd in doc["roads"]:
        rd["kind"] = str(rd["kind"])
    return doc


def obj_move(o, dx, dy):
    if "pts" in o:
        o["pts"] = [[x + dx, y + dy] for x, y in o["pts"]]
    elif "cx" in o:
        o["cx"] += dx
        o["cy"] += dy
    else:
        o["x"] += dx
        o["y"] += dy


def can_rotate(o):
    return "ang" in o or "pts" in o


def obj_rotate(o, da):
    if "ang" in o:
        o["ang"] += da
        return True
    if "pts" in o:
        n = len(o["pts"])
        mx = sum([p[0] for p in o["pts"]]) / n
        my = sum([p[1] for p in o["pts"]]) / n
        ca, sa = math.cos(da), math.sin(da)
        o["pts"] = [[mx + (x - mx) * ca - (y - my) * sa, my + (x - mx) * sa + (y - my) * ca]
                    for x, y in o["pts"]]
        return True
    return False


def next_id(doc):
    return max([o["id"] for o in doc["objects"]] + [-1]) + 1


def nearest_road_angle(doc, x, y):
    return roads_angle(doc["roads"], x, y)


def new_wall_object(doc, kind, x0, y0, x1, y1):
    if math.hypot(x1 - x0, y1 - y0) < 4:
        a = nearest_road_angle(doc, x0, y0)
        x0, y0 = x0 - math.cos(a) * 15, y0 - math.sin(a) * 15
        x1, y1 = x0 + math.cos(a) * 30, y0 + math.sin(a) * 30
    return {"id": next_id(doc), "type": kind, "pts": [[x0, y0], [x1, y1]]}


def new_object(doc, kind, x, y):
    r = random.Random()
    oid = next_id(doc)
    if kind == "house":
        town = doc["kind"] == "town"
        return {"id": oid, "type": "house", "cx": x, "cy": y,
                "ang": nearest_road_angle(doc, x, y),
                "w": r.uniform(14, 20), "d": r.uniform(11, 15),
                "roof": r.choice(C["roofs_town"] if town else C["roofs_village"]),
                "yard": None}
    if kind == "lamp":
        return {"id": oid, "type": "lamp", "x": x, "y": y}
    if kind == "tree":
        return {"id": oid, "type": "tree", "x": x, "y": y, "r": r.uniform(4.5, 8),
                "col": r.choice(C["tree"])}
    raise ValueError(kind)


def _read_file(path):
    f = open(path, "rb")
    try:
        return bytearray(f.read())
    finally:
        f.close()


def _u16(d, i):
    return (d[i] << 8) | d[i + 1]


def _u32(d, i):
    return (d[i] << 24) | (d[i + 1] << 16) | (d[i + 2] << 8) | d[i + 3]


def _unfilter(ft, line, prev, bpp):
    n = len(line)
    if ft == 0:
        return
    if ft == 1:
        for i in range(bpp, n):
            line[i] = (line[i] + line[i - bpp]) & 255
    elif ft == 2:
        for i in range(n):
            line[i] = (line[i] + prev[i]) & 255
    elif ft == 3:
        for i in range(n):
            a = line[i - bpp] if i >= bpp else 0
            line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
    elif ft == 4:
        for i in range(n):
            if i >= bpp:
                a = line[i - bpp]
                c = prev[i - bpp]
            else:
                a = 0
                c = 0
            b = prev[i]
            p = a + b - c
            pa = abs(p - a)
            pb = abs(p - b)
            pc = abs(p - c)
            if pa <= pb and pa <= pc:
                pr = a
            elif pb <= pc:
                pr = b
            else:
                pr = c
            line[i] = (line[i] + pr) & 255
    else:
        raise ValueError("Broken PNG (filter %d)" % ft)


def _png_row_rgb(line, pw, ct, bd, plte):
    if bd == 16:
        line = bytearray([line[i] for i in range(0, len(line), 2)])
        bd = 8
    if bd < 8:
        mask = (1 << bd) - 1
        vals = bytearray(pw)
        for i in range(pw):
            bit = i * bd
            vals[i] = (line[bit >> 3] >> (8 - bd - (bit & 7))) & mask
        if ct == 0:
            vals = bytearray([v * 255 // mask for v in vals])
        line = vals
    out = bytearray(pw * 3)
    if ct == 2:
        out[:] = line[:pw * 3]
    elif ct == 0:
        for i in range(pw):
            v = line[i]
            j = i * 3
            out[j] = v
            out[j + 1] = v
            out[j + 2] = v
    elif ct == 3:
        for i in range(pw):
            k = line[i] * 3
            j = i * 3
            out[j] = plte[k]
            out[j + 1] = plte[k + 1]
            out[j + 2] = plte[k + 2]
    elif ct == 4:
        for i in range(pw):
            v = line[i * 2]
            a = line[i * 2 + 1]
            v = (v * a + 255 * (255 - a)) // 255
            j = i * 3
            out[j] = v
            out[j + 1] = v
            out[j + 2] = v
    elif ct == 6:
        for i in range(pw):
            k = i * 4
            a = line[k + 3]
            ia = 255 * (255 - a)
            j = i * 3
            out[j] = (line[k] * a + ia) // 255
            out[j + 1] = (line[k + 1] * a + ia) // 255
            out[j + 2] = (line[k + 2] * a + ia) // 255
    return out


def decode_png(data):
    if bytes(data[:8]) != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file")
    pos = 8
    idat = []
    plte = None
    w = h = bd = ct = il = None
    while pos + 8 <= len(data):
        ln = _u32(data, pos)
        typ = bytes(data[pos + 4:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h = _u32(body, 0), _u32(body, 4)
            bd, ct, il = body[8], body[9], body[12]
        elif typ == b"PLTE":
            plte = body
        elif typ == b"IDAT":
            idat.append(bytes(body))
        elif typ == b"IEND":
            break
    if w is None:
        raise ValueError("Broken PNG")
    if ct not in (0, 2, 3, 4, 6):
        raise ValueError("Unsupported PNG colour type")
    if ct == 3 and plte is None:
        raise ValueError("PNG palette missing")
    raw = bytearray(zlib.decompress(b"".join(idat)))
    chans = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    bits = chans * bd
    bpp = max(1, bits // 8)
    if il:
        passes = [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
                  (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
    else:
        passes = [(0, 0, 1, 1)]
    out = bytearray(w * h * 3)
    pos = 0
    for x0, y0, dx, dy in passes:
        pw = (w - x0 + dx - 1) // dx
        ph = (h - y0 + dy - 1) // dy
        if pw <= 0 or ph <= 0:
            continue
        stride = (pw * bits + 7) // 8
        prev = bytearray(stride)
        for r in range(ph):
            ft = raw[pos]
            line = raw[pos + 1:pos + 1 + stride]
            pos += 1 + stride
            _unfilter(ft, line, prev, bpp)
            prev = line
            rgb = _png_row_rgb(line, pw, ct, bd, plte)
            y = y0 + r * dy
            if dx == 1:
                o = y * w * 3
                out[o:o + w * 3] = rgb
            else:
                for i in range(pw):
                    o = (y * w + x0 + i * dx) * 3
                    out[o] = rgb[i * 3]
                    out[o + 1] = rgb[i * 3 + 1]
                    out[o + 2] = rgb[i * 3 + 2]
    return w, h, out


_ZZ = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48,
       41, 34, 27, 20, 13, 6, 7, 14, 21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15,
       23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]
_COS = [[(math.sqrt(0.5) if u == 0 else 1.0) * math.cos((2 * x + 1) * u * math.pi / 16) / 2
         for x in range(8)] for u in range(8)]
_COS_T = [[_COS[u][x] for u in range(8)] for x in range(8)]
_DC0 = _COS[0][0]


class _Bits(object):
    def __init__(self, data):
        self.d = data
        self.n = len(data)
        self.p = 0

    def huff(self, tbl):
        d, n, p = self.d, self.n, self.p
        code = 0
        ln = 0
        while ln < 16:
            i = p >> 3
            b = ((d[i] >> (7 - (p & 7))) & 1) if i < n else 1
            p += 1
            code = (code << 1) | b
            ln += 1
            s = tbl.get((ln << 16) | code)
            if s is not None:
                self.p = p
                return s
        raise ValueError("Broken JPEG data")

    def receive(self, s):
        d, n, p = self.d, self.n, self.p
        v = 0
        for _ in range(s):
            i = p >> 3
            b = ((d[i] >> (7 - (p & 7))) & 1) if i < n else 1
            p += 1
            v = (v << 1) | b
        self.p = p
        if s and v < (1 << (s - 1)):
            v -= (1 << s) - 1
        return v


def _build_huff(counts, symbols):
    tbl = {}
    code = 0
    k = 0
    for ln in range(1, 17):
        for _ in range(counts[ln - 1]):
            tbl[(ln << 16) | code] = symbols[k]
            k += 1
            code += 1
        code <<= 1
    return tbl


def _scan_segments(d, pos):
    segs = []
    cur = bytearray()
    n = len(d)
    while pos < n:
        j = d.find(b"\xff", pos)
        if j < 0:
            cur += d[pos:]
            pos = n
            break
        cur += d[pos:j]
        m = d[j + 1] if j + 1 < n else 0xD9
        if m == 0:
            cur.append(0xFF)
            pos = j + 2
        elif 0xD0 <= m <= 0xD7:
            segs.append(cur)
            cur = bytearray()
            pos = j + 2
        elif m == 0xFF:
            pos = j + 1
        else:
            pos = j
            break
    segs.append(cur)
    return segs, pos


def _idct_put(blk, plane, pw, ox, oy):
    rows = []
    for v in range(8):
        b = v * 8
        r = blk[b:b + 8]
        nz = [u for u in range(8) if r[u]]
        if not nz:
            continue
        if nz == [0]:
            c = r[0] * _DC0
            rows.append((v, [c] * 8))
        else:
            tmp = []
            for x in range(8):
                cx = _COS_T[x]
                s = 0.0
                for u in nz:
                    s += r[u] * cx[u]
                tmp.append(s)
            rows.append((v, tmp))
    for y in range(8):
        acc = [128.0] * 8
        cy = _COS_T[y]
        for v, tmp in rows:
            c = cy[v]
            for x in range(8):
                acc[x] += tmp[x] * c
        o = (oy + y) * pw + ox
        for x in range(8):
            val = int(acc[x] + 0.5)
            plane[o + x] = 0 if val < 0 else (255 if val > 255 else val)


def decode_jpeg(data):
    if data[0] != 0xFF or data[1] != 0xD8:
        raise ValueError("Not a JPEG file")
    pos = 2
    qt = {}
    hts = {}
    comps = []
    frame = None
    restart = 0
    adobe = None
    n = len(data)
    while pos < n:
        if data[pos] != 0xFF:
            pos += 1
            continue
        m = data[pos + 1]
        pos += 2
        if m == 0xFF:
            pos -= 1
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            continue
        if m == 0xD9:
            break
        ln = _u16(data, pos)
        seg = data[pos + 2:pos + ln]
        pos += ln
        if m == 0xDB:
            i = 0
            while i < len(seg):
                pq, tq = seg[i] >> 4, seg[i] & 15
                i += 1
                if pq:
                    q = [_u16(seg, i + 2 * k) for k in range(64)]
                    i += 128
                else:
                    q = [seg[i + k] for k in range(64)]
                    i += 64
                qt[tq] = q
        elif m == 0xC4:
            i = 0
            while i < len(seg):
                tc, th = seg[i] >> 4, seg[i] & 15
                counts = [seg[i + 1 + k] for k in range(16)]
                tot = sum(counts)
                syms = [seg[i + 17 + k] for k in range(tot)]
                hts[(tc, th)] = _build_huff(counts, syms)
                i += 17 + tot
        elif m in (0xC0, 0xC1):
            fh, fw, nc = _u16(seg, 1), _u16(seg, 3), seg[5]
            comps = []
            for k in range(nc):
                b = 6 + k * 3
                comps.append({"id": seg[b], "h": seg[b + 1] >> 4, "v": seg[b + 1] & 15,
                              "tq": seg[b + 2]})
            hmax = max([c["h"] for c in comps])
            vmax = max([c["v"] for c in comps])
            mcux = (fw + 8 * hmax - 1) // (8 * hmax)
            mcuy = (fh + 8 * vmax - 1) // (8 * vmax)
            for c in comps:
                c["pw"] = mcux * c["h"] * 8
                c["ph"] = mcuy * c["v"] * 8
                c["plane"] = bytearray(c["pw"] * c["ph"])
                c["bx"] = (((fw * c["h"] + hmax - 1) // hmax) + 7) // 8
                c["by"] = (((fh * c["v"] + vmax - 1) // vmax) + 7) // 8
            frame = (fw, fh, hmax, vmax, mcux, mcuy)
        elif 0xC2 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            raise ValueError("This JPEG type (progressive/lossless) is not supported. "
                             "Please save the picture as PNG.")
        elif m == 0xDD:
            restart = _u16(seg, 0)
        elif m == 0xEE:
            adobe = seg
        elif m == 0xDA:
            if frame is None:
                raise ValueError("Broken JPEG (no frame)")
            ns = seg[0]
            sc = []
            for k in range(ns):
                cid, tt = seg[1 + k * 2], seg[2 + k * 2]
                c = [cc for cc in comps if cc["id"] == cid][0]
                sc.append((c, hts.get((0, tt >> 4)), hts.get((1, tt & 15))))
            segs, pos = _scan_segments(data, pos)
            _decode_scan(frame, sc, segs, qt, restart)
    if frame is None:
        raise ValueError("Broken JPEG")
    fw, fh, hmax, vmax, mcux, mcuy = frame
    if len(comps) == 4:
        raise ValueError("CMYK JPEG is not supported. Please save the picture as PNG (RGB).")
    out = bytearray(fw * fh * 3)
    if len(comps) == 1:
        c = comps[0]
        pl, pw = c["plane"], c["pw"]
        for y in range(fh):
            o = y * fw * 3
            r = y * pw
            for x in range(fw):
                v = pl[r + x]
                out[o] = v
                out[o + 1] = v
                out[o + 2] = v
                o += 3
        return fw, fh, out
    cy, cb, cr = comps[0], comps[1], comps[2]
    maps = []
    for c in (cy, cb, cr):
        xs = [x * c["h"] // hmax for x in range(fw)]
        maps.append(xs)
    xy, xb, xr = maps
    py_, pb_, pr_ = cy["plane"], cb["plane"], cr["plane"]
    ycc = adobe is None or len(adobe) < 12 or adobe[11] != 0
    for y in range(fh):
        ry = (y * cy["v"] // vmax) * cy["pw"]
        rb = (y * cb["v"] // vmax) * cb["pw"]
        rr = (y * cr["v"] // vmax) * cr["pw"]
        o = y * fw * 3
        for x in range(fw):
            Y = py_[ry + xy[x]]
            Cb = pb_[rb + xb[x]]
            Cr = pr_[rr + xr[x]]
            if ycc:
                Cb -= 128
                Cr -= 128
                r = int(Y + 1.402 * Cr + 0.5)
                g = int(Y - 0.344136 * Cb - 0.714136 * Cr + 0.5)
                b = int(Y + 1.772 * Cb + 0.5)
            else:
                r, g, b = Y, Cb, Cr
            out[o] = 0 if r < 0 else (255 if r > 255 else r)
            out[o + 1] = 0 if g < 0 else (255 if g > 255 else g)
            out[o + 2] = 0 if b < 0 else (255 if b > 255 else b)
            o += 3
    return fw, fh, out


def _decode_scan(frame, sc, segs, qt, restart):
    fw, fh, hmax, vmax, mcux, mcuy = frame
    zz = _ZZ
    blk = [0] * 64
    if len(sc) == 1:
        c = sc[0][0]
        units = [(c, bx, by) for by in range(c["by"]) for bx in range(c["bx"])]
        groups = [[u] for u in units]
    else:
        groups = []
        for my in range(mcuy):
            for mx in range(mcux):
                g = []
                for c, _d, _a in sc:
                    for v in range(c["v"]):
                        for h in range(c["h"]):
                            g.append((c, mx * c["h"] + h, my * c["v"] + v))
                groups.append(g)
    tables = {}
    for c, dc, ac in sc:
        tables[c["id"]] = (dc, ac, qt[c["tq"]])
    seg_i = 0
    rd = _Bits(segs[0])
    pred = {}
    for c, _d, _a in sc:
        pred[c["id"]] = 0
    for gi in range(len(groups)):
        if restart and gi and gi % restart == 0:
            seg_i += 1
            rd = _Bits(segs[seg_i] if seg_i < len(segs) else bytearray())
            for k in pred:
                pred[k] = 0
        for c, bx, by in groups[gi]:
            dc, ac, q = tables[c["id"]]
            for k in range(64):
                blk[k] = 0
            t = rd.huff(dc)
            diff = rd.receive(t) if t else 0
            p = pred[c["id"]] + diff
            pred[c["id"]] = p
            blk[0] = p * q[0]
            k = 1
            while k < 64:
                rs = rd.huff(ac)
                r, s = rs >> 4, rs & 15
                if s == 0:
                    if r == 15:
                        k += 16
                        continue
                    break
                k += r
                if k > 63:
                    break
                blk[zz[k]] = rd.receive(s) * q[k]
                k += 1
            _idct_put(blk, c["plane"], c["pw"], bx * 8, by * 8)


def load_image(path):
    data = _read_file(path)
    if data[:8] == bytearray(b"\x89PNG\r\n\x1a\n"):
        return decode_png(data)
    if data[:2] == bytearray(b"\xff\xd8"):
        return decode_jpeg(data)
    raise ValueError("Only PNG and JPG pictures are supported.")


IMPORT_DEFAULTS = {
    "scale": 0, "style": "auto",
    "houses": 1, "roads": 1, "tracks": 1, "water": 1, "areas": 1,
    "fields": 1, "lamps": 1, "garden_trees": 1, "name": "",
}

BG, HOUSE, ROAD, HWY, WATER, AREA, DARK, GRAY, FOREST, FIELD, WHITE, CONTOUR = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11


def _classify_rgb(r, g, b):
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 40:
        return DARK
    if mx < 160 and (mx - mn) < 0.5 * mx:
        if (b > r + 12 and b >= g) or (r > 40 and b >= 0.87 * r and mx > 90):
            return WATER
        return DARK
    d = mx - mn
    s = d / float(mx)
    if mx < 190 and s < 0.24:
        if b >= 0.87 * r:
            return WATER
        return GRAY
    if s < 0.07:
        return BG
    if mx == r:
        h = 60.0 * (((g - b) / float(d)) % 6)
    elif mx == g:
        h = 60.0 * ((b - r) / float(d) + 2)
    else:
        h = 60.0 * ((r - g) / float(d) + 4)
    if 15 <= h < 31 and s >= 0.42:
        return HWY
    if 20 <= h < 43 and s >= 0.2 and mx >= 175:
        return HOUSE
    if 65 <= h <= 260:
        return WATER if (mx > 150 or b > r + 12) else BG
    if 42 <= h < 65:
        if s >= 0.45:
            return ROAD
        if s >= 0.22:
            return AREA
    return BG


def _classify_modern(r, g, b):
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 40:
        return DARK
    d = mx - mn
    s = d / float(mx)
    if s < 0.06:
        if mx >= 245:
            return WHITE
        if mx < 135:
            return DARK
        return HOUSE
    if mx == r:
        h = 60.0 * (((g - b) / float(d)) % 6)
    elif mx == g:
        h = 60.0 * ((b - r) / float(d) + 2)
    else:
        h = 60.0 * ((r - g) / float(d) + 4)
    if mx < 120 and s < 0.3:
        return DARK
    if 12 <= h < 40 and s >= 0.55 and mx >= 200:
        return HWY
    if 10 <= h < 45 and 0.12 <= s < 0.55 and mx >= 170:
        return CONTOUR
    if 40 <= h < 62 and s >= 0.55:
        return ROAD
    if 40 <= h < 60 and 0.15 <= s < 0.5 and mx >= 240:
        return FIELD
    if 60 <= h < 85 and 0.1 <= s < 0.4:
        return AREA
    if 85 <= h < 165 and s >= 0.08:
        return FOREST
    if 170 <= h <= 250 and s >= 0.15:
        return WATER
    return BG


def detect_style(rgb):
    n = 0
    white = 0
    for i in range(0, len(rgb) - 2, 3 * 97):
        n += 1
        if rgb[i] >= 248 and rgb[i + 1] >= 248 and rgb[i + 2] >= 248:
            white += 1
    return "modern" if n and white / float(n) > 0.2 else "old"


def classify_image(w, h, rgb, modern=False):
    fn = _classify_modern if modern else _classify_rgb
    lab = bytearray(w * h)
    cache = {}
    j = 0
    for i in range(0, w * h * 3, 3):
        key = (rgb[i] << 16) | (rgb[i + 1] << 8) | rgb[i + 2]
        c = cache.get(key)
        if c is None:
            c = fn(rgb[i], rgb[i + 1], rgb[i + 2])
            cache[key] = c
        lab[j] = c
        j += 1
    return lab


def downscale(w, h, rgb, f):
    nw, nh = w // f, h // f
    out = bytearray(nw * nh * 3)
    ff = f * f
    for y in range(nh):
        for x in range(nw):
            sr = sg = sb = 0
            for yy in range(y * f, y * f + f):
                o = (yy * w + x * f) * 3
                for k in range(f):
                    sr += rgb[o]
                    sg += rgb[o + 1]
                    sb += rgb[o + 2]
                    o += 3
            q = (y * nw + x) * 3
            out[q] = sr // ff
            out[q + 1] = sg // ff
            out[q + 2] = sb // ff
    return nw, nh, out


def _mask(lab, cls):
    if isinstance(cls, int):
        cls = (cls,)
    out = bytearray(len(lab))
    for i in range(len(lab)):
        if lab[i] in cls:
            out[i] = 1
    return out


def _to_rows(mask, w, h):
    rows = []
    for y in range(h):
        s = bytes(mask[y * w:(y + 1) * w]).replace(b"\x00", b"0").replace(b"\x01", b"1")
        rows.append(int(s[::-1], 2) if s else 0)
    return rows


def _from_rows(rows, w):
    out = bytearray()
    for v in rows:
        s = bin(v)[2:].zfill(w)[::-1][:w]
        if PY3:
            s = s.encode("ascii")
        out += bytearray(s.replace(b"0", b"\x00").replace(b"1", b"\x01"))
    return out


def _dilate(rows, w, r):
    full = (1 << w) - 1
    n = len(rows)
    for _ in range(r):
        hr = [(v | (v << 1) | (v >> 1)) & full for v in rows]
        rows = [hr[i] | (hr[i - 1] if i > 0 else 0) | (hr[i + 1] if i + 1 < n else 0)
                for i in range(n)]
    return rows


def _erode(rows, w, r):
    full = (1 << w) - 1
    n = len(rows)
    for _ in range(r):
        hr = [v & (v << 1) & (v >> 1) & full for v in rows]
        rows = [hr[i] & (hr[i - 1] if i > 0 else 0) & (hr[i + 1] if i + 1 < n else 0)
                for i in range(n)]
    return rows


def _components(mask, w, h, min_size=1):
    m = bytearray(mask)
    comps = []
    offs = (-w - 1, -w, -w + 1, -1, 1, w - 1, w, w + 1)
    n = w * h
    start = m.find(b"\x01")
    while start >= 0:
        stack = [start]
        m[start] = 0
        comp = []
        while stack:
            i = stack.pop()
            comp.append(i)
            x = i % w
            for o in offs:
                j = i + o
                if 0 <= j < n and m[j]:
                    jx = j % w
                    if jx - x > 1 or x - jx > 1:
                        continue
                    m[j] = 0
                    stack.append(j)
        if len(comp) >= min_size:
            comps.append(comp)
        start = m.find(b"\x01", start)
    return comps


def _clear_border(m, w, h):
    for x in range(w):
        m[x] = 0
        m[(h - 1) * w + x] = 0
    for y in range(h):
        m[y * w] = 0
        m[y * w + w - 1] = 0


def _thin(m, pts, w):
    m = bytearray(m)
    pts = [i for i in pts if m[i]]
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            rm = []
            for i in pts:
                if not m[i]:
                    continue
                p2, p3, p4 = m[i - w], m[i - w + 1], m[i + 1]
                p5, p6, p7 = m[i + w + 1], m[i + w], m[i + w - 1]
                p8, p9 = m[i - 1], m[i - w - 1]
                b = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
                if b < 2 or b > 6:
                    continue
                a = ((not p2 and p3) + (not p3 and p4) + (not p4 and p5) + (not p5 and p6) +
                     (not p6 and p7) + (not p7 and p8) + (not p8 and p9) + (not p9 and p2))
                if a != 1:
                    continue
                if step == 0:
                    if (p2 and p4 and p6) or (p4 and p6 and p8):
                        continue
                else:
                    if (p2 and p4 and p8) or (p2 and p6 and p8):
                        continue
                rm.append(i)
            for i in rm:
                m[i] = 0
            if rm:
                changed = True
        pts = [i for i in pts if m[i]]
    return m, pts


def _trace(m, pts, w):
    offs = (-w, 1, w, -1, -w - 1, -w + 1, w + 1, w - 1)
    deg = {}
    for i in pts:
        c = 0
        for o in offs:
            if m[i + o]:
                c += 1
        deg[i] = c
    nodes = set([i for i in pts if deg[i] != 2])
    used = set()
    done_pairs = set()
    paths = []

    def walk(a, b):
        path = [a, b]
        prev, cur = a, b
        while cur not in nodes:
            used.add(cur)
            nxt = None
            for o in offs:
                j = cur + o
                if m[j] and j != prev and j not in used and (j in nodes or j not in path):
                    if j in nodes and j == a and len(path) < 3:
                        continue
                    nxt = j
                    break
            if nxt is None:
                break
            prev, cur = cur, nxt
            path.append(cur)
        return path

    for a in nodes:
        for o in offs:
            b = a + o
            if not m[b]:
                continue
            if b in nodes:
                key = (min(a, b), max(a, b))
                if key not in done_pairs:
                    done_pairs.add(key)
                    paths.append([a, b])
            elif b not in used:
                paths.append(walk(a, b))
    for i in pts:
        if i not in nodes and i not in used:
            nodes.add(i)
            for o in offs:
                b = i + o
                if m[b] and b not in used and b not in nodes:
                    paths.append(walk(i, b))
                    break
            nodes.discard(i)
    out = []
    for path in paths:
        if len(path) >= 2:
            spur = deg.get(path[0], 2) <= 1 or deg.get(path[-1], 2) <= 1
            out.append(([(p % w, p // w) for p in path], spur))
    return out


def _simplify(pts, eps):
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / L
            if d > best:
                best, bi = d, i
        if best > eps:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [pts[i] for i in range(len(pts)) if keep[i]]


def _smooth(pts):
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        out.append((ax * 0.75 + bx * 0.25, ay * 0.75 + by * 0.25))
        out.append((ax * 0.25 + bx * 0.75, ay * 0.25 + by * 0.75))
    out.append(pts[-1])
    return out


def _plen(pts):
    return sum([math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])])


def _lines_from_mask(mask, w, h, min_comp, min_len, close=0, thicken=0):
    rows = _to_rows(mask, w, h)
    if thicken:
        rows = _dilate(rows, w, thicken)
    if close:
        rows = _erode(_dilate(rows, w, close), w, close)
    m = _from_rows(rows, w)
    _clear_border(m, w, h)
    out = []
    for comp in _components(m, w, h, min_comp):
        sk, pts = _thin(m, comp, w)
        for path, spur in _trace(sk, pts, w):
            if _plen(path) >= (min_len if spur else 2):
                out.append(_simplify(path, 1.2))
    return out


def _house_from_comp(comp, w):
    n = len(comp)
    xs = [i % w for i in comp]
    ys = [i // w for i in comp]
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum([(x - mx) ** 2 for x in xs]) / n
    syy = sum([(y - my) ** 2 for y in ys]) / n
    sxy = sum([(xs[k] - mx) * (ys[k] - my) for k in range(n)]) / n
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ca, sa = math.cos(ang), math.sin(ang)
    us = [(xs[k] - mx) * ca + (ys[k] - my) * sa for k in range(n)]
    vs = [-(xs[k] - mx) * sa + (ys[k] - my) * ca for k in range(n)]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    L, D = u1 - u0 + 1, v1 - v0 + 1
    cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    cx = mx + cu * ca - cv * sa
    cy = my + cu * sa + cv * ca
    return cx + 0.5, cy + 0.5, ang, L, D, n / float(L * D)


def _max_rect(grid, rows, cols):
    best = (0, 0, 0, 0, 0)
    hts = [0] * (cols + 1)
    for r in range(rows):
        g = grid[r]
        for c in range(cols):
            hts[c] = hts[c] + 1 if g[c] else 0
        stack = []
        for c in range(cols + 1):
            hc = hts[c] if c < cols else 0
            start = c
            while stack and stack[-1][1] >= hc:
                sc, sh = stack.pop()
                a = sh * (c - sc)
                if a > best[0]:
                    best = (a, r - sh + 1, r, sc, c - 1)
                start = sc
            stack.append((start, hc))
    return best


def _rect_cover(comp, w, max_rects=6, min_area=8):
    n = len(comp)
    xs = [i % w for i in comp]
    ys = [i // w for i in comp]
    mx = sum(xs) / float(n)
    my = sum(ys) / float(n)
    sxx = sum([(x - mx) ** 2 for x in xs]) / n
    syy = sum([(y - my) ** 2 for y in ys]) / n
    sxy = sum([(xs[k] - mx) * (ys[k] - my) for k in range(n)]) / n
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ca, sa = math.cos(ang), math.sin(ang)
    us = [int(round((xs[k] - mx) * ca + (ys[k] - my) * sa)) for k in range(n)]
    vs = [int(round(-(xs[k] - mx) * sa + (ys[k] - my) * ca)) for k in range(n)]
    u0, v0 = min(us), min(vs)
    cols, rows = max(us) - u0 + 1, max(vs) - v0 + 1
    grid = [[0] * cols for _ in range(rows)]
    for k in range(n):
        grid[vs[k] - v0][us[k] - u0] = 1
    for r in range(rows):
        for c in range(cols):
            if not grid[r][c]:
                if 0 < c < cols - 1 and grid[r][c - 1] and grid[r][c + 1]:
                    grid[r][c] = 1
                elif 0 < r < rows - 1 and grid[r - 1][c] and grid[r + 1][c]:
                    grid[r][c] = 1
    out = []
    for _ in range(max_rects):
        a, r0, r1, c0, c1 = _max_rect(grid, rows, cols)
        if a < min_area:
            break
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = 0
        L, D = c1 - c0 + 1, r1 - r0 + 1
        u = (c0 + c1) / 2.0 + u0
        v = (r0 + r1) / 2.0 + v0
        out.append((mx + u * ca - v * sa, my + u * sa + v * ca, ang, L, D))
    return out


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy), qx, qy


def _angle_between(ax, ay, bx, by):
    la = math.hypot(ax, ay)
    lb = math.hypot(bx, by)
    if la < 1e-9 or lb < 1e-9:
        return math.pi
    c = (ax * bx + ay * by) / (la * lb)
    return math.acos(max(-1.0, min(1.0, c)))


def _resample(pts, step):
    out = [pts[0]]
    carry = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        t = step - carry
        while t < L:
            out.append((ax + (bx - ax) * t / L, ay + (by - ay) * t / L))
            t += step
        carry = L - (t - step)
    if math.hypot(out[-1][0] - pts[-1][0], out[-1][1] - pts[-1][1]) > 0.5:
        out.append(pts[-1])
    else:
        out[-1] = pts[-1]
    return out


def _smooth_line(pts, step=2.5, win=2, eps=0.6):
    if len(pts) < 3 or _plen(pts) < 6:
        return [tuple(p) for p in pts]
    r = _resample(pts, step)
    n = len(r)
    out = [r[0]]
    for i in range(1, n - 1):
        k = min(win, i, n - 1 - i)
        sx = sy = 0.0
        for j in range(i - k, i + k + 1):
            sx += r[j][0]
            sy += r[j][1]
        out.append((sx / (2 * k + 1), sy / (2 * k + 1)))
    out.append(r[-1])
    return _simplify(out, eps)


def _network(paths, gap=14.0, snap=8.0, min_len=20.0, spur=10.0, anchors=None, strict=False):
    paths = [[(float(x), float(y)) for x, y in p] for p in paths if len(p) >= 2]
    if not paths:
        return []
    cell = 6.0
    grid = {}
    nodes = []
    edges = []

    def node_for(x, y):
        gx, gy = int(x // cell), int(y // cell)
        best = None
        for ix in (gx - 1, gx, gx + 1):
            for iy in (gy - 1, gy, gy + 1):
                for ni in grid.get((ix, iy), ()):
                    nx, ny, c = nodes[ni]
                    d = math.hypot(nx - x, ny - y)
                    if d <= 2.5 and (best is None or d < best[0]):
                        best = (d, ni)
        if best:
            ni = best[1]
            nx, ny, c = nodes[ni]
            nodes[ni] = ((nx * c + x) / (c + 1), (ny * c + y) / (c + 1), c + 1)
            return ni
        nodes.append((x, y, 1))
        grid.setdefault((gx, gy), []).append(len(nodes) - 1)
        return len(nodes) - 1

    for p in paths:
        a = node_for(p[0][0], p[0][1])
        b = node_for(p[-1][0], p[-1][1])
        if a == b and _plen(p) < 8:
            continue
        edges.append([a, b, p, True])

    def degrees():
        deg = [0] * len(nodes)
        for e in edges:
            if e[3]:
                deg[e[0]] += 1
                deg[e[1]] += 1
        return deg

    for _ in range(3):
        deg = degrees()
        changed = False
        for e in edges:
            if not e[3]:
                continue
            a, b = e[0], e[1]
            if ((deg[a] == 1 and deg[b] >= 3) or (deg[b] == 1 and deg[a] >= 3)) and \
                    _plen(e[2]) < spur:
                e[3] = False
                changed = True
        if not changed:
            break
    edges = [e for e in edges if e[3]]
    for e in edges:
        e[2] = [(nodes[e[0]][0], nodes[e[0]][1])] + e[2][1:-1] + [(nodes[e[1]][0], nodes[e[1]][1])]

    deg = degrees()

    def outward(ni):
        for e in edges:
            if e[0] == ni:
                p = e[2]
            elif e[1] == ni:
                p = e[2][::-1]
            else:
                continue
            x0, y0 = p[0]
            acc = 0.0
            qx, qy = p[-1]
            for (ax, ay), (bx, by) in zip(p, p[1:]):
                acc += math.hypot(bx - ax, by - ay)
                if acc >= 7:
                    qx, qy = bx, by
                    break
            return x0 - qx, y0 - qy
        return 0.0, 0.0

    segs = []
    for e in edges:
        for (ax, ay), (bx, by) in zip(e[2], e[2][1:]):
            segs.append((ax, ay, bx, by, id(e)))
    for an in (anchors or []):
        for (ax, ay), (bx, by) in zip(an, an[1:]):
            segs.append((ax, ay, bx, by, -1))
    sgrid = {}
    for si, (ax, ay, bx, by, _o) in enumerate(segs):
        for ix in range(int(min(ax, bx) // 16) - 1, int(max(ax, bx) // 16) + 2):
            for iy in range(int(min(ay, by) // 16) - 1, int(max(ay, by) // 16) + 2):
                sgrid.setdefault((ix, iy), []).append(si)

    dead = [i for i in range(len(nodes)) if deg[i] == 1]
    used = set()
    new_edges = []
    for a in dead:
        if a in used:
            continue
        ax, ay = nodes[a][0], nodes[a][1]
        ox, oy = outward(a)
        best = None
        for b in dead:
            if b == a or b in used:
                continue
            bx, by = nodes[b][0], nodes[b][1]
            d = math.hypot(bx - ax, by - ay)
            if d > gap or d < 0.5:
                continue
            same = False
            for e in edges:
                if (e[0] == a and e[1] == b) or (e[0] == b and e[1] == a):
                    same = True
                    break
            if same:
                continue
            t1 = _angle_between(ox, oy, bx - ax, by - ay)
            obx, oby = outward(b)
            t2 = _angle_between(obx, oby, ax - bx, ay - by)
            if t1 > 0.9 or t2 > 1.2:
                continue
            score = d * (1 + t1 + 0.5 * t2)
            if best is None or score < best[0]:
                best = (score, b, bx, by)
        if best:
            used.add(a)
            used.add(best[1])
            new_edges.append([a, best[1], [(ax, ay), (best[2], best[3])], True])
            continue
        own = set([id(e) for e in edges if e[0] == a or e[1] == a])
        cand = None
        gx, gy = int(ax // 16), int(ay // 16)
        seen = set()
        for ix in (gx - 1, gx, gx + 1):
            for iy in (gy - 1, gy, gy + 1):
                for si in sgrid.get((ix, iy), ()):
                    if si in seen:
                        continue
                    seen.add(si)
                    sx0, sy0, sx1, sy1, owner = segs[si]
                    if owner in own:
                        continue
                    d, qx, qy = _seg_dist(ax, ay, sx0, sy0, sx1, sy1)
                    if d > snap or d < 0.3:
                        continue
                    if _angle_between(ox, oy, qx - ax, qy - ay) > 1.0:
                        continue
                    if cand is None or d < cand[0]:
                        cand = (d, qx, qy)
        if cand:
            used.add(a)
            new_edges.append([a, -1, [(ax, ay), (cand[1], cand[2])], True])
    edges.extend(new_edges)

    adj = {}
    for k, e in enumerate(edges):
        adj.setdefault(e[0], []).append(k)
        if e[1] >= 0:
            adj.setdefault(e[1], []).append(k)
    seen = [False] * len(edges)
    lines = []
    for k in range(len(edges)):
        if seen[k]:
            continue
        seen[k] = True
        a, b, p = edges[k][0], edges[k][1], list(edges[k][2])
        for direction in (0, 1):
            while True:
                end = b if direction == 0 else a
                if end < 0 or len(adj.get(end, [])) != 2:
                    break
                nxt = [j for j in adj[end] if not seen[j]]
                if not nxt:
                    break
                j = nxt[0]
                seen[j] = True
                ea, eb, ep = edges[j][0], edges[j][1], list(edges[j][2])
                if ea != end:
                    ea, eb, ep = eb, ea, ep[::-1]
                if direction == 0:
                    p = p + ep[1:]
                    b = eb
                else:
                    p = ep[::-1][:-1] + p
                    a = eb
        lines.append((a, b, p))
    deg2 = {}
    for e in edges:
        deg2[e[0]] = deg2.get(e[0], 0) + 1
        if e[1] >= 0:
            deg2[e[1]] = deg2.get(e[1], 0) + 1
    out = []
    for a, b, p in lines:
        L = _plen(p)
        connected = deg2.get(a, 0) >= 3 or (b >= 0 and deg2.get(b, 0) >= 3) or b < 0
        if L < min_len and (strict or not (connected and L >= 4)):
            continue
        out.append(_smooth_line(p))
    return out


def _dash_info(comp, w):
    n = len(comp)
    xs = [i % w for i in comp]
    ys = [i // w for i in comp]
    mx = sum(xs) / float(n)
    my = sum(ys) / float(n)
    sxx = sum([(x - mx) ** 2 for x in xs]) / n
    syy = sum([(y - my) ** 2 for y in ys]) / n
    sxy = sum([(xs[k] - mx) * (ys[k] - my) for k in range(n)]) / n
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ca, sa = math.cos(ang), math.sin(ang)
    us = [(xs[k] - mx) * ca + (ys[k] - my) * sa for k in range(n)]
    vs = [-(xs[k] - mx) * sa + (ys[k] - my) * ca for k in range(n)]
    u0, u1 = min(us), max(us)
    L = u1 - u0 + 1
    D = max(vs) - min(vs) + 1
    return (mx + u0 * ca, my + u0 * sa), (mx + u1 * ca, my + u1 * sa), ang, L, D


def _chain_dashes(dashes, link=16.0, max_turn=0.55):
    ends = []
    for di, (p0, p1, ang, L) in enumerate(dashes):
        ends.append((p0[0], p0[1], di, 0))
        ends.append((p1[0], p1[1], di, 1))
    grid = {}
    cell = link * 1.7
    for ei, (x, y, di, side) in enumerate(ends):
        grid.setdefault((int(x // cell), int(y // cell)), []).append(ei)
    links = {}
    cands = []
    for ei, (x, y, di, side) in enumerate(ends):
        p0, p1, ang, L = dashes[di]
        if side == 1:
            ox, oy = p1[0] - p0[0], p1[1] - p0[1]
        else:
            ox, oy = p0[0] - p1[0], p0[1] - p1[1]
        gx, gy = int(x // cell), int(y // cell)
        for ix in (gx - 1, gx, gx + 1):
            for iy in (gy - 1, gy, gy + 1):
                for ej in grid.get((ix, iy), ()):
                    x2, y2, dj, side2 = ends[ej]
                    if dj == di:
                        continue
                    d = math.hypot(x2 - x, y2 - y)
                    if d > link * 1.7 or d < 1.0:
                        continue
                    lim = max_turn if d <= link else 0.3
                    if _angle_between(ox, oy, x2 - x, y2 - y) > lim:
                        continue
                    q0, q1, ang2, L2 = dashes[dj]
                    if side2 == 0:
                        ox2, oy2 = q1[0] - q0[0], q1[1] - q0[1]
                    else:
                        ox2, oy2 = q0[0] - q1[0], q0[1] - q1[1]
                    if _angle_between(ox, oy, ox2, oy2) > lim:
                        continue
                    cands.append((d, ei, ej))
    cands.sort()
    for d, ei, ej in cands:
        if ei in links or ej in links:
            continue
        links[ei] = ej
        links[ej] = ei
    chains = []
    seen = set()
    for di in range(len(dashes)):
        if di in seen:
            continue
        e0, e1 = di * 2, di * 2 + 1
        if e0 in links and e1 in links:
            continue
        start_end = e1 if e0 in links else e0
        cur = di
        enter = start_end
        pts = []
        count = 0
        while True:
            seen.add(cur)
            count += 1
            other = cur * 2 + (1 - (enter % 2))
            pts.append((ends[enter][0], ends[enter][1]))
            pts.append((ends[other][0], ends[other][1]))
            nxt = links.get(other)
            if nxt is None or ends[nxt][2] in seen:
                break
            enter = nxt
            cur = ends[nxt][2]
        chains.append((count, pts))
    return chains


def _remove_grid(lab, w, h):
    bd = bytes(bytearray([DARK]))
    bg = bytes(bytearray([GRAY]))
    rows = []
    for y in range(h):
        row = bytes(lab[y * w:(y + 1) * w])
        rows.append(row.count(bd) + row.count(bg))
    cols = [0] * w
    for y in range(h):
        base = y * w
        for x in range(w):
            if lab[base + x] == DARK or lab[base + x] == GRAY:
                cols[x] += 1

    def peaks(cnt, n, length):
        out = []
        for i in range(n):
            c = cnt[i]
            if c < 0.15 * length:
                continue
            near = [cnt[j] for j in range(i - 10, i + 11) if 0 <= j < n and abs(j - i) >= 4]
            avg = sum(near) / float(len(near)) if near else 0
            if c >= 3 * avg + 0.05 * length:
                out.append(i)
        return out

    for y in peaks(rows, h, w):
        for yy in (y - 1, y, y + 1):
            if 0 <= yy < h:
                for x in range(w):
                    if lab[yy * w + x] == DARK or lab[yy * w + x] == GRAY:
                        lab[yy * w + x] = BG
    for x in peaks(cols, w, h):
        for xx in (x - 1, x, x + 1):
            if 0 <= xx < w:
                for y in range(h):
                    if lab[y * w + xx] == DARK or lab[y * w + xx] == GRAY:
                        lab[y * w + xx] = BG


def import_image(path, opts=None, progress=None):
    o = dict(IMPORT_DEFAULTS)
    if opts:
        o.update(opts)

    def say(t):
        if progress:
            progress(t)

    say("Reading picture...")
    w, h, rgb = load_image(path)
    f = 1
    while max(w, h) // f > 1800:
        f += 1
    if f > 1:
        say("Shrinking picture...")
        w, h, rgb = downscale(w, h, rgb, f)
    s = float(o["scale"]) or min(3.0, max(1.0, 2400.0 / max(w, h)))
    W, H = int(w * s), int(h * s)
    style = o.get("style", "auto")
    if style not in ("old", "modern"):
        style = detect_style(rgb)
    modern = style == "modern"
    say("Recognising colours (%s map)..." % style)
    lab = classify_image(w, h, rgb, modern)
    rgb = None
    if not modern:
        say("Removing map grid...")
        _remove_grid(lab, w, h)
    rnd = random.Random(w * 7919 + h)

    def M(x, y):
        return (x + 0.5) * s, (y + 0.5) * s

    road_m = _mask(lab, ROAD)
    hwy_m = _mask(lab, HWY)
    house_m = _mask(lab, HOUSE)
    area_m = _mask(lab, AREA)
    dark_m = _mask(lab, DARK)
    objs = []

    def add(obj):
        obj["id"] = len(objs)
        objs.append(obj)

    say("Finding built-up areas and forests...")
    arows = _to_rows(area_m, w, h)
    arows = _erode(_dilate(arows, w, 3), w, 3)
    arows = _dilate(_erode(arows, w, 2 if modern else 4), w, 2 if modern else 4)
    am = _from_rows(arows, w)
    _clear_border(am, w, h)
    area_comps = [(c, "garden" if modern else None) for c in _components(am, w, h, 250)]
    near_area = _from_rows(_dilate(arows, w, 6), w)
    if modern:
        frows = _to_rows(_mask(lab, FOREST), w, h)
        frows = _dilate(_erode(_erode(_dilate(frows, w, 3), w, 3), w, 2), w, 2)
        fm = _from_rows(frows, w)
        _clear_border(fm, w, h)
        area_comps += [(c, "forest") for c in _components(fm, w, h, 250)]

    say("Finding highways...")
    hnear = _from_rows(_dilate(_to_rows(hwy_m, w, h), w, 2), w)
    hm = bytearray(w * h)
    for i in range(w * h):
        if hwy_m[i] or (not modern and house_m[i] and hnear[i]):
            hm[i] = 1
    if modern:
        hm = _from_rows(_erode(_dilate(_to_rows(hm, w, h), w, 2), w, 2), w)
    else:
        hm = _from_rows(_erode(_dilate(_to_rows(hm, w, h), w, 6), w, 5), w)
    _clear_border(hm, w, h)
    hwy_px = bytearray(w * h)
    hwy_lines = []
    for comp in _components(hm, w, h, 60):
        for i in comp:
            hwy_px[i] = 1
        sk, pts = _thin(hm, comp, w)
        for pl, spur in _trace(sk, pts, w):
            hwy_lines.append(pl)
    hwy_lines = _network(hwy_lines, gap=26, snap=12, min_len=30, spur=14)
    hwy_near = _from_rows(_dilate(_to_rows(hwy_px, w, h), w, 3), w)

    house_list = []
    if o["houses"]:
        say("Finding houses...")
        band = road_m
        hm = bytearray(house_m)
        for i in range(w * h):
            if hwy_near[i] or band[i]:
                hm[i] = 0
        roofs = C["roofs_village"]
        near_road = _from_rows(_dilate(_to_rows(road_m, w, h), w, 8), w)
        cands = []
        for comp in _components(hm, w, h, 8):
            if len(comp) > 2500:
                continue
            for cx, cy, ang, L, D in _rect_cover(comp, w):
                if min(L, D) < (3 if modern else 2) or L * D < 12 or \
                        max(L, D) / float(min(L, D)) > 6:
                    continue
                cands.append((comp, cx, cy, ang, L, D))
        for comp, cx, cy, ang, L, D in cands:
            ci = int(cy) * w + int(cx)
            if not (0 <= ci < w * h):
                continue
            if not modern and not near_area[ci] and not (near_road[ci] and L * D >= 20):
                continue
            hx, hy = M(cx, cy)
            hw, hd = max(6.0, L * s), max(5.0, D * s)
            house_list.append((hx, hy, comp, ci))
            add({"type": "house", "cx": hx, "cy": hy, "ang": ang, "w": hw, "d": hd,
                 "roof": rnd.choice(roofs), "yard": None, "yard_type": "stone"})

    house_px = set([hl[3] for hl in house_list])
    forest_in = bytearray(w * h)
    areas = []
    for comp, akind in area_comps:
        cs = set(comp)
        if akind:
            garden = akind == "garden"
        else:
            nh = len([1 for p in house_px if p in cs])
            garden = nh >= 1 and len(comp) / float(nh) < 7000
        areas.append((comp, cs, garden))
        if not garden:
            for i in comp:
                forest_in[i] = 1
    forest_in = _from_rows(_erode(_to_rows(forest_in, w, h), w, 2), w)

    roads = []
    for pl in hwy_lines:
        roads.append({"pts": [list(M(x, y)) for x, y in pl], "w": 13, "kind": "main"})
    road_px = bytearray(w * h)
    street_lines = []
    if o["roads"]:
        say("Finding roads...")
        rm = bytearray(road_m)
        for i in range(w * h):
            if (forest_in[i] and not modern) or hwy_near[i]:
                rm[i] = 0
        if modern:
            rm = _from_rows(_erode(_dilate(_to_rows(rm, w, h), w, 2), w, 1), w)
        else:
            rm = _from_rows(_erode(_dilate(_to_rows(rm, w, h), w, 4), w, 3), w)
        _clear_border(rm, w, h)
        raw = []
        for comp in _components(rm, w, h, 25):
            for i in comp:
                road_px[i] = 1
            sk, pts = _thin(rm, comp, w)
            for pl, spur in _trace(sk, pts, w):
                raw.append(pl)
        street_lines = _network(raw, gap=18, snap=10, min_len=22, spur=10, anchors=hwy_lines)
        for pl in street_lines:
            roads.append({"pts": [list(M(x, y)) for x, y in pl], "w": 9, "kind": "street"})
        if modern:
            say("Finding local roads...")
            wrows = _erode(_dilate(_to_rows(_mask(lab, WHITE), w, h), w, 1), w, 1)
            wide = _dilate(_dilate(_erode(wrows, w, 6), w, 6), w, 1)
            thin = _from_rows([wrows[i] & ~wide[i] for i in range(h)], w)
            for i in range(w * h):
                if road_px[i] or hwy_px[i]:
                    thin[i] = 0
            _clear_border(thin, w, h)
            raw2 = []
            for comp in _components(thin, w, h, 40):
                sk, pts = _thin(thin, comp, w)
                if len(pts) < 25 or not (2.5 <= len(comp) / float(len(pts)) <= 13):
                    continue
                cs = set(comp)
                gray = 0
                other = 0
                for i in comp:
                    for j in (i - 1, i + 1, i - w, i + w):
                        if j in cs or not (0 <= j < w * h):
                            continue
                        if lab[j] == HOUSE or lab[j] == DARK:
                            gray += 1
                        elif lab[j] != WHITE:
                            other += 1
                if gray < 0.3 * (gray + other) or gray < 10:
                    continue
                for i in comp:
                    road_px[i] = 1
                for pl, spur in _trace(sk, pts, w):
                    raw2.append(pl)
            local = _network(raw2, gap=14, snap=10, min_len=30, spur=10,
                             anchors=list(hwy_lines) + list(street_lines), strict=True)
            for pl in local:
                roads.append({"pts": [list(M(x, y)) for x, y in pl], "w": 7, "kind": "street"})
            street_lines = list(street_lines) + local

    roadish = _from_rows(_dilate(_to_rows(bytearray([a | b for a, b in zip(road_px, hwy_px)]),
                                          w, h), w, 4), w)

    fence_lines = []
    track_lines = []
    if o["tracks"]:
        say("Finding dirt tracks...")
        dark = _mask(lab, DARK if modern else (DARK, GRAY))
        rd3 = _from_rows(_dilate(_to_rows(bytearray([a | b for a, b in zip(road_px, hwy_px)]),
                                          w, h), w, 2), w)
        for i in range(len(dark)):
            if rd3[i]:
                dark[i] = 0
        dm = _from_rows(_erode(_dilate(_to_rows(dark, w, h), w, 1), w, 1), w)
        _clear_border(dm, w, h)
        solid = []
        dashes = []
        small_comps = []
        for comp in _components(dm, w, h, 3):
            if len(comp) < 40:
                small_comps.append((sum([i % w for i in comp]) / float(len(comp)),
                                    sum([i // w for i in comp]) / float(len(comp))))
            if len(comp) < 6:
                continue
            dpx = len([1 for i in comp if dark[i]])
            sk, pts = _thin(dm, comp, w)
            if not pts:
                continue
            thick = dpx / float(len(pts))
            if thick > 5.5:
                continue
            cxs = [i % w for i in comp]
            cys = [i // w for i in comp]
            diag = math.hypot(max(cxs) - min(cxs), max(cys) - min(cys)) + 1
            if len(pts) >= 30 and len(pts) / diag > 1.8:
                continue
            if len(pts) >= 6 and (len(pts) < 70 and len(pts) / diag < 1.3 or len(pts) < 30):
                p0, p1, ang, L, D = _dash_info(pts, w)
                if L >= 9 and L / max(D, 1.0) >= 3.0 and thick <= 5.0:
                    dashes.append((p0, p1, ang, L))
                    continue
            if len(pts) >= 30:
                for pl, spur in _trace(sk, pts, w):
                    solid.append(pl)
        cnt = {}
        for comp in small_comps:
            k = (int(comp[0] // 12), int(comp[1] // 12))
            cnt[k] = cnt.get(k, 0) + 1

        def texty(x, y):
            gx, gy = int(x // 12), int(y // 12)
            t = 0
            for ix in (gx - 1, gx, gx + 1):
                for iy in (gy - 1, gy, gy + 1):
                    t += cnt.get((ix, iy), 0)
            return t >= 6

        dashes = [dd for dd in dashes if not texty((dd[0][0] + dd[1][0]) / 2.0,
                                                     (dd[0][1] + dd[1][1]) / 2.0)]
        solid2 = []
        for pl in solid:
            tx = len([1 for x, y in pl if texty(x, y)])
            if tx < 0.4 * len(pl):
                solid2.append(pl)
        solid = solid2
        raw = list(solid)
        for count, pts in _chain_dashes(dashes, link=24.0):
            if (count >= 3 and _plen(pts) >= 50) or (count == 2 and _plen(pts) >= 55):
                raw.append(pts)
        anchors = list(hwy_lines) + list(street_lines if o["roads"] else [])
        road_side = _from_rows(_dilate(_to_rows(bytearray([a | b for a, b in zip(road_px, hwy_px)]),
                                                w, h), w, 8), w)
        for pl in _network(raw, gap=16, snap=9, min_len=50, spur=12, anchors=anchors, strict=True):
            L = _plen(pl)
            (x0, y0), (x1, y1) = pl[0], pl[-1]
            xs2 = [p[0] for p in pl]
            ys2 = [p[1] for p in pl]
            if max(xs2) < 24 or min(xs2) > w - 25 or max(ys2) < 24 or min(ys2) > h - 25:
                continue
            samp = _resample(pl, 4.0)
            along = 0
            for x, y in samp:
                ii = int(y) * w + int(x)
                if 0 <= ii < w * h and road_side[ii]:
                    along += 1
            if along > 0.5 * len(samp):
                continue
            inside = 0
            for x, y in samp:
                ii = int(y) * w + int(x)
                if 0 <= ii < w * h and near_area[ii]:
                    inside += 1
            if inside > 0.6 * len(samp):
                fence_lines.append(pl)
                continue
            roads.append({"pts": [list(M(x, y)) for x, y in pl], "w": 5, "kind": "dirt"})
            track_lines.append(pl)

    for pl in fence_lines:
        if _plen(pl) >= 25:
            add({"type": "fence", "pts": [list(M(x, y)) for x, y in pl]})
    hmask = bytearray(w * h)
    for hl in house_list:
        for i in hl[2]:
            hmask[i] = 1
    blocked = _from_rows(_dilate(_to_rows(bytearray([a | b for a, b in zip(roadish, hmask)]),
                                          w, h), w, 1), w)
    house_clear = _from_rows(_dilate(_to_rows(hmask, w, h), w, 4), w)
    for pl in track_lines + fence_lines:
        for x, y in _resample(pl, 1.0):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ix, iy = int(x) + dx, int(y) + dy
                    if 0 <= ix < w and 0 <= iy < h:
                        blocked[iy * w + ix] = 1

    if o["water"]:
        say("Finding water...")
        wm = _from_rows(_erode(_dilate(_to_rows(_mask(lab, WATER), w, h), w, 1), w, 1), w)
        _clear_border(wm, w, h)
        stream_raw = []
        for comp in _components(wm, w, h, 6):
            xs = [i % w for i in comp]
            ys = [i // w for i in comp]
            bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if bw >= 6 and bh >= 6 and len(comp) >= 20 and len(comp) >= 0.5 * math.pi / 4 * bw * bh:
                x, y = M((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
                add({"type": "pond", "x": x, "y": y, "rx": bw * s / 2.0, "ry": bh * s / 2.0})
                for i in comp:
                    blocked[i] = 1
            else:
                sk, pts = _thin(wm, comp, w)
                for pl, spur in _trace(sk, pts, w):
                    stream_raw.append(pl)
        for pl in _network(stream_raw, gap=14, snap=8, min_len=25, spur=8):
            add({"type": "stream", "pts": [list(M(x, y)) for x, y in pl]})
            for x, y in _resample(pl, 1.0):
                for dy in (-2, -1, 0, 1, 2):
                    for dx in (-2, -1, 0, 1, 2):
                        ix, iy = int(x) + dx, int(y) + dy
                        if 0 <= ix < w and 0 <= iy < h:
                            blocked[iy * w + ix] = 1

    trees = []
    if o["areas"]:
        say("Planting forests and gardens...")
        for comp, cs, garden in areas:
            if garden and not o["garden_trees"]:
                for i in comp:
                    blocked[i] = 1
                continue
            xs = [i % w for i in comp]
            ys = [i // w for i in comp]
            step = (17.0 if garden else 9.5)
            y = min(ys) * s
            while y < (max(ys) + 1) * s:
                x = min(xs) * s
                while x < (max(xs) + 1) * s:
                    tx, ty = x + rnd.uniform(-3, 3), y + rnd.uniform(-3, 3)
                    ix, iy = int(tx / s), int(ty / s)
                    i = iy * w + ix
                    if 0 <= ix < w and 0 <= iy < h and i in cs and not blocked[i] and not house_clear[i]:
                        if not garden or rnd.random() < 0.55:
                            r = rnd.uniform(4, 6.5) if garden else rnd.uniform(5, 8.5)
                            trees.append((tx, ty, r))
                    x += step
                y += step
            for i in comp:
                blocked[i] = 1
    for tx, ty, r in trees:
        add({"type": "tree", "x": tx, "y": ty, "r": r, "col": rnd.choice(C["tree"])})

    if o["fields"]:
        say("Adding fields...")
        bl = _from_rows(_dilate(_to_rows(blocked, w, h), w, 2), w)
        if modern:
            frows2 = _to_rows(_mask(lab, (FIELD, CONTOUR)), w, h)
            frows2 = _dilate(_erode(_erode(_dilate(frows2, w, 2), w, 2), w, 3), w, 1)
            notfield = bytearray([1 - v for v in _from_rows(frows2, w)])
            bl = bytearray([a | b for a, b in zip(bl, notfield)])
        occ = Raster(W, H, 1, 0)
        g = rnd.uniform(0, math.pi)
        target = int((60 if modern else 35) * W * H / 1400000.0) + 5
        made = 0
        for _ in range(target * 40):
            if made >= target:
                break
            x, y = rnd.uniform(10, W - 10), rnd.uniform(10, H - 10)
            ix, iy = int(x / s), int(y / s)
            if bl[iy * w + ix]:
                continue
            if modern:
                fw, fh = rnd.uniform(35, 95), rnd.uniform(28, 70)
            else:
                fw, fh = rnd.uniform(60, 150), rnd.uniform(45, 110)
            ang = g + rnd.choice((0, math.pi / 2)) + rnd.uniform(-0.12, 0.12)
            ok = True
            ca, sa = math.cos(ang), math.sin(ang)
            for a in range(6):
                if not ok:
                    break
                u = -fw / 2 - 3 + (fw + 6) * a / 5.0
                for b in range(6):
                    v = -fh / 2 - 3 + (fh + 6) * b / 5.0
                    px, py = x + ca * u - sa * v, y + sa * u + ca * v
                    ix, iy = int(px / s), int(py / s)
                    if not (0 <= ix < w and 0 <= iy < h) or bl[iy * w + ix] or occ.get(px, py):
                        ok = False
                        break
            if not ok:
                continue
            pasture = rnd.random() < 0.2
            add({"type": "field", "cx": x, "cy": y, "ang": ang, "w": fw, "h": fh,
                 "col": C["pasture"] if pasture else rnd.choice(C["fields"]),
                 "gap": rnd.uniform(4, 7), "rot": rnd.random() < 0.5, "pasture": pasture})
            occ.fill_poly(local_rect(x, y, ang, -fw / 2 - 4, fw / 2 + 4, -fh / 2 - 4, fh / 2 + 4),
                          255)
            made += 1

    if o["lamps"] and house_list:
        say("Placing street lamps...")
        hs = [(hl[0], hl[1]) for hl in house_list]
        for rd in roads:
            if rd["kind"] == "dirt":
                continue
            pts = rd["pts"]
            acc = 20.0
            side = 1
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                L = math.hypot(bx - ax, by - ay)
                if L < 1e-6:
                    continue
                t = acc
                while t < L:
                    px, py = ax + (bx - ax) * t / L, ay + (by - ay) * t / L
                    if min([(px - a) ** 2 + (py - b) ** 2 for a, b in hs]) < 40 * 40:
                        nx, ny = -(by - ay) / L, (bx - ax) / L
                        off = rd["w"] / 2 + 2.5
                        add({"type": "lamp", "x": px + nx * off * side, "y": py + ny * off * side})
                        side = -side
                    t += 45.0
                acc = t - L

    base = os.path.splitext(os.path.basename(path))[0]
    name = to_unicode(o["name"]).strip() or base.replace("_", " ").replace("-", " ").strip() or "Imported map"
    kind = "town" if len(house_list) > 150 else "village"
    opts_doc = {}
    for k in LOOK_KEYS:
        opts_doc[k] = int(DEFAULTS[k])
    say("Done.")
    return {"format": "mapgen", "version": 1, "width": W, "height": H, "kind": kind,
            "name": name, "seed": 0, "source": os.path.basename(path),
            "per_house": 4.0 if kind == "village" else 6.0, "roads": roads, "wall": None,
            "gates": [], "plaza": None, "objects": objs, "opts": opts_doc}


def draw_on_canvas(cv, ops, k, W, H):
    cv.delete("all")

    def P(pts):
        out = []
        for x, y in pts:
            out.append(x * k)
            out.append(y * k)
        return out

    for tag, op in ops:
        tags = ()
        if tag:
            tags = (tag,)
        t = op[0]
        if t == "bg":
            cv.create_rectangle(0, 0, W * k, H * k, fill=hexcol(op[1]), width=0)
        elif t == "ellipse":
            _, x, y, rx, ry, fill, out, ow = op
            cv.create_oval((x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k,
                           fill=hexcol(fill), outline=hexcol(out) if out else "",
                           width=max(1, ow * k) if out else 0, tags=tags)
        elif t == "poly":
            _, pts, fill, out, ow = op
            cv.create_polygon(P(pts), fill=hexcol(fill), outline=hexcol(out) if out else "",
                              width=max(1, ow * k) if out else 0, tags=tags)
        elif t == "outline":
            _, pts, out, ow = op
            cv.create_polygon(P(pts), fill="", outline=hexcol(out), width=1, tags=tags)
        elif t == "line":
            _, pts, col, w = op
            cv.create_line(P(pts), fill=hexcol(col), width=max(1, w * k),
                           capstyle="round", joinstyle="round", tags=tags)
        elif t == "shadow_poly":
            cv.create_polygon(P(op[1]), fill=hexcol(shade(C["grass"], 0.72)), outline="",
                              tags=tags + ("nohit",))
        elif t == "shadow_ellipse":
            _, x, y, rr, a = op
            cv.create_oval((x - rr) * k, (y - rr) * k, (x + rr) * k, (y + rr) * k,
                           fill=hexcol(shade(C["grass"], 0.78)), outline="",
                           tags=tags + ("nohit",))
        elif t == "glow":
            _, x, y, rr, col, a = op
            rr = 5.0
            cv.create_oval((x - rr) * k, (y - rr) * k, (x + rr) * k, (y + rr) * k,
                           fill=hexcol(mix(C["grass"], col, 0.45)), outline="",
                           tags=tags + ("nohit",))
        elif t == "panel":
            _, x0, y0, x1, y1, fill, out = op
            cv.create_rectangle(x0 * k, y0 * k, x1 * k, y1 * k, fill=hexcol(fill),
                                outline=hexcol(out), width=2, tags=tags)
        elif t == "text":
            _, x, y, txt, s, col = op
            cv.create_text(x * k, (y + 1 * s) * k, text=txt, anchor="nw", fill=hexcol(col),
                           font=("Arial", -max(6, int(10 * s * k)), "bold"), tags=tags)


class App(object):
    def __init__(self):
        try:
            import Tkinter as tk
            import tkMessageBox as messagebox
            import tkFileDialog as filedialog
        except ImportError:
            import tkinter as tk
            from tkinter import messagebox, filedialog
        self.tk, self.messagebox, self.filedialog = tk, messagebox, filedialog

        self.root = root = tk.Tk()
        root.title(APP_TITLE + "  -  by " + AUTHOR)
        root.geometry("1360x900")
        self.doc = None
        self.k = 1.0
        self.sel = None
        self.drag = None
        self.draw_line = None
        self.undo = []
        self.rot_sel = None
        self.redraw_job = None
        self.vars = {}

        bar = tk.Frame(root, padx=6, pady=5)
        bar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(bar, text="New village", width=11,
                  command=lambda: self.generate("village")).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="New town", width=11,
                  command=lambda: self.generate("town")).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="Generate (F5)", width=12,
                  command=lambda: self.generate(None)).pack(side=tk.LEFT, padx=2)
        tk.Label(bar, text="   Tool:").pack(side=tk.LEFT)
        self.tool = tk.StringVar()
        self.tool.set("move")
        for val, lbl in (("move", "Move"), ("house", "+ House"), ("lamp", "+ Lamp"),
                         ("tree", "+ Tree"), ("fence", "+ Fence"), ("brickwall", "+ Brick wall"),
                         ("stonewall", "+ Stone wall")):
            tk.Radiobutton(bar, text=lbl, variable=self.tool, value=val, indicatoron=0,
                           padx=4, pady=2).pack(side=tk.LEFT, padx=1)
        tk.Button(bar, text="Rotate L", command=lambda: self.rotate_sel(-1)).pack(side=tk.LEFT, padx=(8, 1))
        tk.Button(bar, text="Rotate R", command=lambda: self.rotate_sel(1)).pack(side=tk.LEFT, padx=1)
        tk.Button(bar, text="Delete", command=self.delete_sel).pack(side=tk.LEFT, padx=1)
        tk.Button(bar, text="Undo", command=self.do_undo).pack(side=tk.LEFT, padx=1)
        tk.Button(bar, text="About", command=self.show_about).pack(side=tk.RIGHT, padx=2)
        tk.Button(bar, text="Import map picture...", command=self.import_dialog,
                  bg="#f0e0b0").pack(side=tk.RIGHT, padx=2)

        outer = tk.Frame(root, bd=1, relief=tk.GROOVE)
        outer.pack(side=tk.LEFT, fill=tk.Y)
        pc = tk.Canvas(outer, width=300, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL, command=pc.yview)
        pc.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        pc.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        panel = tk.Frame(pc, padx=8, pady=4)
        pc.create_window((0, 0), window=panel, anchor="nw")
        panel.bind("<Configure>", lambda e: pc.configure(scrollregion=pc.bbox("all")))
        self.panel = panel
        self.row = 0
        self._build_settings()

        self.cv = tk.Canvas(root, bg="#2b2b2b", highlightthickness=0)
        self.cv.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.status = tk.Label(root, anchor="w", padx=8, text="")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        cv = self.cv
        cv.bind("<Configure>", lambda e: self.schedule_redraw(150))
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<B1-Motion>", self.on_motion)
        cv.bind("<ButtonRelease-1>", self.on_release)
        cv.bind("<Button-3>", self.on_right)
        cv.bind("<MouseWheel>", self.on_wheel)
        cv.bind("<Button-4>", lambda e: self.rotate_sel(-1))
        cv.bind("<Button-5>", lambda e: self.rotate_sel(1))
        root.bind("<Delete>", self.key_delete)
        root.bind("<Control-z>", lambda e: self.do_undo())
        root.bind("<Control-s>", lambda e: self.export())
        root.bind("<F5>", lambda e: self.generate(None))
        root.bind("<Escape>", lambda e: self.select(None))
        root.bind("<KeyPress-q>", lambda e: self.key_rotate(e, -1))
        root.bind("<KeyPress-e>", lambda e: self.key_rotate(e, 1))
        root.after(150, lambda: self.generate(None))
        root.after(300, self.show_about)

    def show_about(self):
        tk = self.tk
        w = tk.Toplevel(self.root)
        w.title("About")
        w.resizable(0, 0)
        w.transient(self.root)
        tk.Label(w, text=APP_TITLE, font=("Arial", 15, "bold")).pack(padx=40, pady=(20, 6))
        tk.Label(w, text="Created by", font=("Arial", 10), fg="#555").pack()
        tk.Label(w, text=AUTHOR, font=("Arial", 13, "bold")).pack(pady=(0, 12))
        tk.Label(w, text="License: " + LICENSE, font=("Arial", 10)).pack()
        tk.Label(w, text="You may share and adapt this program,\n"
                         "but you must give credit to the author.",
                 font=("Arial", 9), fg="#555", justify=tk.CENTER).pack(pady=(2, 12))
        tk.Label(w, text="Discord:", font=("Arial", 10)).pack()
        link = tk.Label(w, text=DISCORD, font=("Arial", 11, "underline"), fg="#2a62c9",
                        cursor="hand2")
        link.pack(pady=(0, 14))
        link.bind("<Button-1>", lambda e: self.open_link(DISCORD))
        tk.Button(w, text="OK", width=12, command=w.destroy).pack(pady=(0, 18))
        w.bind("<Return>", lambda e: w.destroy())
        w.bind("<Escape>", lambda e: w.destroy())
        w.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - w.winfo_height()) // 3
        w.geometry("+%d+%d" % (max(0, x), max(0, y)))
        w.lift()
        w.focus_set()
        try:
            w.grab_set()
        except Exception:
            pass

    def open_link(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            self.messagebox.showinfo("Discord", url)

    def _header(self, text):
        tk = self.tk
        tk.Label(self.panel, text=text, font=("Arial", 10, "bold"), anchor="w").grid(
            row=self.row, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.row += 1

    def _spin(self, key, label, lo, hi, inc):
        tk = self.tk
        tk.Label(self.panel, text=label, anchor="w").grid(row=self.row, column=0, sticky="w")
        var = tk.StringVar()
        sp = tk.Spinbox(self.panel, from_=lo, to=hi, increment=inc, textvariable=var, width=7)
        sp.grid(row=self.row, column=1, sticky="e", pady=1)
        var.set(str(DEFAULTS[key]))
        self.vars[key] = var
        self.row += 1

    def _check(self, key, label, live=False, col=0):
        tk = self.tk
        var = tk.IntVar()
        var.set(DEFAULTS[key])
        cb = tk.Checkbutton(self.panel, text=label, variable=var, anchor="w")
        if live:
            cb.configure(command=self.look_changed)
        cb.grid(row=self.row, column=col, sticky="w")
        self.vars[key] = var
        if col == 1 or not live:
            self.row += 1

    def _build_settings(self):
        tk = self.tk
        p = self.panel
        self._header("General")
        tk.Label(p, text="Settlement type", anchor="w").grid(row=self.row, column=0, sticky="w")
        self.type_var = tk.StringVar()
        self.type_var.set("random")
        tk.OptionMenu(p, self.type_var, "random", "village", "town").grid(
            row=self.row, column=1, sticky="e")
        self.row += 1
        tk.Label(p, text="Name (empty = random)", anchor="w").grid(row=self.row, column=0, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(p, textvariable=self.name_var, width=14).grid(row=self.row, column=1, sticky="e")
        self.row += 1
        tk.Label(p, text="Seed", anchor="w").grid(row=self.row, column=0, sticky="w")
        self.seed_var = tk.StringVar()
        tk.Entry(p, textvariable=self.seed_var, width=10).grid(row=self.row, column=1, sticky="e")
        self.row += 1
        self.lock_var = tk.IntVar()
        tk.Checkbutton(p, text="Keep this seed", variable=self.lock_var).grid(
            row=self.row, column=0, columnspan=2, sticky="w")
        self.row += 1
        self._spin("width", "Map width (px)", 600, 4000, 100)
        self._spin("height", "Map height (px)", 400, 4000, 100)

        self._header("Settlement")
        self._spin("size", "Size (%)", 40, 250, 10)
        self._spin("main_roads", "Main roads (0 = auto)", 0, 10, 1)
        self._spin("streets", "Streets (%)", 0, 300, 10)
        self._spin("house_density", "House density (%)", 0, 150, 5)
        self._spin("house_size", "House size (%)", 50, 200, 5)
        self._spin("yards", "Yards with walls - village (%)", 0, 100, 5)
        self._spin("fence_yards", "  of them wooden fence (%)", 0, 100, 5)
        self._spin("brick_yards", "  of them brick wall (%)", 0, 100, 5)
        self._spin("gardens", "Brick-walled gardens", 0, 40, 1)
        self._check("walls", "Town walls")
        self._spin("towers", "Wall towers (0 = auto)", 0, 40, 1)
        self._check("lamps", "Street lamps")
        self._spin("lamp_spacing", "Lamp spacing (%)", 30, 400, 10)
        self._check("center", "Square / village green")
        self._check("church", "Church (+ town hall)")

        self._header("Countryside")
        self._spin("dirt_roads", "Dirt tracks (%)", 0, 300, 10)
        self._spin("fields", "Fields (%)", 0, 300, 10)
        self._spin("pastures", "Fenced pastures (%)", 0, 100, 5)
        self._spin("forests", "Forests (%)", 0, 400, 10)
        self._spin("trees", "Single trees (%)", 0, 400, 10)

        self._header("Look (applies instantly)")
        self._check("texture", "Grass texture", True, 0)
        self._check("shadows", "Shadows", True, 1)
        self._check("glow", "Lamp light", True, 0)
        self._check("title", "Title", True, 1)
        self._check("legend", "Legend", True, 0)
        self._check("scalebar", "Scale + north", True, 1)

        tk.Button(p, text="Generate with these settings", command=lambda: self.generate(None),
                  bg="#d8e8c8").grid(row=self.row, column=0, columnspan=2, sticky="we", pady=(10, 2))
        self.row += 1
        tk.Button(p, text="Reset settings", command=self.reset_settings).grid(
            row=self.row, column=0, columnspan=2, sticky="we")
        self.row += 1

        self._header("Export (saved next to the script)")
        tk.Label(p, text="Format", anchor="w").grid(row=self.row, column=0, sticky="w")
        self.fmt_var = tk.StringVar()
        self.fmt_var.set("PNG")
        tk.OptionMenu(p, self.fmt_var, *(EXPORT_FORMATS + ["ALL"])).grid(
            row=self.row, column=1, sticky="e")
        self.row += 1
        tk.Label(p, text="Image scale (1-4x)", anchor="w").grid(row=self.row, column=0, sticky="w")
        self.scale_var = tk.StringVar()
        tk.Spinbox(p, from_=1, to=4, increment=1, textvariable=self.scale_var, width=7).grid(
            row=self.row, column=1, sticky="e")
        self.scale_var.set("1")
        self.row += 1
        tk.Button(p, text="Export (Ctrl+S)", command=self.export, bg="#c8dcf0").grid(
            row=self.row, column=0, columnspan=2, sticky="we", pady=(4, 2))
        self.row += 1
        tk.Button(p, text="Open map (.json)...", command=self.open_json).grid(
            row=self.row, column=0, columnspan=2, sticky="we")
        self.row += 1

    def reset_settings(self):
        for k, v in self.vars.items():
            v.set(DEFAULTS[k])
        self.type_var.set("random")
        self.name_var.set("")
        self.look_changed()

    def read_cfg(self):
        cfg = dict(DEFAULTS)
        for k, v in self.vars.items():
            try:
                cfg[k] = int(float(v.get()))
            except (ValueError, TypeError):
                cfg[k] = DEFAULTS[k]
        cfg["width"] = max(400, min(4000, cfg["width"]))
        cfg["height"] = max(300, min(4000, cfg["height"]))
        cfg["name"] = self.name_var.get()
        cfg["type"] = self.type_var.get()
        return cfg

    def set_status(self, text):
        self.status.config(text=text)
        self.root.update_idletasks()

    def generate(self, kind):
        if kind:
            self.type_var.set(kind)
        cfg = self.read_cfg()
        seed = None
        if self.lock_var.get():
            try:
                seed = int(self.seed_var.get())
            except ValueError:
                seed = None
        self.root.config(cursor="watch")
        self.set_status("Generating...")
        try:
            self.doc = generate_doc(cfg, cfg["type"], seed)
        finally:
            self.root.config(cursor="")
        self.seed_var.set(str(self.doc["seed"]))
        self.undo = []
        self.sel = None
        self.redraw()
        self.update_info()

    def update_info(self):
        if not self.doc:
            return
        nb, nl, pop = doc_stats(self.doc)
        self.set_status(u"%s %s  -  %d buildings, %d lamps, %d roads, seed %s     |  drag = move,"
                        u" wheel / Q, E = rotate, Del / right click = delete, Ctrl+Z = undo" % (
                            "Town" if self.doc["kind"] == "town" else "Village",
                            to_unicode(self.doc["name"]), nb, nl, len(self.doc["roads"]),
                            self.doc.get("seed", "-")))

    def look_changed(self):
        if self.doc:
            for k in LOOK_KEYS:
                self.doc["opts"][k] = int(self.vars[k].get())
            self.redraw()

    def schedule_redraw(self, ms=120):
        if self.redraw_job:
            self.root.after_cancel(self.redraw_job)
        self.redraw_job = self.root.after(ms, self.redraw)

    def redraw(self):
        self.redraw_job = None
        if not self.doc:
            return
        cw, ch = max(self.cv.winfo_width(), 100), max(self.cv.winfo_height(), 100)
        W, H = self.doc["width"], self.doc["height"]
        self.k = min(cw / W, ch / H)
        draw_on_canvas(self.cv, build_scene(self.doc), self.k, W, H)
        self.draw_sel()

    def draw_sel(self):
        self.cv.delete("sel")
        if self.sel is None:
            return
        bb = self.cv.bbox("o%d" % self.sel)
        if bb:
            self.cv.create_rectangle(bb[0] - 2, bb[1] - 2, bb[2] + 2, bb[3] + 2,
                                     outline="#00e5ff", dash=(4, 2), width=2, tags=("sel",))

    def select(self, oid):
        self.sel = oid
        self.rot_sel = None
        self.draw_sel()

    def find_obj(self, ex, ey):
        cv = self.cv
        items = cv.find_overlapping(ex - 3, ey - 3, ex + 3, ey + 3)
        for it in reversed(items):
            tags = cv.gettags(it)
            if "nohit" in tags or "sel" in tags:
                continue
            if "ui" in tags:
                return None
            for t in tags:
                if t.startswith("o") and t[1:].isdigit():
                    return int(t[1:])
        return None

    def get_obj(self, oid):
        for o in self.doc["objects"]:
            if o["id"] == oid:
                return o
        return None

    def push_undo(self, snap=None):
        self.undo.append(snap if snap is not None else copy.deepcopy(self.doc["objects"]))
        if len(self.undo) > 60:
            self.undo.pop(0)

    def do_undo(self):
        if self.doc and self.undo:
            self.doc["objects"] = self.undo.pop()
            self.rot_sel = None
            if self.sel is not None and self.get_obj(self.sel) is None:
                self.sel = None
            self.redraw()
            self.update_info()

    def on_press(self, e):
        if not self.doc:
            return
        self.cv.focus_set()
        tool = self.tool.get()
        if tool == "move":
            oid = self.find_obj(e.x, e.y)
            self.select(oid)
            if oid is not None:
                self.drag = {"id": oid, "x": e.x, "y": e.y, "sx": e.x, "sy": e.y,
                             "snap": copy.deepcopy(self.doc["objects"])}
        elif tool in WALL_OBJ:
            self.draw_line = {"x": e.x, "y": e.y}
            self.cv.delete("preview")
            self.cv.create_line(e.x, e.y, e.x, e.y, fill="#00e5ff", width=2, dash=(4, 2),
                                tags=("preview",))
        else:
            x, y = e.x / self.k, e.y / self.k
            if 0 <= x < self.doc["width"] and 0 <= y < self.doc["height"]:
                self.push_undo()
                o = new_object(self.doc, tool, x, y)
                self.doc["objects"].append(o)
                self.sel = o["id"]
                self.rot_sel = None
                self.redraw()
                self.update_info()

    def on_motion(self, e):
        if self.draw_line:
            self.cv.coords("preview", self.draw_line["x"], self.draw_line["y"], e.x, e.y)
            return
        d = self.drag
        if not d:
            return
        dx, dy = e.x - d["x"], e.y - d["y"]
        self.cv.move("o%d" % d["id"], dx, dy)
        self.cv.move("sel", dx, dy)
        d["x"], d["y"] = e.x, e.y

    def on_release(self, e):
        if self.draw_line:
            s = self.draw_line
            self.draw_line = None
            self.cv.delete("preview")
            self.push_undo()
            o = new_wall_object(self.doc, self.tool.get(), s["x"] / self.k, s["y"] / self.k,
                                e.x / self.k, e.y / self.k)
            self.doc["objects"].append(o)
            self.sel = o["id"]
            self.rot_sel = None
            self.redraw()
            return
        d = self.drag
        self.drag = None
        if not d:
            return
        tx, ty = (e.x - d["sx"]) / self.k, (e.y - d["sy"]) / self.k
        if abs(tx) + abs(ty) < 0.5:
            return
        self.push_undo(d["snap"])
        self.rot_sel = None
        o = self.get_obj(d["id"])
        if o:
            obj_move(o, tx, ty)
        self.schedule_redraw(10)

    def on_right(self, e):
        if not self.doc:
            return
        oid = self.find_obj(e.x, e.y)
        if oid is not None:
            self.sel = oid
            self.delete_sel()

    def on_wheel(self, e):
        self.rotate_sel(-1 if e.delta > 0 else 1)

    def _typing(self, e):
        try:
            return e.widget.winfo_class() in ("Entry", "Spinbox")
        except Exception:
            return False

    def key_rotate(self, e, direction):
        if not self._typing(e):
            self.rotate_sel(direction)

    def key_delete(self, e):
        if not self._typing(e):
            self.delete_sel()

    def rotate_sel(self, direction):
        if not self.doc or self.sel is None:
            return
        o = self.get_obj(self.sel)
        if not o or not can_rotate(o):
            self.set_status("This object cannot be rotated.")
            return
        if self.rot_sel != self.sel:
            self.push_undo()
            self.rot_sel = self.sel
        obj_rotate(o, direction * math.radians(10))
        self.schedule_redraw(60)

    def delete_sel(self):
        if not self.doc or self.sel is None:
            return
        self.push_undo()
        self.doc["objects"] = [o for o in self.doc["objects"] if o["id"] != self.sel]
        self.sel = None
        self.rot_sel = None
        self.redraw()
        self.update_info()

    def export(self):
        if not self.doc:
            return
        fmt = self.fmt_var.get()
        try:
            scale = max(1, min(4, int(float(self.scale_var.get()))))
        except ValueError:
            scale = 1
        self.root.config(cursor="watch")
        self.set_status("Exporting %s ... (images can take a while on old Python)" % fmt)
        try:
            names = export_doc(self.doc, fmt, SCRIPT_DIR, scale)
            self.set_status(u"Saved to %s :  %s" % (fs_text(SCRIPT_DIR), ", ".join(names)))
        except Exception as ex:
            self.messagebox.showerror("Export failed", str(ex))
            self.set_status("Export failed.")
        self.root.config(cursor="")

    def open_json(self):
        path = self.filedialog.askopenfilename(initialdir=fs_text(SCRIPT_DIR),
                                               filetypes=[("Map file", "*.json"), ("All", "*.*")])
        if not path:
            return
        try:
            self.doc = load_doc(path)
        except Exception as ex:
            self.messagebox.showerror("Open failed", str(ex))
            return
        for k in LOOK_KEYS:
            self.vars[k].set(int(self.doc["opts"].get(k, 1)))
        self.seed_var.set(str(self.doc.get("seed", "")))
        self.undo = []
        self.sel = None
        self.redraw()
        self.update_info()

    def import_dialog(self):
        tk = self.tk
        path = self.filedialog.askopenfilename(
            initialdir=fs_text(SCRIPT_DIR), title="Choose a map picture",
            filetypes=[("Map picture", "*.png *.jpg *.jpeg"), ("PNG", "*.png"),
                       ("JPG", "*.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return
        w = tk.Toplevel(self.root)
        w.title("Import map picture")
        w.resizable(0, 0)
        w.transient(self.root)
        tk.Label(w, text="Build a map from a picture", font=("Arial", 13, "bold")).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(14, 2), sticky="w")
        tk.Label(w, text=os.path.basename(path), fg="#555").grid(
            row=1, column=0, columnspan=2, padx=16, sticky="w")
        v = {}
        row = [2]

        def chk(key, label):
            var = tk.IntVar()
            var.set(IMPORT_DEFAULTS[key])
            tk.Checkbutton(w, text=label, variable=var).grid(row=row[0], column=0, columnspan=2,
                                                            padx=16, sticky="w")
            v[key] = var
            row[0] += 1

        chk("houses", "Houses (red / pink shapes)")
        chk("roads", "Roads (yellow and orange lines)")
        chk("tracks", "Dirt tracks (black dashed lines)")
        chk("water", "Ponds and streams (blue)")
        chk("areas", "Forests and gardens (yellow areas)")
        chk("garden_trees", "Trees in village gardens")
        chk("fields", "Fill empty land with fields")
        chk("lamps", "Street lamps near houses")
        tk.Label(w, text="Map style").grid(row=row[0], column=0, padx=16, pady=(8, 0),
                                           sticky="w")
        st = tk.StringVar()
        st.set("auto")
        tk.OptionMenu(w, st, "auto", "old", "modern").grid(row=row[0], column=1, padx=16,
                                                            pady=(8, 0), sticky="e")
        row[0] += 1
        tk.Label(w, text="Scale (map px per picture px, 0 = auto)").grid(
            row=row[0], column=0, padx=16, pady=(8, 0), sticky="w")
        sc = tk.StringVar()
        tk.Spinbox(w, from_=0, to=4, increment=0.5, textvariable=sc, width=6).grid(
            row=row[0], column=1, padx=16, pady=(8, 0), sticky="e")
        sc.set("0")
        row[0] += 1
        tk.Label(w, text="Name (empty = file name)").grid(row=row[0], column=0, padx=16,
                                                           sticky="w")
        nm = tk.StringVar()
        tk.Entry(w, textvariable=nm, width=18).grid(row=row[0], column=1, padx=16, sticky="e")
        row[0] += 1
        tk.Label(w, text="old = scanned topographic maps (1950s-1980s)\n"
                         "modern = current CUZK maps with white background\n"
                         "PNG is faster than JPG. Big pictures can take a minute.",
                 fg="#666", justify=tk.LEFT).grid(row=row[0], column=0, columnspan=2,
                                                 padx=16, pady=(8, 4), sticky="w")
        row[0] += 1

        def go():
            opts = {}
            for k in v:
                opts[k] = int(v[k].get())
            try:
                opts["scale"] = max(0.0, min(4.0, float(sc.get())))
            except ValueError:
                opts["scale"] = 0
            opts["name"] = nm.get()
            opts["style"] = st.get()
            w.destroy()
            self.run_import(path, opts)

        bf = tk.Frame(w)
        bf.grid(row=row[0], column=0, columnspan=2, pady=(6, 14))
        tk.Button(bf, text="Import", width=12, command=go, bg="#d8e8c8").pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Cancel", width=12, command=w.destroy).pack(side=tk.LEFT, padx=4)
        w.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - w.winfo_height()) // 3
        w.geometry("+%d+%d" % (max(0, x), max(0, y)))
        try:
            w.grab_set()
        except Exception:
            pass

    def run_import(self, path, opts):
        self.root.config(cursor="watch")

        def prog(t):
            self.set_status("Importing: " + t)
            self.root.update()
        try:
            doc = import_image(path, opts, prog)
        except Exception as ex:
            self.root.config(cursor="")
            import traceback
            tb = traceback.format_exc()
            log = os.path.join(SCRIPT_DIR, "import_error.txt")
            try:
                write_bytes(log, ("Python %s\n%s\n%s" % (sys.version, fs_text(path), tb))
                            .encode("utf-8", "replace") if PY3 else
                            ("Python %s\n%s" % (sys.version, tb)))
            except Exception:
                pass
            self.messagebox.showerror("Import failed", "%s\n\nDetails were saved to "
                                      "import_error.txt" % ex)
            self.set_status("Import failed.")
            return
        self.root.config(cursor="")
        self.doc = doc
        for k in LOOK_KEYS:
            self.vars[k].set(int(doc["opts"].get(k, 1)))
        self.undo = []
        self.sel = None
        self.rot_sel = None
        self.redraw()
        self.update_info()

    def run(self):
        self.root.mainloop()


def main():
    op = OptionParser(usage="%prog [--type village|town|random] [--seed N] "
                            "[--export png,svg,json,...|all] [--count N] [--scale N]")
    op.add_option("--type", default="random", choices=["village", "town", "random"])
    op.add_option("--seed", type="int", default=None)
    op.add_option("--export", default=None,
                  help="formats separated by comma: png,bmp,ppm,svg,eps,json or all "
                       "(no window, saves files and exits)")
    op.add_option("--count", type="int", default=1)
    op.add_option("--scale", type="int", default=1, help="image scale 1-4")
    op.add_option("--width", type="int", default=DEFAULTS["width"])
    op.add_option("--import", dest="import_path", default=None,
                  help="build the map from a PNG/JPG map picture")
    op.add_option("--import-scale", dest="import_scale", type="float", default=0.0)
    op.add_option("--style", default="auto", choices=["auto", "old", "modern"])
    op.add_option("--height", type="int", default=DEFAULTS["height"])
    o, _ = op.parse_args()

    if o.import_path:
        doc = import_image(o.import_path, {"scale": o.import_scale, "style": o.style},
                           lambda t: print(t))
        for f in [x.strip() for x in (o.export or "png").split(",") if x.strip()]:
            for name in export_doc(doc, f, SCRIPT_DIR, max(1, min(4, o.scale))):
                print("Saved: " + name)
        return

    if not o.export:
        try:
            App().run()
            return
        except ImportError:
            print("Tkinter is not available - exporting PNG instead.")
            o.export = "png"

    cfg = {"width": o.width, "height": o.height}
    fmts = [f.strip() for f in o.export.split(",") if f.strip()]
    for i in range(o.count):
        seed = (o.seed + i) if o.seed is not None else None
        doc = generate_doc(cfg, o.type, seed)
        for f in fmts:
            for name in export_doc(doc, f, SCRIPT_DIR, max(1, min(4, o.scale))):
                print("Saved: " + name)


if __name__ == "__main__":
    main()
