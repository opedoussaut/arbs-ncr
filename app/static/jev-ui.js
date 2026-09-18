(() => {
  const baseRender = window.render;
  const baseAgentGlyph = window.agentGlyph;

  window.agentGlyph = function(name){
    const extra = {Jev:'J', Lean:'L', Human:'H', Classifier:'Z'};
    return extra[name] || (baseAgentGlyph ? baseAgentGlyph(name) : '•');
  };

  function ensureDecisionUI(){
    const lanes=document.querySelector('.lanes');
    if(lanes){
      lanes.classList.add('decision-grid');
      if(!document.querySelector('#jevLane')){
        const card=document.createElement('article');
        card.className='lane card jev'; card.id='jevLane';
        lanes.appendChild(card);
      }
      if(!document.querySelector('#classifierLane')){
        const card=document.createElement('article');
        card.className='lane card classifier'; card.id='classifierLane';
        lanes.appendChild(card);
      }
    }

    const heroStats=document.querySelector('.hero-stats');
    if(heroStats&&!document.querySelector('#frontierSaving')){
      const d=document.createElement('div');
      d.innerHTML='<strong id="frontierSaving">—</strong><span>Jev frontier calls</span>';
      heroStats.appendChild(d);
    }

    const evidenceColumns=document.querySelector('.evidence-columns');
    if(evidenceColumns){
      evidenceColumns.classList.add('decision-evidence-grid');
      if(!document.querySelector('#jevEvidence')){
        const article=document.createElement('article');
        article.className='card evidence-card jev-evidence';
        article.innerHTML='<div class="evidence-card-head"><span class="evidence-badge">J</span><div><h2>Jev decision trace</h2><p>Typed decisions, confidence and escalation policy.</p></div></div><div id="jevEvidence" class="evidence-placeholder">Run an investigation to populate the Jev decision trace.</div>';
        evidenceColumns.appendChild(article);
      }
      if(!document.querySelector('#classifierEvidence')){
        const article=document.createElement('article');
        article.className='card evidence-card classifier-evidence';
        article.innerHTML='<div class="evidence-card-head"><span class="evidence-badge">Z</span><div><h2>Open zero-shot trace</h2><p>Control experiment using the same typed decision contract.</p></div></div><div id="classifierEvidence" class="evidence-placeholder">Run an investigation to populate the open-model decision trace.</div>';
        evidenceColumns.appendChild(article);
      }
    }

    const intro=document.querySelector('#investigationView .topbar p');
    if(intro) intro.textContent='Compare four architectures on the same evidence universe: agent-heavy reasoning, Lean + agents, Lean + Jev, and Lean + an open zero-shot decision model.';
    const benchmarkIntro=document.querySelector('#benchmarksView .view-header p');
    if(benchmarkIntro) benchmarkIntro.textContent='Compare context, orchestration, latency, cost and frontier-reasoning demand across four architectures using the same case and human gate.';
    const buttonSpan=document.querySelector('#runBtn span');
    if(buttonSpan&&buttonSpan.textContent.includes('dual')) buttonSpan.textContent='Run 4-way investigation';
  }

  function loadingDecisionLanes(){
    const jev=document.querySelector('#jevLane');
    const classifier=document.querySelector('#classifierLane');
    if(jev) jev.innerHTML=window.loadingLane('J','Lean + Jev','Typed decisions first; frontier reasoning only on uncertainty',3);
    if(classifier) classifier.innerHTML=window.loadingLane('Z','Lean + open zero-shot','Open control model using the same decision contract',3);
  }

  function decisionEvidence(targetId, result, label, dotClass){
    const target=document.querySelector(targetId);
    if(!target||!result)return;
    const d=result.decisions||{}, answers=d.answers||{}, root=answers.primary_cause||{}, ambiguity=answers.requires_frontier_reasoning||{};
    const lines=[
      `Model: ${d.model||'unknown'}`,
      `Primary cause: ${root.choice||'unknown'} · ${Math.round((root.confidence||0)*100)}% confidence`,
      `Frontier reasoning need: ${Math.round((ambiguity.noul||0)*100)}%`,
      `Policy: confidence < ${Math.round((d.confidence_threshold||0)*100)}% OR ambiguity ≥ ${Math.round((d.escalation_probability||0)*100)}%`,
      d.escalated?'Result: escalated to frontier reasoning':'Result: frontier reasoning avoided'
    ];
    target.className='evidence-list';
    target.innerHTML=lines.map((text,i)=>`<div class="evidence-row"><span class="evidence-dot ${dotClass}"></span><div><small>${label} ${String(i+1).padStart(2,'0')}</small><p>${window.escapeHtml(text)}</p></div></div>`).join('');
  }

  function renderDecisionMetrics(out){
    if(!out.jev||!out.classifier)return;
    const b=out.baseline.metrics,n=out.nifi.metrics,j=out.jev.metrics,z=out.classifier.metrics;
    const rows=[
      ['Model input tokens',b.estimated_input_tokens,n.estimated_input_tokens,j.estimated_input_tokens,z.estimated_input_tokens,'num'],
      ['Frontier LLM calls',b.frontier_llm_calls??b.llm_calls,n.frontier_llm_calls??n.llm_calls,j.frontier_llm_calls??0,z.frontier_llm_calls??0,'num'],
      ['Decision-model calls',b.decision_model_calls??0,n.decision_model_calls??0,j.decision_model_calls??0,z.decision_model_calls??0,'num'],
      ['Tool calls',b.tool_calls,n.tool_calls,j.tool_calls,z.tool_calls,'num'],
      ['Context to intelligence',b.context_bytes,n.context_bytes,j.context_bytes,z.context_bytes,'bytes'],
      ['End-to-end latency',b.latency_ms,n.latency_ms,j.latency_ms,z.latency_ms,'ms'],
      ['Estimated model cost',b.estimated_cost_usd,n.estimated_cost_usd,j.estimated_cost_usd,z.estimated_cost_usd,'money'],
      ['Evidence precision',b.evidence_precision,n.evidence_precision,j.evidence_precision,z.evidence_precision,'ratio']
    ];
    const head='<div class="metric-row decision-metric header"><div>Metric</div><div>Agent only</div><div>Lean + agents</div><div>Lean + Jev</div><div>Lean + open</div></div>';
    document.querySelector('#metricTable').innerHTML=head+rows.map(([name,a,l,jv,zv,type])=>`<div class="metric-row decision-metric"><div class="metric-name">${name}</div><div class="metric-val">${window.metricFmt(a,type)}</div><div class="metric-val">${window.metricFmt(l,type)}</div><div class="metric-val">${window.metricFmt(jv,type)}</div><div class="metric-val">${window.metricFmt(zv,type)}</div></div>`).join('');
  }

  function renderDecisionSummary(out){
    const summary=document.querySelector('#benchmarkSummary');
    if(!summary||!out.jev||!out.classifier)return;
    const je=Boolean(out.jev.decisions?.escalated), ze=Boolean(out.classifier.decisions?.escalated);
    summary.innerHTML=`
      <div class="benchmark-run-head"><div><div class="eyebrow">LATEST RUN · FOUR ARCHITECTURES</div><h2>${window.escapeHtml(out.case.case_id)}</h2><p>${window.escapeHtml(out.case.deviation)}</p></div><span class="run-badge">${out.case.scenario==='ai_factory_anomaly'?'AI Factory':'Aerospace'}</span></div>
      <div class="benchmark-highlight-grid decision-summary-grid">
        <div><strong>${window.fmtPct(out.token_reduction_pct)}</strong><span>Lean context vs baseline</span></div>
        <div><strong>${window.fmtPct(out.tool_call_reduction_pct)}</strong><span>Lean tool calls</span></div>
        <div><strong>${window.fmtPct(out.jev_vs_nifi_cost_reduction_pct)}</strong><span>Jev cost vs Lean agents</span></div>
        <div><strong>${window.fmtPct(out.classifier_vs_nifi_cost_reduction_pct)}</strong><span>Open cost vs Lean agents</span></div>
        <div><strong>${je?'Escalated':'Avoided'}</strong><span>Jev frontier reasoning</span></div>
        <div><strong>${ze?'Escalated':'Avoided'}</strong><span>Open frontier reasoning</span></div>
      </div>`;
  }

  window.render=function(out){
    baseRender(out);
    if(!out.jev||!out.classifier)return;
    document.querySelector('#jevLane').innerHTML=window.laneHtml(out.jev,'J','NiFi state → Jev typed decisions → confidence gate');
    document.querySelector('#classifierLane').innerHTML=window.laneHtml(out.classifier,'Z','NiFi state → open zero-shot decisions → same confidence gate');
    const frontier=document.querySelector('#frontierSaving');
    if(frontier) frontier.textContent=out.jev.decisions?.escalated?'Used':'Avoided';
    renderDecisionMetrics(out);
    renderDecisionSummary(out);
    decisionEvidence('#jevEvidence',out.jev,'JEV','jev');
    decisionEvidence('#classifierEvidence',out.classifier,'OPEN','classifier');
  };

  function reliabilityBars(buckets){
    return buckets.map(b=>{
      if(!b.count)return '';
      const conf=Math.round((b.confidence||0)*100), acc=Math.round((b.accuracy||0)*100);
      return `<div class="reliability-row">
        <span>${Math.round(b.low*100)}–${Math.round(b.high*100)}%</span>
        <div class="reliability-track"><i style="width:${conf}%"></i><b style="width:${acc}%"></b></div>
        <small>${conf}% conf · ${acc}% correct · n=${b.count}</small>
      </div>`;
    }).join('');
  }

  async function runCalibration(){
    const btn=document.querySelector('#runCalibrationBtn');
    const area=document.querySelector('#calibrationResults');
    btn.disabled=true; btn.textContent='Running calibration…';
    area.innerHTML='<div class="benchmark-placeholder"><span class="mini-spinner">◌</span><div><strong>Evaluating labeled cases…</strong><p>Computing accuracy, ECE, Brier score and reliability buckets.</p></div></div>';
    try{
      const out=await fetch('/api/calibration').then(r=>{if(!r.ok)throw new Error('Calibration endpoint failed');return r.json();});
      area.innerHTML=`<div class="calibration-note"><strong>${out.case_count} labeled smoke-test cases</strong><span>${window.escapeHtml(out.note)}</span></div><div class="calibration-provider-grid">${out.providers.map(p=>`
        <article class="calibration-provider">
          <div class="calibration-head"><div><span class="mode-pill ${p.mode}">${p.mode}</span><h3>${window.escapeHtml(p.name)}</h3></div><strong>${Math.round(p.accuracy*100)}%</strong></div>
          ${p.warning?'<div class="simulation-warning">'+window.escapeHtml(p.warning)+'</div>':''}
          <div class="calibration-kpis">
            <div><b>${Math.round(p.accuracy*100)}%</b><span>Accuracy</span></div>
            <div><b>${p.ece.toFixed(3)}</b><span>ECE ↓</span></div>
            <div><b>${p.brier.toFixed(3)}</b><span>Brier ↓</span></div>
            <div><b>${p.nll.toFixed(2)}</b><span>NLL ↓</span></div>
          </div>
          <div class="reliability-title"><strong>Reliability</strong><span>thin = claimed confidence · thick = empirical accuracy</span></div>
          <div class="reliability-chart">${reliabilityBars(p.buckets)}</div>
        </article>`).join('')}</div>`;
    }catch(err){
      area.innerHTML=`<div class="benchmark-placeholder"><span>!</span><div><strong>Calibration failed</strong><p>${window.escapeHtml(err.message)}</p></div></div>`;
    }finally{btn.disabled=false;btn.textContent='Run calibration smoke test';}
  }

  ensureDecisionUI();
  const form=document.querySelector('#caseForm');
  if(form) form.addEventListener('submit',loadingDecisionLanes);
  document.querySelector('#runCalibrationBtn')?.addEventListener('click',runCalibration);

  document.querySelectorAll('.scenario-btn').forEach(btn=>btn.addEventListener('click',()=>{
    [['#jevEvidence','Run an investigation to populate the Jev decision trace.'],['#classifierEvidence','Run an investigation to populate the open-model decision trace.']].forEach(([q,t])=>{const el=document.querySelector(q);if(el){el.className='evidence-placeholder';el.textContent=t;}});
  }));

  const runText=document.querySelector('#runBtn span');
  if(runText){
    new MutationObserver(()=>{if(runText.textContent==='Run dual investigation')runText.textContent='Run 4-way investigation';}).observe(runText,{childList:true,characterData:true,subtree:true});
  }

  fetch('/api/health').then(r=>r.json()).then(h=>{
    const runtime=document.querySelector('#runtimeMode');
    if(runtime) runtime.textContent=`LLM ${h.llm_mode||'unknown'} · Jev ${h.jev_mode||'unknown'} · Open ${h.classifier_mode||'unknown'}`;
    if(h.llm_mode==='live'||h.jev_mode==='live'||h.classifier_mode==='live') document.querySelector('#modeDot')?.classList.add('live');
  }).catch(()=>{});
})();
