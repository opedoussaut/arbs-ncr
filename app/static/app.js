const $ = (q) => document.querySelector(q);
const form = $('#ncrForm');
const sample = {
  ncr_id:'NCR-2026-004381', severity:'High', aircraft_config:'C128', timestamp:'2026-09-15T08:42:31',
  part:'Wing structural component', operation:'Automated drilling', machine:'DRILL_CELL_07', supplier_batch:'B-81932',
  deviation:'Hole diameter +0.18 mm above tolerance', notes:'Deviation detected during in-process dimensional inspection.'
};

async function init(){
  try{
    const h = await fetch('/api/health').then(r=>r.json());
    $('#runtimeMode').textContent = h.llm_mode === 'live' ? 'Live LLM' : 'Simulation';
    if(h.llm_mode === 'live') $('#modeDot').classList.add('live');
  }catch{ $('#runtimeMode').textContent = 'Offline'; }
}

$('#sampleBtn').addEventListener('click', ()=>{
  Object.entries(sample).forEach(([k,v])=>{ const el=form.elements[k]; if(el) el.value=v; });
});

form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const btn=$('#runBtn'); btn.disabled=true; btn.querySelector('span').textContent='Investigating…';
  $('#emptyState').classList.add('hidden'); $('#results').classList.remove('hidden');
  $('#headline').textContent='Both architectures are investigating the same evidence universe…';
  $('#costSaving').textContent='—'; $('#tokenSaving').textContent='—'; $('#toolSaving').textContent='—';
  $('#baselineLane').innerHTML=loadingLane('A','Agent-only baseline','Agents retrieve and reduce source evidence');
  $('#nifiLane').innerHTML=loadingLane('N','NiFi-assisted','Deterministic data plane prepares context');
  $('#metricTable').innerHTML='';
  const data = Object.fromEntries(new FormData(form).entries());
  try{
    const res=await fetch('/api/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    if(!res.ok) throw new Error(await res.text());
    const out=await res.json(); render(out);
  }catch(err){
    $('#headline').textContent='Investigation failed';
    $('#baselineLane').innerHTML=`<div class="finding"><strong>Runtime error</strong><p>${escapeHtml(err.message)}</p></div>`;
    $('#nifiLane').innerHTML='';
  }finally{btn.disabled=false;btn.querySelector('span').textContent='Run dual investigation';}
});

function loadingLane(letter,title,sub){
  return `<div class="lane-head"><div class="lane-title"><div class="lane-logo">${letter}</div><div><h3>${title}</h3><span>${sub}</span></div></div></div>
  <div class="agent-stack">${[1,2,3,4].map(()=>`<div class="agent-step loading-shimmer" style="height:74px"></div>`).join('')}</div>`;
}

function render(out){
  $('#headline').textContent=out.headline;
  $('#costSaving').textContent=fmtPct(out.savings_pct);
  $('#tokenSaving').textContent=fmtPct(out.token_reduction_pct);
  $('#toolSaving').textContent=fmtPct(out.tool_call_reduction_pct);
  $('#baselineLane').innerHTML=laneHtml(out.baseline,'A','Agents query source systems directly');
  $('#nifiLane').innerHTML=laneHtml(out.nifi,'N','NiFi prepares a governed context pack');
  renderMetrics(out.baseline.metrics,out.nifi.metrics);
}

function laneHtml(r,letter,subtitle){
  const m=r.metrics;
  return `<div class="lane-head">
    <div class="lane-title"><div class="lane-logo">${letter}</div><div><h3>${r.title}</h3><span>${subtitle}</span></div></div>
    <div class="confidence">${Math.round(r.confidence*100)}% confidence</div>
  </div>
  <div class="agent-stack">${r.steps.map((s,i)=>`<div class="agent-step">
    <div class="agent-avatar">${agentGlyph(s.agent)}</div><div><h4>${escapeHtml(s.title)}</h4><p>${escapeHtml(s.detail)}</p></div><div class="agent-meta">${s.evidence_count} ev.</div>
  </div>`).join('')}</div>
  <div class="finding"><div class="label">Leading hypothesis</div><strong>${escapeHtml(r.likely_cause)}</strong><p>${escapeHtml(r.recommendation)}</p></div>
  <div class="human-gate">◉ ${escapeHtml(r.human_gate)}</div>
  <div class="lane-kpis">
    <div><strong>${compact(m.estimated_input_tokens)}</strong><span>input tokens</span></div>
    <div><strong>${m.tool_calls}</strong><span>tool calls</span></div>
    <div><strong>${formatBytes(m.context_bytes)}</strong><span>agent context</span></div>
    <div><strong>${formatMoney(m.estimated_cost_usd)}</strong><span>LLM cost*</span></div>
  </div>
  <details class="provenance"><summary>${r.lane==='nifi'?'NiFi provenance':'Retrieval trace'}</summary><ul>${r.evidence.map(e=>`<li>${escapeHtml(e)}</li>`).join('')}</ul></details>`;
}

function renderMetrics(b,n){
  const rows=[
    ['Agent input tokens',b.estimated_input_tokens,n.estimated_input_tokens,'num',true],
    ['Agent-facing tool calls',b.tool_calls,n.tool_calls,'num',true],
    ['API calls to source layer',b.api_calls,n.api_calls,'num',true],
    ['Context delivered to agents',b.context_bytes,n.context_bytes,'bytes',true],
    ['End-to-end latency',b.latency_ms,n.latency_ms,'ms',true],
    ['Estimated LLM cost',b.estimated_cost_usd,n.estimated_cost_usd,'money',true],
    ['Evidence precision',b.evidence_precision,n.evidence_precision,'ratio',false],
    ['Deterministic processing steps',b.deterministic_steps,n.deterministic_steps,'num',false],
  ];
  const head=`<div class="metric-row header"><div>Metric</div><div>Agent only</div><div>NiFi + agents</div><div>Delta</div></div>`;
  $('#metricTable').innerHTML=head+rows.map(([name,bv,nv,type,lowerBetter])=>{
    const delta = bv===0?0:((nv-bv)/bv)*100;
    const good = lowerBetter ? delta<=0 : delta>=0;
    return `<div class="metric-row"><div class="metric-name">${name}</div><div class="metric-val">${metricFmt(bv,type)}</div><div class="metric-val">${metricFmt(nv,type)}</div><div class="metric-delta ${good?'good':'warn'}">${delta>0?'+':''}${delta.toFixed(0)}%</div></div>`
  }).join('');
}

function agentGlyph(name){return ({Quality:'Q',Manufacturing:'M',Design:'D',Supervisor:'S'})[name]||'•'}
function metricFmt(v,t){if(t==='bytes')return formatBytes(v);if(t==='money')return formatMoney(v);if(t==='ms')return `${(v/1000).toFixed(1)} s`;if(t==='ratio')return `${Math.round(v*100)}%`;return Number(v).toLocaleString()}
function formatMoney(v){return v<.01?`$${v.toFixed(4)}`:`$${v.toFixed(2)}`}
function formatBytes(v){if(v<1024)return `${v} B`;if(v<1024*1024)return `${(v/1024).toFixed(1)} KB`;return `${(v/1024/1024).toFixed(1)} MB`}
function compact(v){return v>999?`${(v/1000).toFixed(1)}k`:String(v)}
function fmtPct(v){const sign=v>0?'−':'';return `${sign}${Math.abs(v).toFixed(0)}%`}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
init();
