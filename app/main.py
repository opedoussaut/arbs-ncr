from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import InvestigationEngine
from .models import CaseInput, ComparisonResponse

BASE = Path(__file__).parent
app = FastAPI(title="Lean AI Benchmark", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
engine = InvestigationEngine()


@app.get("/")
async def home():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "llm_mode": "live" if engine.reasoner.live else "simulated",
        "scenarios": ["aerospace_ncr", "ai_factory_anomaly"],
    }


@app.post("/api/investigate", response_model=ComparisonResponse)
async def investigate(case: CaseInput):
    return await engine.compare(case)
