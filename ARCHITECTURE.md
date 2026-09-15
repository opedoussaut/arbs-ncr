# Architecture

```text
                         SAME NCR
                            |
               +------------+------------+
               |                         |
        AGENT-ONLY LANE            NIFI-ASSISTED LANE
               |                         |
      direct source tools           NiFi context builder
 QMS / MES / PLM / IoT / supplier       |
               |                   canonical evidence pack
               |                         |
       Quality / Mfg / Design     Quality / Mfg / Design
               |                         |
          Supervisor                 Supervisor
               +------------+------------+
                            |
                     HUMAN APPROVAL
                            |
                       BENCHMARKER
```

## Boundary rule

- **NiFi** owns deterministic data movement, filtering, normalization, buffering and provenance.
- **Agents** own interpretation, hypothesis formation and synthesis.
- **Humans** own final engineering disposition.

This prevents the benchmark from hiding deterministic work inside prompts while also preventing NiFi from becoming an agent orchestrator.
