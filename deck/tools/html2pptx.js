// Converts deck/index.html into an editable PPTX: boxes become shapes, text becomes text boxes,
// icons and inline SVG drawings become transparent PNGs. Also exports deck/images for reuse.
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");
const pptxgen = require("pptxgenjs");

const DECK = path.resolve(__dirname, "..");
const OUT = path.join(DECK, "out");
const ASSETS = path.join(OUT, "assets");
const IMAGES = path.join(DECK, "images");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PX = 1 / 144; // 1920px slide maps to 13.333in
const NOTES = JSON.parse(fs.readFileSync(path.join(__dirname, "notes.json"), "utf8"));
const TEMPLATE = JSON.parse(fs.readFileSync(path.join(__dirname, "template.json"), "utf8"));
// template text the HTML replaces with its own copy, by slide index
const LS_SCALE = 1.263, LS_TRACK = 0.054, LS_DY = -0.00348;
const SKIP_TEMPLATE_TEXT = { 2: ["Team Name", "TEAM MEMBERS"] };

for (const d of [OUT, ASSETS, IMAGES, path.join(IMAGES, "icons"), path.join(IMAGES, "mockups"), path.join(IMAGES, "diagrams")]) fs.mkdirSync(d, { recursive: true });

// Runs in the page: returns per-slide lists of shapes, text boxes and image targets in paint order.
function extract() {
  const slides = [...document.querySelectorAll("section.slide")];
  const rgba = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(",").map((v) => parseFloat(v));
    const a = p.length > 3 ? p[3] : 1;
    if (a === 0) return null;
    return { hex: p.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, "0")).join("").toUpperCase(), a };
  };
  const firstGradientColor = (bg) => {
    const m = bg && bg.match(/linear-gradient\([^,]+,\s*(rgba?\([^)]+\))/);
    return m ? rgba(m[1]) : null;
  };
  let imgId = 0;
  return slides.map((slide, si) => {
    const base = slide.getBoundingClientRect();
    const items = [];
    const rel = (r) => ({ x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height });

    const clipAncestor = (el) => {
      for (let a = el.parentElement; a && a !== slide; a = a.parentElement) {
        const cs = getComputedStyle(a);
        if (cs.overflow === "hidden" && parseFloat(cs.borderTopLeftRadius) > 0) return a;
      }
      return null;
    };

    const emitShape = (el, cs) => {
      const r = el.getBoundingClientRect();
      if (r.width < 0.5 || r.height < 0.5) return;
      let fill = rgba(cs.backgroundColor);
      if (!fill && cs.backgroundImage.includes("gradient")) fill = firstGradientColor(cs.backgroundImage);
      const sides = ["Top", "Right", "Bottom", "Left"].map((s) => ({
        s, w: parseFloat(cs["border" + s + "Width"]) || 0, c: rgba(cs["border" + s + "Color"]), st: cs["border" + s + "Style"],
      })).filter((b) => b.w > 0 && b.c && b.st !== "none");
      if (!fill && !sides.length) return;
      const uniform = sides.length === 4 && sides.every((b) => b.w === sides[0].w && b.c.hex === sides[0].c.hex && b.st === sides[0].st);
      const radius = parseFloat(cs.borderTopLeftRadius) || 0;
      const box = rel(r);
      const shape = { kind: "shape", ...box, fill, radius, shadow: cs.boxShadow !== "none" };
      if (uniform) shape.line = { hex: sides[0].c.hex, a: sides[0].c.a, w: sides[0].w, dash: sides[0].st === "dashed" };
      if (radius >= Math.min(r.width, r.height) / 2 - 0.5 && Math.abs(r.width - r.height) < 1) shape.ellipse = true;
      // square-cornered children of a rounded clipping parent get the parent's corners where they touch
      const anc = clipAncestor(el);
      if (anc && !radius && fill) {
        const ar = anc.getBoundingClientRect();
        const rr = parseFloat(getComputedStyle(anc).borderTopLeftRadius);
        const near = (a, b) => Math.abs(a - b) < 1.5;
        shape.corners = {
          tl: near(r.left, ar.left) && near(r.top, ar.top), tr: near(r.right, ar.right) && near(r.top, ar.top),
          bl: near(r.left, ar.left) && near(r.bottom, ar.bottom), br: near(r.right, ar.right) && near(r.bottom, ar.bottom),
        };
        if (Object.values(shape.corners).some(Boolean)) shape.radius = rr; else delete shape.corners;
      }
      items.push(shape);
      if (!uniform) for (const b of sides) {
        const l = { kind: "line", hex: b.c.hex, a: b.c.a, w: b.w, dash: b.st === "dashed" };
        if (b.s === "Top") Object.assign(l, { x: box.x, y: box.y + b.w / 2, x2: box.x + box.w, y2: box.y + b.w / 2 });
        if (b.s === "Bottom") Object.assign(l, { x: box.x, y: box.y + box.h - b.w / 2, x2: box.x + box.w, y2: box.y + box.h - b.w / 2 });
        if (b.s === "Left") Object.assign(l, { x: box.x + b.w / 2, y: box.y, x2: box.x + b.w / 2, y2: box.y + box.h });
        if (b.s === "Right") Object.assign(l, { x: box.x + box.w - b.w / 2, y: box.y, x2: box.x + box.w - b.w / 2, y2: box.y + box.h });
        items.push(l);
      }
    };

    const runStyle = (cs) => ({
      family: cs.fontFamily.split(",")[0].replace(/["']/g, "").trim(), weight: parseInt(cs.fontWeight, 10),
      size: parseFloat(cs.fontSize), color: rgba(cs.color), italic: cs.fontStyle === "italic", spacing: parseFloat(cs.letterSpacing) || 0,
    });

    // Text owned directly by el plus its inline descendants, as styled runs with their line rects.
    const emitText = (el, cs) => {
      const runs = [];
      const rects = [];
      const walk = (node, style) => {
        for (const ch of node.childNodes) {
          if (ch.nodeType === 3) {
            const t = ch.textContent.replace(/\s+/g, " ");
            if (!t.trim() && !runs.length) continue;
            if (t.length) {
              runs.push({ text: t, ...style });
              const range = document.createRange();
              range.selectNodeContents(ch);
              for (const q of range.getClientRects()) if (q.width > 0.5) rects.push(q);
            }
          } else if (ch.nodeType === 1) {
            if (ch.tagName === "BR") { if (runs.length) runs[runs.length - 1].br = true; continue; }
            const ccs = getComputedStyle(ch);
            if (ccs.display === "inline" && !ch.classList.contains("ic")) walk(ch, runStyle(ccs));
          }
        }
      };
      walk(el, runStyle(cs));
      if (!runs.length || !rects.length) return;
      runs[0].text = runs[0].text.replace(/^\s+/, "");
      runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\s+$/, "");
      if (!runs.map((r) => r.text).join("").trim()) return;
      const left = Math.min(...rects.map((q) => q.left)), right = Math.max(...rects.map((q) => q.right));
      const top = Math.min(...rects.map((q) => q.top)), bottom = Math.max(...rects.map((q) => q.bottom));
      const tops = [];
      for (const q of rects) if (!tops.some((t) => Math.abs(t - q.top) < 4)) tops.push(q.top);
      const lh = parseFloat(cs.lineHeight);
      let align = cs.textAlign;
      if (align === "start") align = "left";
      if (align === "end") align = "right";
      const er = el.getBoundingClientRect();
      const multi = tops.length > 1;
      let x, w;
      if (multi) {
        x = er.left + parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth);
        w = er.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth);
      } else {
        w = (right - left) * 1.12 + 4;
        x = align === "center" ? (left + right) / 2 - w / 2 : align === "right" ? right - w : left;
      }
      const lineH = isNaN(lh) ? null : lh;
      const y = lineH && multi ? top - (lineH - (rects[0].height)) / 2 : top;
      const h = lineH && multi ? tops.length * lineH : bottom - top;
      items.push({ kind: "text", x: x - base.left, y: y - base.top, w, h, runs, align, multi, lineH });
    };

    const visit = (el) => {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || el.tagName === "STYLE" || el.hasAttribute("data-pptx-skip")) return;
      const isImg = el.tagName.toLowerCase() === "svg" || el.classList.contains("ic") || el.tagName === "IMG";
      if (isImg) {
        const r = el.getBoundingClientRect();
        if (r.width > 0.5 && r.height > 0.5) {
          const id = "s" + (si + 1) + "_img" + String(++imgId).padStart(3, "0");
          el.setAttribute("data-img", id);
          items.push({ kind: "image", id, ...rel(r) });
        }
        return;
      }
      if (el !== slide && cs.display !== "inline") emitShape(el, cs);
      if (el !== slide && cs.display === "inline" && cs.borderBottomStyle !== "none" && parseFloat(cs.borderBottomWidth) > 0) emitShape(el, cs);
      if (cs.display !== "inline") emitText(el, cs);
      for (const ch of el.children) visit(ch);
    };
    visit(slide);
    const bg = getComputedStyle(slide).backgroundImage.match(/url\("?([^")]+)"?\)/);
    return { bg: bg ? bg[1] : null, items };
  });
}

