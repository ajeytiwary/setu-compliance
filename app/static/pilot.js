const eur=n=>new Intl.NumberFormat("en-IE",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(n||0);
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
function statusPill(s){const cls=(s==="SIGNAL_PRESENT"||s==="CONNECTED_ROWS"||s==="READY")?"good":((s==="NO_SIGNAL"||s==="NO_ROWS"||s==="BLOCKED")?"bad":"");return '<span class="pill '+cls+'">'+esc(s)+"</span>";}
function cards(items){return items.map(x=>'<div class="card"><div class="muted">'+esc(x[0])+'</div><div class="value">'+x[1]+"</div></div>").join("");}
async function simulate(shipment,rule){
 if(!rule)return;
 const raw=prompt("Estimated remediation cost (€)","5000");if(raw===null)return;
 const cost=Math.max(0,Number(raw)||0);
 const res=await fetch("/api/market-access/shipments/"+encodeURIComponent(shipment)+"/simulate-remediation",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({requirement_code:rule,estimated_cost_eur:cost})});
 const s=await res.json();
 alert(res.ok?(s.shipment_no+" · "+s.requirement.code+" → PASS\n"+(s.after.market_ready?"Shipment becomes market-ready":"Shipment remains blocked")+"\nRevenue unlocked: "+eur(s.after.revenue_unlocked_eur)+" · net: "+eur(s.after.net_value_unlocked_eur)+(s.after.next_blocker?"\nNext blocker: "+s.after.next_blocker.code:"")):(s.detail||"Simulation failed"));
}
async function load(){
 const d=await fetch("/api/pilot/overview").then(r=>r.json());
 document.querySelector("#scope-line").textContent=d.scope.notice;
 const k=d.kpis;
 document.querySelector("#kpis").innerHTML=cards([["Pilot shipments",k.shipments],["Order book",eur(k.order_book_eur)],["Ready",k.ready_pct+"%"],["Revenue at risk",eur(k.revenue_at_risk_eur)],["CBAM verified",k.cbam_verified+" / "+k.cbam_calculations],["Open requests",k.open_requests],["Genealogy edges",k.genealogy_edges],["Activity rows",k.activity_rows]]);
 document.querySelector("#weeks").innerHTML=d.weeks.map(w=>'<div class="row"><b>W'+w.week+"</b> · "+esc(w.objective)+'<span style="float:right">'+statusPill(w.status)+'</span><div class="muted">Exit: '+esc(w.exit)+'</div><div class="muted">Signal: '+esc(w.signal)+" = "+esc(w.signal_value??"manual")+"</div></div>").join("");
 document.querySelector("#contracts").innerHTML=d.contracts.map(c=>'<div class="row"><b>'+esc(c.label)+'</b><span style="float:right">'+statusPill(c.status)+(c.sample_only?' <span class="pill">SAMPLE_ONLY</span>':"")+'</span><div class="muted">'+esc(c.rows)+" canonical rows · "+esc(c.unlocks)+'</div><div class="muted">Last run: '+esc(c.last_run||"never")+"</div></div>").join("");
 document.querySelector("#shipments").innerHTML=d.shipments.map(s=>'<div class="row"><b>'+esc(s.shipment_no)+"</b> · "+esc(s.destination_country)+" · "+esc(s.cn_code)+'<span style="float:right">'+eur(s.value_eur)+'</span><div class="'+(s.ready?"good":"bad")+'">'+(s.ready?"READY":"BLOCKED")+" · "+s.open_blockers+"/"+s.blocking_total+" blocking open"+(s.first_blocker?" · "+esc(s.first_blocker.code)+" — "+esc(s.first_blocker.label):"")+"</div>"+(s.ready||!s.first_blocker?"":'<button class="simulate" data-shipment="'+esc(s.shipment_no)+'" data-rule="'+esc(s.first_blocker.code)+'">Simulate fix</button>')+"</div>").join("")||'<div class="muted">No shipments yet.</div>';
 document.querySelector("#cbam").innerHTML="<p><b>"+d.cbam_calculations.length+"</b> persisted calculations (newest first)</p>"+d.cbam_calculations.slice(0,20).map(c=>'<div class="row"><b>'+esc(c.cn_code)+"</b> · "+esc(c.installation_id||"—")+" · "+esc(c.reporting_period||"—")+'<span style="float:right">'+esc(c.status)+'</span><div class="muted">'+esc(c.specific_embedded_emissions)+" tCO2e/t · "+esc(c.created_at||"")+"</div></div>").join("");
 const r=d.remediation;
 document.querySelector("#remediation").innerHTML="<p><b>"+r.open_requests+"</b> open · "+r.resolved_requests+" resolved · "+eur(r.revenue_at_risk_eur)+"</p>"+r.requests.slice(0,30).map(x=>'<div class="row"><b>'+esc(x.shipment_no)+"</b> → "+esc(x.supplier_name)+'<span style="float:right" class="'+(x.status==="RESOLVED"?"good":"bad")+'">'+esc(x.status)+'</span><div class="muted">'+esc(x.evidence_type)+" · "+esc(x.owner)+" · due "+esc(x.due_date||"unset")+"</div></div>").join("");
 document.querySelector("#regulatory").innerHTML=Object.entries(d.regulatory).map(([key,v])=>'<div class="row"><b>'+esc(key)+"</b>"+(v.snapshot?'<span style="float:right" class="good">SNAPSHOT</span>':'<span style="float:right" class="bad">NO SNAPSHOT</span>')+'<div class="muted">'+esc(v.purpose||v.error||"")+"</div><div class=\"muted\">"+esc(v.snapshot?((v.snapshot.provider||"?")+" · "+(v.snapshot.record_count??"?")+" records · sha "+String(v.snapshot.sha256||"").slice(0,12)+"… · manifest "+(v.manifest_version||"—")):("run POST /api/data-sources/"+key+"/sync"))+"</div></div>").join("");
 document.querySelector("#audit").innerHTML=d.audit.map(a=>'<div class="row"><b>'+esc(a.event_type)+'</b><span style="float:right" class="muted">'+esc(a.created_at||"")+'</span><div class="muted">'+esc(a.shipment_id||"—")+"</div></div>").join("")||'<div class="muted">No audit events yet.</div>';
 document.querySelectorAll(".simulate").forEach(e=>e.onclick=()=>simulate(e.dataset.shipment,e.dataset.rule));
}
load();
