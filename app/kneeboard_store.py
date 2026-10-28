"""Kneeboards pilots edit in the Briefing Room, and the squadron kneeboard library.

DCS shows a mission's kneeboard pages per aircraft type: the images in KNEEBOARD/<type id>/
IMAGES/ in the .miz, in filename order, for everyone flying that type. A pilot with a seat
in that type (the server checks the roster) can hide, show and reorder its pages, add a
notes page and upload pages (PNG, JPG or PDF); each change rewrites that part of the .miz.

One mission's state is <stem>.kb.json plus its page images in the <stem>.kb/ folder: the
generated pages (copied out of the .miz on the first edit, so hidden pages and Reset still
work), uploads and notes pages. Uploads are decoded and re-encoded as plain PNGs, so only
pixels reach the .miz.

The squadron library is kneeboards/<type id>/ in the missions folder (index.json plus PNGs).
Its pages go into every new mission with that type, where they can be hidden like any other.
Callers hold the mission's lock (server._locked) around anything that changes a mission.
"""
import io
import json
import re
import secrets
import shutil
import time
import warnings
import zipfile

from PIL import Image, ImageOps

from . import kneeboard, paths

MAX_PAGES = 30             # per aircraft type in one mission
MAX_PDF_PAGES = 20         # read from one PDF
MAX_LIBRARY = 40           # per aircraft type
MAX_SIDE = (1536, 2048)    # uploads are kept up to twice the size of a generated page
TYPE_ID = re.compile(r"[\w\-.]{1,60}")
PAGE_ID = re.compile(r"[gunl]:[\w\-.]{1,80}")
IMAGE_FORMATS = {"PNG", "JPEG", "WEBP", "GIF", "BMP"}


class KneeboardError(ValueError):
    """Something a pilot can fix: a bad upload, too many pages, an unknown page."""


def _out():
    return paths.output_dir()


def state_path(stem):
    return _out() / f"{stem}.kb.json"


def pages_dir(stem):
    return _out() / f"{stem}.kb"


def library_dir(type_id=None):
    root = _out() / "kneeboards"
    return root / type_id if type_id else root


# ------------------------------------------------------------------ the .miz
def _miz_pages(z):
    """{type id: [entry names, in the order DCS shows them]} from a .miz."""
    out = {}
    for name in z.namelist():
        m = re.fullmatch(r"KNEEBOARD/([^/]+)/IMAGES/+([^/]+\.(?:png|jpe?g))", name, re.IGNORECASE)
        if m:
            out.setdefault(m.group(1), []).append(name)
    return {t: sorted(names, key=lambda n: n.rsplit("/", 1)[1]) for t, names in out.items()}


def flight_types(stem):
    """{flight number: type id}: which type folder holds each flight's kneeboard_<n>.png."""
    with zipfile.ZipFile(_out() / f"{stem}.miz") as z:
        found = {}
        for type_id, names in _miz_pages(z).items():
            for n in names:
                m = re.fullmatch(r"(?:\d+_)?kneeboard_(\d+)\.png", n.rsplit("/", 1)[1])
                if m:
                    found[int(m.group(1))] = type_id
    return found


def _type_of(brief, flight_number, types):
    f = brief["flights"][flight_number - 1]
    return f.get("type") or types.get(flight_number)


def types_in(stem, brief):
    """{type id: {"label": aircraft name, "flights": [flight names]}} for the mission's player flights."""
    types, out = flight_types(stem), {}
    for i, f in enumerate(brief["flights"], start=1):
        type_id = _type_of(brief, i, types)
        if type_id:
            entry = out.setdefault(type_id, {"label": f["aircraft"], "flights": []})
            entry["flights"].append(f["name"])
    return out


