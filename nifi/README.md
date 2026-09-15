# NiFi lane

The current UI ships with a deterministic Python emulation of the intended NiFi process groups so the A/B benchmark works immediately. The real NiFi integration should preserve the same input/output contract so benchmark results remain comparable.

## Common pattern

1. Receive case envelope
2. Fan out to operational sources + K&KH corpus
3. Validate schema and identifiers
4. Normalize timestamps/units
5. Filter to the relevant asset, batch/pod and event window
6. Correlate cross-source evidence
7. Deduplicate / aggregate deterministic data
8. Retrieve only relevant corpus items
9. Build a compact Evidence Context Pack
10. Record provenance
11. Return the pack to the agent service

## Aerospace process group

Sources: QMS, MES, PLM/engineering definition, inspection, machine telemetry, supplier records, historical NCRs and K&KH.

Primary deterministic keys: machine, supplier batch, part/subject, operation and event time window.

Output: `AerospaceEvidencePack`.

## High-Tech AI Factory process group

Sources: rack/GPU telemetry, cooling/CDU telemetry, network fabric, DCIM, workload telemetry, rack/pod configuration, historical incidents and K&KH.

Primary deterministic keys: rack, pod, cooling loop, network leaf and event time window.

The flow should compute deterministic summaries such as:
- average/max GPU and HBM temperatures
- rack inlet temperature
- rack power versus configured design limit
- coolant flow versus configured minimum
- CDU supply temperature / pump / valve demand
- network CRC/retry counters and fabric utilization
- workload throughput impact
- matching historical incident signatures
- relevant operating standards, runbooks and lessons learned

Output: `AIFactoryEvidencePack`.

## Boundary

NiFi prepares and traces evidence. It does **not** decide root cause. The agent layer reasons over the evidence pack and the final intervention remains a human/governed workflow decision.

`docker-compose.yml` includes Apache NiFi for the next phase, when these process groups replace the Python adapter.
