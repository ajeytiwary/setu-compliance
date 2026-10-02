const eur=n=>new Intl.NumberFormat("en-IE",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(n||0);
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
const pct=(n,d)=>d?Math.round(100*n/d):0;
let overview=null;
let filter={country:null,rule:null,shipment:null};
let simRank=[];
function statusPill(s){const cls=(s==="SIGNAL_PRESENT"||s==="CONNECTED_ROWS"||s==="READY")?"good":((s==="NO_SIGNAL"||s==="NO_ROWS"||s==="BLOCKED")?"bad":"");return '<span class="pill '+cls+'">'+esc(s)+"</span>";}
function renderKpis(){
 const m=overview.risk.metrics,k=overview.kpis;
 document.querySelector("#kpis").innerHTML=[
  ["EU order book",eur(m.eu_order_book_eur),"total EU-bound value",""],
  ["Market ready",eur(m.market_ready_value_eur),(m.market_ready_value_pct??0)+"% of book","accent"],
  ["Revenue at risk",eur(m.revenue_at_risk_eur),"blocked by evidence or unmet rules","danger"],
  ["Ready",(m.market_ready_value_pct??0)+"%","share of value shippable",""],
  ["Open requests",k.open_requests,"evidence requests open",""],
  ["CBAM verified",k.cbam_verified+" / "+k.cbam_calculations,"persisted calculations",""],
  ["Genealogy edges",k.genealogy_edges,"heat→slab→coil coverage",""],
  ["Activity rows",k.activity_rows,"metered process observations",""],
 ].map(x=>'<div class="card '+x[3]+'"><div class="label">'+x[0]+'</div><div class="value">'+x[1]+'</div><div class="sub">'+esc(x[2])+"</div></div>").join("");
}
function renderRisk(){
 const risk=overview.risk;
 document.querySelector("#countries").innerHTML=risk.countries.map(c=>
  '<div class="row clickable'+(filter.country===c.country?" selected":"")+'" data-country="'+esc(c.country)+'"><div class="kv"><span class="t">'+esc(c.country)+'</span><span class="v bad">'+eur(c.at_risk_value_eur)+'</span></div><div class="bar"><i style="width:'+pct(c.at_risk_value_eur,c.total_value_eur)+'%"></i></div><div class="muted" style="font-size:12px">'+eur(c.total_value_eur)+" total</div></div>").join("")||'<div class="muted">No destinations.</div>';
 document.querySelector("#rules").innerHTML=risk.rule_risk.map(r=>
  '<div class="row clickable'+(filter.rule===r.code?" selected":"")+'" data-rule="'+esc(r.code)+'"><div class="kv"><span class="t">'+esc(r.code)+'</span><span class="v bad">'+eur(r.value_eur)+"</span></div></div>").join("")||'<div class="muted">No blocking rules.</div>';
 const rows=risk.drilldown.filter(x=>(!filter.country||x.country===filter.country)&&(!filter.rule||x.blocker.code===filter.rule)&&(!filter.shipment||x.shipment_id===filter.shipment));
 const selShip=(overview.shipments||[]).find(s=>s.id===filter.shipment);
 const selShipNo=selShip?selShip.shipment_no:filter.shipment;
 document.querySelector("#breadcrumb").textContent=["Portfolio",filter.country,filter.rule,selShipNo].filter(Boolean).join(" → ");
 document.querySelector("#activeFilters").innerHTML=
  (filter.country?'<span class="chip">'+esc(filter.country)+'<button data-clear="country" aria-label="clear">×</button></span>':"")+
  (filter.rule?'<span class="chip">'+esc(filter.rule)+'<button data-clear="rule" aria-label="clear">×</button></span>':"")+
  (filter.shipment?'<span class="chip">'+esc(selShipNo)+'<button data-clear="shipment" aria-label="clear">×</button></span>':"");
 document.querySelector("#drilldown").innerHTML=rows.map(x=>
  '<div class="drill"><div class="drill-head"><span><b>'+esc(x.shipment_no)+"</b> · "+esc(x.country)+
  '</span><span class="v">'+eur(x.value_eur)+"</span></div>"+
  '<div class="bad blocker">'+esc(x.blocker.code)+" · "+esc(x.blocker.label)+" · "+esc(x.blocker.status)+"</div>"+
  '<div class="muted">'+esc(x.blocker.notes||"Evidence or rule condition incomplete")+"</div>"+
  '<div class="sim-row"><button class="secondary small simulate" data-shipment="'+esc(x.shipment_id)+'" data-rule="'+esc(x.blocker.code)+'">Simulate fix</button></div>'+
  (x.suppliers||[]).map(s=>'<div class="supplier"><b>'+esc(s.supplier_name)+"</b> · "+esc(s.material||"material")+
   '<br><span class="muted">Needed: '+esc(s.required_evidence_type||x.blocker.code)+" · owner: "+esc(s.owner||"unassigned")+" · due: "+esc(s.due_date||"unset")+
   '</span><br><button class="small prefill" data-shipment="'+esc(x.shipment_id)+'" data-supplier="'+esc(s.supplier_id)+'" data-evidence="'+esc(s.required_evidence_type||x.blocker.code)+'">Request evidence</button></div>').join("")+"</div>").join("")||'<div class="row muted">No blockers for this selection.</div>';
 document.querySelectorAll("[data-country]").forEach(e=>e.onclick=()=>{filter.country=filter.country===e.dataset.country?null:e.dataset.country;renderRisk();});
 document.querySelectorAll("[data-rule]").forEach(e=>e.onclick=()=>{filter.rule=filter.rule===e.dataset.rule?null:e.dataset.rule;renderRisk();});
 document.querySelectorAll("[data-clear]").forEach(e=>e.onclick=()=>{filter[e.dataset.clear]=null;renderRisk();});
 if(filter.country||filter.rule||filter.shipment)markStep(1);
 wireActions();
}
function wireActions(){
 document.querySelectorAll(".simulate").forEach(e=>e.onclick=()=>simulate(e.dataset.shipment,e.dataset.rule));
 document.querySelectorAll(".prefill").forEach(e=>e.onclick=()=>{
  document.querySelector("#shipmentId").value=e.dataset.shipment;
  document.querySelector("#supplierId").value=e.dataset.supplier;
  document.querySelector("#evidenceType").value=e.dataset.evidence;
  document.querySelector("#owner").focus();
  document.querySelector("#requestForm").scrollIntoView({behavior:"smooth",block:"center"});
 });
}
function wireShipmentRows(){
 document.querySelectorAll("[data-shipment-row]").forEach(e=>{
  const open=()=>{
   filter.shipment=filter.shipment===e.dataset.shipmentRow?null:e.dataset.shipmentRow;
   renderRisk();
   renderShipments();
   document.querySelector("#drilldown").scrollIntoView({behavior:"smooth",block:"center"});
  };
  e.onclick=open;
  e.onkeydown=ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();open();}};
 });
}
function renderShipments(){
 const d=overview;
 document.querySelector("#shipments").innerHTML=d.shipments.map(s=>'<div class="row clickable'+(filter.shipment===s.id?" selected":"")+'" data-shipment-row="'+esc(s.id)+'" role="button" tabindex="0" aria-label="Inspect '+esc(s.shipment_no)+' blockers"><div class="kv"><span class="t"><b>'+esc(s.shipment_no)+"</b> · "+esc(s.destination_country)+" · "+esc(s.cn_code)+'</span><span class="v">'+eur(s.value_eur)+'</span></div><div class="'+(s.ready?"good":"bad")+'">'+(s.ready?"READY":"BLOCKED")+" · "+s.open_blockers+"/"+s.blocking_total+" blocking open"+(s.first_blocker?" · "+esc(s.first_blocker.code)+" · "+esc(s.first_blocker.label):"")+'</div><div class="muted" style="font-size:12px">Click to see what is blocked and what is blocking it.</div></div>').join("")||'<div class="muted">No shipments yet.</div>';
 wireShipmentRows();
}
async function simulate(shipment,rule){
 if(!rule)return;
 const box=document.querySelector("#simulation");
 const costInput=document.querySelector("#simCost");
 const cost=Math.max(0,Number(costInput?.value)||0);
 box.classList.add("muted");
 box.textContent="Simulating…";
 const res=await fetch("/api/pilot/shipments/"+encodeURIComponent(shipment)+"/simulate-remediation",{method:"POST",headers:pilotHeaders({"Content-Type":"application/json"}),body:JSON.stringify({requirement_code:rule,estimated_cost_eur:cost})});
 const s=await res.json();
 if(!res.ok){box.classList.remove("muted");box.textContent=s.detail||"Simulation failed";return;}
 box.classList.remove("muted");
 const p=s.proposed_solution||{};
 const story=(p.story||[]).map(t=>"<p>"+esc(t)+"</p>").join("");
 const steps=(p.steps||[]).map((st,i)=>"<li><b>Step "+(i+1)+":</b> "+esc(st.action)+' <span class="muted">· owner: '+esc(st.owner)+" · artifact: "+esc(st.artifact)+"</span></li>").join("");
 const checklist=(p.evidence_checklist||[]).map(e=>"<li>"+esc(e)+"</li>").join("");
 box.innerHTML="<b>"+esc(s.shipment_no)+" · "+esc(s.requirement.code)+" → PASS</b>"+
  '<div class="'+(s.after.market_ready?"good":"bad")+'">'+(s.after.market_ready?"Shipment becomes market-ready":"Shipment remains blocked")+"</div>"+
  "<div>Revenue unlocked: <b>"+eur(s.after.revenue_unlocked_eur)+"</b> · remediation cost: "+eur(s.after.estimated_remediation_cost_eur)+" · net value unlocked: <b>"+eur(s.after.net_value_unlocked_eur)+"</b></div>"+
  '<div class="muted">'+(s.after.next_blocker?"Next blocker: "+esc(s.after.next_blocker.code)+", "+esc(s.after.next_blocker.label):"No remaining blocking requirements.")+"</div>"+
  (p.title?'<hr><div class="sim-story"><b>Proposed solution: '+esc(p.title)+"</b>"+story+
   (steps?"<b>Remediation plan</b><ol class=\"sim-steps\">"+steps+"</ol>":"")+
   (checklist?"<b>Evidence checklist</b><ul class=\"sim-steps\">"+checklist+"</ul>":"")+
   '<div class="sim-meta">'+
    (p.owner_suggestion?'<span class="pill">Suggested owner: '+esc(p.owner_suggestion)+"</span>":"")+
    (p.typical_timeline?'<span class="pill">Typical timeline: '+esc(p.typical_timeline)+"</span>":"")+
    (p.cost_guidance?'<span class="pill">'+esc(p.cost_guidance)+"</span>":"")+
   "</div>"+
   (p.headline?'<div class="muted"><b>Bottom line:</b> '+esc(p.headline)+"</div>":"")+
   '<div class="sim-row"><button class="secondary small start-request" data-shipment="'+esc(s.shipment_id)+'" data-rule="'+esc(s.requirement.code)+'">Start evidence request for this fix</button></div>'+
  "</div>":"")+
  '<div class="muted">What-if only, no compliance state was changed.</div>';
 box.scrollIntoView({behavior:"smooth",block:"center"});
 trackSim(s);
 document.querySelectorAll(".start-request").forEach(e=>e.onclick=()=>{
  const row=(overview.risk.drilldown||[]).find(x=>x.shipment_id===e.dataset.shipment&&x.blocker.code===e.dataset.rule);
  const sup=row&&(row.suppliers||[])[0];
  if(sup){
   document.querySelector("#shipmentId").value=e.dataset.shipment;
   document.querySelector("#supplierId").value=sup.supplier_id;
   document.querySelector("#evidenceType").value=sup.required_evidence_type||e.dataset.rule;
   document.querySelector("#requirementCode").value="SUPPLIER_DATA";
   document.querySelector("#owner").focus();
   document.querySelector("#requestForm").scrollIntoView({behavior:"smooth",block:"center"});
  }else{
   document.querySelector("#requestForm").scrollIntoView({behavior:"smooth",block:"center"});
  }
 });
}
function trackSim(s){
 const key=s.shipment_id+"|"+s.requirement.code;
 simRank=simRank.filter(x=>x.key!==key);
 simRank.push({key,shipment_no:s.shipment_no,code:s.requirement.code,label:s.requirement.label,net:s.after.net_value_unlocked_eur,unlocked:s.after.revenue_unlocked_eur,cost:s.after.estimated_remediation_cost_eur,ready:s.after.market_ready});
 simRank.sort((a,b)=>b.net-a.net);
 renderRank();
 markStep(2);
}
function renderRank(){
 const box=document.querySelector("#rankBox");
 if(!box)return;
 if(!simRank.length){box.innerHTML='<div class="muted">Simulate blockers above to rank them by net value unlocked.</div>';return;}
 box.innerHTML="<b>Blocker ranking by net value unlocked</b>"+simRank.map((r,i)=>'<div class="row"><b>#'+(i+1)+" "+esc(r.shipment_no)+" · "+esc(r.code)+"</b>"+'<span style="float:right">net <b>'+eur(r.net)+"</b> (unlock "+eur(r.unlocked)+" − cost "+eur(r.cost)+")</span>"+'<div class="'+(r.ready?"good":"bad")+'">'+esc(r.ready?"unlocks shipment":"still blocked after this fix")+"</div></div>").join("");
}
function renderStatic(){
 const d=overview;
 document.querySelector("#scope-line").textContent=d.scope.notice;
 const dm=document.querySelector("#dataModeBanner"),dl=document.querySelector("#data-mode-line");
 if(dm&&dl){
  const mode=d.data_mode||"UNKNOWN";
  const label={DEMO_JSW_SYNTHETIC:"DEMO: synthetic JSW Vijayanagar showcase ("+(d.demo_shipment_count||0)+" demo shipments, €7.79M). No client data yet. Real pilot unlocks after client CSVs are imported.",CLIENT_LIVE:"LIVE PILOT: client rows present ("+(d.client_shipment_count||0)+" client shipments). Demo rows should be cleared before handover.",EMPTY_NO_CLIENT_DATA:"CLEAN PILOT SHELL: no shipments yet. Import the 6 client CSVs to unlock."}[mode]||mode;
  dl.textContent=label;dm.hidden=false;
 }
 document.querySelector("#weeks").innerHTML=d.weeks.map(w=>'<div class="row"><b>W'+w.week+"</b> · "+esc(w.objective)+'<span style="float:right">'+statusPill(w.status)+'</span><div class="muted">Exit: '+esc(w.exit)+'</div><div class="muted">Signal: '+esc(w.signal)+" = "+esc(w.signal_value??"manual")+"</div></div>").join("");
 document.querySelector("#contracts").innerHTML=d.contracts.map(c=>'<div class="row"><b>'+esc(c.label)+'</b><span style="float:right">'+statusPill(c.status)+(c.sample_only?' <span class="pill">SAMPLE_ONLY</span>':"")+'</span><div class="muted">'+esc(c.rows)+" canonical rows · "+esc(c.unlocks)+'</div><div class="muted">Last run: '+esc(c.last_run||"never")+"</div></div>").join("");
 renderShipments();
 document.querySelector("#cbam").innerHTML="<p><b>"+d.cbam_calculations.length+"</b> persisted calculations (newest first)</p>"+d.cbam_calculations.slice(0,20).map(c=>'<div class="row"><b>'+esc(c.cn_code)+"</b> · "+esc(c.installation_id||"n/a")+" · "+esc(c.reporting_period||"n/a")+'<span style="float:right">'+esc(c.status)+'</span><div class="muted">'+esc(c.specific_embedded_emissions)+" tCO2e/t · "+esc(c.created_at||"")+"</div></div>").join("");
 renderRemediation();
 document.querySelector("#regulatory").innerHTML=Object.entries(d.regulatory).map(([key,v])=>'<div class="row"><b>'+esc(key)+"</b>"+(v.snapshot?'<span style="float:right" class="good">SNAPSHOT</span>':'<span style="float:right" class="bad">NO SNAPSHOT</span>')+'<div class="muted">'+esc(v.purpose||v.error||"")+"</div><div class=\"muted\">"+esc(v.snapshot?((v.snapshot.provider||"?")+" · "+(v.snapshot.record_count??"?")+" records · sha "+String(v.snapshot.sha256||"").slice(0,12)+"… · manifest "+(v.manifest_version||"n/a")):("run POST /api/data-sources/"+key+"/sync"))+"</div></div>").join("");
 document.querySelector("#audit").innerHTML=d.audit.map(a=>'<div class="row"><b>'+esc(a.event_type)+'</b><span style="float:right" class="muted">'+esc(a.created_at||"")+'</span><div class="muted">'+esc(a.shipment_id||"n/a")+"</div></div>").join("")||'<div class="muted">No audit events yet.</div>';
 wireActions();
}
function renderRemediation(){
 const r=overview.remediation;
 document.querySelector("#remediation").innerHTML="<p><b>"+r.open_requests+"</b> open · "+r.resolved_requests+" resolved · "+eur(r.revenue_at_risk_eur)+" linked revenue at risk</p>"+r.requests.slice(0,30).map(x=>'<div class="row"><div class="kv"><span class="t"><b>'+esc(x.shipment_no)+"</b> → "+esc(x.supplier_name)+'</span><span class="v '+(x.status==="RESOLVED"?"good":"bad")+'">'+esc(x.status)+'</span></div><div class="muted">'+esc(x.evidence_type)+" · "+esc(x.owner)+" · due "+esc(x.due_date||"unset")+"</div>"+evidenceCycleHtml(x)+"</div>").join("")||'<div class="muted">No evidence requests yet.</div>';
 wireEvidenceCycle();
}
function evidenceCycleHtml(x){
 if(x.status==="RESOLVED")return '<div class="muted">Resolved with evidence '+esc(x.submitted_evidence_id||"")+".</div>";
 const ev=(x.evidence||[]).map(e=>"<li><b>"+esc(e.evidence_type)+"</b> · "+esc(e.status)+(e.verifier?" · verifier: "+esc(e.verifier):"")+' <span class="muted">'+esc(e.created_at||"")+"</span>"+(e.status!=="VERIFIED"?'<br><span class="ev-row"><input placeholder="Verifier name" data-verify-name="'+esc(e.id)+'"><button class="small verify-ev" data-evidence="'+esc(e.id)+'">Mark VERIFIED</button></span>':"")+(e.status==="VERIFIED"?'<br><button class="small secondary resolve-req" data-request="'+esc(x.id)+'" data-evidence="'+esc(e.id)+'">Resolve request with this evidence</button>':"")+"</li>").join("");
 return '<div class="evidence-cycle"><b>Evidence cycle</b><div class="muted">1) Supplier submits → 2) verifier marks VERIFIED → 3) resolve the request.</div>'+
  '<div class="ev-row"><input placeholder="Evidence content / file ref" data-submit-content="'+esc(x.id)+'"><input placeholder="Issuer (optional)" data-submit-issuer="'+esc(x.id)+'"><button class="small submit-ev" data-request="'+esc(x.id)+'" data-supplier="'+esc(x.supplier_id)+'" data-evidence-type="'+esc(x.evidence_type)+'">Submit evidence</button></div>'+
  (ev?"<ul class=\"ev-list\">"+ev+"</ul>":'<div class="muted">No supplier evidence yet for this supplier.</div>')+"</div>";
}
function wireEvidenceCycle(){
 document.querySelectorAll(".submit-ev").forEach(b=>b.onclick=async()=>{
  const reqId=b.dataset.request;
  const content=(document.querySelector('[data-submit-content="'+reqId+'"]')||{}).value||"";
  const issuer=(document.querySelector('[data-submit-issuer="'+reqId+'"]')||{}).value||null;
  if(!content.trim()){alert("Enter the evidence content or file reference first.");return;}
  const res=await fetch("/api/pilot/suppliers/"+encodeURIComponent(b.dataset.supplier)+"/evidence",{method:"POST",headers:pilotHeaders({"Content-Type":"application/json"}),body:JSON.stringify({evidence_type:b.dataset.evidenceType,content,issuer})});
  const out=await res.json();
  if(!res.ok){alert(out.detail||"Submit failed");return;}
  markStep(4);await load();
 });
 document.querySelectorAll(".verify-ev").forEach(b=>b.onclick=async()=>{
  const name=(document.querySelector('[data-verify-name="'+b.dataset.evidence+'"]')||{}).value||"";
  if(!name.trim()){alert("Enter the verifier name first.");return;}
  const res=await fetch("/api/pilot/evidence/"+encodeURIComponent(b.dataset.evidence)+"/verify",{method:"POST",headers:pilotHeaders({"Content-Type":"application/json"}),body:JSON.stringify({verifier:name})});
  const out=await res.json();
  if(!res.ok){alert(out.detail||"Verify failed");return;}
  markStep(4);await load();
 });
 document.querySelectorAll(".resolve-req").forEach(b=>b.onclick=async()=>{
  const res=await fetch("/api/pilot/remediation/requests/"+encodeURIComponent(b.dataset.request)+"/resolve",{method:"POST",headers:pilotHeaders({"Content-Type":"application/json"}),body:JSON.stringify({evidence_id:b.dataset.evidence})});
  const out=await res.json();
  if(!res.ok){alert(out.detail||"Resolve failed");return;}
  markStep(5);await load();
 });
}
function markStep(n){
 document.querySelectorAll("#workflow .wstep").forEach(e=>{
  if(Number(e.dataset.step)<=n)e.classList.add("done");
 });
}
document.querySelector("#requestForm").addEventListener("submit",async e=>{
 e.preventDefault();
 const status=document.querySelector("#formStatus");
 const payload={
  shipment_id:document.querySelector("#shipmentId").value,
  supplier_id:document.querySelector("#supplierId").value,
  requirement_code:document.querySelector("#requirementCode").value||"SUPPLIER_DATA",
  evidence_type:document.querySelector("#evidenceType").value,
  owner:document.querySelector("#owner").value,
  due_date:document.querySelector("#dueDate").value||null,
  message:document.querySelector("#message").value||null,
 };
 const res=await fetch("/api/pilot/remediation/requests",{method:"POST",headers:pilotHeaders({"Content-Type":"application/json"}),body:JSON.stringify(payload)});
 const out=await res.json();
 status.textContent=res.ok?" Request created":" "+(out.detail||"Request failed");
 if(res.ok){
  e.target.reset();
  document.querySelector("#requirementCode").value="SUPPLIER_DATA";
  markStep(3);
  await load();
 }
});
const TOKEN_KEY="eurosetu_pilot_token";
const TENANT_KEY="eurosetu_pilot_tenant";
const bearer=()=>localStorage.getItem(TOKEN_KEY)||"";
const tenant=()=>localStorage.getItem(TENANT_KEY)||"tenant-a";
function pilotHeaders(extra={}){
 const h={...extra};
 const t=bearer();
 if(t)h["Authorization"]="Bearer "+t;
 const tn=tenant();
 if(tn)h["x-eurosetu-tenant"]=tn;
 return h;
}
function showGate(){
 const g=document.querySelector("#pilotGate");
 if(g)g.hidden=false;
 const m=document.querySelector("#pilotMain");
 if(m)m.hidden=true;
 wireUnlock();
}
function hideGate(){
 const g=document.querySelector("#pilotGate");
 if(g)g.hidden=true;
 const m=document.querySelector("#pilotMain");
 if(m)m.hidden=false;
}
function wireUnlock(){
 const btn=document.querySelector("#unlockPilot");
 if(!btn||btn.dataset.wired)return;
 btn.dataset.wired="1";
 btn.onclick=async()=>{
  const err=document.querySelector("#unlockError");
  const tok=(document.querySelector("#pilotToken")||{}).value||"";
  const tn=((document.querySelector("#pilotTenant")||{}).value||"tenant-a").trim()||"tenant-a";
  if(!tok.trim()){if(err){err.hidden=false;err.textContent="Paste your pilot access key first.";}return;}
  localStorage.setItem(TOKEN_KEY,tok.trim());
  localStorage.setItem(TENANT_KEY,tn);
  if(err)err.hidden=true;
  await load();
 };
}
async function load(){
 let res;
 try{
  res=await fetch("/api/pilot/overview",{headers:pilotHeaders()});
 }catch(e){
  showGate();
  return;
 }
 if(res.status===401||res.status===403){
  showGate();
  return;
 }
 overview=await res.json();
 hideGate();
 renderKpis();
 renderRisk();
 renderStatic();
 renderRank();
}
load();
