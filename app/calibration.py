from __future__ import annotations

import asyncio
import math
from typing import Any


CALIBRATION_CASES = [
    # AI Factory
    ("ai_factory_anomaly", "Rack inlet and HBM temperature rise together; branch flow is below minimum while CDU pump and valve demand are high.", "cooling_flow"),
    ("ai_factory_anomaly", "Rack power repeatedly hits the configured cap; temperatures and coolant flow remain normal.", "power"),
    ("ai_factory_anomaly", "CRC errors and link retries spike with throughput loss; thermal and power telemetry remain inside limits.", "network"),
    ("ai_factory_anomaly", "Performance loss appears only for one distributed training topology; infrastructure telemetry remains normal.", "workload"),
    ("ai_factory_anomaly", "Persistent GPU Xid faults remain on one node after workload migration; network, power and cooling are normal.", "hardware"),
    ("ai_factory_anomaly", "Sparse conflicting telemetry with no repeatable thermal, power, network, workload or hardware signature.", "unknown"),
    ("ai_factory_anomaly", "Low rack coolant flow and hot inlet correlate with throttling; fabric errors remain negligible.", "cooling_flow"),
    ("ai_factory_anomaly", "PDU event shows voltage sag and rack power oscillation without a thermal excursion.", "power"),
    ("ai_factory_anomaly", "Retransmits and fabric congestion align with job slowdown while GPU temperatures stay stable.", "network"),
    ("ai_factory_anomaly", "A scheduler placement change reproduces slowdown across healthy racks with normal infrastructure signals.", "workload"),
    ("ai_factory_anomaly", "A single GPU reports repeated ECC/Xid events independent of workload and rack conditions.", "hardware"),
    ("ai_factory_anomaly", "Symptoms are intermittent and mutually inconsistent across sensors; evidence is insufficient.", "unknown"),
    # Manufacturing / NCR
    ("aerospace_ncr", "Vibration rises with tool-cycle count and adjacent holes trend oversize using the same spindle and tool.", "tool_wear_spindle"),
    ("aerospace_ncr", "Deviation occurs only with one fixture setup; tool health and measurement repeatability are normal.", "setup"),
    ("aerospace_ncr", "Only one incoming material lot correlates with the defect; machine and gage evidence are stable.", "material"),
    ("aerospace_ncr", "Independent re-measurement disagrees with the original gage and the gage repeatability study is poor.", "measurement"),
    ("aerospace_ncr", "A new NC program revision changes the relevant process parameter immediately before defects begin.", "programming"),
    ("aerospace_ncr", "Evidence is sparse and conflicting across machine, material, measurement and program sources.", "unknown"),
    ("aerospace_ncr", "High tool cycles, growing spindle vibration and clustered oversize features point to progressive wear.", "tool_wear_spindle"),
    ("aerospace_ncr", "Defects track one clamp orientation and disappear after fixture correction.", "setup"),
    ("aerospace_ncr", "Incoming inspection shows the affected lot outside a material property control band.", "material"),
    ("aerospace_ncr", "CMM drift is confirmed by reference artifact checks; production process signals are stable.", "measurement"),
    ("aerospace_ncr", "The defect begins exactly after an unapproved parameter-table revision and clears when reverted.", "programming"),
    ("aerospace_ncr", "No source establishes a dominant cause and two hypotheses remain equally plausible.", "unknown"),
]


