"""Make a bounded SVG typography derivative; do not execute HTML or alter routes."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent
SOURCE = EVIDENCE / "base.html"
OUTPUT = ROOT / "kirocrew-managed-controls-diagram.html"
PARAMETERS = {"node_font": 20, "sublabel_font": 16, "edge_font": 16, "boundary_font": 16}

def fingerprint(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def width(text, font):
    # Match the conservative estimator in the packaged artifact checker.
    return sum(1.8 if ord(char) > 255 else .62 for char in text) * font

def wrap(text, font, maximum):
    lines = []
    for word in text.split():
        if width(word, font) > maximum:
            raise ValueError(f"Unbreakable text exceeds its box: {word}")
        if lines and width(lines[-1] + " " + word, font) <= maximum:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if " ".join(lines) != text:
        raise ValueError("Wrapping changed semantic text")
    return lines

html = SOURCE.read_text()
match = re.search(r"<svg\b[\s\S]*?</svg>", html)
svg = ET.fromstring(match.group(), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
before_paths = [dict(e.attrib) for e in svg.iter("path") if "data-edge-id" in e.attrib]
before_frames = [dict(e.attrib) for e in svg.iter("rect") if "data-composition-frame-id" in e.attrib]
before_node_rects = {}
text_checks = []
node_count = 0

for group in [e for e in svg.iter("g") if "data-node-id" in e.attrib]:
    node_count += 1
    rect = next(e for e in group if e.tag == "rect")
    before_node_rects[group.get("data-node-id")] = dict(rect.attrib)
    x, y, w, h = (float(rect.get(key)) for key in ("x", "y", "width", "height"))
    labels = wrap(group.get("data-node-label"), 20, w - 12)
    subtitles = wrap(group.get("data-node-sublabel"), 16, w - 12)
    block_height = 20 + (len(labels) - 1) * 21 + 4 + 16 + (len(subtitles) - 1) * 18 + 4
    if block_height > h - 2:
        raise ValueError(f"Text block exceeds node {group.get('data-node-id')}: {block_height}/{h}")
    baseline = y + (h - block_height) / 2 + 20
    for child in list(group):
        if child.tag == "text":
            group.remove(child)
    for index, line in enumerate(labels):
        attrs = {"data-node-label": "", "data-detail-anchor": "", "x": str(x + w / 2), "y": str(baseline + index * 21), "class": "t-primary", "font-size": "20", "font-weight": "600", "text-anchor": "middle"}
        ET.SubElement(group, "text", attrs).text = line
        text_checks.append({"node": group.get("data-node-id"), "kind": "label", "text": line, "font": 20, "width": width(line, 20), "available_width": w - 12})
    baseline += (len(labels) - 1) * 21 + 4 + 16
    for index, line in enumerate(subtitles):
        attrs = {"data-detail": "context", "x": str(x + w / 2), "y": str(baseline + index * 18), "class": "t-muted", "font-size": "16", "text-anchor": "middle"}
        ET.SubElement(group, "text", attrs).text = line
        text_checks.append({"node": group.get("data-node-id"), "kind": "sublabel", "text": line, "font": 16, "width": width(line, 16), "available_width": w - 12})

edge_count = 0
for group in [e for e in svg.iter("g") if "data-edge-id" in e.attrib]:
    edge_count += 1
    edge_id = group.get("data-edge-id")
    old_text = next(e for e in group if e.tag == "text")
    center_x, baseline = float(old_text.get("x")), float(old_text.get("y"))
    accent = old_text.get("class")
    maximum = 180
    if edge_id == "native-ssh-client": maximum = 132
    if edge_id == "native-mcp-call": maximum = 144
    if edge_id in ("native-s3-allow-call", "native-s3-deny-call"): maximum = 106
    lines = wrap(group.get("data-edge-label"), 16, maximum)
    if edge_id == "native-crew-controls": baseline = 276
    if edge_id in ("native-workspace-io", "native-role-credentials"): baseline = 464
    mask_width = max(width(line, 16) for line in lines) + 12
    first_baseline = baseline - (len(lines) - 1) * 18
    for child in list(group): group.remove(child)
    ET.SubElement(group, "rect", {"x": str(center_x - mask_width / 2), "y": str(first_baseline - 18), "width": str(mask_width), "height": str((len(lines) - 1) * 18 + 24), "rx": "3", "class": "c-mask"})
    for index, line in enumerate(lines):
        ET.SubElement(group, "text", {"x": str(center_x), "y": str(first_baseline + index * 18), "class": accent, "font-size": "16", "text-anchor": "middle"}).text = line

for group in [e for e in svg.iter("g") if e.get("data-graph-role") == "structural-frame-label"]:
    text = next(e for e in group if e.tag == "text")
    mask = next(e for e in group if e.tag == "rect")
    text.set("font-size", "16")
    mask.set("width", str(width(text.text, 16) + 12))
    mask.set("y", str(float(text.get("y")) - 18))
    mask.set("height", "24")

# Legend has fixed, already separated horizontal slots; its semantic wording stays intact.
for text in svg.iter("text"):
    if float(text.get("y", "0")) >= 724:
        text.set("font-size", "18" if text.text == "Legend" else "16")

after_paths = [dict(e.attrib) for e in svg.iter("path") if "data-edge-id" in e.attrib]
after_frames = [dict(e.attrib) for e in svg.iter("rect") if "data-composition-frame-id" in e.attrib]
after_node_rects = {g.get("data-node-id"): dict(next(e for e in g if e.tag == "rect").attrib) for g in svg.iter("g") if "data-node-id" in g.attrib}
if (node_count, edge_count, len(after_frames)) != (8, 7, 1):
    raise ValueError("Diagram topology changed")
if before_paths != after_paths or before_frames != after_frames or before_node_rects != after_node_rects:
    raise ValueError("Node, route, or enclosure geometry changed")

rendered = ET.tostring(svg, encoding="unicode")
OUTPUT.write_text(html[:match.start()] + rendered + html[match.end():])
receipt = {"schema_version": 1, "kind": "bounded-typography-derivative", "source": fingerprint(SOURCE), "output": fingerprint(OUTPUT), "script": fingerprint(Path(__file__).resolve()), "parameters": PARAMETERS, "node_count": node_count, "edge_count": edge_count, "endpoint_boundary_count": len(after_frames), "node_route_boundary_geometry_unchanged": True, "semantic_text_and_cards_unchanged": True, "text_fit_checks": text_checks, "stage_projection": {"source": "Parent screenshot stage-dark.jpg; 280-unit runtime node appears about209px wide", "assumed_svg_scale": 209/280, "predicted_node_px": 20*209/280, "predicted_subtitle_and_edge_px": 16*209/280, "status": "Prediction only; parent must verify actual SVG screen transform in browser."}, "scope": "Explicit SVG font attributes, word wrapping, baseline spacing and matching text masks only. No CSS-only font overrides, node movement, route changes, hidden overflow, smaller text, or browser execution."}
(EVIDENCE / "typography-derivative.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"candidate": receipt["output"], "node_count": node_count, "edge_count": edge_count, "text_fit_checks": len(text_checks)}))
