import json
from pathlib import Path
base=Path(__file__).parent
s={
 'schema_version':1,'diagram_type':'architecture',
 'meta':{'title':'KiroCrew · One endpoint, layered control','subtitle':'Execution host → governed MCP → target authorization','locale':'en','quality_profile':'showcase','viewBox':[1380,1030]},
 'components':[
  {'id':'developer-entry','type':'frontend','label':'Developer','sublabel':'Desktop · browser · CLI','tag':'Identity at entry','pos':[20,555],'size':[170,100]},
  {'id':'endpoint-control','type':'security','label':'Endpoint control','sublabel':'Enterprise baseline + KiroCrew L0–L5','tag':'Local endpoint or remote execution host','pos':[330,255],'size':[710,700]},
  {'id':'central-policy','type':'security','label':'Central policy authority','sublabel':'Protected policy → local enforcement','tag':'Remote distribution adapter proposed','pos':[545,30],'size':[280,105]},
  {'id':'mcp-tool-governance','type':'security','label':'MCP governance','sublabel':'Server / tool grants · OAuth','tag':'Proposed LiteLLM / service tier','pos':[1160,555],'size':[200,100]},
  {'id':'target-permissions','type':'cloud','label':'Target authorization','sublabel':'AWS IAM · SaaS permissions','tag':'Independent resource decision','pos':[1160,850],'size':[200,100]}
 ],
 'connections':[
  {'id':'authenticated-entry','from':'developer-entry','to':'endpoint-control','label':'Access','variant':'emphasis'},
  {'id':'policy-sync','from':'central-policy','to':'endpoint-control','label':'Policy ceiling','variant':'security','labelAt':[685,195]},
  {'id':'governed-mcp-route','from':'endpoint-control','to':'mcp-tool-governance','label':'Routed MCP','variant':'emphasis'},
  {'id':'resource-request','from':'mcp-tool-governance','to':'target-permissions','label':'Scoped API','variant':'security','labelAt':[1260,755]}
 ],
 'cards':[
  {'dot':'cyan','title':'One box = the execution host','items':[
   'Local mode: the developer endpoint. Remote mode: the EC2 host, or a proposed session MicroVM with Crew and the agent together.',
   'Enterprise protection and Crew enforcement have separate owners. Independent laptop agents are outside a remote Crew service.'
  ]},
  {'dot':'rose','title':'Prove the enforcement path','items':[
   '* Pre-tool decisions require the actual backend to reach a Crew hook or permission callback. Native auto-approval can skip that boundary.',
   'Sandbox, schema and redaction coverage depend on the active platform, backend, tool and sink. L0 confines agent descendants when active.'
  ]},
  {'dot':'emerald','title':'Keep the authorities separate','items':[
   'Crew evaluates the effective Policy ∩ Profile locally. Routed MCP calls face service grants, then the target system’s IAM or OAuth decision.',
   'Skills and memory provide context, not ACLs. SEL verification covers recorded events; external collection and retention are deployment work.'
  ]}
 ]
}
(base/'kirocrew-security-layers.architecture.json').write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
