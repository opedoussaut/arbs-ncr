(() => {
  const nativeFetch = window.fetch.bind(window);

  function jsonResponse(data, status=200){
    return Promise.resolve(new Response(JSON.stringify(data), {
      status,
      headers:{'Content-Type':'application/json'}
    }));
  }

  function metrics({source,context,tokens,out=220,llm=0,tools=1,api=6,steps=8,latency=300,cost=0,precision=.9,frontier=0,decision=0}){
    return {
      source_bytes:source, context_bytes:context, estimated_input_tokens:tokens, output_tokens:out,
      llm_calls:llm, tool_calls:tools, api_calls:api, deterministic_steps:steps, retries:0,
      latency_ms:latency, estimated_cost_usd:cost, evidence_precision:precision,
      mode:'simulated', frontier_llm_calls:frontier, decision_model_calls:decision
    };
  }

  function scenarioData(caseData){
    const ai=caseData.scenario==='ai_factory_anomaly';
    if(ai){
      return {
        cause:'Cooling branch restriction / CDU flow imbalance',
        recommendation:'Reduce or drain workload on the affected rack; validate branch flow and valve state; compare neighboring racks on the same CDU before changing GPU, network or scheduler settings.',
        gate:'Infrastructure Operations must approve workload drain and any cooling-loop intervention.',
        baselineAgents:[
          ['Thermal','Thermal Agent','GPU/HBM temperatures and inlet-air temperature rise with throttling; raw retrieval contains substantial unrelated telemetry.'],
          ['Infrastructure','Infrastructure Agent','Reduced branch flow and high CDU pump/valve demand are the strongest infrastructure deviations.'],
          ['Network','Network Agent','Fabric utilization rises, but errors and retries are too low to explain the throughput loss.'],
          ['Knowledge','Knowledge Agent','Historical thermal-throttle-low-flow incidents and runbooks point to branch restriction or balancing issues.'],
          ['Supervisor','Supervisor synthesis','Evidence converges on a local cooling-distribution problem rather than power, network or workload as the primary cause.']
        ],
        leanAgents:[
          ['Thermal','Thermal Agent','Lean rack summary isolates sustained GPU/HBM heat, inlet excursion and repeated throttle events.'],
          ['Infrastructure','Infrastructure Agent','Correlated CDU data shows low flow with high commanded cooling effort.'],
          ['Network','Network Agent','Lean fabric summary rules out network errors as the dominant explanation.'],
          ['Knowledge','Knowledge Agent','High-relevance runbooks and historical incidents match the observed signature.'],
          ['Supervisor','Supervisor synthesis','The compact evidence pack supports cooling branch restriction / flow imbalance as the working cause.']
        ],
        choice:'cooling_flow', source:1780000, rawContext:1180000, leanContext:12800
      };
    }
    return {
      cause:'Progressive tool wear / spindle drift',
      recommendation:'Quarantine the affected production scope; verify tool condition and spindle calibration; inspect adjacent features and same-tool output before engineering disposition.',
      gate:'Final disposition requires authorized Quality/Engineering approval.',
      baselineAgents:[
        ['Quality','Quality Agent','Clustered dimensional deviations are present, but the raw evidence requires broad retrieval and reduction.'],
        ['Manufacturing','Manufacturing Agent','Tool-cycle count and vibration growth make progressive wear or spindle drift the leading manufacturing hypothesis.'],
        ['Design','Design Agent','The characteristic requires controlled engineering disposition.'],
        ['Supervisor','Supervisor synthesis','Evidence supports a manufacturing-process cause over incoming material.']
      ],
      leanAgents:[
        ['Quality','Quality Agent','Lean evidence isolates the adjacent out-of-tolerance features and relevant historical NCRs.'],
        ['Manufacturing','Manufacturing Agent','Filtered telemetry highlights elevated vibration and high tool-cycle count around the event.'],
        ['Design','Design Agent','Current engineering definition and human disposition gate are already resolved in the evidence pack.'],
        ['Supervisor','Supervisor synthesis','The compact evidence pack supports progressive tool wear / spindle drift as the working cause.']
      ],
      choice:'tool_wear_spindle', source:720000, rawContext:480000, leanContext:9400
    };
  }

  function steps(rows, lean=false){
    return rows.map((r,i)=>({
      agent:r[0], state:'done', title:r[1], detail:r[2],
      evidence_count:lean ? 7 : 20,
      duration_ms:lean ? 280 : 520
    }));
  }

  function result(caseData, lane){
    const s=scenarioData(caseData);
    const ai=caseData.scenario==='ai_factory_anomaly';
    if(lane==='baseline'){
      return {
        lane:'baseline', title:'Agent-only baseline',
        summary:'Agents retrieve, reduce and reason over the broad source universe directly.',
        confidence:ai ? .77 : .78, likely_cause:s.cause, recommendation:s.recommendation, human_gate:s.gate,
        steps:steps(s.baselineAgents,false),
        metrics:metrics({source:s.source,context:s.rawContext,tokens:Math.round(s.rawContext/3.6),llm:s.baselineAgents.length,tools:ai?18:14,api:ai?18:14,steps:1,latency:ai?6900:5100,cost:ai ? .31 : .18,precision:ai ? .56 : .61,frontier:s.baselineAgents.length}),
        evidence:['Agent/tool layer queried raw operational sources and corpus directly']
      };
    }
    if(lane==='nifi'){
      return {
        lane:'nifi', title:'Lean / NiFi-assisted',
        summary:'Deterministic preprocessing prepares a compact evidence pack before agent reasoning.',
        confidence:ai ? .90 : .88, likely_cause:s.cause, recommendation:s.recommendation, human_gate:s.gate,
        steps:steps(s.leanAgents,true),
        metrics:metrics({source:s.source,context:s.leanContext,tokens:Math.round(s.leanContext/3.8),llm:s.leanAgents.length,tools:ai?3:2,api:ai?8:6,steps:ai?11:8,latency:ai?2100:1700,cost:ai ? .034 : .021,precision:ai ? .94 : .92,frontier:s.leanAgents.length}),
        evidence:[
          'Filtered source telemetry to the event window',
          'Correlated operational records across the affected asset and configuration',
          'Retrieved only high-relevance K&KH items',
          'Normalized evidence into one provenance-preserving state'
        ]
      };
    }
    if(lane==='jev'){
      const conf=ai ? .95 : .91, ambiguity=ai ? .12 : .18;
      return {
        lane:'jev', title:'Lean + Jev decision layer',
        summary:'Jev resolves the structured working decision without a frontier LLM call in this simulated architecture run.',
        confidence:conf, likely_cause:s.cause, recommendation:s.recommendation, human_gate:s.gate,
        steps:[
          {agent:'Lean',state:'done',title:'Lean state preparation',detail:'Deterministic preprocessing builds one compact, typed decision state.',evidence_count:7,duration_ms:110},
          {agent:'Jev',state:'done',title:'Parallel Jev decisions',detail:`Primary cause=${s.choice} (${Math.round(conf*100)}% confidence); ambiguity=${Math.round(ambiguity*100)}%.`,evidence_count:7,duration_ms:210},
          {agent:'Human',state:'info',title:'Human workflow gate',detail:s.gate,evidence_count:0,duration_ms:0}
        ],
        metrics:metrics({source:s.source,context:s.leanContext,tokens:Math.round(s.leanContext/4),out:55,llm:1,tools:1,api:ai?8:6,steps:ai?12:9,latency:360,cost:.0006,precision:ai ? .94 : .92,frontier:0,decision:1}),
        evidence:['Lean state prepared','Jev typed decisions evaluated','Confidence gate passed','Frontier reasoning avoided'],
        decisions:{model:'jev-simulated',escalated:false,confidence_threshold:.80,escalation_probability:.50,answers:{
          primary_cause:{type:'choice',choice:s.choice,confidence:conf,probabilities:{[s.choice]:conf,unknown:1-conf}},
          severity:{type:'score',score:2.1,confidence:.86},
          requires_frontier_reasoning:{type:'noul',noul:ambiguity}
        }}
      };
    }
    const conf=ai ? .84 : .82, ambiguity=ai ? .27 : .30;
    return {
      lane:'classifier', title:'Lean + open zero-shot',
      summary:'The open zero-shot control reaches the same structured decision surface without a frontier LLM call in this simulated architecture run.',
      confidence:conf, likely_cause:s.cause, recommendation:s.recommendation, human_gate:s.gate,
      steps:[
        {agent:'Lean',state:'done',title:'Lean state preparation',detail:'The same compact state is used for the open control.',evidence_count:7,duration_ms:110},
        {agent:'Classifier',state:'done',title:'Open zero-shot decisions',detail:`Primary cause=${s.choice} (${Math.round(conf*100)}% confidence); ambiguity=${Math.round(ambiguity*100)}%.`,evidence_count:7,duration_ms:260},
        {agent:'Human',state:'info',title:'Human workflow gate',detail:s.gate,evidence_count:0,duration_ms:0}
      ],
      metrics:metrics({source:s.source,context:s.leanContext,tokens:Math.round(s.leanContext/4),out:55,llm:1,tools:1,api:ai?8:6,steps:ai?12:9,latency:450,cost:0,precision:ai ? .94 : .92,frontier:0,decision:1}),
      evidence:['Lean state prepared','Open zero-shot typed decisions evaluated','Confidence gate passed','Frontier reasoning avoided'],
      decisions:{model:'zero-shot-simulated',provider:'open-zero-shot',escalated:false,confidence_threshold:.80,escalation_probability:.50,answers:{
        primary_cause:{type:'choice',choice:s.choice,confidence:conf,probabilities:{[s.choice]:conf,unknown:1-conf}},
        severity:{type:'score',score:2.0,confidence:.71},
        requires_frontier_reasoning:{type:'noul',noul:ambiguity}
      }}
    };
  }

  function investigate(caseData){
    const baseline=result(caseData,'baseline');
    const nifi=result(caseData,'nifi');
    const jev=result(caseData,'jev');
    const classifier=result(caseData,'classifier');
    const pct=(a,b)=>b?((a/b)*100):0;
    return {
      case:caseData, baseline,nifi,jev,classifier,
      headline:'Four architectures, one evidence universe: Lean preprocessing reduces context before reasoning, while Jev and an open control test selective frontier escalation.',
      savings_pct:pct(baseline.metrics.estimated_cost_usd-nifi.metrics.estimated_cost_usd,baseline.metrics.estimated_cost_usd),
      token_reduction_pct:pct(baseline.metrics.estimated_input_tokens-nifi.metrics.estimated_input_tokens,baseline.metrics.estimated_input_tokens),
      latency_reduction_pct:pct(baseline.metrics.latency_ms-nifi.metrics.latency_ms,baseline.metrics.latency_ms),
      tool_call_reduction_pct:pct(baseline.metrics.tool_calls-nifi.metrics.tool_calls,baseline.metrics.tool_calls),
      jev_vs_nifi_cost_reduction_pct:pct(nifi.metrics.estimated_cost_usd-jev.metrics.estimated_cost_usd,nifi.metrics.estimated_cost_usd),
      jev_vs_nifi_latency_reduction_pct:pct(nifi.metrics.latency_ms-jev.metrics.latency_ms,nifi.metrics.latency_ms),
      frontier_call_reduction_pct:100,
      classifier_vs_nifi_cost_reduction_pct:100,
      classifier_vs_nifi_latency_reduction_pct:pct(nifi.metrics.latency_ms-classifier.metrics.latency_ms,nifi.metrics.latency_ms)
    };
  }

  const calibration={
    case_count:24,
    note:'Small labeled smoke test. Simulated adapters validate the interface and metric pipeline only; replace with 300+ representative labeled cases for model evaluation.',
    providers:[
      {name:'Jev',mode:'simulated',warning:'SIMULATED ADAPTER — these are interface/logic test numbers, not model benchmark evidence.',accuracy:.83,ece:.12,brier:.08,nll:.48,buckets:[
        {low:0,high:.2,count:0,confidence:null,accuracy:null},{low:.2,high:.4,count:0,confidence:null,accuracy:null},
        {low:.4,high:.6,count:2,confidence:.55,accuracy:.50},{low:.6,high:.8,count:6,confidence:.73,accuracy:.67},{low:.8,high:1,count:16,confidence:.91,accuracy:.88}
      ]},
      {name:'Open zero-shot',mode:'simulated',warning:'SIMULATED ADAPTER — these are interface/logic test numbers, not model benchmark evidence.',accuracy:.75,ece:.17,brier:.12,nll:.66,buckets:[
        {low:0,high:.2,count:0,confidence:null,accuracy:null},{low:.2,high:.4,count:1,confidence:.38,accuracy:0},
        {low:.4,high:.6,count:4,confidence:.53,accuracy:.50},{low:.6,high:.8,count:10,confidence:.71,accuracy:.70},{low:.8,high:1,count:9,confidence:.84,accuracy:.89}
      ]}
    ]
  };

  window.fetch = async function(input, init={}){
    const url = typeof input==='string' ? input : input.url;
    if(url.endsWith('/api/health') || url==='/api/health'){
      return jsonResponse({ok:true,llm_mode:'simulated',jev_mode:'simulated',classifier_mode:'simulated',runtime:'static-demo',scenarios:['aerospace_ncr','ai_factory_anomaly']});
    }
    if(url.endsWith('/api/calibration') || url==='/api/calibration'){
      return jsonResponse(calibration);
    }
    if(url.endsWith('/api/investigate') || url==='/api/investigate'){
      try{
        const body=typeof init.body==='string' ? JSON.parse(init.body) : (init.body||{});
        return jsonResponse(investigate(body));
      }catch(e){
        return jsonResponse({detail:String(e)},500);
      }
    }
    return nativeFetch(input,init);
  };
})();
