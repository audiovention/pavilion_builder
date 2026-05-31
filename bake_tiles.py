#!/usr/bin/env python3
"""Crop white borders off the tile photos and bake them into a self-contained HTML.

Two tasks, run as one pipeline:

  1. AUTO-CROP — trim the white photographic border around each tile so the
     texture maps edge-to-edge. (Some product shots — e.g. the Kalina wall
     tile — have a light frame that otherwise reads as a fake grout line.)

  2. BAKE — replace every `tiles/*.jpg` reference in the HTML with a base64
     `data:` URI of the cropped image, producing a single self-contained
     <out>.html that needs no `tiles/` folder (and works straight off
     `file://`, since it fetches nothing).

Usage
-----
  python3 bake_tiles.py                     # crop -> tiles/cropped/, bake bathrooms_baked.html
  python3 bake_tiles.py --inplace           # also overwrite tiles/*.jpg (originals -> tiles/_originals/)
  python3 bake_tiles.py --no-bake           # only crop
  python3 bake_tiles.py --no-crop           # only bake, using the images as-is
  python3 bake_tiles.py --white 248 --erode 3 --pad 2 --quality 82 --max-size 1024

Tuning
------
  --white N     pixels with grey >= N count as "white" border       (default 244)
  --erode N     odd window that erodes speckle before bbox detect    (default 3)
  --pad N       keep N px of border after cropping                   (default 0)
  --max-trim F  never trim more than fraction F off any one side     (default 0.45)
  --quality Q   JPEG quality for the baked data URIs                 (default 85)
  --max-size N  downscale so the longest side <= N px (0 = keep)     (default 0)

Requires: Pillow  ->  pip install Pillow
"""
import argparse
import base64
import io
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("This script needs Pillow.  Install it with:  pip install Pillow")


# ── cropping ──────────────────────────────────────────────────────────────
def content_bbox(img, white=244, erode=3):
    """Bounding box of the non-white content, robust to JPEG speckle in the border."""
    gray = img.convert("L")
    # content = darker than the white threshold
    mask = gray.point(lambda p: 255 if p < white else 0)
    if erode and erode >= 3 and erode % 2 == 1:
        # MinFilter erodes the white 255 islands, so lone noise pixels in the
        # border don't keep the bbox from shrinking.
        mask = mask.filter(ImageFilter.MinFilter(erode))
    return mask.getbbox()


def autocrop(img, white=244, erode=3, pad=0, max_trim=0.45):
    """Return (cropped_image, bbox_or_None). bbox is None when nothing was trimmed."""
    w, h = img.size
    bbox = content_bbox(img, white, erode)
    if not bbox:
        return img, None
    l, t, r, b = bbox
    # safety clamp: never eat more than `max_trim` of a side (guards a near-white image)
    l = min(l, int(w * max_trim))
    t = min(t, int(h * max_trim))
    r = max(r, w - int(w * max_trim))
    b = max(b, h - int(h * max_trim))
    # optional padding kept around the content
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(w, r + pad)
    b = min(h, b + pad)
    if (l, t, r, b) == (0, 0, w, h):
        return img, None
    return img.crop((l, t, r, b)), (l, t, r, b)


# ── encoding ──────────────────────────────────────────────────────────────
def to_data_uri(img, quality=85, max_size=0):
    """Encode a PIL image as a JPEG base64 data: URI. Returns (uri, jpeg_byte_len)."""
    im = img
    if max_size and max(im.size) > max_size:
        im = im.copy()
        im.thumbnail((max_size, max_size), Image.LANCZOS)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True)
    data = buf.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii"), len(data)


def kb(n):
    return f"{n / 1024:.0f} KB"


# ── pipeline ──────────────────────────────────────────────────────────────
def source_path(tiles_dir, name, inplace):
    """Where to read the ORIGINAL of `name` from.

    With --inplace we keep a pristine copy in tiles/_originals/ and always crop
    from it, so re-running the script is idempotent (never crops a crop)."""
    live = tiles_dir / name
    if inplace:
        backup = tiles_dir / "_originals" / name
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, backup)
        return backup
    return live


def prepare(tiles_dir, name, args):
    """Load `name`, crop it (unless --no-crop), return (image, bbox_or_None, orig_size)."""
    src = source_path(tiles_dir, name, args.inplace)
    img = Image.open(src)
    img.load()
    orig = img.size
    if args.no_crop:
        return img, None, orig
    cropped, bbox = autocrop(img, args.white, args.erode, args.pad, args.max_trim)
    return cropped, bbox, orig


