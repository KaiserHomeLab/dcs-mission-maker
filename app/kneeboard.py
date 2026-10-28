"""Kneeboard pages (PNG) for each player flight."""
import functools
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from . import comms, paths

W, H = 768, 1024
MARGIN = 28
FONT_DIR = paths.vendor_dir() / "fonts"


@dataclass(frozen=True)
class Palette:
    ink: str
    muted: str
    accent: str
    rule: str
    bg: str          # page
    paper: str       # route sketch and symbol fill
    threat: str
    on_accent: str   # text on a filled accent symbol


DAY = Palette("#111111", "#555555", "#9a5b00", "#bbbbbb", "#f7f4ec", "#fbf9f3", "#b03a2e", "#ffffff")
# Night: dark page, dim warm ink, so the kneeboard doesn't blind you in a dark cockpit.
NIGHT = Palette("#c9b994", "#857a64", "#c98a3a", "#38362e", "#0d0e0b", "#13140f", "#c4594b", "#0d0e0b")


def save_png(img, path):
    """Kneeboard pages are flat colours: a 64-colour palette PNG is a fraction of the
    size of a full-colour one and quicker to compress."""
    img.quantize(colors=64, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(path, "PNG")


@functools.lru_cache(maxsize=4096)
def _width(text, font):
    return font.getlength(text)


@functools.cache
def _font(size, bold=False, mono=False):
    name = "DejaVuSansMono" if mono else "DejaVuSans"
    name += "-Bold" if bold else ""
    try:
        return ImageFont.truetype(str(FONT_DIR / f"{name}.ttf"), size)
    except OSError:
        return ImageFont.load_default(size)


class Page:
    def __init__(self, palette=DAY):
        self.c = palette
        self.img = Image.new("RGB", (W, H), palette.bg)
        self.d = ImageDraw.Draw(self.img)
        self.y = MARGIN

    def title(self, text, sub=""):
        self.d.text((MARGIN, self.y), text, font=_font(30, bold=True), fill=self.c.ink)
        self.y += 40
        if sub:
            self.d.text((MARGIN, self.y), sub, font=_font(16), fill=self.c.muted)
            self.y += 26
        self.rule()

    def rule(self):
        self.d.line((MARGIN, self.y, W - MARGIN, self.y), fill=self.c.rule, width=2)
        self.y += 10

    def heading(self, text):
        if self.y > H - 80:
            return False
        self.y += 4
        self.d.text((MARGIN, self.y), text.upper(), font=_font(15, bold=True), fill=self.c.accent)
        self.y += 22
        return True

    def line(self, text, mono=False, size=15):
        font = _font(size, mono=mono)
        for chunk in self._wrap(text, font):
            if self.y > H - 30:
                return
            self.d.text((MARGIN, self.y), chunk, font=font, fill=self.c.ink)
            self.y += size + 6

    def table(self, header, rows, widths):
        font, bold = _font(14, mono=True), _font(14, bold=True, mono=True)
        x = MARGIN
        for h, w in zip(header, widths, strict=True):
            self.d.text((x, self.y), h, font=bold, fill=self.c.muted)
            x += w
        self.y += 20
        for row in rows:
            if self.y > H - 30:
                return
            x = MARGIN
            for cell, w in zip(row, widths, strict=False):
                self.d.text((x, self.y), str(cell), font=font, fill=self.c.ink)
                x += w
            self.y += 20
        self.y += 4

    def numbered(self, n, name, text, size=14):
        """A numbered note: "3  Ingress  text that wraps under the name"."""
        font, bold = _font(size), _font(size, bold=True)
        if self.y > H - 30:
            return
        self.d.text((MARGIN, self.y), f"{n}", font=bold, fill=self.c.accent)
        self.d.text((MARGIN + 26, self.y), name, font=bold, fill=self.c.ink)
        indent = MARGIN + 160
        if MARGIN + 26 + self.d.textlength(name, font=bold) > indent - 8:   # long name: text below it
            self.y += size + 5
        for chunk in self._wrap(text, font, W - MARGIN - indent):
            if self.y > H - 30:
                return
            self.d.text((indent, self.y), chunk, font=font, fill=self.c.ink)
            self.y += size + 5
        self.y += 3

    def paste(self, img):
        self.img.paste(img, (MARGIN, self.y))
        self.y += img.height + 10

    def _wrap(self, text, font, width=W - 2 * MARGIN):
        """Greedy word wrap. Measures each word once and sums widths, which is
        close enough for these fonts and much faster than re-measuring the line."""
        space = _width(" ", font)
        out, cur, cur_w = [], [], 0.0
        for word in text.split():
            w = _width(word, font)
            if cur and cur_w + space + w > width:
                out.append(" ".join(cur))
                cur, cur_w = [word], w
            else:
                cur_w += (space if cur else 0) + w
                cur.append(word)
        return out + ([" ".join(cur)] if cur else [])

    def save(self, path):
        save_png(self.img, path)


def flight_page(card, mission, path):
    """card/mission are plain dicts prepared by the generator."""
    p = Page(NIGHT if mission.get("night") else DAY)
    p.title(f"{card['name']}  ·  {card['aircraft']}",
            f"{mission['title']}  ·  {mission['start']}  ·  {card['squadron'] or 'Mission Maker'}")
    p.heading("Tasking")
    for t in mission["tasking"]:
        p.line(t)
    p.heading("Flight")
    p.line(f"{card['seats']} player seat(s)" + (f" + {card['ai']} AI wingmen" if card["ai"] else "")
           + f" from {card['base']} ({card['start']} start). Loadout: {card['loadout']}.")
    if card.get("pilots"):
        p.line("Pilots: " + ", ".join(card["pilots"]))
    if card.get("timing"):
        p.line(card["timing"] + ".")
    p.heading("Steerpoints")
    p.table(["#", "NAME", "POSITION", "ALT FT", "BULLS"],
            [(i, s["name"][:13], s["latlon"], s["alt_ft"], s["bulls"])
             for i, s in enumerate(card["steerpoints"], start=1)],
            [36, 150, 290, 110, 110])
    if card.get("radios"):
        p.heading("Radio presets")
        header, rows = comms.channel_rows(card["radios"])
        p.table(header, rows, [40] + [210] * (len(header) - 1))
    p.heading("Support")
    for line in mission["support"] or ["None."]:
        p.line(line)
    if mission["threats"]:
        p.heading("Known threats")
        for line in mission["threats"]:
            p.line(line)
    p.heading("Environment")
    p.line(mission["weather"])
    p.line(f"Bullseye {mission['bullseye']}. Bearings are true.")
    if mission.get("home"):
        p.heading("Home field")
        p.line(mission["home"])
    p.save(path)


def _nice_step(span_nm):
    """A round scale-bar length (nm) about a fifth of the sketch width."""
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200):
        if step >= span_nm / 5:
            return step
    return 500


