"use strict";
const $ = (id) => document.getElementById(id);
const nonce = document.querySelector('meta[name="demo-nonce"]').content;
let mode = "direct", snapshot = null, renderedReceipt = "";
const stepTitles = {allow:"Allowed read", "ask-pending":"Approval boundary", "ask-resolved":"Scripted approval", deny:"Configured denial", "protected-path":"Protected path", "command-gate":"Command gate", "policy-profile":"Policy ∩ Profile", redaction:"Credential redaction", "sel-integrity":"SEL integrity", "sel-tamper-detection":"Changed record detected"};
function field(parent, label, value) { const term = document.createElement("dt"), detail = document.createElement("dd"); term.textContent=label; detail.textContent=String(value); parent.append(term, detail); }
function setMode(next) {
  mode=next; renderedReceipt=""; $("receipt-json").hidden=true;
  for(const choice of ["direct","synthetic"]) { $("tab-"+choice).classList.toggle("selected",choice===mode); $("tab-"+choice).setAttribute("aria-pressed",String(choice===mode)); }
  $("screen-title").textContent=mode==="direct"?"Direct MCP/AWS probe":"Local synthetic control rehearsal";
  $("screen-description").textContent=mode==="direct"?"Run the fixed three-outcome check on the ARM server and inspect its receipt.":"Exercise Crew control functions in disposable local state and inspect the result.";
  $("boundary-detail").textContent=mode==="direct"?"This command invokes the remote MCP service directly. Native Kiro CLI acceptance is a separate step.":"Synthetic requests, scripted approval, no backend session and no network calls.";
  $("direct-results").hidden=mode!=="direct"; $("synthetic-results").hidden=mode!=="synthetic";
  $("footer-scope").textContent=mode==="direct"?"Fixed command · remote MCP service · real S3 requests":"Local synthetic control rehearsal · frozen package snapshot · isolated disposable state";
  render();
}
function render() {
  if(!snapshot)return;
  const run=snapshot.runs[mode], receipt=run.receipt;
  $("server-clock").textContent=new Date(snapshot.server_time).toISOString().replace("T"," ").slice(0,19)+" UTC";
  $("run-status").className="status "+run.status;
  $("run-status").textContent={idle:"Ready",running:"Running",passed:"Checks passed",failed:"Run failed"}[run.status];
  $("start-run").disabled=Boolean(snapshot.active);
  $("start-run").textContent=mode==="direct"?"Start bounded probe":"Start synthetic rehearsal";
  const elapsed=run.started_at?Math.max(0,Math.floor(((run.finished_at?Date.parse(run.finished_at):Date.parse(snapshot.server_time))-Date.parse(run.started_at))/1000)):0;
  $("run-progress").textContent=run.status==="idle"?"No command has been run in this screen.":run.status==="running"?`Fixed command is running · ${elapsed}s elapsed · ${run.output_bytes} output bytes received`:run.error_type?`Command could not produce a valid receipt · ${run.error_type}`:`Completed in ${elapsed}s · ${new Date(run.finished_at).toISOString().slice(11,19)} UTC · exit ${run.exit_code}`;
  $("receipt-download").hidden=!run.artifact_url; $("receipt-toggle").hidden=!receipt;
  if(run.artifact_url)$("receipt-download").href=run.artifact_url;
  $("receipt-heading").textContent=receipt?(receipt.passed?"Completed command · receipt retained":"Command completed with failed checks"):run.status==="running"?"Waiting for the command’s receipt":"Evidence appears after the command finishes";
  $("receipt-summary").textContent=receipt?mode==="direct"?"Authentication, catalog and three tool outcomes are checked. Trace and AWS request IDs come from this run.":`Frozen package ${receipt.baseline.installed_version}. Harness-emitted SEL events and scripted approval remain separate from native Kiro CLI proof.`:mode==="direct"?"The direct probe returns one JSON receipt when the command finishes.":"The launcher creates new isolated state. Its approval step is scripted; the native approval interface is not involved.";
  const signature=JSON.stringify(receipt)+run.artifact_sha256;
  if(signature===renderedReceipt)return;
  renderedReceipt=signature;
  $("receipt-meta").replaceChildren();
  if(receipt){$("receipt-json").textContent=JSON.stringify(receipt,null,2);field($("receipt-meta"),"Receipt SHA-256",run.artifact_sha256);field($("receipt-meta"),"Started at",run.started_at);}
  if(mode==="direct")for(const name of ["read_allowed","mcp_denied","iam_denied"]){
    const card=$("card-"+name), row=receipt?.checks?.find(c=>c.name===name), data=row?.result, fields=card.querySelector("dl");
    card.className="result-card"+(row?(row.passed?" passed":" failed"):""); card.querySelector(".outcome").textContent=row?(row.passed?"Verified":"Check failed"):"Awaiting run"; fields.replaceChildren();
    if(!data)continue;
    field(fields,"Result",name==="read_allowed"?`Allowed · ${data.object_bytes} bytes`:name==="mcp_denied"?data.error_code:`${data.error_code} · HTTP ${data.http_status}`);
    field(fields,"Trace ID",data.trace_id);
    if(data.aws_request_id)field(fields,"AWS request ID",data.aws_request_id);
    else field(fields,"AWS dispatch","Blocked at MCP grant check");
    if(data.object_sha256)field(fields,"Object SHA-256",data.object_sha256);
    field(fields,"Invocation ID",data.invocation_id);
  }
  if(mode==="synthetic"){
    $("synthetic-steps").replaceChildren();
    for(const [name,title] of Object.entries(stepTitles)){
      const row=receipt?.steps?.find(s=>s.step===name), card=document.createElement("article"), heading=document.createElement("strong"), detail=document.createElement("span");
      card.className="step"+(row?" complete":"");heading.textContent=title;
      detail.textContent=!row?"Awaiting rehearsal":name==="ask-resolved"?"Script supplied approval":name==="ask-pending"?"No write before approval":name==="redaction"?row.output:name==="sel-integrity"?`${row.valid}/${row.total} valid records`:name==="sel-tamper-detection"?`${row.valid}/${row.total} valid after mutation; original restored`:name==="policy-profile"?"Read permitted; Write and Deny limited":row.crew_action?`Crew action: ${row.crew_action}`:"Recorded in receipt";
      card.append(heading,detail);$("synthetic-steps").append(card);
    }
  }
}
async function refresh(){try{const response=await fetch("/api/state",{cache:"no-store"});if(!response.ok)throw new Error();snapshot=await response.json();render();}catch{$("run-progress").textContent="Local operator server is unavailable.";$("start-run").disabled=true;}}
$("tab-direct").addEventListener("click",()=>setMode("direct"));$("tab-synthetic").addEventListener("click",()=>setMode("synthetic"));
$("receipt-toggle").addEventListener("click",()=>{$("receipt-json").hidden=!$("receipt-json").hidden;});
$("start-run").addEventListener("click",async()=>{ $("start-run").disabled=true;try{const response=await fetch("/api/run",{method:"POST",headers:{"Content-Type":"application/json","X-Demo-Nonce":nonce},body:JSON.stringify({mode})});if(!response.ok)throw new Error(`HTTP ${response.status}`);renderedReceipt="";$("receipt-json").hidden=true;await refresh();}catch(error){$("run-progress").textContent="Run was not started: "+error.message;}});
refresh();setInterval(refresh,500);
