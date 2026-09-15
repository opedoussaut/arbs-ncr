const $ = (q) => document.querySelector(q);
const $$ = (q) => [...document.querySelectorAll(q)];
const form = $('#caseForm');

const scenarios = {
  aerospace_ncr: {
    meta: {
      eyebrow: 'AEROSPACE QUALITY',
      title: 'New NCR',
      description: 'Investigate a dimensional non-conformance using quality, manufacturing, engineering and historical knowledge.',
      labels: {
        caseId: 'NCR ID', configuration: 'Aircraft configuration', subject: 'Part / assembly',
        process: 'Operation', asset: 'Machine / cell', batch: 'Supplier batch', deviation: 'Deviation'
      },
      safety: 'No autonomous disposition — engineering approval gate enforced.'
    },
    sample: {
      scenario:'aerospace_ncr', case_id:'NCR-2026-004381', severity:'High', configuration:'C128', timestamp:'2026-09-15T08:42:31',
      subject:'Wing structural component', process:'Automated drilling', asset:'DRILL_CELL_07', batch:'B-81932',
      deviation:'Hole diameter +0.18 mm above tolerance', notes:'Deviation detected during in-process dimensional inspection.'
    }
  },
  ai_factory_anomaly: {
    meta: {
      eyebrow: 'HIGH-TECH · AI FACTORY',
      title: 'Infrastructure anomaly',
      description: 'Investigate GPU throttling by correlating rack telemetry, cooling, network, DCIM, workload impact and the K&KH corpus.',
      labels: {
        caseId: 'Incident ID', configuration: 'Rack profile', subject: 'Affected resource',
        process: 'Workload / process', asset: 'Rack / asset', batch: 'Pod / cluster', deviation: 'Observed anomaly'
      },
      safety: 'No autonomous infrastructure intervention — Operations approval gate enforced.'
    },
    sample: {
      scenario:'ai_factory_anomaly', case_id:'AIF-INC-2026-0017', severity:'High', configuration:'72-GPU liquid-cooled rack', timestamp:'2026-09-15T08:42:31',
      subject:'GPU rack R27', process:'Distributed AI training at peak load', asset:'RACK-R27', batch:'POD-03',
      deviation:'GPU inlet temperature +6.8°C with HBM throttling and ~18% throughput loss',
      notes:'Issue appears above 90% sustained GPU utilization. No GPU hard failure. Determine whether cooling, power, network or workload behavior is the primary cause.'
    }
  }
};

let currentScenario = 'aerospace_ncr';

async function init(){
  applyScenario(currentScenario, true);
  try{
    const h = await fetch('/api/health').then(r=>r.json());
    $('#runtimeMode').textContent = h.llm_mode === 'live' ? 'Live LLM' : 'Simulation';
    if(h.llm_mode === 'live') $('#modeDot').classList.add('live');
  }catch{ $('#runtimeMode').textContent = 'Offline'; }
}

$$('.scenario-btn').forEach(btn => btn.addEventListener('click', () => {
  currentScenario = btn.dataset.scenario;
  $$('.scenario-btn').forEach(x => x.classList.toggle('active', x === btn));
  applyScenario(currentScenario, true);
  $('#results').classList.add('hidden');
  $('#emptyState').classList.remove('hidden');
}));

$('#sampleBtn').addEventListener('click', () => applyScenario(currentScenario, true));

function applyScenario(key, loadSample=false){
  const cfg = scenarios[key];
  const m = cfg.meta;
  form.elements.scenario.value = key;
  $('#domainEyebrow').textContent = m.eyebrow;
  $('#caseTitle').textContent = m.title;
  $('#caseDescription').textContent = m.description;
  $('#caseIdLabel').textContent = m.labels.caseId;
  $('#configurationLabel').textContent = m.labels.configuration;
  $('#subjectLabel').textContent = m.labels.subject;
  $('#processLabel').textContent = m.labels.process;
  $('#assetLabel').textContent = m.labels.asset;
  $('#batchLabel').textContent = m.labels.batch;
  $('#deviationLabel').textContent = m.labels.deviation;
  $('#safetyText').innerHTML = `<span>◉</span> ${escapeHtml(m.safety)}`;
  if(loadSample){
    Object.entries(cfg.sample).forEach(([k,v])=>{ const el=form.elements[k]; if(el) el.value=v; });
  }
}