def main():
    ap = argparse.ArgumentParser(description="Crop tile white borders and bake them into a self-contained HTML.")
    ap.add_argument("--tiles-dir", default="tiles", help="folder with the tile JPGs (default: tiles)")
    ap.add_argument("--html", default="bathrooms.html", help="source HTML to bake (default: bathrooms.html)")
    ap.add_argument("--out", default="bathrooms_baked.html", help="self-contained HTML to write")
    ap.add_argument("--crop-dir", default=None, help="where to write cropped JPGs (default: <tiles-dir>/cropped)")
    ap.add_argument("--inplace", action="store_true", help="overwrite tiles/*.jpg (originals saved to tiles/_originals/)")
    ap.add_argument("--no-crop", action="store_true", help="skip cropping; bake images as-is")
    ap.add_argument("--no-bake", action="store_true", help="skip baking; only crop")
    ap.add_argument("--white", type=int, default=244)
    ap.add_argument("--erode", type=int, default=3)
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--max-trim", type=float, default=0.45)
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--max-size", type=int, default=0)
    args = ap.parse_args()

    tiles_dir = Path(args.tiles_dir)
    if not tiles_dir.is_dir():
        sys.exit(f"tiles dir not found: {tiles_dir}")

    # The set of images we operate on = the tile JPGs referenced by the HTML if
    # it exists, else every top-level *.jpg in the tiles dir.
    html_text = None
    if Path(args.html).is_file():
        html_text = Path(args.html).read_text(encoding="utf-8")
        refs = sorted(set(re.findall(r"tiles/[A-Za-z0-9_.\-/]+\.(?:jpe?g|png)", html_text)))
        names = [Path(r).name for r in refs]
    else:
        refs = []
        names = sorted(p.name for p in tiles_dir.glob("*.jpg"))
        if not args.no_bake:
            print(f"! HTML '{args.html}' not found — baking disabled, cropping only.")
            args.no_bake = True

    if not names:
        sys.exit("no tile images found to process")

    crop_dir = Path(args.crop_dir) if args.crop_dir else tiles_dir / "cropped"
    if not args.no_crop and not args.inplace:
        crop_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(names)} tile(s) from {tiles_dir}/\n")
    print(f"{'tile':32} {'original':>11}  {'cropped':>11}  {'jpeg(b64)':>10}")
    print("-" * 70)

    uris = {}          # name -> data URI
    total_jpeg = 0
    for name in names:
        path = tiles_dir / name
        if not path.exists():
            print(f"{name:32} {'MISSING':>11}  (referenced by HTML but not on disk — skipped)")
            continue
        img, bbox, orig = prepare(tiles_dir, name, args)

        # task 1 output: write the cropped JPG
        if not args.no_crop:
            dest = (tiles_dir / name) if args.inplace else (crop_dir / name)
            save_img = img if img.mode in ("RGB", "L") else img.convert("RGB")
            save_img.save(dest, format="JPEG", quality=max(args.quality, 90), optimize=True)

        # task 2 output: data URI (uses the cropped pixels)
        jb = 0
        if not args.no_bake:
            uri, jb = to_data_uri(img, args.quality, args.max_size)
            uris[name] = uri
            total_jpeg += jb

        crop_str = f"{img.size[0]}x{img.size[1]}" if bbox else "(no trim)"
        print(f"{name:32} {f'{orig[0]}x{orig[1]}':>11}  {crop_str:>11}  {kb(jb) if jb else '-':>10}")

    # ── bake the HTML ──
    if not args.no_bake and html_text is not None:
        baked = html_text
        replaced = 0
        for ref in refs:
            name = Path(ref).name
            if name in uris:
                baked = baked.replace(ref, uris[name])
                replaced += 1
        out = Path(args.out)
        out.write_text(baked, encoding="utf-8")
        print("-" * 70)
        print(f"Baked {replaced}/{len(refs)} texture(s) into {out}")
        print(f"  embedded JPEG payload : {kb(total_jpeg)}  (base64 ≈ {kb(total_jpeg * 4 / 3)})")
        print(f"  self-contained HTML   : {kb(out.stat().st_size)}  — opens straight off file://")

    if not args.no_crop:
        where = f"{tiles_dir}/ (originals in {tiles_dir}/_originals/)" if args.inplace else f"{crop_dir}/"
        print(f"Cropped images written to {where}")


if __name__ == "__main__":
    main()