def route_sketch(sk, width, height, c=DAY):
    """North-up sketch of the route: base, numbered waypoints, threat rings, bullseye, scale."""
    img = Image.new("RGB", (width, height), c.paper)
    d = ImageDraw.Draw(img)
    pts = [sk["origin"], *sk["points"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 0.12
    span = max(max(xs) - min(xs), (max(ys) - min(ys)) * width / height, 10.0) * (1 + 2 * pad)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    k = width / span                                   # px per km

    def px(p):
        return width / 2 + (p[0] - cx) * k, height / 2 - (p[1] - cy) * k

    small, bold = _font(12), _font(13, bold=True)
    for t in sk["threats"]:
        x, y = px(t["xy"])
        r = t["r"] * k
        if x + r < 0 or x - r > width or y + r < 0 or y - r > height:
            continue
        d.ellipse((x - r, y - r, x + r, y + r), outline=c.threat, width=2)
        d.line((x - 5, y - 5, x + 5, y + 5), fill=c.threat, width=2)
        d.line((x - 5, y + 5, x + 5, y - 5), fill=c.threat, width=2)
        d.text((x + 7, y + 2), t["name"], font=small, fill=c.threat)
    bx, by = px(sk["bulls"])
    if 0 <= bx <= width and 0 <= by <= height:
        for rr in (4, 9):
            d.ellipse((bx - rr, by - rr, bx + rr, by + rr), outline=c.muted, width=1)
        d.text((bx + 11, by - 7), "BULLS", font=small, fill=c.muted)
    xy = [px(p) for p in pts]
    d.line(xy, fill=c.ink, width=3, joint="curve")
    ox, oy = xy[0]
    d.rectangle((ox - 7, oy - 7, ox + 7, oy + 7), outline=c.ink, width=2, fill=c.paper)
    for n, ((x, y), kind) in enumerate(zip(xy[1:], sk["kinds"], strict=True), start=1):
        fill = c.accent if kind == "TGT" else c.paper
        d.ellipse((x - 11, y - 11, x + 11, y + 11), outline=c.ink, width=2, fill=fill)
        d.text((x, y), str(n), font=bold, fill=c.on_accent if kind == "TGT" else c.ink, anchor="mm")
    # north arrow and scale bar
    d.polygon([(width - 24, 14), (width - 31, 34), (width - 24, 29), (width - 17, 34)], fill=c.ink)
    d.text((width - 24, 46), "N", font=bold, fill=c.ink, anchor="mm")
    step = _nice_step(span / 1.852)
    bar = step * 1.852 * k
    d.line((12, height - 16, 12 + bar, height - 16), fill=c.ink, width=3)
    for x in (12, 12 + bar):
        d.line((x, height - 22, x, height - 10), fill=c.ink, width=2)
    d.text((18 + bar, height - 23), f"{step} nm", font=small, fill=c.ink)
    d.rectangle((0, 0, width - 1, height - 1), outline=c.rule, width=2)
    return img


def route_page(log, mission, path):
    """Second page for a flight: route sketch, nav log and what to do at each waypoint."""
    p = Page(NIGHT if mission.get("night") else DAY)
    p.title(f"{log['name']}  ·  Route", f"{mission['title']}  ·  {log['aircraft']}  ·  bearings true")
    p.paste(route_sketch(log["sketch"], W - 2 * MARGIN, 330, p.c))
    p.heading("Nav log")
    p.table(["#", "NAME", "CRS", "LEG", "TOTAL", "ALT FT", "KT", "ETA"],
            [(r["n"], r["name"][:15], r["crs"], r["leg"], r["total"], r["alt"], r["kt"], r["eta"])
             for r in log["rows"]],
            [32, 150, 60, 60, 76, 120, 60, 70])
    p.line(log["eta_note"] + " Distances in nm.", size=12)
    p.heading("At each waypoint")
    for n, name, text in log["notes"]:
        p.numbered(n, name, text)
    p.save(path)


def text_pages(title, sub, text, palette=DAY, size=14):
    """A plain-text document (e.g. the briefing, or a pilot's notes page) as kneeboard-sized
    pages; ALL-CAPS lines become headings. Returns PIL images, starting a new page whenever
    one fills up."""
    pages = [Page(palette)]
    pages[0].title(title, sub)
    for raw in text.splitlines():
        p = pages[-1]
        if p.y > H - 60:
            pages.append(Page(palette))
            p = pages[-1]
            p.title(title, f"{sub}  ·  page {len(pages)}")
        stripped = raw.strip()
        if not stripped:
            p.y += 6
        elif stripped.isupper() and len(stripped) < 40:
            p.heading(stripped)
        else:
            p.line(stripped, size=size)
    return [p.img for p in pages]