def _question(scenario: str) -> dict[str, Any]:
    if scenario == "ai_factory_anomaly":
        return {
            "primary_cause": {
                "type": "choice",
                "instructions": "Select the best supported primary cause.",
                "criteria": {
                    "cooling_flow": "Cooling distribution, CDU balance, branch restriction or low flow",
                    "power": "Rack/PDU power cap, delivery or power-quality issue",
                    "network": "Fabric congestion, errors, retries or network bottleneck",
                    "workload": "Workload shape, topology or scheduler behavior",
                    "hardware": "GPU, node or rack hardware fault",
                    "unknown": "Evidence is insufficient or materially conflicting",
                },
            }
        }
    return {
        "primary_cause": {
            "type": "choice",
            "instructions": "Select the best supported primary cause.",
            "criteria": {
                "tool_wear_spindle": "Progressive tool wear, vibration growth or spindle drift",
                "setup": "Fixture or manufacturing setup issue",
                "material": "Incoming material or supplier-related issue",
                "measurement": "Inspection, gage or measurement-system issue",
                "programming": "Program revision or process-parameter issue",
                "unknown": "Evidence is insufficient or materially conflicting",
            },
        }
    }


async def run_calibration(engine) -> dict[str, Any]:
    async def evaluate_provider(name: str, client):
        rows = []
        # Small smoke-test corpus: intentionally not positioned as production validation.
        for scenario, text, truth in CALIBRATION_CASES:
            response = await client.evaluate(
                {"observation": text, "scenario": scenario},
                _question(scenario),
                scenario=scenario,
            )
            ans = (response.answers or {}).get("primary_cause", {})
            probs = {str(k): float(v) for k, v in (ans.get("probabilities") or {}).items()}
            pred = str(ans.get("choice", "unknown"))
            conf = float(ans.get("confidence", max(probs.values(), default=0.0)) or 0.0)
            rows.append({
                "truth": truth,
                "prediction": pred,
                "confidence": conf,
                "probabilities": probs,
                "correct": pred == truth,
            })
        return _summarize(name, rows, live=client.live)

    jev, classifier = await asyncio.gather(
        evaluate_provider("Jev", engine.jev),
        evaluate_provider("Open zero-shot", engine.classifier),
    )
    return {
        "case_count": len(CALIBRATION_CASES),
        "note": "Small labeled smoke test. Use 300+ representative labeled production examples before making deployment decisions.",
        "providers": [jev, classifier],
    }


def _summarize(name: str, rows: list[dict[str, Any]], live: bool) -> dict[str, Any]:
    n = max(1, len(rows))
    accuracy = sum(1 for r in rows if r["correct"]) / n

    brier_terms = []
    nll_terms = []
    for r in rows:
        labels = set(r["probabilities"].keys()) | {r["truth"]}
        if not labels:
            continue
        k = max(1, len(labels))
        brier_terms.append(sum(
            (float(r["probabilities"].get(label, 0.0)) - (1.0 if label == r["truth"] else 0.0)) ** 2
            for label in labels
        ) / k)
        p_truth = max(1e-9, min(1.0, float(r["probabilities"].get(r["truth"], 0.0))))
        nll_terms.append(-math.log(p_truth))

    buckets = []
    ece = 0.0
    for low in [0.0, 0.2, 0.4, 0.6, 0.8]:
        high = low + 0.2
        members = [r for r in rows if (low <= r["confidence"] < high) or (high >= 1.0 and r["confidence"] <= 1.0)]
        if not members:
            buckets.append({"low": low, "high": high, "count": 0, "confidence": None, "accuracy": None})
            continue
        avg_conf = sum(r["confidence"] for r in members) / len(members)
        avg_acc = sum(1 for r in members if r["correct"]) / len(members)
        ece += (len(members) / n) * abs(avg_conf - avg_acc)
        buckets.append({
            "low": low,
            "high": high,
            "count": len(members),
            "confidence": round(avg_conf, 4),
            "accuracy": round(avg_acc, 4),
        })

    return {
        "name": name,
        "mode": "live" if live else "simulated",
        "warning": None if live else "SIMULATED ADAPTER — these are interface/logic test numbers, not model benchmark evidence.",
        "accuracy": round(accuracy, 4),
        "ece": round(ece, 4),
        "brier": round(sum(brier_terms) / max(1, len(brier_terms)), 4),
        "nll": round(sum(nll_terms) / max(1, len(nll_terms)), 4),
        "buckets": buckets,
    }
