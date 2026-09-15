from __future__ import annotations
import hashlib
import random
from datetime import datetime, timedelta


def _rng(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def build_source_universe(ncr) -> dict:
    rng = _rng(ncr.ncr_id)
    base = datetime.fromisoformat(ncr.timestamp)

    telemetry = []
    for i in range(360):
        ts = base - timedelta(minutes=180-i)
        close = abs((ts - base).total_seconds()) <= 12 * 60
        telemetry.append({
            "timestamp": ts.isoformat(),
            "machine": ncr.machine if rng.random() < 0.72 else f"DRILL_CELL_{rng.randint(1,12):02d}",
            "spindle_rpm": round(rng.gauss(4850 if not close else 4760, 85), 1),
            "feed_mm_s": round(rng.gauss(3.20, .08), 3),
            "tool_vibration_rms": round(rng.gauss(.74 if not close else 1.18, .12), 3),
            "tool_cycles": rng.randint(280, 520) if close else rng.randint(20, 650),
            "coolant_pressure_bar": round(rng.gauss(5.8, .18), 2),
        })

    historic = []
    for i in range(48):
        similar = i < 7
        historic.append({
            "ncr_id": f"NCR-2026-{rng.randint(1000,3999):06d}",
            "part_family": ncr.part if similar else rng.choice(["Fuselage frame", "Bracket", "Rib component", "Panel fitting"]),
            "operation": ncr.operation if similar else rng.choice(["Manual drilling", "Milling", "Fastening", "Inspection"]),
            "delta_mm": round(rng.uniform(.11, .24), 2) if similar else round(rng.uniform(-.4, .4), 2),
            "root_cause": "Tool wear / spindle drift" if similar and i < 5 else rng.choice(["Setup", "Material", "Measurement", "Programming", "Unknown"]),
            "disposition": rng.choice(["Use-as-is", "Repair", "Rework", "Scrap", "Engineering review"]),
        })

    inspections = []
    for i in range(72):
        adjacent = i < 12
        inspections.append({
            "feature": f"H-{i+1:03d}",
            "part": ncr.part if adjacent else rng.choice([ncr.part, "Adjacent assembly"]),
            "diameter_delta_mm": round(rng.gauss(.12 if adjacent else .0, .07), 3),
            "status": "out" if adjacent and i in {2,4,5,8} else "in",
            "gage": rng.choice(["CMM-02", "BORE-05", "CMM-03"]),
        })

    operations = []
    for i in range(55):
        operations.append({
            "work_order": f"WO-{rng.randint(100000,999999)}",
            "machine": ncr.machine if i < 8 else f"DRILL_CELL_{rng.randint(1,12):02d}",
            "part": ncr.part if i < 9 else rng.choice(["Panel", "Frame", "Rib", "Bracket"]),
            "supplier_batch": ncr.supplier_batch if i < 5 else f"B-{rng.randint(10000,99999)}",
            "tool_id": "T-8831" if i < 8 else f"T-{rng.randint(1000,9999)}",
            "program_rev": "DRL-42.7" if i < 8 else f"DRL-{rng.randint(30,48)}.{rng.randint(1,9)}",
        })

    engineering = {
        "drawing_current": "DWG-WS-8842 Rev J",
        "drawing_superseded": ["DWG-WS-8842 Rev H", "DWG-WS-8842 Rev G"],
        "nominal_mm": 8.0,
        "upper_tolerance_mm": 0.10,
        "lower_tolerance_mm": -0.08,
        "special_process": False,
        "critical_characteristic": True,
    }

    supplier = {
        "batch": ncr.supplier_batch,
        "material_lot": "AL-LT-26-9181",
        "certificate_status": "valid",
        "incoming_inspection": "accepted",
        "recent_supplier_escape": False,
    }

    return {
        "ncr": ncr.model_dump(),
        "telemetry": telemetry,
        "historic_ncrs": historic,
        "inspections": inspections,
        "operations": operations,
        "engineering": engineering,
        "supplier": supplier,
    }


def nifi_reduce(source: dict) -> tuple[dict, list[str]]:
    """Deterministic stand-in for the NiFi flow used by the first UI slice."""
    ncr = source["ncr"]
    base = datetime.fromisoformat(ncr["timestamp"])

    telemetry = [
        x for x in source["telemetry"]
        if x["machine"] == ncr["machine"]
        and abs((datetime.fromisoformat(x["timestamp"]) - base).total_seconds()) <= 15 * 60
    ]
    historic = [
        x for x in source["historic_ncrs"]
        if x["part_family"] == ncr["part"] and x["operation"] == ncr["operation"]
    ]
    inspections = [
        x for x in source["inspections"]
        if x["part"] == ncr["part"] and (x["status"] == "out" or abs(x["diameter_delta_mm"]) > .08)
    ]
    operations = [
        x for x in source["operations"]
        if x["machine"] == ncr["machine"] or x["supplier_batch"] == ncr["supplier_batch"]
    ]

    avg_vibration = sum(x["tool_vibration_rms"] for x in telemetry) / max(len(telemetry), 1)
    max_cycles = max((x["tool_cycles"] for x in telemetry), default=0)

    compact = {
        "ncr": ncr,
        "engineering": source["engineering"],
        "supplier": source["supplier"],
        "telemetry_summary": {
            "records": len(telemetry),
            "average_vibration_rms": round(avg_vibration, 3),
            "max_tool_cycles": max_cycles,
            "spindle_rpm_min": min((x["spindle_rpm"] for x in telemetry), default=0),
            "spindle_rpm_max": max((x["spindle_rpm"] for x in telemetry), default=0),
        },
        "similar_historic_ncrs": historic,
        "relevant_inspections": inspections,
        "relevant_operations": operations,
    }
    provenance = [
        f"Filtered telemetry to {len(telemetry)} records for {ncr['machine']} within ±15 min",
        f"Selected {len(historic)} historical NCRs matching part family + operation",
        f"Selected {len(inspections)} dimensional results at/near tolerance boundary",
        f"Resolved engineering definition to {source['engineering']['drawing_current']}",
        f"Correlated {len(operations)} work-order records by machine/batch",
        "Validated supplier certificate and incoming inspection status",
    ]
    return compact, provenance
