const fs=require('fs');
const sharp=require('sharp');
const base=__dirname+'/';
const html=fs.readFileSync(base+'kirocrew-aws-remote.html','utf8');
let css=[...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map(m=>m[1]).join('\n');
css=css.replace(/\/\*[\s\S]*?\*\//g,'').replace(/@font-face\s*\{[^}]*\}/g,'');
const rules=[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(m=>({selector:m[1].trim(),body:m[2]}));
const light=rules.find(r=>r.selector==='[data-theme="light"]');
const vars=Object.fromEntries([...light.body.matchAll(/(--[a-z-]+)\s*:\s*([^;]+);/g)].map(m=>[m[1],m[2].trim()]));
const selected=rules.filter(r=>!r.selector.includes('[')&&!r.selector.includes(':')&&/(?:^|[\s,])\.(?:c-|t-|a-|m-|s-|semantic-sigil|sigil-fill)/.test(r.selector));
let resolved=selected.map(r=>r.selector+'{'+r.body+'}').join('\n').replace(/var\((--[a-z-]+)\)/g,(_,name)=>{if(!vars[name])throw Error('Missing theme value '+name);return vars[name];});
resolved+='\ntext {font-family:"DejaVu Sans Mono",monospace;}';
let svg=html.match(/<svg\b[\s\S]*?<\/svg>/)[0];
svg=svg.replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" width="1980" height="1320" ');
svg=svg.replace('<defs>','<style><![CDATA['+resolved+']]></style><rect width="1320" height="880" fill="'+vars['--panel']+'"/><defs>');
// Static presentation wrapper; the checked interactive HTML remains unchanged.
const notes=[
  '* Policy sync is a proposed adapter: IAM reads S3; a protected file:// source supplies Crew policy.',
  'Human tunnel identity, Crew permissions, and downstream MCP task-role IAM are separate controls.',
  'SSM does not record forwarded payload. Collect Crew / MCP logs; CloudTrail records SSM API activity.',
  'Private AWS access: S3 gateway endpoint + Logs interface endpoint. NAT alone does not filter egress.',
  'Proposed pilot · retained nightly 0.7.0.dev20260911060948 · deployment and integrations untested.'
];
const escape=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
svg=svg.replace('width="1980" height="1320"','width="1980" height="1530"').replace('viewBox="0 0 1320 880"','viewBox="0 0 1320 1020"').replace('<rect width="1320" height="880"','<rect width="1320" height="1020"');
svg=svg.replace('</svg>', '<text x="30" y="38" fill="#192b40" font-family="DejaVu Sans,sans-serif" font-size="24" font-weight="700">KiroCrew remote Gateway on AWS</text>'
  +'<rect x="0" y="885" width="1320" height="135" fill="#f5f8fc"/>'
  +notes.map((line,i)=>'<text x="30" y="'+(910+i*21)+'" fill="#34445c" font-family="DejaVu Sans,sans-serif" font-size="11">'+escape(line)+'</text>').join('')+'</svg>');
fs.writeFileSync(base+'kirocrew-aws-remote-preview.svg',svg);
sharp(Buffer.from(svg)).png().toFile(base+'kirocrew-aws-remote-preview.png').then(()=>console.log('Rendered a static AWS diagram with title and deployment notes.'));