def write_miz(stem, st):
    """Rewrites the .miz's KNEEBOARD folders from the state: visible pages, in order."""
    path = _out() / f"{stem}.miz"
    with zipfile.ZipFile(path) as z:
        keep = [(i, z.read(i.filename)) for i in z.infolist() if not i.filename.startswith("KNEEBOARD/")]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in keep:
            z.writestr(info, data)
        for type_id, t in st["types"].items():
            visible = [p for p in t["pages"] if not p.get("hidden")]
            for n, p in enumerate(visible, start=1):
                # DCS sorts by file name; the original name stays in it for the Briefing Room's links
                z.writestr(f"KNEEBOARD/{type_id}/IMAGES/{n:02d}_{p['file']}", _page_file(stem, p).read_bytes())
    tmp = path.with_suffix(".miz.tmp")
    tmp.write_bytes(out.getvalue())
    tmp.replace(path)


# ------------------------------------------------------------------ state
def _page_file(stem, page):
    return pages_dir(stem) / page["file"]  # library pages are copied in too (apply_library)


def _labels(brief):
    """Generated page file name -> "Viper 1 · Route"."""
    out = {}
    for i, f in enumerate(brief["flights"], start=1):
        for k in f.get("kneeboards") or [{"page": str(i), "label": "Flight"}]:
            out[f"kneeboard_{k['page']}.png"] = f"{f['name']} · {k['label']}"
    return out


