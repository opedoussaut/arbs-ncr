# Lean AI

A side-by-side PoC that compares conventional agentic workflows with a NiFi-assisted architecture to measure how deterministic preprocessing can reduce context, tool calls, latency and cost.

The current implementation uses a generic aerospace non-conformance investigation as the first benchmark scenario, with additional industry scenarios planned.

## What works now

- Apple-inspired investigation UI
- Synthetic industrial evidence generator
- Multi-agent investigation lane
- Agent-only and NiFi-assisted lanes run from the same case and same evidence universe
- Deterministic NiFi emulation: filtering, correlation, normalization and provenance
- Benchmark metrics: tokens, tool/API calls, data reduction, modeled/live latency and estimated LLM cost
- Optional real OpenAI Responses API calls when `OPENAI_API_KEY` is set
- Docker Compose scaffold with Apache NiFi

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8088
```

Open http://localhost:8088

Without an API key the application explicitly runs in **simulation mode**. Copy `.env.example` to `.env` or export the variables to enable live LLM calls.

## GitHub Codespaces

This repository includes a devcontainer named **Lean AI**. Open **Code → Codespaces → Create codespace on main**. Dependencies install automatically and the app starts on port `8088`.

When Codespaces reports that port `8088` is available, choose **Open in Browser**.

## With Docker / NiFi

```bash
docker compose up --build
```

App: http://localhost:8088  
NiFi: https://localhost:8443/nifi

The current UI still uses the emulated NiFi adapter; the real flow can be wired once the process-group API contract is stable.

## Benchmark rule

Both lanes use the same case, source universe, reasoning model and final safety gate. The experimental variable is whether deterministic source reduction/correlation occurs in the agent/tool layer or in a dedicated NiFi data plane.
