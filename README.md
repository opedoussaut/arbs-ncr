# Lean AI

Lean AI is a side-by-side benchmark PoC that tests one simple hypothesis:

> **Agents should spend tokens on reasoning, not on deterministic data reduction.**

The application runs the same industrial case through two architectures:

1. **Agent-only baseline** — agents query a broad raw source universe and the K&KH corpus directly.
2. **Lean / NiFi-assisted** — a deterministic dataflow first filters, correlates, normalizes and contextualizes the same evidence, then gives the agents a compact evidence pack.

The goal is to measure when a dedicated deterministic preprocessing layer reduces context, tool calls, latency and LLM cost without losing decision-relevant evidence.

## Benchmark scenarios

### Aerospace · Non-conformance investigation

Synthetic dimensional NCR on a structural component. Evidence includes machine telemetry, inspection results, work orders, engineering definition, supplier information, historical NCRs and a small K&KH corpus.

Specialist agents:
- Quality
- Manufacturing
- Design
- Supervisor

Human gate: final quality/engineering disposition remains mandatory.

### High-Tech · AI Factory infrastructure anomaly

Synthetic GPU-rack performance incident during a high-load distributed AI workload. The rack experiences elevated inlet/GPU/HBM temperatures, throttling and throughput loss.

Evidence includes:
- GPU/rack telemetry
- liquid-cooling/CDU telemetry
- network-fabric telemetry
- DCIM events
- workload/job impact
- rack/pod configuration limits
- historical infrastructure incidents
- K&KH corpus: operating standards, architecture rules, runbooks and lessons learned

Specialist agents:
- Thermal
- Infrastructure
- Network
- Knowledge
- Supervisor

The synthetic evidence is deliberately constructed so the agents must distinguish a cooling-distribution problem from plausible network, power or workload explanations. Human Infrastructure Operations approval remains mandatory before intervention.

## What works now

- Apple-inspired dual-domain investigation UI
- Aerospace / High-Tech scenario selector
- Deterministic synthetic evidence generators for both domains
- Same source universe used by both A/B lanes
- Domain-specific multi-agent investigations
- Deterministic NiFi emulation: filtering, correlation, normalization, aggregation and provenance
- K&KH corpus retrieval in both scenarios
- Benchmark metrics: input tokens, tool/API calls, context size, modeled/live latency, evidence precision and estimated LLM cost
- Optional real OpenAI Responses API calls when `OPENAI_API_KEY` is set
- Docker Compose scaffold with Apache NiFi
- Automated tests for both domains

## Architecture

```text
         OPERATIONAL DATA + K&KH CORPUS
                     |
          +----------+----------+
          |                     |
   AGENT-ONLY                LEAN LANE
      BASELINE            NiFi / deterministic
          |                 preprocessing
          |                     |
   broad/raw context        evidence pack
          |                     |
          +----------+----------+
                     |
              specialist agents
                     |
                 supervisor
                     |
                 human gate
                     |
                 benchmark
```

**Corpus = what the organization knows.**  
**Deterministic layer = what is relevant now.**  
**Agents = what the evidence means.**  
**Humans/workflow = what we decide to do.**

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8088
```

Open `http://localhost:8088`.

Without an API key the application explicitly runs in **simulation mode**. Copy `.env.example` to `.env` or export the variables to enable live LLM calls.

## GitHub Codespaces

This repository includes a devcontainer named **Lean AI**. Open **Code → Codespaces → Create codespace on main**. Dependencies install automatically and the app starts on port `8088`.

When Codespaces reports that port `8088` is available, choose **Open in Browser**.

## Docker / Apache NiFi

```bash
docker compose up --build
```

App: `http://localhost:8088`  
NiFi: `https://localhost:8443/nifi`

The application currently uses a Python implementation of the deterministic NiFi contract so the A/B experiment is immediately runnable. The next implementation step is to replace that adapter with real NiFi Process Groups while preserving the exact same input/output contract and benchmark instrumentation.

## Benchmark rule

For each run, both lanes use the same:

- case
- synthetic source universe
- K&KH corpus
- reasoning model
- specialist-agent mission
- human decision gate

The experimental variable is **where deterministic reduction/correlation happens**.

Simulation numbers are illustrative and must not be presented as measured production savings. The project is designed so those metrics can later be replaced with real token, latency, infrastructure and cost measurements.
