"""Add a detailed endpoint panel to an unchanged, checked Archify base.
The derivative retains node IDs, geometry, relationships and viewer controls.
"""
from pathlib import Path
import re,html,json,hashlib
base=Path(__file__).parent
source=base/'kirocrew-security-layers-base.html'
s=source.read_text()
def esc(t):return html.escape(t,quote=True)
def text(x,y,t,size=12,cls='t-primary',weight=None,extra=''):
 return f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}"'+(f' font-weight="{weight}"' if weight else '')+f' {extra}>{esc(t)}</text>'
def rect(x,y,w,h,cls,rx=8):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>'
def line(x1,y1,x2,y2):return f'<path d="M{x1} {y1}H{x2}" class="ep-divider"/>' if y1==y2 else f'<path d="M{x1} {y1}V{y2}" class="ep-divider"/>'
icons={
 'shield':'<path d="M12 2 21 6v6c0 5-5 8-9 10-4-2-9-5-9-10V6Z"/><path d="m7 12 3 3 7-7"/>',
 'laptop':'<rect x="4" y="3" width="16" height="13" rx="2"/><path d="M1 20h22l-3-4H4Z"/><path d="M10 19h4"/>',
 'policy':'<rect x="4" y="3" width="16" height="19" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
 'tools':'<rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="8" y="14" width="8" height="8" rx="2"/><path d="M6 10v3h12v-3M12 13v1"/>',
 'key':'<circle cx="8" cy="9" r="5"/><path d="m12 13 9 9M16 17l3-3M19 20l3-3"/>',
 'gateway':'<path d="M4 21V4h16v17M9 21v-7h6v7M8 8h2M14 8h2"/>',
 'agent':'<rect x="3" y="6" width="18" height="15" rx="4"/><path d="M12 2v4M8 12h1M15 12h1M8 17h8"/>',
 'terminal':'<rect x="2" y="3" width="20" height="18" rx="3"/><path d="m6 8 4 4-4 4M13 16h5"/>',
}
def icon(name,x,y,size=26,cls='ep-icon'):
 return f'<g class="{cls}" aria-hidden="true" transform="translate({x} {y}) scale({size/24})">{icons[name]}</g>'
def node_span(id):
 start=s.index(f'<g id="node-{id}"');depth=0
 for m in re.finditer(r'<g\b[^>]*>|</g>',s[start:]):
  depth+=-1 if m.group().startswith('</') else 1
  if depth==0:return start,start+m.end()
 raise ValueError(id)
def replace_node(id,body):
 global s
 start,end=node_span(id);old=s[start:end]
 op=old[:old.index('>')+1];title=re.search(r'<title>.*?</title>',old,re.S).group()
 s=s[:start]+op+title+body+'</g>'+s[end:]
# One host enclosure; internal rows are information, not separate trust boundaries.
a=rect(330,255,710,700,'c-mask',12)+rect(330,255,710,700,'ep-shell',12)
a+=icon('shield',354,277,30)+text(398,302,'Endpoint control',24,weight=700,extra='data-node-label="" data-detail-anchor=""')
a+=text(354,329,'Execution host · local endpoint or remote Crew host',12,'t-muted')
a+=line(354,347,1016,347)
a+=rect(350,365,670,92,'ep-host-band')+icon('laptop',368,391,28,'ep-icon-muted')
a+=text(414,387,'ENTERPRISE HOST PROTECTION',12,'t-muted',700)
a+=text(414,411,'EDR / MDM where supported · managed OS',13)
a+=text(414,435,'Disk encryption · device identity · network egress',12,'t-muted')
a+=text(354,490,'KiroCrew managed execution',16,'t-backend',700)
a+=rect(350,505,670,66,'ep-runtime-band')
for x,name,title,sub in [
 (364,'gateway','Gateway + session','Auth · origin · app scopes'),
 (586,'agent','Selected backend','Kiro CLI / Codex / Claude Code'),
 (824,'terminal','Tool execution','Files · shell · routed MCP')]:
 a+=icon(name,x,519,20,'ep-icon-green')+text(x+28,529,title,12,weight=600)
 a+=text(x,553,sub,10,'t-muted')
