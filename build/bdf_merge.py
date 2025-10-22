#!/usr/bin/env python3
import sys, argparse, re
from collections import namedtuple, OrderedDict

Glyph = namedtuple("Glyph", "encoding swidth dwidth bbw bbh bbx bby bitmap props")

ENCODING_RE = re.compile(r"^ENCODING\s+(-?\d+)")
BBX_RE      = re.compile(r"^BBX\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)")
DWIDTH_RE   = re.compile(r"^DWIDTH\s+(-?\d+)(?:\s+(-?\d+))?")
SWIDTH_RE   = re.compile(r"^SWIDTH\s+(-?\d+)\s+(-?\d+)")
PROP_RE     = re.compile(r'^([A-Z0-9_]+)\s+(?:"(.*)"|(.+))$')

def eprint(*a): print(*a, file=sys.stderr)

def parse_args():
    ap = argparse.ArgumentParser(description="Merge BDFs without FontForge.")
    ap.add_argument("inputs", nargs="+", help="BDF files in priority order (first wins)")
    ap.add_argument("-o","--out", required=True, help="Output BDF")
    ap.add_argument("--align", choices=["baseline","center","descent","none"], default="baseline",
                    help="Vertical donor alignment vs base (default: baseline)")
    ap.add_argument("--xshift", type=int, default=0, help="Extra X shift applied to all donor glyphs")
    ap.add_argument("--yshift", type=int, default=0, help="Extra Y shift applied to all donor glyphs")
    ap.add_argument("--recalc-metrics", action="store_true",
                    help="Recompute FONT_ASCENT/DESCENT from glyph extents")
    ap.add_argument("--keep-metrics", action="store_true",
                    help="Keep base FONT_ASCENT/DESCENT (default if neither flag set)")
    return ap.parse_args()