form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const btn=$('#runBtn'); btn.disabled=true; btn.querySelector('span').textContent='Investigating…';
  $('#emptyState').classList.add('hidden'); $('#results').classList.remove('hidden');
  $('#headline').textContent='Both architectures are investigating the same corpus and operational evidence…';
  $('#costSaving').textContent='—'; $('#tokenSaving').textContent='—'; $('#toolSaving').textContent='—';
  const steps = currentScenario === 'ai_factory_anomaly' ? 5 : 4;
  $('#baselineLane').innerHTML=loadingLane('A','Agent-only baseline','Agents retrieve and reduce raw evidence',steps);
  $('#nifiLane').innerHTML=loadingLane('L','Lean / NiFi-assisted','Deterministic layer prepares the evidence pack',steps);
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

function loadingLane(letter,title,sub,count){
  return `<div class="lane-head"><div class="lane-title"><div class="lane-logo">${letter}</div><div><h3>${title}</h3><span>${sub}</span></div></div></div>
  <div class="agent-stack">${Array.from({length:count},()=>`<div class="agent-step loading-shimmer" style="height:74px"></div>`).join('')}</div>`;
}

function render(out){
  $('#headline').textContent=out.headline;
  $('#costSaving').textContent=fmtPct(out.savings_pct);
  $('#tokenSaving').textContent=fmtPct(out.token_reduction_pct);
  $('#toolSaving').textContent=fmtPct(out.tool_call_reduction_pct);
  $('#baselineLane').innerHTML=laneHtml(out.baseline,'A','Agents query raw sources + corpus directly');
  $('#nifiLane').innerHTML=laneHtml(out.nifi,'L','NiFi prepares a lean, governed context pack');
  renderMetrics(out.baseline.metrics,out.nifi.metrics);
}

function laneHtml(r,letter,subtitle){
  const m=r.metrics;
  return `<div class="lane-head">
    <div class="lane-title"><div class="lane-logo">${letter}</div><div><h3>${escapeHtml(r.title)}</h3><span>${subtitle}</span></div></div>
    <div class="confidence">${Math.round(r.confidence*100)}% confidence</div>
  </div>
  <div class="agent-stack">${r.steps.map(s=>`<div class="agent-step">
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
  <details class="provenance"><summary>${r.lane==='nifi'?'Lean preprocessing provenance':'Retrieval trace'}</summary><ul>${r.evidence.map(e=>`<li>${escapeHtml(e)}</li>`).join('')}</ul></details>`;
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
  const head=`<div class="metric-row header"><div>Metric</div><div>Agent only</div><div>Lean + agents</div><div>Delta</div></div>`;
  $('#metricTable').innerHTML=head+rows.map(([name,bv,nv,type,lowerBetter])=>{
    const delta = bv===0?0:((nv-bv)/bv)*100;
    const good = lowerBetter ? delta<=0 : delta>=0;
    return `<div class="metric-row"><div class="metric-name">${name}</div><div class="metric-val">${metricFmt(bv,type)}</div><div class="metric-val">${metricFmt(nv,type)}</div><div class="metric-delta ${good?'good':'warn'}">${delta>0?'+':''}${delta.toFixed(0)}%</div></div>`
  }).join('');
}

function agentGlyph(name){return ({Quality:'Q',Manufacturing:'M',Design:'D',Thermal:'T',Infrastructure:'I',Network:'N',Knowledge:'K',Supervisor:'S'})[name]||'•'}
function metricFmt(v,t){if(t==='bytes')return formatBytes(v);if(t==='money')return formatMoney(v);if(t==='ms')return `${(v/1000).toFixed(1)} s`;if(t==='ratio')return `${Math.round(v*100)}%`;return Number(v).toLocaleString()}
function formatMoney(v){return v<.01?`$${v.toFixed(4)}`:`$${v.toFixed(2)}`}
function formatBytes(v){if(v<1024)return `${v} B`;if(v<1024*1024)return `${(v/1024).toFixed(1)} KB`;return `${(v/1024/1024).toFixed(1)} MB`}
function compact(v){return v>999?`${(v/1000).toFixed(1)}k`:String(v)}
function fmtPct(v){const sign=v>0?'−':'';return `${sign}${Math.abs(v).toFixed(0)}%`}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
init();
