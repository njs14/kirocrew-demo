import React, {useCallback, useEffect, useState} from 'react';
import {useAppApi, useTheme} from '@kirocrew/app-sdk';

const h = React.createElement;
const css = `
.demo-obs{--ink:#203040;--muted:#627184;--line:#dce4ec;--panel:#fff;--canvas:#f5f8fb;--ok:#13765c;--ok-bg:#e8f6ef;--warn:#94510b;--warn-bg:#fff3df;--bad:#ac3038;--bad-bg:#fff0f0;box-sizing:border-box;flex:1;min-height:0;overflow:auto;background:var(--canvas);color:var(--ink);font:14px/1.5 system-ui,sans-serif}
.demo-obs[data-theme=dark]{--ink:#e3eaf4;--muted:#a5b2c5;--line:#334154;--panel:#1c2735;--canvas:#141d29;--ok:#84dcb9;--ok-bg:#153d32;--warn:#f2c27e;--warn-bg:#44341e;--bad:#ffa3a9;--bad-bg:#49242a}
.demo-obs *{box-sizing:border-box}.demo-obs .wrap{max-width:1240px;margin:auto;padding:24px 28px 36px}.demo-obs .head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:18px}.demo-obs h1{font-size:26px;line-height:1.2;letter-spacing:-.6px;font-weight:650;margin:4px 0 8px}.demo-obs h2{font-size:18px;line-height:1.3;font-weight:650;margin:0}.demo-obs p{margin:0;color:var(--muted)}.demo-obs .eyebrow{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted)}.demo-obs .btn{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:7px;padding:7px 12px;font:inherit;cursor:pointer}.demo-obs .btn:hover{border-color:var(--muted)}.demo-obs .btn:focus-visible{outline:3px solid #6aa8ec;outline-offset:2px}.demo-obs .btn[disabled]{opacity:.6;cursor:wait}.demo-obs .btn[aria-pressed=true]{background:var(--ink);color:var(--panel)}.demo-obs .cards{display:grid;grid-template-columns:1fr 1fr;gap:16px}.demo-obs .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px}.demo-obs .card-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:2px}.demo-obs .pill{display:inline-flex;align-items:center;border-radius:20px;padding:3px 9px;font-size:11px;font-weight:650;white-space:nowrap;background:var(--warn-bg);color:var(--warn)}.demo-obs .pill.good{background:var(--ok-bg);color:var(--ok)}.demo-obs .pill.bad{background:var(--bad-bg);color:var(--bad)}.demo-obs .stamp{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}.demo-obs .stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:17px 0}.demo-obs .stat-label{color:var(--muted);font-size:12px}.demo-obs .stat-value{font-size:27px;line-height:1.4;letter-spacing:-.6px;font-weight:600}.demo-obs .stat-value small{font-size:12px;letter-spacing:0;color:var(--muted);font-weight:400;margin-left:4px}.demo-obs .checks{border-top:1px solid var(--line);padding-top:10px;display:grid;gap:7px}.demo-obs .check{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:12px}.demo-obs .check-state{font-size:11px;font-weight:650;color:var(--ok)}.demo-obs .check-state.bad{color:var(--bad)}.demo-obs .check-state.unknown{color:var(--muted)}.demo-obs .source{margin-top:12px;font-size:11px;line-height:1.45;color:var(--muted)}.demo-obs .source strong{color:var(--ink);font-weight:600}.demo-obs .source-note{font-size:11px;margin-top:3px}.demo-obs .events{margin-top:16px}.demo-obs .events-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.demo-obs .filters{display:flex;gap:5px}.demo-obs .filters .btn{padding:4px 10px;font-size:12px}.demo-obs table{width:100%;border-collapse:collapse;font-size:12px}.demo-obs th{text-align:left;color:var(--muted);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid var(--line);padding:0 10px 8px 0}.demo-obs td{padding:10px 10px 10px 0;border-bottom:1px solid var(--line);vertical-align:top}.demo-obs tbody tr:last-child td{border:0}.demo-obs .time{font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--muted)}.demo-obs .scope{border-left:3px solid #6c97c6;padding-left:12px;margin-top:16px;font-size:12px}.demo-obs .scope strong{color:var(--ink);font-weight:600}.demo-obs .error{padding:12px 15px;margin-bottom:16px;background:var(--bad-bg);color:var(--bad);border-radius:8px}.demo-obs details{margin-top:12px;font-size:12px}.demo-obs summary{cursor:pointer;color:var(--muted)}.demo-obs .details-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;margin-top:8px;color:var(--muted)}.demo-obs .details-grid span:nth-child(even){text-align:right;font-variant-numeric:tabular-nums}.demo-obs .empty{padding:18px 0;color:var(--muted);font-size:12px}.demo-obs .footer{margin-top:12px;font-size:11px;color:var(--muted)}
@media(max-width:720px){.demo-obs .wrap{padding:20px 16px}.demo-obs .cards{grid-template-columns:1fr}.demo-obs .head,.demo-obs .events-head{flex-wrap:wrap}.demo-obs h1{font-size:23px}.demo-obs .time{white-space:normal}.demo-obs .card{padding:16px}}
`;
const checkLabels = {
  client_running:'KiroCrew desktop running',remote_gateway_reachable:'SSH tunnel listener reachable',local_gateway_off:'Local Gateway off',
  gateway_service_active:'Gateway service active',mcp_service_active:'MCP service active',gateway_loopback_reachable:'Gateway loopback reachable',mcp_loopback_reachable:'MCP loopback reachable'
};
const detailedLabels = {
  process_count:['Client processes',''],memory_used_mib:['Memory used','MiB'],memory_total_mib:['Memory total','MiB'],
  disk_used_gib:['Disk used','GiB'],disk_total_gib:['Disk total','GiB'],gateway_cpu_percent:['Gateway main-process CPU','%'],
  gateway_rss_mib:['Gateway main-process memory','MiB'],mcp_cpu_percent:['MCP main-process CPU','%'],mcp_rss_mib:['MCP main-process memory','MiB']
};
const num = (v,d=1) => typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString(undefined,{maximumFractionDigits:d}) : '—';
const when = v => v ? new Date(v).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}) : 'No sample';
const ageLabel = v => v == null ? '' : v < 60 ? `${Math.floor(v)}s ago` : `${Math.floor(v/60)}m ago`;

