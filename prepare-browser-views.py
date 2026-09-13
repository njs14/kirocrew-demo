"""Create browser derivatives; preserve accepted SVGs and original HTML exactly."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

records = []
for name, note in [
    ('kirocrew-security-layers', '* Pre-tool prevention requires a Crew hook or permission callback. Coverage and ownership: Controls & demo proof.'),
    ('kirocrew-aws-deployment', 'Proposed EC2 + SSM deployment. Policy sync, MCP gateway and external collection require separate implementation.'),
]:
    source = ROOT / (name + '.html')
    original = source.read_text()
    text = original
    # The supplied runtime only fits diagrams wider than 1.55:1. These accepted
    # diagrams are taller. Extend eligibility without assigning wide-diagram CSS.
    old = 'shell && diagram && svg && ratio >= WIDE_RATIO &&'
    if text.count(old) != 1:
        raise RuntimeError('Unexpected reader-layout source')
    text = text.replace(old, 'shell && diagram && svg && ratio > 0 &&')
    text = text.replace('var MIN_READER_WIDTH = 960;', 'var MIN_READER_WIDTH = 720;')
    # The detailed endpoint uses ep-* classes added after the base renderer.
    # Include those existing rules in the standalone SVG/raster export style
    # collection. This changes the export runtime, not the authored SVG.
    export_classes = r'\.c-|\.t-|\.a-|\.m-'
    if text.count(export_classes) != 1:
        raise RuntimeError('Unexpected export stylesheet filter')
    text = text.replace(export_classes, export_classes + r'|\.ep-')
    # The reference tab already retains all three conclusion cards. Replace
    # duplicate prose with a visible caveat, retaining normal document flow.
    start = text.index('<div class="cards">')
    depth = 0
    end = None
    for match in re.finditer(r'<div\b[^>]*>|</div>', text[start:]):
        depth += -1 if match.group().startswith('</') else 1
        if depth == 0:
            end = start + match.end()
            break
    if end is None:
        raise RuntimeError('Unbalanced conclusion cards')
    text = text[:start] + '<p class="cards browser-caveat">' + note + '</p>' + text[end:]
    text = text.replace('</head>', '<style>.browser-caveat{display:block;font-size:12px;line-height:1.5;margin-top:10px;color:var(--text-secondary)}@media(min-width:1024px){body{padding:12px 24px}.header{margin-bottom:10px;padding-right:max(0px,calc(29.5rem - (100vw - var(--archify-reader-width,1440px))/2))}}</style>\n</head>')
    svg = lambda s: re.search(r'<svg\b[\s\S]*?</svg>', s).group()
    if svg(original) != svg(text):
        raise RuntimeError('Accepted SVG changed')
    output = ROOT / (name + '-browser.html')
    output.write_text(text)
    records.append({'source': source.name, 'source_sha256': sha(source.read_bytes()),
                    'artifact': output.name, 'artifact_sha256': sha(output.read_bytes()),
                    'svg_sha256': sha(svg(text).encode()), 'svg_unchanged': True})
(ROOT / 'evidence/browser/derivatives.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(records, indent=2))
