# AeroNCR Agent Benchmark

A side-by-side PoC that compares a conventional agent-only non-conformance investigation with a NiFi-assisted architecture.

## What works now

- Apple-inspired NCR intake UI
- Synthetic aerospace manufacturing evidence generator
- Four-agent investigation lane (Quality, Manufacturing, Design, Supervisor)
- Agent-only and NiFi-assisted lanes run from the same NCR and same evidence universe
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

## GitHub Codespaces (recommended for the PoC)

This repository includes a devcontainer. Open **Code → Codespaces → Create codespace on main**. Dependencies install automatically and the app starts on port `8088`.

When Codespaces reports that port `8088` is available, choose **Open in Browser**.

## With Docker / NiFi

```bash
docker compose up --build
```

App: http://localhost:8088  
NiFi: https://localhost:8443/nifi

The current UI still uses the emulated NiFi adapter; the real flow can be wired once the process-group API contract is stable.

## Benchmark rule

Both lanes use the same NCR, source universe, reasoning model and final safety gate. The experimental variable is whether deterministic source reduction/correlation occurs in the agent/tool layer or in a dedicated NiFi data plane.
