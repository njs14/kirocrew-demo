import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

// Load the shipped module. Only the host-provided React/SDK imports are inert;
// these checks exercise the same presentation function the live cards call.
const source=await readFile(new URL('../app/ui/dist/index.mjs',import.meta.url),'utf8');
const context=vm.createContext({});
const react=new vm.SyntheticModule(['default','useCallback','useEffect','useState'],function(){
  this.setExport('default',{createElement:()=>{}});
  for(const name of ['useCallback','useEffect','useState']) this.setExport(name,()=>{});
},{context});
const sdk=new vm.SyntheticModule(['useAppApi','useTheme'],function(){
  this.setExport('useAppApi',()=>{});this.setExport('useTheme',()=>{});
},{context});
const app=new vm.SourceTextModule(source,{context});
await app.link(name=>name==='react'?react:sdk);
await app.evaluate();
const view=app.namespace.samplePresentation;
const sample={collected_at:'2026-09-13T14:00:00Z',status:'ok',age_seconds:0,freshness:'current'};
const stamp=Date.parse(sample.collected_at);

test('sample age advances and becomes stale without a network refresh',()=>{
  assert.equal(view(sample,false,stamp+5000).age,5);
  assert.equal(view(sample,false,stamp+180000).good,true);
  assert.equal(view(sample,false,stamp+181000).label,'Stale');
  assert.equal(view(sample,false,stamp+181000).good,false);
});
test('failed refresh retains a labeled last-known sample and never shows green Current',()=>{
  assert.equal(view(sample,true,stamp+10000).label,'Last known sample');
  assert.equal(view(sample,true,stamp+10000).good,false);
  assert.equal(view(sample,true,stamp+200000).label,'Last known · stale');
  assert.equal(view(sample,true,stamp+200000).age,200);
});
test('missing and future timestamps cannot look current',()=>{
  assert.equal(view({},false,stamp).label,'No sample');
  assert.equal(view({},true,stamp).good,false);
  assert.equal(view(sample,false,stamp-61000).label,'Check clock');
  assert.equal(view(sample,false,stamp-61000).age,null);
});
test('transport-only probe has an exact UI label',()=>{
  assert.match(source,/remote_gateway_reachable:'SSH tunnel listener reachable'/);
  assert.doesNotMatch(source,/Remote Gateway reachable/);
});
