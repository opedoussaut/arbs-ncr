import asyncio

from app.calibration import run_calibration
from app.engine import InvestigationEngine


def test_calibration_report_shape():
    engine = InvestigationEngine()
    report = asyncio.run(run_calibration(engine))
    assert report["case_count"] >= 20
    assert len(report["providers"]) == 2
    for provider in report["providers"]:
        assert 0 <= provider["accuracy"] <= 1
        assert provider["ece"] >= 0
        assert provider["brier"] >= 0
        assert provider["nll"] >= 0
        assert len(provider["buckets"]) == 5
