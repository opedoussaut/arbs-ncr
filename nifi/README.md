# NiFi lane

The UI's first slice ships with a deterministic Python emulation of the intended NiFi process group so the benchmark works immediately.

Target real NiFi flow:

1. Receive NCR envelope
2. Fan out to synthetic QMS / MES / PLM / telemetry / supplier sources
3. ValidateRecord
4. QueryRecord / RouteOnAttribute by machine, batch, part family and event window
5. DeduplicateRecord
6. UpdateRecord to canonical units/schema
7. MergeRecord into an Engineering Context Pack
8. Record provenance and return the compact pack to the agent service

`docker-compose.yml` includes Apache NiFi 2.11.0 because that tag is currently available in the Apache Docker repository. The adapter will be wired in the next iteration after the UI/benchmark contract is fixed.
