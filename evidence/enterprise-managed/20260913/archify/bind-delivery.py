"""Bind the managed diagram and static checks without browser or live operations."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
import hashlib, json, re, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[4]
EV=Path(__file__).resolve().parent
STEM='kirocrew-managed-controls-diagram'
def fp(path):
    path=Path(path); path=path if path.is_absolute() else ROOT/path
    b=path.read_bytes(); return {'path':str(path.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(name,data): (EV/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def require(condition,message):
    if not condition: raise ValueError(message)
html_path=ROOT/(STEM+'.html'); html=html_path.read_text(); base=(EV/'base.html').read_text()
source_path=ROOT/(STEM+'.architecture.json'); spec=json.loads(source_path.read_text())
prior_spec=json.loads((ROOT/'kirocrew-native-controls-diagram.architecture.json').read_text())
svg_match=lambda s:re.search(r'<svg\b[\s\S]*?</svg>',s)
m=svg_match(html);bm=svg_match(base)
require(html[:m.start()]+html[m.end():]==base[:bm.start()]+base[bm.end():],'HTML outside SVG changed')
def geometry(s):
    svg=ET.fromstring(svg_match(s).group())
    nodes=[]
    for group in svg.iter('g'):
        if 'data-node-id' in group.attrib:
            rect=next(c for c in group if c.tag=='rect')
            nodes.append((group.get('data-node-id'), {k:rect.get(k) for k in ['x','y','width','height']}))
    return {'nodes':nodes,'routes':[(e.get('data-edge-id'),e.get('d')) for e in svg.iter('path') if 'data-edge-id' in e.attrib], 'frames':[dict(e.attrib) for e in svg.iter('rect') if 'data-composition-frame-id' in e.attrib], 'viewBox':svg.get('viewBox')}
geo=geometry(html);prior_geo=geometry((ROOT/'kirocrew-native-controls-diagram.html').read_text())
require(geo==prior_geo,'Prior accepted topology/geometry changed')
require(len(geo['nodes'])==8 and len(geo['routes'])==7 and len(geo['frames'])==1,'Topology counts changed')
require(spec['boundaries']==prior_spec['boundaries'],'Endpoint enclosure changed')
require(spec['meta']['quality_profile']=='showcase','Missing showcase contract')
archive=json.loads((EV/'accepted-before-managed/manifest.json').read_text())
for item in archive['files']:
    require(fp(item['source_path'])['sha256']==item['sha256'],'Accepted source changed: '+item['source_path'])
    require(fp(item['archived_path'])['sha256']==item['sha256'],'Archived source mismatch')
class Scan(HTMLParser):
    def __init__(self): super().__init__();self.scripts=0;self.styles=0;self.assets=[];self.nav=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script' and 'src' not in a:self.scripts+=1
        if tag=='style':self.styles+=1
        for key in ['src','poster','href','xlink:href']:
            if key in a:
                val=a[key]
                if tag=='a' and key=='href':self.nav.append(val)
                elif not (val.startswith('data:') or val.startswith('#')):self.assets.append({'tag':tag,'attribute':key,'value':val})
scan=Scan();scan.feed(html)
css='\n'.join(re.findall(r'<style\b[^>]*>([\s\S]*?)</style>',html)); urls=re.findall(r'url\(\s*[\"\']?([^\)\"\']+)',css)
external_css=[u for u in urls if not(u.startswith('data:') or u.startswith('#'))]
require(not scan.assets and not external_css and '@import' not in css,'External asset dependency detected')
require(not scan.nav,'Unexpected navigation dependencies')
assets={'schema_version':1,'artifact':fp(html_path),'required_asset_files':[str(html_path.relative_to(ROOT))],'external_asset_dependencies':[],'inline_script_count':scan.scripts,'inline_style_count':scan.styles,'embedded_resource_count':len(re.findall(r'(?:src|href)=[\"\']data:',html)),'embedded_css_url_count':len(urls),'navigation_links':scan.nav,'scope':'Static HTML attribute and CSS resource scan. All dependencies are inline; no browser or network execution. SVG typography derivative preserves all HTML outside its SVG byte-for-byte.'}
write('asset-dependencies.json',assets)
source_names=['managed-presentation.json','policy-plan.json','policy-verify.json','mcp-verify.json','native-managed-verification.json','native-managed-ui4-verification.json','native-managed-artifact-review.json','host-runtime-check.json','client-relaunch.json','media-review.json']
sources=[fp('evidence/enterprise-managed/20260913/'+n) for n in source_names]
require(sources[0]['sha256']=='871f808d6ff8d5d5bc6c97f1afc2893bacc84f0248cdff879bf5f86b1223a77d','Managed summary differs from parent freeze')
legacy_names=['evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json','evidence/native-client-demo/20260913-ui2-reconciled-final/review.json','evidence/native-client-demo/20260913-ui2/authority-arm-readback.json','evidence/native-client-demo/20260913-ui2/authority-aws-readback.json']
legacy_sources=[fp(n) for n in legacy_names]
summary=json.loads((ROOT/'evidence/enterprise-managed/20260913/managed-presentation.json').read_text())
verified_refs=[]
def verify_refs(obj):
    if isinstance(obj,dict):
        if {'path','sha256','bytes'} <= obj.keys():
            f=fp(obj['path']);require(f['sha256']==obj['sha256'] and f['bytes']==obj['bytes'],'Public summary source mismatch: '+obj['path']);verified_refs.append(f)
        for v in obj.values():verify_refs(v)
    elif isinstance(obj,list):
        for v in obj:verify_refs(v)
verify_refs(summary)
write('source-bindings.json',{'schema_version':1,'kind':'managed_diagram_source_bindings','current_managed_sources':sources,'earlier_native_authorities':legacy_sources,'frozen_summary_references_verified':verified_refs,'scope':'Current managed facts are bound to deployed receipts. Earlier authority and refusal evidence retains its recorded date. No dependency on the new deck, mutable current-status file, or unfinished guide edits.'})
base_delivery=json.loads((EV/'base-delivery.json').read_text());artifact_check=json.loads((EV/'final-artifact-check.txt').read_text())
require(base_delivery['ok'] and base_delivery['validation']['checksPassed']==9,'Base delivery failed')
require(artifact_check['ok'] and len(artifact_check['checks'])==9 and all(c['ok'] for c in artifact_check['checks']),'Final static check failed')
require(artifact_check['composition']['summary']=={'errors':0,'warnings':0},'Final composition diagnostics')
require(fp(source_path)['sha256']==base_delivery['specification']['sha256'],'Spec changed after delivery')
require(fp(EV/'base.html')['sha256']==base_delivery['artifact']['sha256'],'Base changed after delivery')
write('perceptual-static-review.json',{'schema_version':1,'kind':'static_svg_perceptual_review','reviewer':'/root/actual_archify','images':[fp(EV/(STEM+'-1152x480.png')),fp(EV/'stage-static-1030x568.png')],'observed':['All eight nodes, seven routes and the single EC2 enclosure remain visible.','Managed policy label and cc/YOLO subtitle fit the existing control node.','Mac client, original CLI, separate MCP UID and IAM authority labels remain readable at the 1030×568 stage approximation.','No overlapping node text, clipped labels, or route-label collisions observed.'],'scope':'Image-capable review of librsvg exports only. The 1152×480 export is supplemental; the deck links the standalone HTML for exploration. Cards and viewer behavior need parent browser QA.','browser_review_performed':False})
limits=[
 'Browser interaction, dark/light rendering, cards, presentation mode and four-viewport coverage are not validated by these static checks; parent browser review is separate.',
 'Only the fresh managed denial was filmed. The allowed read has native/service evidence but no retained ui3 video. Earlier MCP-grant and IAM-refusal clips predate the managed policy.',
 'Native managed denial attribution uses the explicit host governance notice and policy SEL correlated by isolated slot/time and adjacent hash linkage; the governance event has no direct native tool ID.',
 'Owner Crew-only MCP availability can narrow exposure. The captured restriction was staged and discarded; no applied local restriction test is claimed.',
 'The pinned S3 upload deny and unavailable YOLO mode are policy/UI observations, not fresh native denial takes. Reads and Trust remain available.',
 'Linux cc is not Seatbelt or strict isolation. CLI seccomp/mount snapshots and a disposable crew-UID child PTY EPERM do not establish exact-slot/tool sandbox enforcement.',
 'Sensitive-path read, protected-path write and native IMDS execution recordings remain unfinished.',
 'The client quit/relaunch receipt predates policy installation; the later native turns establish governed behavior.',
 'Host root retains authority. No signed fleet policy, enterprise SSO, human-role RBAC or central MCP registry is claimed.',
 'The current installer source differs from the hash in the retained policy plan. This artifact binds the deployed policy bytes and observations; it does not claim the present installer equals that deployed candidate.'
]
receipt={'schema_version':1,'kind':'managed_architecture_delivery','created_at':datetime.now(timezone.utc).isoformat(),'specification':fp(source_path),'artifact':fp(html_path),'base_delivery':fp(EV/'base-delivery.json'),'base_artifact':fp(EV/'base.html'),'typography_derivative':fp(EV/'typography-derivative.json'),'final_artifact_check':fp(EV/'final-artifact-check.txt'),'validation':{'checks_passed':9,'check_count':9,'quality_profile':'showcase','composition_errors':0,'composition_warnings':0},'topology':{'nodes':8,'routes':7,'endpoint_control_enclosures':1,'node_route_enclosure_geometry_byte_values_unchanged':True,'accepted_reference':fp(ROOT/'kirocrew-native-controls-diagram.html')},'accepted_archive_manifest':fp(EV/'accepted-before-managed/manifest.json'),'source_bindings':fp(EV/'source-bindings.json'),'asset_dependencies':fp(EV/'asset-dependencies.json'),'static_export':fp(EV/(STEM+'-static.json')),'perceptual_static_review':fp(EV/'perceptual-static-review.json'),'browser_validation':{'status':'not_run_in_this_lane','reason':'Parent owns the actual browser check. No browser/server reroute was attempted after the prior CUA file-URL policy block.','prior_native_browser_receipt_reused_as_managed_pass':False},'installed_archify_skill_modified':False,'source_changes':'New managed derivative only: policy node wording, policy edge wording, dated earlier S3-denial subtitle and three evidence cards. Accepted native and historical ARM/x86 artifacts remain unchanged.','commands':['archify validate architecture kirocrew-managed-controls-diagram.architecture.json --quality showcase --json','archify deliver architecture kirocrew-managed-controls-diagram.architecture.json evidence/enterprise-managed/20260913/archify/base.html --quality showcase --json','python3 evidence/enterprise-managed/20260913/archify/enlarge-typography.py','check-render-output.mjs kirocrew-managed-controls-diagram.html','node evidence/enterprise-managed/20260913/archify/render-static.cjs kirocrew-managed-controls-diagram'],'limits':limits,'receipt_generator':fp(Path(__file__).resolve())}
write('delivery-receipt.json',receipt)
print(json.dumps({'artifact':receipt['artifact'],'specification':receipt['specification'],'asset_dependencies':receipt['asset_dependencies'],'delivery_receipt':fp(EV/'delivery-receipt.json'),'frozen_summary_public_references_verified':len(verified_refs),'topology':{'nodes':8,'routes':7,'enclosures':1}},indent=2))