def load(stem):
    try:
        return json.loads(state_path(stem).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _save(stem, st):
    tmp = state_path(stem).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(state_path(stem))


def ensure(stem, brief):
    """The mission's state, created from the .miz the first time (generated pages copied out)."""
    st = load(stem)
    if st:
        return st
    labels = _labels(brief)
    folder = pages_dir(stem)
    folder.mkdir(exist_ok=True)
    st = {"types": {}, "log": []}
    with zipfile.ZipFile(_out() / f"{stem}.miz") as z:
        for type_id, names in _miz_pages(z).items():
            pages = []
            for name in names:
                file = re.sub(r"^\d+_", "", name.rsplit("/", 1)[1])
                (folder / file).write_bytes(z.read(name))
                pages.append({"id": f"g:{file.rsplit('.', 1)[0]}", "kind": "generated", "file": file,
                              "label": labels.get(file, file), "hidden": False})
            st["types"][type_id] = {"pages": pages, "original": [p["id"] for p in pages]}
    _save(stem, st)
    return st


def _type_state(st, type_id):
    t = st["types"].get(type_id)
    if t is None:
        if not TYPE_ID.fullmatch(type_id or ""):
            raise KneeboardError("Unknown aircraft type.")
        t = st["types"][type_id] = {"pages": [], "original": []}
    return t


def _log(st, by, type_id, what):
    st["log"] = (st.get("log") or [])[-199:] + [{"at": time.time(), "by": by, "type": type_id, "what": what}]


def page_bytes(stem, page_id):
    """A page image for the Briefing Room, hidden or not; None if there's no such page."""
    st = load(stem)
    for t in (st or {}).get("types", {}).values():
        for p in t["pages"]:
            if p["id"] == page_id:
                f = _page_file(stem, p)
                return f.read_bytes() if f.exists() else None
    return None


def view(stem, brief):
    """What the Kneeboards tab shows: per aircraft type, its pages (hidden ones too) and who did what."""
    st = load(stem)
    if st is None:  # never edited: read the .miz without writing anything
        labels = _labels(brief)
        with zipfile.ZipFile(_out() / f"{stem}.miz") as z:
            miz = _miz_pages(z)
        st = {"types": {t: {"pages": [{"id": f"g:{n.rsplit('/', 1)[1][:-4]}", "kind": "generated",
                                       "label": labels.get(n.rsplit("/", 1)[1], n.rsplit("/", 1)[1]),
                                       "hidden": False} for n in names]} for t, names in miz.items()},
              "log": []}
    out = []
    for type_id, info in types_in(stem, brief).items():
        t = st["types"].get(type_id, {"pages": []})
        out.append({"type": type_id, "label": info["label"], "flights": info["flights"],
                    "pages": [{k: p.get(k) for k in ("id", "kind", "label", "hidden", "by")} for p in t["pages"]],
                    "library": [{k: e[k] for k in ("id", "label", "by")} for e in library(type_id)]})
    return {"types": out, "log": list(reversed(st.get("log") or []))[:50]}


# ------------------------------------------------------------------ changes
def arrange(stem, brief, type_id, order, by):
    """order: [{"id", "hidden"}] covering every page of that type, in the new order."""
    st = ensure(stem, brief)
    t = _type_state(st, type_id)
    by_id = {p["id"]: p for p in t["pages"]}
    ids = [str((o or {}).get("id")) for o in order if isinstance(o, dict)]
    if sorted(ids) != sorted(by_id):
        raise KneeboardError("The pages changed meanwhile: reload and try again.")
    t["pages"] = [{**by_id[o["id"]], "hidden": bool(o.get("hidden"))} for o in order]
    _log(st, by, type_id, "rearranged the pages")
    _save(stem, st)
    write_miz(stem, st)


def remove(stem, brief, type_id, page_id, by):
    """Deletes an uploaded or notes page. Generated and library pages can only be hidden."""
    st = ensure(stem, brief)
    t = _type_state(st, type_id)
    page = next((p for p in t["pages"] if p["id"] == page_id), None)
    if not page or page["kind"] not in ("upload", "notes"):
        raise KneeboardError("Only pages pilots added can be deleted; hide the others.")
    t["pages"].remove(page)
    (pages_dir(stem) / page["file"]).unlink(missing_ok=True)
    _log(st, by, type_id, f"deleted {page['label']}")
    _save(stem, st)
    write_miz(stem, st)


def reset(stem, brief, type_id, by):
    """Back to the pages the mission was built with; pilots' uploads and notes are deleted."""
    st = ensure(stem, brief)
    t = _type_state(st, type_id)
    original = set(t["original"])
    for p in t["pages"]:
        if p["id"] not in original and not p["id"].startswith("l:"):
            (pages_dir(stem) / p["file"]).unlink(missing_ok=True)
    pages = {p["id"]: p for p in t["pages"]}
    t["pages"] = [{**pages[i], "hidden": False} for i in t["original"] if i in pages]
    _log(st, by, type_id, "reset to the original pages")
    _save(stem, st)
    write_miz(stem, st)


def _add_pages(stem, st, type_id, images, label, kind, by):
    t = _type_state(st, type_id)
    if len(t["pages"]) + len(images) > MAX_PAGES:
        raise KneeboardError(f"That's more than {MAX_PAGES} pages for one aircraft.")
    pages_dir(stem).mkdir(exist_ok=True)
    added = []
    for n, img in enumerate(images, start=1):
        key = secrets.token_hex(4)
        prefix = "u" if kind == "upload" else "n"
        file = f"{prefix}_{key}.png"
        _save_image(img, pages_dir(stem) / file)
        page_label = label if len(images) == 1 else f"{label} ({n}/{len(images)})"
        page = {"id": f"{prefix}:{key}", "kind": kind, "file": file, "label": page_label, "hidden": False, "by": by}
        t["pages"].append(page)
        added.append(page)
    return added


def add_notes(stem, brief, type_id, title, text, by, night=False):
    title = re.sub(r"[\x00-\x1f]", "", str(title or "")).strip()[:60] or "Notes"
    text = str(text or "").replace("\r", "")[:4000].strip()
    if not text:
        raise KneeboardError("The notes page is empty.")
    st = ensure(stem, brief)
    label = types_in(stem, brief).get(type_id, {}).get("label", type_id)
    images = kneeboard.text_pages(title, f"{label}  ·  by {by}", text,
                                  palette=kneeboard.NIGHT if night else kneeboard.DAY, size=16)
    pages = _add_pages(stem, st, type_id, images, title, "notes", by)
    _log(st, by, type_id, f"added notes page {title}")
    _save(stem, st)
    write_miz(stem, st)
    return pages


def add_upload(stem, brief, type_id, filename, data, by, to_library=False):
    """A PNG, JPG or PDF file as one or more kneeboard pages; optionally into the library too."""
    images = decode(data)
    label = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", re.sub(r"[^\w \-.()]", "", str(filename or "")))[:60].strip() or "Page"
    st = ensure(stem, brief)
    pages = _add_pages(stem, st, type_id, images, label, "upload", by)
    if to_library:
        for img, page in zip(images, pages, strict=True):
            add_to_library(type_id, page["label"], img, by)
    _log(st, by, type_id, f"uploaded {label}" + (" (also saved to the squadron library)" if to_library else ""))
    _save(stem, st)
    write_miz(stem, st)
    return pages


# ------------------------------------------------------------------ uploads
def decode(data):
    """Bytes of an image or a PDF -> kneeboard-sized RGB images. Raises KneeboardError."""
    if data[:5] == b"%PDF-":
        return _decode_pdf(data)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(data))
            if img.format not in IMAGE_FORMATS:
                raise KneeboardError("Upload a PNG, JPG or PDF.")
            img.load()
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise KneeboardError("That file isn't an image or PDF that can be read.") from e
    return [_fit(ImageOps.exif_transpose(img))]