export function samplePresentation(sample,refreshFailed,now){
  const stamp=Date.parse(sample?.collected_at);
  if(!Number.isFinite(stamp)) return {age:null,good:false,label:'No sample'};
  const elapsed=(now-stamp)/1000;
  const age=Math.max(0,elapsed);
  if(refreshFailed) return {age,good:false,label:elapsed>180?'Last known · stale':'Last known sample'};
  if(elapsed < -60) return {age:null,good:false,label:'Check clock'};
  if(elapsed > 180) return {age,good:false,label:'Stale'};
  return {age,good:sample.status==='ok',label:sample.status==='ok'?'Current':'Partial sample'};
}

function Stat({label,value,unit}){
  return h('div',null,h('div',{className:'stat-label'},label),h('div',{className:'stat-value'},num(value),h('small',null,unit)));
}
function SourceCard({source,data,refreshFailed,now}){
  const sample=data || {metrics:{},checks:{},freshness:'unavailable'};
  const metrics=sample.metrics;
  const presentation=samplePresentation(sample,refreshFailed,now);
  return h('section',{className:'card','aria-label':source==='client'?'Client telemetry':'Server telemetry'},
    h('div',{className:'card-head'},h('h2',null,source==='client'?'Client · macOS':'Server · EC2'),h('span',{className:`pill ${presentation.good?'good':''}`},presentation.label)),
    h('div',{className:'stamp'},when(sample.collected_at),presentation.age==null?'':` · ${ageLabel(presentation.age)}`),
    h('div',{className:'stats'},h(Stat,{label:source==='client'?'KiroCrew process CPU':'Host CPU',value:metrics.cpu_percent,unit:'%'}),h(Stat,{label:source==='client'?'KiroCrew process memory':'Memory available',value:source==='client'?metrics.rss_mib:typeof metrics.memory_available_mib==='number'?metrics.memory_available_mib/1024:null,unit:source==='client'?'MiB':'GiB'})),
    h('div',{className:'checks'},Object.entries(sample.checks).map(([key,value])=>h('div',{className:'check',key},h('span',null,checkLabels[key]||key),h('span',{className:`check-state ${value===false?'bad':value==null?'unknown':''}`},value===true?'Yes':value===false?'No':'Unknown')))),
    h('div',{className:'source'},h('strong',null,'Collection source: '),sample.collection_source || 'Waiting for collector'),
    h('p',{className:'source-note'},source==='client'?'CPU is the sum of process scheduler averages; it can exceed 100%.':'Host CPU uses a one-second sample. Service metrics cover each main process.'),
    h('details',null,h('summary',null,'More measurements'),h('div',{className:'details-grid'},Object.entries(detailedLabels).filter(([key])=>Object.hasOwn(metrics,key)).flatMap(([key,[label,unit]])=>[h('span',{key:`${key}-label`},label),h('span',{key},`${num(metrics[key])}${unit?' '+unit:''}`)])))
  );
}