def read_bdf(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    # Header
    i = 0
    if not lines or not lines[0].startswith("STARTFONT"):
        raise ValueError(f"{path}: Not a BDF (missing STARTFONT)")

    header = []
    props  = OrderedDict()
    in_props = False
    num_props_expected = None

    # Collect header & properties until CHARS
    while i < len(lines):
        line = lines[i]
        header.append(line)
        if line.startswith("STARTPROPERTIES"):
            in_props = True
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                num_props_expected = int(parts[1])
        elif in_props and line.startswith("ENDPROPERTIES"):
            in_props = False
        elif in_props:
            m = PROP_RE.match(line)
            if m:
                k = m.group(1)
                v = m.group(2) if m.group(2) is not None else m.group(3)
                props[k] = v
        elif line.startswith("CHARS"):
            i += 1
            break
        i += 1

    # Glyphs
    glyphs = []
    while i < len(lines):
        if lines[i].startswith("STARTCHAR"):
            start = i
            # parse glyph block
            encoding = None
            swx = swy = None
            dwx = dwy = None
            bbw=bbh=bbx=bby=None
            bitmap = []
            gprops = []

            i += 1
            while i < len(lines) and not lines[i].startswith("ENDCHAR"):
                l = lines[i]
                if l.startswith("ENCODING"):
                    m = ENCODING_RE.match(l)
                    if m: encoding = int(m.group(1))
                elif l.startswith("SWIDTH"):
                    m = SWIDTH_RE.match(l); 
                    if m: swx, swy = int(m.group(1)), int(m.group(2))
                elif l.startswith("DWIDTH"):
                    m = DWIDTH_RE.match(l)
                    if m:
                        dwx = int(m.group(1))
                        dwy = int(m.group(2)) if m.group(2) else 0
                elif l.startswith("BBX"):
                    m = BBX_RE.match(l)
                    if m:
                        bbw, bbh, bbx, bby = map(int, m.groups())
                elif l == "BITMAP":
                    i += 1
                    while i < len(lines) and not lines[i].startswith("ENDCHAR"):
                        if lines[i] == "ENDCHAR":
                            break
                        if re.match(r"^[0-9A-Fa-f]+$", lines[i]):
                            bitmap.append(lines[i].strip())
                            i += 1
                        else:
                            break
                    # don't consume ENDCHAR here; outer loop will
                    continue
                else:
                    gprops.append(l)  # keep any extra lines (e.g., ATTRIBUTES)
                i += 1
            # now lines[i] is ENDCHAR
            glyphs.append(Glyph(
                encoding=encoding,
                swidth=(swx, swy),
                dwidth=(dwx, dwy),
                bbw=bbw or 0, bbh=bbh or 0, bbx=bbx or 0, bby=bby or 0,
                bitmap=bitmap,
                props=gprops
            ))
        if i < len(lines) and lines[i].startswith("ENDFONT"):
            break
        i += 1

    return {"path": path, "header": header, "props": props, "glyphs": glyphs}

def glyph_extents(g):
    # Returns (xmin, ymin, xmax, ymax) in font grid coordinates
    # Glyph bitmap box at (bbx, bby) with size (bbw x bbh)
    x0 = g.bbx
    y0 = g.bby
    x1 = g.bbx + g.bbw
    y1 = g.bby + g.bbh
    return x0, y0, x1, y1

def compute_ascent_descent(glyph_map):
    # ascent: max y above baseline; descent: max depth below baseline (positive)
    ascent = 0
    descent = 0
    for g in glyph_map.values():
        _, y0, _, y1 = glyph_extents(g)
        ascent  = max(ascent, y1)
        descent = max(descent, max(0, -y0))
    return ascent, descent

def compute_global_bbx(glyph_map):
    xmin = ymin =  10**9
    xmax = ymax = -10**9
    for g in glyph_map.values():
        x0, y0, x1, y1 = glyph_extents(g)
        xmin = min(xmin, x0); ymin = min(ymin, y0)
        xmax = max(xmax, x1); ymax = max(ymax, y1)
    if xmin == 10**9:
        return (0,0,0,0)  # empty
    return (xmax - xmin, ymax - ymin, xmin, ymin)

def align_delta(base_props, donor_props, mode):
    # Use FONT_ASCENT / FONT_DESCENT for baseline math; fallback to 0.
    ba = int(base_props.get("FONT_ASCENT", "0"))
    bd = int(base_props.get("FONT_DESCENT", "0"))
    da = int(donor_props.get("FONT_ASCENT", "0"))
    dd = int(donor_props.get("FONT_DESCENT", "0"))

    if mode == "baseline":
        return 0, (ba - da)
    elif mode == "descent":
        return 0, (bd - dd) * -1  # move donor so bottom depths match
    elif mode == "center":
        base_c  = (ba - bd) / 2.0
        donor_c = (da - dd) / 2.0
        return 0, int(round(base_c - donor_c))
    else:
        return 0, 0

def write_bdf(out_path, base_header, out_props, glyph_map):
    # Rebuild header: keep STARTFONT.. up to STARTPROPERTIES from base_header,
    # but overwrite SIZE/FONTBOUNDINGBOX/FONT_ASCENT/FONT_DESCENT/CHARS as per out_props.
    # Simpler: synthesize a clean header.
    lines = []
    lines.append("STARTFONT 2.1")
    # Carry over FONT name if present
    fontname = out_props.get("FONT", None)
    if fontname:
        lines.append(f"FONT {fontname}")
    size = out_props.get("SIZE", None)
    if size:
        lines.append(f"SIZE {size}")
    bbx = out_props.get("FONTBOUNDINGBOX", None)
    if bbx:
        lines.append(f"FONTBOUNDINGBOX {bbx}")

    # Properties
    # Ensure required props present
    props = OrderedDict(out_props)
    props["FONT_ASCENT"]  = str(out_props.get("FONT_ASCENT", "0"))
    props["FONT_DESCENT"] = str(out_props.get("FONT_DESCENT", "0"))
    # Remove any duplicates that we rewrote numerically below
    prop_items = list(props.items())

    lines.append(f"STARTPROPERTIES {len(prop_items)}")
    for k,v in prop_items:
        if k in ("FONTBOUNDINGBOX",):  # not a property; header field
            continue
        # quote non-numeric values
        try:
            int(v)
            lines.append(f"{k} {v}")
        except Exception:
            vv = v.replace('"','\\"')
            lines.append(f'{k} "{vv}"')
    lines.append("ENDPROPERTIES")
    lines.append(f"CHARS {len(glyph_map)}")

    # Glyphs
    for enc, g in sorted(glyph_map.items(), key=lambda kv: kv[0]):
        lines.append(f"STARTCHAR uni{enc:04X}" if enc >= 0 else "STARTCHAR .notdef")
        lines.append(f"ENCODING {enc}")
        if g.swidth[0] is not None:
            lines.append(f"SWIDTH {g.swidth[0]} {g.swidth[1]}")
        if g.dwidth[0] is not None:
            if g.dwidth[1] not in (None, 0):
                lines.append(f"DWIDTH {g.dwidth[0]} {g.dwidth[1]}")
            else:
                lines.append(f"DWIDTH {g.dwidth[0]}")
        lines.append(f"BBX {g.bbw} {g.bbh} {g.bbx} {g.bby}")
        # Preserve extra per-glyph props if any (ATTRIBUTES, etc.), prior to BITMAP
        for pp in g.props:
            # avoid duplicating BBX/DWIDTH/SWIDTH etc.
            if pp.startswith(("ENCODING","BBX","DWIDTH","SWIDTH","BITMAP")):
                continue
            lines.append(pp)
        lines.append("BITMAP")
        lines.extend(g.bitmap)
        lines.append("ENDCHAR")
    lines.append("ENDFONT")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    args = parse_args()
    files = [read_bdf(p) for p in args.inputs]

    base = files[0]
    base_props = OrderedDict(base["props"])
    # Keep some base header-ish fields if present
    # Normalize SIZE as a raw string to preserve original DPI
    size_tokens = []
    for h in base["header"]:
        if h.startswith("SIZE "):
            size_tokens = h.split(None, 1)[1]
        if h.startswith("FONT "):
            base_props.setdefault("FONT", h[5:])
        if h.startswith("FONTBOUNDINGBOX "):
            base_props.setdefault("FONTBOUNDINGBOX", h.split(None,1)[1])

    # Build glyph map from base (encoded >= 0)
    glyph_map = OrderedDict()
    for g in base["glyphs"]:
        if g.encoding is not None and g.encoding >= 0:
            glyph_map[g.encoding] = g

    # Priority fill from fallbacks
    for donor in files[1:]:
        dx, dy_auto = align_delta(base_props, donor["props"], args.align)
        dx += args.xshift
        dy = dy_auto + args.yshift

        taken = 0
        added = 0
        for g in donor["glyphs"]:
            if g.encoding is None or g.encoding < 0:
                continue
            if g.encoding in glyph_map:
                taken += 1
                continue
            # adjust BBX offsets (shift) — bitmap stays the same
            new_g = Glyph(
                encoding=g.encoding,
                swidth=g.swidth,
                dwidth=g.dwidth,
                bbw=g.bbw, bbh=g.bbh,
                bbx=g.bbx + dx,
                bby=g.bby + dy,
                bitmap=g.bitmap,
                props=g.props,
            )
            glyph_map[g.encoding] = new_g
            added += 1
        eprint(f"[merge] {donor['path']}: kept {taken} existing, added {added}, shift=({dx},{dy}) via {args.align}")

    # Compute global BBX
    gbw, gbh, gbx, gby = compute_global_bbx(glyph_map)
    eprint(f"[bbx] global bbx: width={gbw} height={gbh} xoff={gbx} yoff={gby}")

    # Prepare output properties
    out_props = OrderedDict(base_props)
    # SIZE: keep from base header if found
    if size_tokens:
        out_props["SIZE"] = size_tokens
    # FONTBOUNDINGBOX
    out_props["FONTBOUNDINGBOX"] = f"{gbw} {gbh} {gbx} {gby}"

    if args.recalc_metrics and not args.keep_metrics:
        asc, desc = compute_ascent_descent(glyph_map)
        out_props["FONT_ASCENT"]  = str(asc)
        out_props["FONT_DESCENT"] = str(desc)
        eprint(f"[metrics] recalculated ascent={asc} descent={desc} total={asc+desc}")
    else:
        # keep base ascent/descent
        asc = int(out_props.get("FONT_ASCENT","0"))
        desc= int(out_props.get("FONT_DESCENT","0"))
        eprint(f"[metrics] kept base ascent={asc} descent={desc} total={asc+desc}")

    write_bdf(args.out, base["header"], out_props, glyph_map)
    eprint(f"[done] wrote {args.out} with {len(glyph_map)} glyphs")

if __name__ == "__main__":
    main()