def _decode_pdf(data):
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise KneeboardError("PDF pages can't be read on this install; upload PNG or JPG.") from e
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as e:
        raise KneeboardError("That PDF can't be read.") from e
    try:
        if len(pdf) > MAX_PDF_PAGES:
            raise KneeboardError(f"That PDF has {len(pdf)} pages; upload at most {MAX_PDF_PAGES} at a time.")
        images = []
        for i in range(len(pdf)):
            page = pdf[i]
            w, h = page.get_size()
            scale = min(MAX_SIDE[0] / w, MAX_SIDE[1] / h, 4)
            images.append(_fit(page.render(scale=scale).to_pil()))
            page.close()
        return images
    finally:
        pdf.close()


def _fit(img):
    img = img.convert("RGB")
    img.thumbnail(MAX_SIDE, Image.LANCZOS)
    return img


def _save_image(img, path):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    path.write_bytes(buf.getvalue())


# ------------------------------------------------------------------ squadron library
def library(type_id):
    try:
        entries = json.loads((library_dir(type_id) / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in entries if (library_dir(type_id) / e["file"]).exists()]


def _save_library(type_id, entries):
    folder = library_dir(type_id)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "index.json.tmp"
    tmp.write_text(json.dumps(entries, indent=1), encoding="utf-8")
    tmp.replace(folder / "index.json")


def add_to_library(type_id, label, img, by):
    if not TYPE_ID.fullmatch(type_id or ""):
        raise KneeboardError("Unknown aircraft type.")
    entries = library(type_id)
    if len(entries) >= MAX_LIBRARY:
        raise KneeboardError(f"The squadron library already has {MAX_LIBRARY} pages for this aircraft.")
    key = secrets.token_hex(4)
    library_dir(type_id).mkdir(parents=True, exist_ok=True)
    _save_image(img, library_dir(type_id) / f"{key}.png")
    entries.append({"id": key, "file": f"{key}.png", "label": label, "by": by, "at": time.time()})
    _save_library(type_id, entries)


def remove_from_library(type_id, entry_id):
    """Takes a page out of the library; missions that already have it keep it."""
    entries = library(type_id)
    entry = next((e for e in entries if e["id"] == entry_id), None)
    if entry is None:
        raise KneeboardError("No such library page.")
    entries.remove(entry)
    _save_library(type_id, entries)
    (library_dir(type_id) / entry["file"]).unlink(missing_ok=True)
    return entry


def apply_library(stem, brief):
    """A new mission: adds the library pages for its aircraft types. Returns True if it changed the .miz."""
    wanted = {t: library(t) for t in types_in(stem, brief)}
    wanted = {t: e for t, e in wanted.items() if e}
    if not wanted:
        return False
    st = ensure(stem, brief)
    for type_id, entries in wanted.items():
        t = _type_state(st, type_id)
        room = MAX_PAGES - len(t["pages"])
        for e in entries[:max(room, 0)]:
            # Copied into the mission, so later library changes don't touch it.
            file = f"l_{e['id']}.png"
            shutil.copyfile(library_dir(type_id) / e["file"], pages_dir(stem) / file)
            page = {"id": f"l:{e['id']}", "kind": "library", "file": file, "label": e["label"],
                    "hidden": False, "by": e.get("by")}
            t["pages"].append(page)
            t["original"].append(page["id"])
    _save(stem, st)
    write_miz(stem, st)
    return True