const FONT = (family, weight) => {
  if (family.startsWith("League")) return weight >= 800 ? { face: "League Spartan ExtraBold", bold: false } : { face: "League Spartan", bold: true };
  if (family.startsWith("JetBrains")) return { face: "JetBrains Mono Medium", bold: weight >= 600 };
  if (weight >= 700) return { face: "Inter", bold: true };
  if (weight >= 600) return { face: "Inter SemiBold", bold: false };
  return { face: "Inter", bold: false };
};

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--allow-file-access-from-files"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 * 7, deviceScaleFactor: 1 });
  await page.goto("file:///" + path.join(DECK, "index.html").replace(/\\/g, "/"), { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts.ready);
  const data = await page.evaluate(extract);

  // standalone images for the images folder, rendered with everything visible
  await page.setViewport({ width: 1920, height: 1080 * 7, deviceScaleFactor: 2 });
  await page.evaluate(() => document.fonts.ready);
  const shot = async (sel, idx, file) => {
    const els = await page.$$(sel);
    if (els[idx]) await els[idx].screenshot({ path: file });
  };
  await shot(".browser", 0, path.join(IMAGES, "mockups", "dashboard.png"));
  await shot(".browser", 1, path.join(IMAGES, "mockups", "issue_drawer.png"));
  await shot(".browser", 2, path.join(IMAGES, "mockups", "supplier_graph.png"));
  for (let i = 0; i < 7; i++) await page.screenshot({ path: path.join(IMAGES, "diagrams", `slide${i + 1}_full.png`), clip: { x: 0, y: i * 1080, width: 1920, height: 1080 } });
  await page.screenshot({ path: path.join(IMAGES, "diagrams", "architecture_flow.png"), clip: { x: 130, y: 4 * 1080 + 255, width: 1660, height: 600 } });
  await page.screenshot({ path: path.join(IMAGES, "diagrams", "problem_story.png"), clip: { x: 130, y: 1 * 1080 + 300, width: 1660, height: 285 } });

  // icon sheet: every icon file in deck colours, for reuse in other slides
  const icons = fs.readdirSync(path.join(DECK, "icons")).filter((f) => f.endsWith(".svg"));
  const brand = { nextdotjs: "000000", typescript: "3178C6", tailwindcss: "06B6D4", python: "3776AB", fastapi: "009688", postgresql: "4169E1", pandas: "150458", scikitlearn: "F7931E", anthropic: "D97757", docker: "2496ED", vercel: "000000", render: "000000", pydantic: "E92063", supabase: "3ECF8E", reactquery: "FF4154", framer: "0055FF", duckdb: "000000", polars: "CD792C" };
  const sheet = await browser.newPage();
  await sheet.setViewport({ width: 300, height: 300, deviceScaleFactor: 1 });
  for (const f of icons) {
    const name = f.replace(/\.svg$/, "");
    const cols = name.startsWith("l-") ? { orange: "D2601A", ink: "24110C" } : { brand: brand[name] || "24110C" };
    for (const [label, hex] of Object.entries(cols)) {
      let svg = fs.readFileSync(path.join(DECK, "icons", f), "utf8");
      svg = svg.includes("currentColor") ? svg.replace(/currentColor/g, "#" + hex) : svg.replace("<svg", `<svg fill="#${hex}"`);
      const src = "data:image/svg+xml;base64," + Buffer.from(svg).toString("base64");
      await sheet.setContent(`<html><body style="margin:0;background:transparent"><img id="i" src="${src}" style="display:block;width:256px;height:256px;margin:22px"></body></html>`);
      await new Promise((r) => setTimeout(r, 60));
      const el = await sheet.$("#i");
      await el.screenshot({ path: path.join(IMAGES, "icons", `${name.replace(/^l-/, "")}_${label}.png`), omitBackground: true });
    }
  }
  await sheet.close();
  const logo = await page.$("#logo-lockup");
  if (logo) {
    await page.addStyleTag({ content: `html.isologo, html.isologo body{background:transparent!important} html.isologo *{visibility:hidden!important} html.isologo #logo-lockup, html.isologo #logo-lockup *{visibility:visible!important}` });
    await page.evaluate(() => document.documentElement.classList.add("isologo"));
    await logo.screenshot({ path: path.join(IMAGES, "logo_ledgerlens.png"), omitBackground: true });
    await page.evaluate(() => document.documentElement.classList.remove("isologo"));
  }

  // isolated transparent renders of every icon and drawing
  await page.setViewport({ width: 1920, height: 1080 * 7, deviceScaleFactor: 4 });
  await page.addStyleTag({ content: `html.iso, html.iso body{background:transparent!important} html.iso *{visibility:hidden!important;box-shadow:none!important} html.iso .iso-t, html.iso .iso-t *{visibility:visible!important}` });
  await page.evaluate(() => document.documentElement.classList.add("iso"));
  const all = data.flatMap((s, si) => s.items.filter((it) => it.kind === "image").map((it) => ({ ...it, si })));
  for (const it of all) {
    const el = await page.$(`[data-img="${it.id}"]`);
    await page.evaluate((e) => e.classList.add("iso-t"), el);
    const pad = 1;
    await page.screenshot({ path: path.join(ASSETS, it.id + ".png"), omitBackground: true, clip: { x: it.x - pad, y: it.si * 1080 + it.y - pad, width: it.w + pad * 2, height: it.h + pad * 2 } });
    await page.evaluate((e) => e.classList.remove("iso-t"), el);
    it.pad = pad;
  }
  await browser.close();

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "LedgerLens, Fintechstico V7.0";
  const S = pres.ShapeType;
  const inch = (v) => +(v * PX).toFixed(4);
  const color = (c) => (c ? { color: c.hex, transparency: Math.round((1 - c.a) * 100) } : undefined);

  data.forEach((sd, si) => {
    const slide = pres.addSlide();
    const tpl = TEMPLATE[si];
    slide.background = { color: tpl.bg || "FFEFDA" };
    for (const g of tpl.paths) {
      slide.addShape(S.custGeom, {
        x: g.x, y: g.y, w: g.w, h: g.h, points: g.points,
        fill: g.fill ? { color: g.fill, transparency: Math.round((1 - g.fillAlpha) * 100) } : { type: "none" },
        line: g.line && g.lineWidth ? { color: g.line, width: g.lineWidth, transparency: Math.round((1 - g.lineAlpha) * 100) } : { type: "none" },
      });
    }
    for (const im of tpl.images) slide.addImage({ path: im.file, x: im.x, y: im.y, w: im.w, h: im.h });
    for (const t of tpl.texts) {
      if ((SKIP_TEMPLATE_TEXT[si] || []).includes(t.text)) continue;
      // the template was set in an older League Spartan cut: larger glyphs, tighter tracking
      const league = t.font.startsWith("LeagueSpartan");
      const size = league ? t.size * LS_SCALE : t.size;
      const cx = (t.x0 + t.x1) / 2, w = (t.x1 - t.x0) * 1.3;
      slide.addText(t.text, {
        x: cx - w / 2, y: t.y0 + (league ? t.size * LS_DY : 0), w, h: t.y1 - t.y0, margin: 0, align: "center", valign: "top", wrap: false, fit: "none", isTextBox: true,
        fontFace: league ? "League Spartan" : "Inter", bold: league, fontSize: +size.toFixed(2), color: t.color, ...(league ? { charSpacing: +(-LS_TRACK * size).toFixed(2) } : {}),
      });
    }
    for (const it of sd.items) {
      if (it.kind === "shape") {
        const opts = { x: inch(it.x), y: inch(it.y), w: inch(it.w), h: inch(it.h) };
        opts.fill = it.fill ? color(it.fill) : { type: "none" };
        opts.line = it.line ? { ...color(it.line), width: it.line.w * 0.5, dashType: it.line.dash ? "dash" : "solid" } : { type: "none" };
        if (it.shadow) opts.shadow = { type: "outer", color: "50200A", opacity: 0.22, blur: 14, offset: 6, angle: 90 };
        let type = S.rect;
        if (it.ellipse) type = S.ellipse;
        else if (it.radius > 0) { type = S.roundRect; opts.rectRadius = Math.min(inch(it.radius), Math.min(opts.w, opts.h) / 2); }
        slide.addShape(type, opts);
        if (it.corners) {
          const r = inch(it.radius);
          const sq = (x, y) => slide.addShape(S.rect, { x, y, w: r, h: r, fill: color(it.fill), line: { type: "none" } });
          if (!it.corners.tl) sq(opts.x, opts.y);
          if (!it.corners.tr) sq(opts.x + opts.w - r, opts.y);
          if (!it.corners.bl) sq(opts.x, opts.y + opts.h - r);
          if (!it.corners.br) sq(opts.x + opts.w - r, opts.y + opts.h - r);
        }
      } else if (it.kind === "line") {
        const x = inch(Math.min(it.x, it.x2)), y = inch(Math.min(it.y, it.y2));
        slide.addShape(S.line, { x, y, w: Math.max(inch(Math.abs(it.x2 - it.x)), 0), h: Math.max(inch(Math.abs(it.y2 - it.y)), 0), line: { ...color(it), width: it.w * 0.5, dashType: it.dash ? "dash" : "solid" } });
      } else if (it.kind === "image") {
        slide.addImage({ path: path.join(ASSETS, it.id + ".png"), x: inch(it.x - 1), y: inch(it.y - 1), w: inch(it.w + 2), h: inch(it.h + 2) });
      } else if (it.kind === "text") {
        const runs = it.runs.filter((r) => r.text.length).map((r) => {
          const f = FONT(r.family, r.weight);
          const o = { fontFace: f.face, bold: f.bold, italic: r.italic, fontSize: +(r.size * 0.5).toFixed(2), ...(r.color ? { color: r.color.hex } : {}) };
          if (r.spacing) o.charSpacing = +(r.spacing * 0.5).toFixed(2);
          if (r.br) o.breakLine = true;
          return { text: r.text, options: o };
        });
        if (!runs.length) continue;
        const lead = it.runs.find((r) => r.text.trim());
        const lift = lead && lead.family.startsWith("League") ? lead.size * 0.2 : 0;
        const opts = { x: inch(it.x), y: inch(it.y - lift), w: inch(it.w), h: Math.max(inch(it.h), 0.05), margin: 0, valign: "top", align: it.align === "justify" ? "left" : it.align, wrap: it.multi && !it.runs.some((r) => r.br), fit: "none", isTextBox: true, paraSpaceBefore: 0, paraSpaceAfter: 0 };
        if (it.multi && it.lineH) opts.lineSpacing = +(it.lineH * 0.5).toFixed(2);
        slide.addText(runs, opts);
      }
    }
    if (NOTES[si]) slide.addNotes(NOTES[si]);
  });
  const file = path.join(OUT, "LedgerLens_Fintechstico.pptx");
  await pres.writeFile({ fileName: file });
  const counts = data.map((s) => s.items.reduce((a, it) => ((a[it.kind] = (a[it.kind] || 0) + 1), a), {}));
  console.log(JSON.stringify(counts));
  console.log("wrote", file);
})();
