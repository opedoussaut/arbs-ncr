from typing import Literal
from pydantic import BaseModel, Field


Scenario = Literal["aerospace_ncr", "semiconductor_yield"]


class CaseInput(BaseModel):
    scenario: Scenario = "aerospace_ncr"
    case_id: str = Field(default="NCR-2026-004381")
    severity: Literal["Low", "Medium", "High", "Critical"] = "High"
    timestamp: str = Field(default="2026-09-15T08:42:31")
    subject: str = Field(default="Wing structural component")
    process: str = Field(default="Automated drilling")
    asset: str = Field(default="DRILL_CELL_07")
    batch: str = Field(default="B-81932")
    deviation: str = Field(default="Hole diameter +0.18 mm above tolerance")
    configuration: str = Field(default="C128")
    notes: str = Field(default="Deviation detected during in-process dimensional inspection.")


class AgentStep(BaseModel):
    agent: str
    state: Literal["done", "warning", "info"] = "done"
    title: str
    detail: str
    evidence_count: int = 0
    duration_ms: int = 0


class Metrics(BaseModel):
    source_bytes: int
    context_bytes: int
    estimated_input_tokens: int
    output_tokens: int
    llm_calls: int
    tool_calls: int
    api_calls: int
    deterministic_steps: int
    retries: int
    latency_ms: int
    estimated_cost_usd: float
    evidence_precision: float
    mode: Literal["simulated", "live"]


class InvestigationResult(BaseModel):
    lane: Literal["baseline", "nifi"]
    title: str
    summary: str
    confidence: float
    likely_cause: str
    recommendation: str
    human_gate: str
    steps: list[AgentStep]
    metrics: Metrics
    evidence: list[str]


class ComparisonResponse(BaseModel):
    case: CaseInput
    baseline: InvestigationResult
    nifi: InvestigationResult
    headline: str
    savings_pct: float
    token_reduction_pct: float
    latency_reduction_pct: float
    tool_call_reduction_pct: float
