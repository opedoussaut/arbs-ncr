import asyncio
from app.engine import InvestigationEngine
from app.models import CaseInput


def assert_lean_lane_reduces_agent_work(out):
    assert out.nifi.metrics.context_bytes < out.baseline.metrics.context_bytes
    assert out.nifi.metrics.tool_calls < out.baseline.metrics.tool_calls
    assert out.nifi.metrics.estimated_input_tokens < out.baseline.metrics.estimated_input_tokens
    assert out.nifi.metrics.evidence_precision > out.baseline.metrics.evidence_precision
    assert out.baseline.human_gate
    assert out.nifi.human_gate


def test_aerospace_ncr_benchmark():
    engine = InvestigationEngine()
    out = asyncio.run(engine.compare(CaseInput()))
    assert out.case.scenario == "aerospace_ncr"
    assert any(step.agent == "Quality" for step in out.nifi.steps)
    assert_lean_lane_reduces_agent_work(out)


def test_ai_factory_benchmark():
    engine = InvestigationEngine()
    case = CaseInput(
        scenario="ai_factory_anomaly",
        case_id="AIF-INC-2026-0017",
        subject="GPU rack R27",
        process="Distributed AI training at peak load",
        asset="RACK-R27",
        batch="POD-03",
        deviation="GPU inlet temperature +6.8°C with HBM throttling and ~18% throughput loss",
        configuration="72-GPU liquid-cooled rack",
        notes="Determine whether cooling, power, network or workload behavior is the primary cause.",
    )
    out = asyncio.run(engine.compare(case))
    assert out.case.scenario == "ai_factory_anomaly"
    assert any(step.agent == "Thermal" for step in out.nifi.steps)
    assert any(step.agent == "Network" for step in out.nifi.steps)
    assert any(step.agent == "Knowledge" for step in out.nifi.steps)
    assert "Cooling" in out.nifi.likely_cause
    assert_lean_lane_reduces_agent_work(out)
