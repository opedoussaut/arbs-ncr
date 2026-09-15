import asyncio
from app.engine import InvestigationEngine
from app.models import NCRInput


def test_nifi_lane_reduces_agent_context_and_tool_calls():
    engine = InvestigationEngine()
    out = asyncio.run(engine.compare(NCRInput()))
    assert out.nifi.metrics.context_bytes < out.baseline.metrics.context_bytes
    assert out.nifi.metrics.tool_calls < out.baseline.metrics.tool_calls
    assert out.nifi.metrics.estimated_input_tokens < out.baseline.metrics.estimated_input_tokens
    assert out.baseline.human_gate
    assert out.nifi.human_gate
