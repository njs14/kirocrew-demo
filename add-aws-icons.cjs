const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const base = __dirname;
const sourceRoot = path.join(base,'aws-icons-source');
const spec = JSON.parse(fs.readFileSync(path.join(base,'kirocrew-aws-remote.architecture.json'),'utf8'));
let html = fs.readFileSync(path.join(base,'kirocrew-aws-remote-base.html'),'utf8');
const map = {
  'session-manager':['ManagementGovernance/SystemsManager.png'],
  'policy-bucket':['Storage/SimpleStorageService.png'],
  'app-logs':['ManagementGovernance/CloudWatch.png'],
  'ssm-endpoints':['NetworkingContentDelivery/PrivateLink.png'],
  'execution-host':['Compute/EC2.png'],
  'mcp-tier':['Containers/Fargate.png'],
  'controlled-egress':['SecurityIdentityCompliance/NetworkFirewall.png','NetworkingContentDelivery/VPCNATGateway.png'],
  'encrypted-volume':['Storage/ElasticBlockStore.png'],
  'tool-resources':['SecurityIdentityCompliance/IdentityandAccessManagement.png']
};
const manifest = {schemaVersion:1,source:'https://github.com/awslabs/aws-icons-for-plantuml',revision:'e26e2c05daf8b6bc4c764669fc2be04c314ccb8c',method:'AWS-published PNG assets embedded in a derivative of the checked Archify HTML. Base HTML and specification remain unchanged.',assets:[]};
fs.mkdirSync(path.join(base,'aws-diagram-assets'),{recursive:true});
for(const [id,assets] of Object.entries(map)) {
  const n=spec.components.find(n=>n.id===id);
  const start=html.indexOf('<g id="node-'+id+'"');
  const next=html.indexOf('<g id="node-', start+1);
  const end=next<0?html.indexOf('<!-- Relationship',start):next;
  if(start<0)throw Error('Missing node '+id);
  const sigil=/<g aria-hidden="true" data-semantic-sigil="[^"]+"[\s\S]*?<\/g>/;
  const tail=html.slice(start,end>start?end:undefined);
  if(!sigil.test(tail)) throw Error('Missing sigil '+id);
  const images=assets.map((file,i)=>{
    const local=path.basename(file);
    const source=path.join(sourceRoot,'dist',file);
    const bytes=fs.readFileSync(fs.existsSync(source)?source:path.join(base,'aws-diagram-assets',local));
    fs.writeFileSync(path.join(base,'aws-diagram-assets',local),bytes);
    manifest.assets.push({node:id,repositoryPath:'dist/'+file,localPath:'aws-diagram-assets/'+local,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length});
    return '<image aria-hidden="true" data-aws-service-icon="'+local+'" x="'+(n.pos[0]+8+i*33)+'" y="'+(n.pos[1]+6)+'" width="28" height="28" preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,'+bytes.toString('base64')+'"/>';
  }).join('\n');
  const changed=tail.replace(sigil,images);
  html=html.slice(0,start)+changed+(end>start?html.slice(end):'');
}
html=html.replace('</head>','<!-- AWS service icon provenance: awslabs/aws-icons-for-plantuml @ '+manifest.revision+'; see kirocrew-aws-icons.json. -->\n</head>');
fs.writeFileSync(path.join(base,'kirocrew-aws-remote.html'),html);
fs.writeFileSync(path.join(base,'kirocrew-aws-icons.json'),JSON.stringify(manifest,null,2)+'\n');
console.log('Embedded '+manifest.assets.length+' AWS service icons in a separate HTML derivative.');
