# AeroNCR Context Builder — target NiFi process group

## Contract

**Input**: one NCR JSON envelope.  
**Output**: one canonical `EngineeringContextPack` JSON envelope + provenance identifiers.

## Planned processors

1. **HandleHttpRequest / ConsumeKafka** — accept NCR event.
2. **UpdateAttribute** — assign correlation ID (`ncr_id`) and event window.
3. **InvokeHTTP / database processors** — retrieve QMS, MES, engineering definition, supplier and telemetry evidence.
4. **ValidateRecord** — enforce source schemas and route malformed evidence.
5. **QueryRecord** — filter telemetry by machine and ±15 minute window.
6. **QueryRecord** — filter historical NCRs by part family + operation.
7. **QueryRecord** — retain measurements outside/near tolerance boundary.
8. **UpdateRecord** — normalize units and canonical field names.
9. **DetectDuplicate / record-oriented dedupe** — remove duplicate evidence.
10. **MergeRecord** — create one compact engineering context pack.
11. **Publish/HTTP response** — return the context pack to the agent service.

## Benchmark instrumentation

Capture per run:

- bytes entering NiFi
- bytes leaving NiFi toward agents
- FlowFile count
- queue time / processor time
- retries and failure routes
- provenance chain
- source API call count

The agent-only lane records equivalent source and agent metrics so the benchmark compares cost per successfully investigated NCR.
