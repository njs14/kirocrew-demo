const fs=require('fs');
const sharp=require('sharp');
const base=__dirname+'/';
const theme=process.argv.includes('--dark')?'dark':'light';
const html=fs.readFileSync(base+'kirocrew-security-layers.html','utf8');
let css=[...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map(m=>m[1]).join('\n').replace(/\/\*[\s\S]*?\*\//g,'').replace(/@font-face\s*\{[^}]*\}/g,'');
const rules=[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(m=>({selector:m[1].trim(),body:m[2]}));
const themeRule=rules.find(r=>r.selector.split(',').map(x=>x.trim()).includes('[data-theme="'+theme+'"]'));
const vars=Object.fromEntries([...themeRule.body.matchAll(/(--[a-z-]+)\s*:\s*([^;]+);/g)].map(m=>[m[1],m[2].trim()]));
const selected=rules.filter(r=>!r.selector.includes('[')&&!r.selector.includes(':')&&/(?:^|[\s,])\.(?:c-|t-|a-|m-|s-|ep-|semantic-sigil|sigil-fill)/.test(r.selector));
let resolved=selected.map(r=>r.selector+'{'+r.body+'}').join('\n').replace(/var\((--[a-z-]+)\)/g,(_,name)=>{if(!vars[name])throw Error('Missing theme value '+name);return vars[name];});
resolved+='\ntext {font-family:"DejaVu Sans Mono",monospace;}';
const original=html.match(/<svg\b[\s\S]*?<\/svg>/)[0];
const opening=original.slice(0,original.indexOf('>')+1);
const body=original.slice(opening.length,-6);
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
const notes=[
 '* Pre-tool enforcement requires a Crew hook or permission callback; coverage depends on backend and configuration.',
 'This is a control map. OS sandbox, schema and output coverage vary; the reference tab records the limits and demo proof.',
 'Verified nightly: 0.7.0.dev20260911060948. Latest-feed refresh unavailable. External integrations remain proposed.'
];
let svg='<svg xmlns="http://www.w3.org/2000/svg" width="2070" height="1860" viewBox="0 0 1380 1240">'+
 '<style><![CDATA['+resolved+']]></style><rect width="1380" height="1240" fill="'+vars['--bg']+'"/>'+
 '<text x="24" y="38" fill="'+vars['--text']+'" font-size="25" font-weight="700">One endpoint, layered control</text>'+
 '<text x="24" y="65" fill="'+vars['--text-muted']+'" font-size="12">KiroCrew governance · host protection · controlled tool access</text>'+
 '<g transform="translate(0 85)">'+body+'</g>'+
 '<path d="M24 1130H1356" stroke="'+vars['--lane-stroke']+'"/>'+
 notes.map((l,i)=>'<text x="24" y="'+(1158+i*27)+'" fill="'+vars['--text-muted']+'" font-size="11">'+esc(l)+'</text>').join('')+'</svg>';
const stem=theme==='light'?'kirocrew-security-layers-preview':'kirocrew-security-layers-dark-preview';
fs.writeFileSync(base+stem+'.svg',svg);
sharp(Buffer.from(svg)).png().toFile(base+(theme==='light'?'kirocrew-aws-remote-preview.png':stem+'.png')).then(()=>console.log('Rendered '+theme+' security preview.'));
