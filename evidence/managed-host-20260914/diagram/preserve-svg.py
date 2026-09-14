"""Reuse the accepted SVG byte-for-byte with the newly delivered host card."""
from pathlib import Path
import hashlib,html as html_module,json,re
ROOT=Path(__file__).resolve().parents[3]
EV=Path(__file__).resolve().parent
ACCEPTED=ROOT/'evidence/managed-host-20260914/accepted-diagram/kirocrew-managed-controls-diagram.html'
OUTPUT=ROOT/'kirocrew-managed-controls-diagram.html'
def fp(p):
 b=p.read_bytes();return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def require(c,m):
 if not c:raise ValueError(m)
old=ACCEPTED.read_text();base=(EV/'base.html').read_text();old_svg=re.search(r'<svg\b[\s\S]*?</svg>',old);base_svg=re.search(r'<svg\b[\s\S]*?</svg>',base)
require(old_svg is not None and base_svg is not None,'SVG not found')
change=json.loads((EV/'card-change.json').read_text())
expected=old
for before,after in zip(change['before']['items'],change['after']['items']):
 before=html_module.escape(before);after=html_module.escape(after)
 require(expected.count(before)==1,'Old card text must occur exactly once')
 expected=expected.replace(before,after,1)
final=base[:base_svg.start()]+old_svg.group()+base[base_svg.end():]
require(final==expected,'Changes outside three card text replacements')
require(OUTPUT.read_bytes()==ACCEPTED.read_bytes(),'Current accepted HTML changed before update')
OUTPUT.write_text(final)
svg_bytes=old_svg.group().encode()
receipt={'schema_version':1,'kind':'host_card_only_html_derivative','accepted_source':fp(ACCEPTED),'new_base_delivery':fp(EV/'base-delivery.json'),'new_base_html':fp(EV/'base.html'),'output':fp(OUTPUT),'script':fp(Path(__file__).resolve()),'card_change':fp(EV/'card-change.json'),'svg_sha256':hashlib.sha256(svg_bytes).hexdigest(),'svg_bytes':len(svg_bytes),'accepted_svg_byte_identical':True,'all_html_outside_three_card_text_replacements_byte_identical':True,'artwork_rerendered':False,'scope':'New Archify base proves specification rendering and validation. Final HTML reuses the exact accepted SVG, including its typography; only the three host card bullet strings differ from the accepted HTML.'}
(EV/'card-derivative.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'artifact':receipt['output'],'svg_sha256':receipt['svg_sha256'],'changes':'3 card text strings only'}))
