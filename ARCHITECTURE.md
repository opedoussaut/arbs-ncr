# Lean AI architecture

Lean AI benchmarks whether deterministic preprocessing can make agentic investigations cheaper and more robust by reducing the amount of raw enterprise data reaching the reasoning layer.

```text
                 SAME INDUSTRIAL CASE
                         |
              same source universe
                  + K&KH corpus
                         |
            +------------+------------+
            |                         |
     AGENT-ONLY LANE             LEAN LANE
            |                         |
   direct source tools          NiFi / deterministic
   broad corpus access           context builder
            |                         |
    raw/broad context          compact evidence pack
            |                         |
            +------------+------------+
                         |
                 SPECIALIST AGENTS
                         |
                    SUPERVISOR
                         |
                    HUMAN GATE
                         |
                    BENCHMARKER
```

## Boundary rule

- **Corpus / K&KH patrimony** owns durable standards, architecture rules, procedures, lessons learned and historical cases.
- **NiFi / deterministic data layer** owns data movement, time-window selection, filtering, normalization, correlation, aggregation, buffering and provenance.
- **Agents** own interpretation, hypothesis formation, competing-cause analysis and synthesis.
- **Humans / governed workflow** own final engineering, quality or infrastructure decisions.

The PoC deliberately avoids hiding deterministic work inside prompts and avoids turning NiFi into an agent orchestrator.

## Scenario A — Aerospace NCR

```text
Machine telemetry ----+
Inspection results ---+
Work orders ----------+----> Lean preprocessing ----> NCR evidence pack
Engineering definition+
Supplier records -----+
Historical NCRs ------+
K&KH corpus ----------+
                                      |
                         Quality / Manufacturing / Design
                                      |
                                  Supervisor
                                      |
                           Quality / Engineering gate
```

## Scenario B — High-Tech AI Factory

```text
GPU/rack telemetry ---+
Cooling / CDU data ---+
Network fabric -------+
DCIM events ----------+----> Lean preprocessing ----> AI Factory evidence pack
Workload telemetry ---+
Rack/pod config ------+
Historical incidents -+
K&KH corpus ----------+
                                      |
                     Thermal / Infrastructure / Network / Knowledge
                                      |
                                  Supervisor
                                      |
                         Infrastructure Operations gate
```

The AI Factory scenario is intentionally multi-causal: thermal throttling can superficially resemble power, network, scheduler or hardware problems. The deterministic layer does not decide the root cause; it builds a traceable, compact evidence package so the agents can reason over the relevant cross-domain signals.

## Benchmark outputs

For both scenarios the UI compares:

- agent input tokens
- agent-facing tool calls
- source/API calls
- context bytes delivered to the agents
- latency
- estimated LLM cost
- evidence precision
- number of deterministic preprocessing steps

The principal future KPI is **cost per successfully investigated case**, not token reduction in isolation.