# Chevrons indicate the managed execution path, without extra node borders.
a+='<path d="m570 528 5 5-5 5m236-10 5 5-5 5" class="ep-icon-green"/>'
a+=rect(350,585,670,50,'ep-policy-band')+icon('policy',367,597,23,'ep-icon-rose')
a+=text(410,607,'Policy ∩ Profile · protected configuration',13,weight=600)
a+=text(410,624,'Approvals · tool / app scopes · backend admission',11,'t-muted')
rows=[
 ('L0','Isolate processes','OS sandbox · agent descendants',354,673),
 ('L1','Protect paths*','Resolved paths · protected policy files',700,673),
 ('L2','Gate commands*','Deny rules · exfiltration checks',354,747),
 ('L3','Validate tool inputs','Registered schemas · bounded arguments',700,747),
 ('L4','Redact outputs','Credential / URL patterns · covered sinks',354,821),
 ('L5','Record decisions','SEL events · HMAC-chain verification',700,821),
]
for code,title,detail,x,y in rows:
 a+=rect(x,y-20,34,30,'ep-layer-badge',6)+text(x+7,y,code,12,'t-backend',700)
 a+=text(x+46,y,title,14,weight=600)+text(x+46,y+23,detail,10.5,'t-muted')
a+=line(685,651,685,859)+line(354,711,1016,711)+line(354,785,1016,785)
a+=line(354,875,1016,875)+text(354,903,'ACROSS THE LAYERS',10,'t-muted',700)
a+=text(354,928,'Credential scrub · resource limits · project-skill trust',12)
replace_node('endpoint-control',a)
# Expand service symbols and reflow the concise outside-node labels.
def outside(id,x,y,w,h,name,title,lines,tag,cls='c-security'):
 body=rect(x,y,w,h,'c-mask')+rect(x,y,w,h,cls)
 body+=icon(name,x+12,y+12,24,'ep-icon-rose' if cls=='c-security' else 'ep-icon')
 body+=text(x+46,y+29,title,12,weight=700,extra='data-node-label="" data-detail-anchor=""')
 for i,l in enumerate(lines):body+=text(x+12,y+53+i*15,l,10,'t-muted')
 body+=text(x+12,y+h-12,tag,9,'t-muted')
 replace_node(id,body)
outside('developer-entry',20,555,170,100,'laptop','Developer',['Desktop / browser / CLI'],'Identity at entry','c-frontend')
outside('central-policy',545,30,280,105,'policy','Central policy authority',['Protected policy → local enforcement'],'Distribution adapter proposed')
outside('mcp-tool-governance',1160,555,200,100,'tools','MCP governance',['Server / tool grants · OAuth'],'LiteLLM / service tier proposed')
outside('target-permissions',1160,850,200,100,'key','Target authorization',['AWS IAM / SaaS permissions'],'Independent resource decision','c-cloud')
styles='''
/* Authored endpoint detail. Theme variables preserve the Archify light/dark palette. */
.ep-shell {fill:var(--mask);stroke:var(--frontend-stroke);stroke-width:2;}
.ep-host-band {fill:var(--external-fill);stroke:none;}
.ep-runtime-band {fill:var(--backend-fill);stroke:none;}
.ep-policy-band {fill:var(--security-fill);stroke:none;}
.ep-layer-badge {fill:var(--backend-fill);stroke:none;}
.ep-divider {fill:none;stroke:var(--lane-stroke);stroke-width:1;}
.ep-icon {fill:none;stroke:var(--frontend-stroke);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
.ep-icon-muted {fill:none;stroke:var(--external-stroke);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
.ep-icon-green {fill:none;stroke:var(--backend-stroke);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
.ep-icon-rose {fill:none;stroke:var(--security-stroke);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
'''
s=s.replace('</head>','<style>'+styles+'</style>\n</head>')
# All inner labels remain discoverable in screen-reader name and node context.
s=s.replace('aria-label="Focus Endpoint control, Enterprise baseline + KiroCrew L0–L5, Architecture component"',
 'aria-label="Focus Endpoint control: enterprise host protection; Gateway, agent and tools; policy and profile; L0 sandbox, L1 paths, L2 commands, L3 schemas, L4 redaction, L5 security event log; credentials, resource limits and project-skill trust"')
# Remove the generic component legend: the endpoint enclosure uses its own
# visual hierarchy, and every actor/band is already explicitly named.
start=s.index('<g data-legend=""')
depth=0
for m in re.finditer(r'<g\b[^>]*>|</g>',s[start:]):
 depth+=-1 if m.group().startswith('</') else 1
 if depth==0:
  s=s[:start]+s[start+m.end():]
  break
output=base/'kirocrew-security-layers.html';output.write_text(s)
def fingerprint(p):
 b=p.read_bytes();return {'path':p.name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
(base/'kirocrew-endpoint-detail.json').write_text(json.dumps({'method':'Detailed SVG content inside one endpoint component; original Archify topology, geometry and base preserved. Generic hand-authored vector symbols; AWS service icons retained in the deployment view.','base':fingerprint(source),'derivative':fingerprint(output),'script':'detail-endpoint-panel.py','endpointInternalLayers':[r[0] for r in rows]},indent=2)+'\n')
print('Built a single detailed endpoint panel and four outside actors.')
