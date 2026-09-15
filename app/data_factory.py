from __future__ import annotations
import hashlib
import random
from datetime import datetime, timedelta


def _rng(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def build_source_universe(case) -> dict:
    """Build a deterministic synthetic source universe for the selected domain."""
    if case.scenario == "ai_factory_anomaly":
        return _build_ai_factory_universe(case)
    return _build_aerospace_universe(case)


def _build_aerospace_universe(case) -> dict:
    rng = _rng(case.case_id)
    base = datetime.fromisoformat(case.timestamp)

    telemetry = []
    for i in range(360):
        ts = base - timedelta(minutes=180 - i)
        close = abs((ts - base).total_seconds()) <= 12 * 60
        telemetry.append({
            "timestamp": ts.isoformat(),
            "machine": case.asset if rng.random() < 0.72 else f"DRILL_CELL_{rng.randint(1, 12):02d}",
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
            "case_id": f"NCR-2026-{rng.randint(1000, 3999):06d}",
            "subject": case.subject if similar else rng.choice(["Fuselage frame", "Bracket", "Rib component", "Panel fitting"]),
            "process": case.process if similar else rng.choice(["Manual drilling", "Milling", "Fastening", "Inspection"]),
            "delta_mm": round(rng.uniform(.11, .24), 2) if similar else round(rng.uniform(-.4, .4), 2),
            "root_cause": "Tool wear / spindle drift" if similar and i < 5 else rng.choice(["Setup", "Material", "Measurement", "Programming", "Unknown"]),
            "disposition": rng.choice(["Use-as-is", "Repair", "Rework", "Scrap", "Engineering review"]),
        })

    inspections = []
    for i in range(72):
        adjacent = i < 12
        inspections.append({
            "feature": f"H-{i + 1:03d}",
            "subject": case.subject if adjacent else rng.choice([case.subject, "Adjacent assembly"]),
            "diameter_delta_mm": round(rng.gauss(.12 if adjacent else .0, .07), 3),
            "status": "out" if adjacent and i in {2, 4, 5, 8} else "in",
            "gage": rng.choice(["CMM-02", "BORE-05", "CMM-03"]),
        })

    operations = []
    for i in range(55):
        operations.append({
            "work_order": f"WO-{rng.randint(100000, 999999)}",
            "machine": case.asset if i < 8 else f"DRILL_CELL_{rng.randint(1, 12):02d}",
            "subject": case.subject if i < 9 else rng.choice(["Panel", "Frame", "Rib", "Bracket"]),
            "batch": case.batch if i < 5 else f"B-{rng.randint(10000, 99999)}",
            "tool_id": "T-8831" if i < 8 else f"T-{rng.randint(1000, 9999)}",
            "program_rev": "DRL-42.7" if i < 8 else f"DRL-{rng.randint(30, 48)}.{rng.randint(1, 9)}",
        })

    engineering = {
        "drawing_current": "DWG-WS-8842 Rev J",
        "drawing_superseded": ["DWG-WS-8842 Rev H", "DWG-WS-8842 Rev G"],
        "nominal_mm": 8.0,
        "upper_tolerance_mm": 0.10,
        "lower_tolerance_mm": -0.08,
        "critical_characteristic": True,
    }

    supplier = {
        "batch": case.batch,
        "material_lot": "AL-LT-26-9181",
        "certificate_status": "valid",
        "incoming_inspection": "accepted",
        "recent_supplier_escape": False,
    }

    corpus = [
        {"type": "work_instruction", "id": "WI-DRL-042", "title": "Automated drilling tool-life control", "relevance": "high"},
        {"type": "lesson_learned", "id": "LL-DRL-017", "title": "Vibration growth preceding oversize holes", "relevance": "high"},
        {"type": "quality_rule", "id": "QR-CC-004", "title": "Critical characteristic disposition gate", "relevance": "high"},
    ] + [
        {"type": "reference", "id": f"REF-{i:03d}", "title": rng.choice(["Drilling setup", "Material handling", "CMM guide", "Fastening standard"]), "relevance": "low"}
        for i in range(35)
    ]

    return {
        "case": case.model_dump(),
        "domain": "aerospace",
        "machine_telemetry": telemetry,
        "historic_cases": historic,
        "inspections": inspections,
        "operations": operations,
        "engineering_definition": engineering,
        "supplier": supplier,
        "knowledge_corpus": corpus,
    }


def _build_ai_factory_universe(case) -> dict:
    """Synthetic AI Factory incident: rack thermal excursion + GPU throttling under peak load."""
    rng = _rng(case.case_id)
    base = datetime.fromisoformat(case.timestamp)
    target_rack = case.asset
    pod = case.batch

    rack_telemetry = []
    for i in range(1440):
        ts = base - timedelta(seconds=(720 - i) * 15)
        close = abs((ts - base).total_seconds()) <= 35 * 60
        rack = target_rack if rng.random() < 0.38 else f"RACK-R{rng.randint(1, 48):02d}"
        affected = rack == target_rack and close
        rack_telemetry.append({
            "timestamp": ts.isoformat(),
            "rack": rack,
            "pod": pod if rack == target_rack else f"POD-{rng.randint(1, 6):02d}",
            "gpu_util_pct": round(min(100, max(0, rng.gauss(93 if affected else 76, 8))), 1),
            "gpu_temp_c": round(rng.gauss(81.5 if affected else 69.5, 2.4), 1),
            "hbm_temp_c": round(rng.gauss(88.0 if affected else 74.0, 2.8), 1),
            "inlet_air_c": round(rng.gauss(28.8 if affected else 22.0, 1.2), 1),
            "rack_power_kw": round(rng.gauss(118.0 if affected else 91.0, 5.5), 1),
            "coolant_supply_c": round(rng.gauss(24.8 if affected else 20.5, .7), 1),
            "coolant_return_c": round(rng.gauss(34.7 if affected else 29.0, 1.0), 1),
            "coolant_flow_lpm": round(rng.gauss(77 if affected else 96, 5.0), 1),
            "gpu_throttle_events": max(0, int(rng.gauss(14 if affected else .4, 3.0))),
        })

    network = []
    for i in range(620):
        ts = base - timedelta(seconds=(310 - i) * 30)
        close = abs((ts - base).total_seconds()) <= 40 * 60
        switch = "LEAF-27A" if i < 150 else f"LEAF-{rng.randint(1, 48):02d}{rng.choice(['A', 'B'])}"
        relevant = switch == "LEAF-27A" and close
        network.append({
            "timestamp": ts.isoformat(),
            "switch": switch,
            "pod": pod if switch == "LEAF-27A" else f"POD-{rng.randint(1, 6):02d}",
            "fabric_util_pct": round(min(100, max(0, rng.gauss(78 if relevant else 61, 10))), 1),
            "ecn_marks": max(0, int(rng.gauss(8 if relevant else 5, 3))),
            "crc_errors": max(0, int(rng.gauss(.2, .5))),
            "link_retries": max(0, int(rng.gauss(2 if relevant else 1.5, 1))),
        })

    cooling = []
    for i in range(360):
        ts = base - timedelta(minutes=180 - i)
        loop = "CDU-03" if i < 120 else f"CDU-{rng.randint(1, 8):02d}"
        close = abs((ts - base).total_seconds()) <= 45 * 60
        relevant = loop == "CDU-03" and close
        cooling.append({
            "timestamp": ts.isoformat(),
            "cdu": loop,
            "supply_temp_c": round(rng.gauss(24.6 if relevant else 20.4, .6), 1),
            "return_temp_c": round(rng.gauss(34.2 if relevant else 28.8, .8), 1),
            "flow_lpm": round(rng.gauss(1510 if relevant else 1810, 45), 1),
            "pump_speed_pct": round(rng.gauss(91 if relevant else 73, 4), 1),
            "valve_position_pct": round(rng.gauss(94 if relevant else 68, 6), 1),
        })

    dcim_events = []
    for i in range(130):
        relevant = i < 8
        dcim_events.append({
            "timestamp": (base - timedelta(minutes=rng.randint(0, 55) if relevant else rng.randint(60, 1440))).isoformat(),
            "asset": target_rack if relevant else f"RACK-R{rng.randint(1, 48):02d}",
            "type": rng.choice(["thermal", "power", "cooling", "capacity"]),
            "severity": "warning" if relevant else rng.choice(["info", "warning"]),
            "message": "Rack inlet temperature above operating target" if relevant and i < 5 else "Infrastructure event",
        })

    jobs = []
    for i in range(95):
        relevant = i < 12
        jobs.append({
            "job_id": f"JOB-{rng.randint(100000, 999999)}",
            "pod": pod if relevant else f"POD-{rng.randint(1, 6):02d}",
            "rack": target_rack if relevant else f"RACK-R{rng.randint(1, 48):02d}",
            "workload": rng.choice(["LLM pretraining", "fine-tuning", "inference burn-in", "distributed benchmark"]),
            "gpu_count": rng.choice([32, 64, 72]),
            "throughput_delta_pct": round(rng.gauss(-18 if relevant else 0, 3.5), 1),
            "collective_time_delta_pct": round(rng.gauss(3 if relevant else 0, 2.0), 1),
        })

    historical = []
    for i in range(58):
        similar = i < 7
        historical.append({
            "incident_id": f"AIF-INC-202{rng.randint(4, 6)}-{rng.randint(100, 999)}",
            "signature": "thermal-throttle-low-flow" if similar else rng.choice(["network-congestion", "power-cap", "gpu-xid", "firmware", "sensor-drift"]),
            "root_cause": "CDU flow imbalance / rack branch restriction" if similar and i < 5 else rng.choice(["Network tuning", "Power policy", "Firmware", "Unknown"]),
            "action": rng.choice(["Balance coolant loop", "Inspect branch valve", "Retune fabric", "Drain node", "Engineering review"]),
        })

    configuration = {
        "rack": target_rack,
        "pod": pod,
        "rack_profile": case.configuration,
        "cooling_loop": "CDU-03",
        "network_leaf": "LEAF-27A",
        "power_domain": "PDU-B3",
        "design_power_kw": 120,
        "target_inlet_air_c_max": 24.0,
        "target_coolant_supply_c_max": 22.0,
        "target_rack_flow_lpm_min": 90.0,
    }

    corpus = [
        {"type": "operating_standard", "id": "AIF-OPS-014", "title": "GPU rack thermal operating envelope", "tags": ["thermal", "gpu", "rack"], "relevance": "high"},
        {"type": "design_rule", "id": "AIF-COOL-008", "title": "Liquid cooling branch flow and CDU balancing", "tags": ["cooling", "cdu", "flow"], "relevance": "high"},
        {"type": "runbook", "id": "RB-THERM-006", "title": "GPU throttling investigation runbook", "tags": ["throttle", "temperature", "telemetry"], "relevance": "high"},
        {"type": "lesson_learned", "id": "LL-AIF-021", "title": "Rack throttling caused by branch restriction", "tags": ["cooling", "restriction", "rack"], "relevance": "high"},
        {"type": "architecture", "id": "ARCH-POD-003", "title": "AI Factory pod power, cooling and network topology", "tags": ["topology", "pod", "dependency"], "relevance": "high"},
    ] + [
        {
            "type": rng.choice(["standard", "runbook", "lesson", "architecture", "procedure"]),
            "id": f"K-AIF-{i:04d}",
            "title": rng.choice(["GPU firmware rollout", "Storage QoS", "Network fabric maintenance", "PDU inspection", "Cluster scheduling", "Spare inventory"]),
            "tags": [rng.choice(["firmware", "storage", "network", "power", "scheduler", "inventory"])],
            "relevance": "low",
        }
        for i in range(120)
    ]

    return {
        "case": case.model_dump(),
        "domain": "high-tech-ai-factory",
        "rack_telemetry": rack_telemetry,
        "network_telemetry": network,
        "cooling_telemetry": cooling,
        "dcim_events": dcim_events,
        "workload_jobs": jobs,
        "historic_cases": historical,
        "configuration": configuration,
        "knowledge_corpus": corpus,
    }


def nifi_reduce(source: dict) -> tuple[dict, list[str]]:
    """Deterministic stand-in for the NiFi preprocessing flow."""
    if source["case"]["scenario"] == "ai_factory_anomaly":
        return _reduce_ai_factory(source)
    return _reduce_aerospace(source)


def _reduce_aerospace(source: dict) -> tuple[dict, list[str]]:
    case = source["case"]
    base = datetime.fromisoformat(case["timestamp"])
    telemetry = [
        x for x in source["machine_telemetry"]
        if x["machine"] == case["asset"] and abs((datetime.fromisoformat(x["timestamp"]) - base).total_seconds()) <= 15 * 60
    ]
    historic = [x for x in source["historic_cases"] if x["subject"] == case["subject"] and x["process"] == case["process"]]
    inspections = [x for x in source["inspections"] if x["subject"] == case["subject"] and (x["status"] == "out" or abs(x["diameter_delta_mm"]) > .08)]
    operations = [x for x in source["operations"] if x["machine"] == case["asset"] or x["batch"] == case["batch"]]
    corpus = [x for x in source["knowledge_corpus"] if x["relevance"] == "high"]

    compact = {
        "case": case,
        "engineering_definition": source["engineering_definition"],
        "supplier": source["supplier"],
        "telemetry_summary": {
            "records": len(telemetry),
            "average_vibration_rms": round(sum(x["tool_vibration_rms"] for x in telemetry) / max(len(telemetry), 1), 3),
            "max_tool_cycles": max((x["tool_cycles"] for x in telemetry), default=0),
        },
        "similar_historic_cases": historic,
        "relevant_inspections": inspections,
        "relevant_operations": operations,
        "relevant_knowledge": corpus,
    }
    provenance = [
        f"Filtered machine telemetry to {len(telemetry)} records for {case['asset']} within ±15 min",
        f"Selected {len(historic)} historical NCRs matching subject + process",
        f"Selected {len(inspections)} dimensional results at/near tolerance boundary",
        f"Correlated {len(operations)} work-order records by machine/batch",
        f"Retrieved {len(corpus)} high-relevance K&KH corpus items",
        f"Resolved current engineering definition to {source['engineering_definition']['drawing_current']}",
    ]
    return compact, provenance


def _reduce_ai_factory(source: dict) -> tuple[dict, list[str]]:
    case = source["case"]
    base = datetime.fromisoformat(case["timestamp"])
    rack = case["asset"]
    pod = case["batch"]
    config = source["configuration"]

    rack_rows = [
        x for x in source["rack_telemetry"]
        if x["rack"] == rack and abs((datetime.fromisoformat(x["timestamp"]) - base).total_seconds()) <= 30 * 60
    ]
    network_rows = [
        x for x in source["network_telemetry"]
        if x["pod"] == pod and abs((datetime.fromisoformat(x["timestamp"]) - base).total_seconds()) <= 30 * 60
    ]
    cooling_rows = [
        x for x in source["cooling_telemetry"]
        if x["cdu"] == config["cooling_loop"] and abs((datetime.fromisoformat(x["timestamp"]) - base).total_seconds()) <= 45 * 60
    ]
    dcim = [x for x in source["dcim_events"] if x["asset"] == rack]
    jobs = [x for x in source["workload_jobs"] if x["rack"] == rack or x["pod"] == pod]
    historic = [x for x in source["historic_cases"] if x["signature"] == "thermal-throttle-low-flow"]
    corpus = [x for x in source["knowledge_corpus"] if x["relevance"] == "high"]

    avg = lambda rows, key: round(sum(x[key] for x in rows) / max(len(rows), 1), 2)
    compact = {
        "case": case,
        "configuration": config,
        "rack_summary": {
            "records": len(rack_rows),
            "avg_gpu_temp_c": avg(rack_rows, "gpu_temp_c"),
            "avg_hbm_temp_c": avg(rack_rows, "hbm_temp_c"),
            "avg_inlet_air_c": avg(rack_rows, "inlet_air_c"),
            "avg_rack_power_kw": avg(rack_rows, "rack_power_kw"),
            "avg_coolant_flow_lpm": avg(rack_rows, "coolant_flow_lpm"),
            "total_throttle_events": sum(x["gpu_throttle_events"] for x in rack_rows),
        },
        "cooling_summary": {
            "records": len(cooling_rows),
            "avg_supply_temp_c": avg(cooling_rows, "supply_temp_c"),
            "avg_flow_lpm": avg(cooling_rows, "flow_lpm"),
            "avg_pump_speed_pct": avg(cooling_rows, "pump_speed_pct"),
        },
        "network_summary": {
            "records": len(network_rows),
            "avg_fabric_util_pct": avg(network_rows, "fabric_util_pct"),
            "crc_errors": sum(x["crc_errors"] for x in network_rows),
            "link_retries": sum(x["link_retries"] for x in network_rows),
        },
        "relevant_dcim_events": dcim,
        "affected_jobs": jobs,
        "similar_historic_cases": historic,
        "relevant_knowledge": corpus,
    }
    provenance = [
        f"Filtered {len(rack_rows)} rack telemetry samples for {rack} within ±30 min",
        f"Correlated {len(cooling_rows)} cooling samples from {config['cooling_loop']} within ±45 min",
        f"Correlated {len(network_rows)} fabric samples for {pod}; isolated network errors from thermal symptoms",
        f"Selected {len(dcim)} DCIM events and {len(jobs)} affected workload records",
        f"Selected {len(historic)} historical incidents with thermal-throttle-low-flow signature",
        f"Retrieved {len(corpus)} relevant K&KH items from standards, runbooks, architecture and lessons learned",
        "Normalized rack, cooling and network timestamps into one evidence window",
        "Compared observed values with configured thermal and flow operating limits",
    ]
    return compact, provenance
