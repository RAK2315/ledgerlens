"""Turn the organiser's PDF template into a JSON layer of images, vector paths and text for html2pptx.js."""
import json
from pathlib import Path

import pymupdf
from PIL import Image

PDF = Path.home() / "Downloads" / "fintechstico_submission_format.pdf"
HERE = Path(__file__).parent
ASSETS = HERE.parent / "out" / "template_assets"
ASSETS.mkdir(parents=True, exist_ok=True)
PT = 1 / 108  # 1440pt page width maps to 13.333in


def hexcol(c):
    return "".join(f"{round(v * 255):02X}" for v in c[:3]) if c else None


def path_points(d):
    """Convert one PyMuPDF drawing into pptxgenjs custGeom points relative to its bbox, in inches."""
    xs, ys, segs = [], [], []
    for it in d["items"]:
        op = it[0]
        if op == "l":
            segs.append(("l", it[1], it[2]))
        elif op == "c":
            segs.append(("c", it[1], it[2], it[3], it[4]))
        elif op == "re":
            r = it[1]
            segs.append(("re", r))
        elif op == "qu":
            q = it[1]
            segs.append(("qu", q))
    for s in segs:
        pts = [s[1].tl, s[1].br] if s[0] == "re" else ([s[1].ul, s[1].ur, s[1].ll, s[1].lr] if s[0] == "qu" else s[1:])
        for p in pts:
            xs.append(p.x)
            ys.append(p.y)
    if not xs:
        return None
    x0, y0 = min(xs), min(ys)
    w, h = max(max(xs) - x0, 0.5), max(max(ys) - y0, 0.5)
    f = lambda p: {"x": round((p.x - x0) * PT, 5), "y": round((p.y - y0) * PT, 5)}
    out, cur = [], None
    for s in segs:
        if s[0] == "re":
            r = s[1]
            out += [{**f(r.tl), "moveTo": True}, f(r.tr), f(r.br), f(r.bl), {"close": True}]
            cur = None
            continue
        if s[0] == "qu":
            q = s[1]
            out += [{**f(q.ul), "moveTo": True}, f(q.ur), f(q.lr), f(q.ll), {"close": True}]
            cur = None
            continue
        start = s[1]
        if cur is None or abs(cur.x - start.x) > 0.01 or abs(cur.y - start.y) > 0.01:
            out.append({**f(start), "moveTo": True})
        if s[0] == "l":
            out.append(f(s[2]))
            cur = s[2]
        else:
            c1, c2, end = f(s[2]), f(s[3]), f(s[4])
            out.append({**end, "curve": {"type": "cubic", "x1": c1["x"], "y1": c1["y"], "x2": c2["x"], "y2": c2["y"]}})
            cur = s[4]
    if d.get("closePath"):
        out.append({"close": True})
    return {"x": round(x0 * PT, 5), "y": round(y0 * PT, 5), "w": round(w * PT, 5), "h": round(h * PT, 5), "points": out}


doc = pymupdf.open(PDF)
pages = []
for pi, page in enumerate(doc):
    W, H = page.rect.width, page.rect.height
    layer = {"bg": None, "paths": [], "images": [], "texts": []}
    for d in page.get_drawings():
        r = d["rect"]
        if d.get("fill") and r.width >= W - 1 and r.height >= H - 1:
            layer["bg"] = hexcol(d["fill"])
            continue
        fa = d.get("fill_opacity")
        fa = 1 if fa is None else fa
        if (not d.get("fill") or fa == 0) and not d.get("color"):
            continue
        geo = path_points(d)
        if not geo:
            continue
        geo["fill"] = hexcol(d.get("fill"))
        geo["fillAlpha"] = fa
        geo["line"] = hexcol(d.get("color"))
        geo["lineAlpha"] = 1 if d.get("stroke_opacity") is None else d.get("stroke_opacity")
        geo["lineWidth"] = round((d.get("width") or 0) * 0.6667, 3)  # pt on a 960pt-wide slide
        layer["paths"].append(geo)
    for im in page.get_images(full=True):
        xref, smask = im[0], im[1]
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n - pix.alpha >= 4:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        if smask:
            pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, smask))
        name = f"p{pi + 1}_x{xref}.png"
        pix.save(ASSETS / name)
        for r in page.get_image_rects(xref):
            vis = r & page.rect
            if vis.is_empty:
                continue
            img = Image.open(ASSETS / name)
            sx, sy = img.width / r.width, img.height / r.height
            box = (round((vis.x0 - r.x0) * sx), round((vis.y0 - r.y0) * sy), round((vis.x1 - r.x0) * sx), round((vis.y1 - r.y0) * sy))
            if box != (0, 0, img.width, img.height):
                img.crop(box).save(ASSETS / name)
            layer["images"].append({"file": str(ASSETS / name), "x": vis.x0 * PT, "y": vis.y0 * PT, "w": vis.width * PT, "h": vis.height * PT})
    seen = {}
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                if not s["text"].strip():
                    continue
                # stacked duplicates share a bbox; the last one drawn is the visible one
                seen[(s["text"], tuple(round(v) for v in s["bbox"]))] = s
    for s in seen.values():
        x0, y0, x1, y1 = s["bbox"]
        layer["texts"].append({
            "text": s["text"], "font": s["font"], "size": round(s["size"] * 0.6667, 2), "color": f"{s['color']:06X}",
            "x0": x0 * PT, "x1": x1 * PT, "y0": y0 * PT, "y1": y1 * PT, "origin": s["origin"][1] * PT,
        })
    pages.append(layer)

(HERE / "template.json").write_text(json.dumps(pages), encoding="utf-8")
print([(len(p["paths"]), len(p["images"]), len(p["texts"]), p["bg"]) for p in pages])
