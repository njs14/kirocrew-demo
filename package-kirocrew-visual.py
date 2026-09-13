"""Check embedding, bind validation/review receipts, and package the demo source."""
from pathlib import Path
import json,hashlib,re,base64,subprocess,zipfile
base=Path(__file__).parent
load=lambda name:json.loads((base/name).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def fp(name):
 b=(base/name).read_bytes();return {'name':name,'sha256':sha(b),'bytes':len(b)}
wrapper=(base/'kirocrew-aws-remote.html').read_text()
script=re.search(r'<script>([\s\S]*?)</script>',wrapper).group(1)
(base/'security-viewer-script.js').write_text(script)
subprocess.run(['node','--check',str(base/'security-viewer-script.js')],check=True)
embedding={}
for key,name in [('security','kirocrew-security-layers.html'),('aws','kirocrew-aws-deployment.html')]:
 data=base64.b64decode(re.search(key+r":'([^']+)'",script).group(1));assert data==(base/name).read_bytes()
 embedding[key]={'source':name,'sha256':sha(data),'exactBytesMatch':True}
assert embedding['aws']['sha256']=='4375acf0466215035c06b9a9d643555eb9b6e5a478e541b6558435b14ac07784'
assert len(load('kirocrew-control-layers.json')['layers'])==15
checks={}
for name in ['kirocrew-security-layers.html','kirocrew-aws-deployment.html']:
 r=subprocess.run(['node',str(base/'archify-source/archify/bin/archify.mjs'),'check',str(base/name),'--json'],check=True,text=True,capture_output=True)
 checks[name]=json.loads(r.stdout)
review=load('kirocrew-endpoint-review.json')
assert review['status']=='completed'
files=[
 'kirocrew-aws-remote.html','kirocrew-aws-remote-preview.png','kirocrew-aws-remote-notes.md',
 'kirocrew-security-layers.html','kirocrew-security-layers-base.html','kirocrew-security-layers.architecture.json',
 'kirocrew-security-layers-preview.svg','kirocrew-security-layers-dark-preview.png','kirocrew-security-layers-dark-preview.svg',
 'kirocrew-control-layers.json','kirocrew-security-layers-delivery.json','kirocrew-endpoint-detail.json',
 'kirocrew-security-layers.visual-check.json','kirocrew-security-layers-base.visual-check.json',
 'kirocrew-endpoint-review.json','kirocrew-aws-deployment.html','kirocrew-aws-deployment-preview.png',
 'kirocrew-aws-deployment-notes.md','kirocrew-aws-remote.architecture.json','kirocrew-aws-remote-base.html',
 'kirocrew-aws-icons.json','kirocrew-aws-base-delivery.json','build-security-diagram.py','detail-endpoint-panel.py',
 'build-security-viewer.py','export-security-preview.cjs','package-kirocrew-visual.py','add-aws-icons.cjs','export-aws-preview.cjs'
]
receipt={
 'schemaVersion':3,
 'artifactType':'Viewer with two checked Archify architecture diagrams and a 15-control reference',
 'kirocrewBaseline':{'version':'0.7.0.dev20260911060948','commit':'fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482','freshLatestFeedVerified':False},
 'diagramChecks':checks,'newBaseDiagramDelivery':load('kirocrew-security-layers-delivery.json'),
 'detailedEndpointDerivative':load('kirocrew-endpoint-detail.json'),
 'embedding':embedding,
 'wrapperChecks':{'javascriptSyntax':'node --check passed','controlEntries':15,'awsViewUnchanged':True,'browserBehavior':'unverified'},
 'browserEvidence':load('kirocrew-security-layers.visual-check.json'),
 'visualReview':review,
 'artifacts':[fp(n) for n in files]
}
(base/'kirocrew-aws-remote-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
readme='''KiroCrew endpoint control and AWS governance

Open kirocrew-aws-remote.html. It is self-contained and embeds both diagrams.
The security view now has one endpoint panel, with host protection, runtime,
policy, six numbered layers and cross-cutting controls inside it. The AWS
view and all 15 reference entries remain available in the same viewer.

Editing and reproduction (Archify revision c1443b31b496eebf4a68bf83151816c955ddb796):
1. Edit kirocrew-security-layers.architecture.json. The authoring script
   build-security-diagram.py reproduces the accepted geometry and label fixes.
2. Validate with Archify, then deliver to kirocrew-security-layers-base.html.
   Keep this accepted base unchanged.
3. Run detail-endpoint-panel.py to add detailed SVG rows and vector icons in a
   separate kirocrew-security-layers.html derivative. Check that derivative.
4. Run export-security-preview.cjs (requires sharp), also with --dark.
5. Run build-security-viewer.py to assemble the viewer and notes.
6. Review the rendered previews and viewer where a browser is available.
   Record artifact-bound findings, then use package-kirocrew-visual.py.

AWS source: kirocrew-aws-remote.architecture.json. The image-bearing derivative
is kirocrew-aws-deployment.html. AWS icons and the retained AWS preview are included.
The older add-aws-icons.cjs writes kirocrew-aws-remote.html: if regenerating AWS,
copy its output to kirocrew-aws-deployment.html before rebuilding the viewer.

Validation and limitation:
The Archify base and both displayed diagrams passed 9/9 static artifact checks.
The detailed security SVG was visually reviewed in light and dark by the author
and a subagent. See kirocrew-endpoint-review.json for findings and resolutions.
Chromium was unavailable; browser containment and interactions remain unverified.
The wrapper is a separate integration artifact, not a single-diagram deliver receipt.
Nightly source remains the verified Sept 11 build; the latest feed was not refreshed.
Source links, control limits, and demo proof are in the notes and reference tab.
'''
with zipfile.ZipFile(base/'kirocrew-aws-remote-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in files+['kirocrew-aws-remote-receipt.json']:z.write(base/n,n)
 for p in sorted((base/'aws-diagram-assets').glob('*')):
  if p.is_file():z.write(p,str(p.relative_to(base)))
 z.writestr('README.txt',readme)
print(json.dumps({'diagramChecks':{k:v['ok'] for k,v in checks.items()},'embedding':embedding,'review':review['status'],'zipBytes':(base/'kirocrew-aws-remote-source.zip').stat().st_size},indent=2))
