# K&KH community post — Lean AI

## Don't give an agent everything we know. Give it everything it needs to know.

We often focus on making agents more capable: better models, more tools, more memory and more autonomous reasoning.

But there is another lever that may be just as important: **reduce and contextualize what reaches the agent in the first place.**

I have been experimenting with a small PoC called **Lean AI**. The idea is simple: run the same industrial investigation through two architectures and measure the difference.

**Agent-first:** agents directly query the source systems and a broad Knowledge & Know-How corpus.

**Lean:** a deterministic data layer first filters, correlates, normalizes and aggregates operational evidence, retrieves only the relevant K&KH, and then provides the agents with a compact evidence pack.

The High-Tech demonstrator uses a generic **AI Factory infrastructure anomaly**: a GPU rack starts throttling during a high-load distributed AI workload. The investigation has access to rack/GPU telemetry, liquid-cooling data, network-fabric data, DCIM events, workload impact, rack configuration, historical incidents, operating standards, runbooks and lessons learned.

The deterministic layer can establish facts such as:

- which rack and pod are affected,
- the relevant ±30 minute telemetry window,
- coolant flow versus the configured minimum,
- inlet/GPU/HBM temperatures,
- rack power versus design limits,
- network error counters,
- affected workloads,
- similar historical incident signatures,
- and the relevant K&KH documents.

It should **not** decide the root cause.

That is where the agents add value. Thermal, Infrastructure, Network and Knowledge agents interpret the evidence, test competing explanations and let a supervisor agent synthesize the most plausible hypothesis and next actions — with a human decision gate before intervention.

The architectural principle is:

> **Corpus = what we know.  
> Deterministic layer = what is relevant now.  
> Agents = what it means.  
> Governed workflow = what we do about it.**

Apache NiFi is the deterministic layer used in the PoC because it makes filtering, correlation, routing, provenance and future streaming/backpressure capabilities easy to demonstrate. It is not the only possible implementation.

The real question is broader:

**Which tasks truly require probabilistic intelligence, and which should remain deterministic?**

An LLM probably should not spend tokens removing duplicates, selecting timestamps, normalizing units, joining identifiers or aggregating thousands of telemetry records when traditional software can do those operations reliably and cheaply.

The next step is to measure the effect rather than assume it: context size, tokens, tool calls, latency, evidence precision and ultimately **cost per successfully investigated case**.

For K&KH, this suggests an important shift. The goal is not simply to make our entire patrimony searchable by agents. It is to make the right knowledge available **in context, at the right moment, with the right operational evidence**.

Sometimes the best way to make an AI system more intelligent is to give it less to process.
