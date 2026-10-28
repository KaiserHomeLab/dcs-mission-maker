"""Downloads the real 3-view drawings used on the Threat ID blueprint sheets.

Reads drawings.json (pinned Wikimedia Commons files with SHA-1 checksums),
verifies each download, shrinks very large raster images, and writes them plus
an index with author/licence credits to OUT_DIR. Commons rate-limits, so this
is slow and polite. Failures are soft: a drawing that can't be fetched is
skipped and the sheet falls back to the generated drawing.
"""
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

MANIFEST = sys.argv[1] if len(sys.argv) > 1 else "drawings.json"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "/srv/drawings"
UA = {"User-Agent": "DCSMissionMaker/1.0 (self-hosted DCS mission generator; image build)"}
MAX_W = 2000


def fetch(url):
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(int(e.headers.get("retry-after") or 15) + 5 * attempt)
                continue
            raise
    raise RuntimeError("still rate-limited")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(MANIFEST) as fh:
        manifest = json.load(fh)
    index, failed = {}, []
    for key, d in manifest.items():
        name = d["file"]
        path = os.path.join(OUT_DIR, name)
        try:
            data = fetch(d["url"])
            if hashlib.sha1(data).hexdigest() != d["sha1"]:
                raise ValueError("checksum mismatch")
            if d["mime"] in ("image/jpeg", "image/png", "image/gif") and d.get("w", 0) > MAX_W:
                from PIL import Image
                img = Image.open(io.BytesIO(data)).convert("L")
                img.thumbnail((MAX_W, MAX_W * 2))
                buf = io.BytesIO()
                img.save(buf, "PNG", optimize=True)
                data = buf.getvalue()
                name = os.path.splitext(name)[0] + ".png"
                path = os.path.join(OUT_DIR, name)
            with open(path, "wb") as fh:
                fh.write(data)
            index[key] = {"file": name, "title": d["title"], "artist": d["artist"],
                          "license": d["license"], "page": d["page"],
                          "lowres": d["mime"] != "image/svg+xml" and d.get("w", 0) < 900}
            print(f"ok   {key}", flush=True)
        except Exception as e:  # noqa: BLE001 - soft failure, sheet falls back
            failed.append(key)
            print(f"skip {key}: {e}", flush=True)
        time.sleep(4)
    with open(os.path.join(OUT_DIR, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1)
    print(f"{len(index)} drawings, {len(failed)} skipped", flush=True)


if __name__ == "__main__":
    main()