export default function DemoObservability(){
  const api=useAppApi();
  const theme=useTheme();
  const [data,setData]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState(false);
  const [filter,setFilter]=useState('all');
  const [now,setNow]=useState(Date.now);
  const load=useCallback(async()=>{
    setBusy(true);
    try {const next=await api.get('/apps/demo-observability/api/snapshot');setData(next);setError(false);}
    catch {setError(true);}
    finally {setBusy(false);}
  },[api]);
  useEffect(()=>{load();const timer=setInterval(load,15000);return()=>clearInterval(timer);},[load]);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[]);
  const events=(data?.events||[]).filter(event=>filter==='all'||event.source===filter);
  return h('main',{className:'demo-obs','data-theme':theme.mode},h('style',null,css),h('div',{className:'wrap'},
    h('header',{className:'head'},h('div',null,h('div',{className:'eyebrow'},'KiroCrew demo · Custom telemetry'),h('h1',null,'Client and server, in one view'),h('p',null,'Live collector samples and recent collection events.')),h('button',{className:'btn',onClick:load,disabled:busy},busy?'Refreshing…':'Refresh')),
    error?h('div',{className:'error',role:'alert'},'Could not refresh telemetry. Any values below are from the last successful refresh.'):null,
    h('div',{className:'cards'},h(SourceCard,{source:'client',data:data?.sources?.client,refreshFailed:error,now}),h(SourceCard,{source:'server',data:data?.sources?.server,refreshFailed:error,now})),
    h('section',{className:'card events','aria-label':'Telemetry collection logs'},h('div',{className:'events-head'},h('div',null,h('h2',null,'Collection logs'),h('p',{className:'source-note'},'First samples, health changes and collection errors.')),h('div',{className:'filters','aria-label':'Filter logs by source'},['all','client','server'].map(value=>h('button',{key:value,className:'btn','aria-pressed':filter===value,onClick:()=>setFilter(value)},value[0].toUpperCase()+value.slice(1))))),
      events.length?h('table',null,h('thead',null,h('tr',null,h('th',null,'Collected at'),h('th',null,'Source'),h('th',null,'Event'),h('th',null,'Level'))),h('tbody',null,events.slice(0,20).map((event,index)=>h('tr',{key:`${event.at}-${event.source}-${index}`},h('td',{className:'time'},when(event.at)),h('td',null,event.source==='client'?'Client':'Server'),h('td',null,event.message),h('td',null,h('span',{className:`pill ${event.level==='info'?'good':event.level==='error'?'bad':''}`},event.level)))))):
      h('div',{className:'empty'},data?.events_available?'No collection events for this source yet.':'Collection logs are not available yet.'),
      h('div',{className:'footer'},`Showing ${Math.min(events.length,20)} of ${events.length} matching events. The collector retains up to ${data?.events_limit||200} events.`)),
    h('p',{className:'scope'},h('strong',null,'What this view proves. '),'These are custom health probes from the laptop and EC2 instance. KiroCrew’s native Telemetry panel reports Gateway instrumentation separately. Collection logs contain fixed event labels; prompts, chat content and credentials are excluded.'),
    h('div',{className:'footer'},'Refreshes every 15 seconds. Samples become stale after three minutes.',data?.generated_at?` Last successful refresh: ${when(data.generated_at)}.`:'')
  ));
}
