# Lean AI Context Builders — target NiFi process groups

## Common contract

**Input**: one industrial case JSON envelope.  
**Output**: one canonical evidence-pack JSON envelope plus provenance identifiers.

The agent-only lane receives equivalent source data directly. The benchmark must keep the reasoning model, case and human gate identical.

## Process Group A — Aerospace NCR Context Builder

1. **HandleHttpRequest / ConsumeKafka** — accept NCR event.
2. **UpdateAttribute** — assign correlation ID and event window.
3. **InvokeHTTP / database processors** — retrieve QMS, MES, engineering definition, supplier, machine telemetry and K&KH evidence.
4. **ValidateRecord** — enforce source schemas and route malformed evidence.
5. **QueryRecord** — filter machine telemetry by asset and ±15 minute window.
6. **QueryRecord** — filter historical NCRs by subject + process.
7. **QueryRecord** — retain dimensional measurements outside/near tolerance boundary.
8. **UpdateRecord** — normalize units and canonical field names.
9. **DeduplicateRecord / record-oriented dedupe** — remove duplicate evidence.
10. **QueryRecord** — retain relevant K&KH corpus items.
11. **MergeRecord** — create `AerospaceEvidencePack`.
12. **Publish/HTTP response** — return the compact pack to the agent service.

## Process Group B — AI Factory Context Builder

1. **HandleHttpRequest / ConsumeKafka** — accept infrastructure incident.
2. **UpdateAttribute** — assign correlation ID, rack, pod and event windows.
3. **Fan-out retrieval** — collect:
   - GPU/rack telemetry
   - cooling/CDU telemetry
   - network-fabric telemetry
   - DCIM events
   - workload/job telemetry
   - rack/pod configuration
   - historical incidents
   - K&KH corpus
4. **ValidateRecord** — validate source schemas and timestamps.
5. **QueryRecord** — filter target rack to ±30 minute window.
6. **QueryRecord** — resolve rack → cooling loop → ±45 minute cooling evidence.
7. **QueryRecord** — resolve pod/rack → network leaf and retain matching fabric evidence.
8. **QueryRecord** — correlate DCIM events and affected workloads.
9. **UpdateRecord** — normalize timestamps and canonical units.
10. **Record aggregation** — calculate deterministic summaries: GPU/HBM temperature, inlet temperature, rack power, coolant flow, CDU state, fabric errors/utilization and workload throughput delta.
11. **QueryRecord** — match historical `thermal-throttle-low-flow` incident signatures.
12. **QueryRecord / corpus adapter** — retrieve only standards, runbooks, architecture rules and lessons learned relevant to thermal/cooling symptoms.
13. **MergeRecord** — create `AIFactoryEvidencePack`.
14. **Publish/HTTP response** — return the pack to the agent service.

## Important boundary

NiFi may calculate factual/physical comparisons such as:

- observed coolant flow < configured minimum
- observed inlet temperature > configured target
- network CRC error count
- affected workload throughput delta

NiFi must **not** decide that cooling is the root cause. Root-cause reasoning remains in the agent layer; authorization to drain workloads or intervene on cooling remains human/governed.

## Benchmark instrumentation

Capture per run:

- bytes entering the deterministic layer
- bytes leaving toward agents
- FlowFile / record count
- queue time and processor time
- retries and failure routes
- provenance chain
- source API call count
- agent input/output tokens
- agent tool calls
- end-to-end latency
- successful investigation rate
- estimated total cost

The long-term comparison KPI is **cost per successfully investigated case**.
