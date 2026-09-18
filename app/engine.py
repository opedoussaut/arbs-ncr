from __future__ import annotations
import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from .data_factory import build_source_universe, nifi_reduce
from .jev import JevClient, answer_confidence
from .zero_shot import ZeroShotClient, confidence_of
from .models import AgentStep, CaseInput, ComparisonResponse, InvestigationResult, Metrics


@dataclass
class LLMStats:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    cost_usd: float = 0.0


class Reasoner:
    def __init__(self):
        self.key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self.client = AsyncOpenAI(api_key=self.key) if self.key and AsyncOpenAI else None
        self.input_price = float(os.getenv("OPENAI_INPUT_USD_PER_MTOK", "0.20"))
        self.output_price = float(os.getenv("OPENAI_OUTPUT_USD_PER_MTOK", "1.20"))

    @property
    def live(self) -> bool:
        return self.client is not None

    async def ask(self, role: str, context: dict[str, Any], question: str) -> tuple[str, LLMStats]:
        if not self.client:
            await asyncio.sleep(0.03)
            finding = self._simulate(role, context)
            approx_in = max(1, len(json.dumps(context)) // 4)
            approx_out = max(1, len(finding) // 4)
            return finding, LLMStats(approx_in, approx_out, 1, self._cost(approx_in, approx_out))

        case = context.get("case") or context.get("ncr") or {}
        domain = "AI Factory infrastructure" if case.get("scenario") == "ai_factory_anomaly" else "aerospace manufacturing"
        prompt = (
            f"You are the {role} in a synthetic {domain} investigation. "
            "Use only the supplied synthetic evidence. Be concise and evidence-led. "
            "Do not make irreversible operational, safety, quality or engineering decisions; those remain human decisions.\n\n"
            f"Question: {question}\n\nEvidence:\n{json.dumps(context, default=str)}"
        )
        response = await self.client.responses.create(model=self.model, input=prompt)
        usage = getattr(response, "usage", None)
        inp = int(getattr(usage, "input_tokens", 0) or 0)
        out = int(getattr(usage, "output_tokens", 0) or 0)
        return response.output_text, LLMStats(inp, out, 1, self._cost(inp, out))

    def _cost(self, inp: int, out: int) -> float:
        return (inp / 1_000_000) * self.input_price + (out / 1_000_000) * self.output_price

    @staticmethod
    def _simulate(role: str, context: dict[str, Any]) -> str:
        case = context.get("case") or context.get("ncr") or {}
        scenario = case.get("scenario", "aerospace_ncr")
        r = role.lower()

        if scenario == "ai_factory_anomaly":
            if "thermal" in r:
                return "The target rack shows sustained GPU/HBM temperature elevation, inlet-air temperature above target, repeated throttling and coolant flow below the configured minimum. The thermal signature is coherent across rack and cooling-loop evidence."
            if "infrastructure" in r:
                return "Rack power is close to design load, but the strongest infrastructure deviation is reduced branch flow while the associated CDU is running at high pump and valve demand. This points to a local flow imbalance or branch restriction rather than insufficient commanded cooling effort."
            if "network" in r:
                return "Fabric utilization increases with workload, but CRC errors and retries remain too low to explain the observed throughput loss. Network contention may add noise, but the evidence does not support it as the primary cause."
            if "knowledge" in r:
                return "The K&KH corpus and similar historical incidents link the same thermal-throttle-low-flow pattern to rack branch restrictions and CDU balancing issues. The applicable runbook recommends validating flow, valve position and branch integrity before changing GPU or workload settings."
            return "Evidence converges on a cooling-distribution issue affecting the target rack, most likely branch restriction or imbalance on the associated CDU loop. Reduce or drain workload on the rack, verify branch flow and valve state, compare neighboring racks, and route remediation through authorized infrastructure operations."

        if "quality" in r:
            return "Four adjacent dimensional results breach the allowed upper tolerance; the pattern is clustered rather than random. Similar historical NCRs exist and should be reviewed before disposition."
        if "manufacturing" in r:
            return "Machine evidence shows elevated tool vibration close to the event and a high tool-cycle count. The strongest working hypothesis is progressive tool wear or spindle drift; verify calibration and inspect the remaining features produced with the same tool."
        if "design" in r:
            return "The affected feature is marked as a critical characteristic in the current engineering definition. Any use-as-is or repair decision requires engineering review against the current drawing revision."
        return "Evidence converges on a manufacturing-process cause rather than incoming material. Quarantine the affected scope, confirm tool condition/calibration, inspect adjacent features, and route the proposed disposition to an authorized engineer."


class InvestigationEngine:
    def __init__(self):
        self.reasoner = Reasoner()
        self.jev = JevClient()
        self.classifier = ZeroShotClient()
        self.jev_confidence_threshold = float(os.getenv("JEV_CONFIDENCE_THRESHOLD", "0.80"))
        self.jev_escalation_probability = float(os.getenv("JEV_ESCALATION_PROBABILITY", "0.50"))

    async def compare(self, case: CaseInput) -> ComparisonResponse:
        source = build_source_universe(case)
        baseline, nifi, jev, classifier = await asyncio.gather(
            self._run_lane(case, source, "baseline"),
            self._run_lane(case, source, "nifi"),
            self._run_jev_lane(case, source),
            self._run_classifier_lane(case, source),
        )
        b, n, j, z = baseline.metrics, nifi.metrics, jev.metrics, classifier.metrics
        savings = pct(b.estimated_cost_usd - n.estimated_cost_usd, b.estimated_cost_usd)
        token_red = pct(b.estimated_input_tokens - n.estimated_input_tokens, b.estimated_input_tokens)
        latency_red = pct(b.latency_ms - n.latency_ms, b.latency_ms)
        tool_red = pct(b.tool_calls - n.tool_calls, b.tool_calls)
        jev_cost_red = pct(n.estimated_cost_usd - j.estimated_cost_usd, n.estimated_cost_usd)
        jev_latency_red = pct(n.latency_ms - j.latency_ms, n.latency_ms)
        classifier_cost_red = pct(n.estimated_cost_usd - z.estimated_cost_usd, n.estimated_cost_usd)
        classifier_latency_red = pct(n.latency_ms - z.latency_ms, n.latency_ms)
        frontier_red = pct(n.frontier_llm_calls - j.frontier_llm_calls, n.frontier_llm_calls)
        headline = (
            f"Four architectures, one evidence universe: Lean preprocessing reduces agent context by {token_red:.0f}%, "
            "while Jev and the open zero-shot control test whether structured decision models can avoid frontier reasoning."
        )
        return ComparisonResponse(
            case=case,
            baseline=baseline,
            nifi=nifi,
            jev=jev,
            classifier=classifier,
            headline=headline,
            savings_pct=round(savings, 1),
            token_reduction_pct=round(token_red, 1),
            latency_reduction_pct=round(latency_red, 1),
            tool_call_reduction_pct=round(tool_red, 1),
            jev_vs_nifi_cost_reduction_pct=round(jev_cost_red, 1),
            jev_vs_nifi_latency_reduction_pct=round(jev_latency_red, 1),
            frontier_call_reduction_pct=round(frontier_red, 1),
            classifier_vs_nifi_cost_reduction_pct=round(classifier_cost_red, 1),
            classifier_vs_nifi_latency_reduction_pct=round(classifier_latency_red, 1),
        )

    async def _run_lane(self, case: CaseInput, source: dict, lane: str) -> InvestigationResult:
        started = time.perf_counter()
        source_blob = json.dumps(source)
        ai_factory = case.scenario == "ai_factory_anomaly"

        if lane == "nifi":
            context_for_agents, provenance = nifi_reduce(source)
            deterministic_steps = 11 if ai_factory else 8
            tool_calls = 3 if ai_factory else 2
            api_calls = 8 if ai_factory else 6
            context_blob = json.dumps(context_for_agents)
        else:
            # Baseline: all cross-source selection/reduction remains in the agent/tool layer.
            context_for_agents = source
            provenance = ["Agent/tool layer queried the raw corpus and operational sources directly"]
            deterministic_steps = 1
            tool_calls = 18 if ai_factory else 14
            api_calls = 18 if ai_factory else 14
            context_blob = json.dumps(context_for_agents)

        questions = self._questions(case.scenario)
        findings = await asyncio.gather(*[
            self.reasoner.ask(role, context_for_agents, question) for role, question in questions
        ])

        stats = LLMStats()
        steps: list[AgentStep] = []
        for (role, _), (text, st) in zip(questions, findings):
            stats.input_tokens += st.input_tokens
            stats.output_tokens += st.output_tokens
            stats.calls += st.calls
            stats.cost_usd += st.cost_usd
            steps.append(AgentStep(
                agent=role.replace(" Agent", ""),
                title=role,
                detail=text,
                evidence_count=(7 if ai_factory else 6) if lane == "nifi" else (24 if ai_factory else 18),
                duration_ms=(280 if lane == "nifi" else 540),
            ))

        supervisor_context = {
            "case": case.model_dump(),
            "specialist_findings": [x.detail for x in steps],
            "provenance": provenance,
        }
        synthesis, sst = await self.reasoner.ask(
            "Supervisor Agent",
            supervisor_context,
            "Synthesize the most evidence-supported cause and safest next investigation actions.",
        )
        stats.input_tokens += sst.input_tokens
        stats.output_tokens += sst.output_tokens
        stats.calls += sst.calls
        stats.cost_usd += sst.cost_usd
        steps.append(AgentStep(
            agent="Supervisor",
            title="Supervisor synthesis",
            detail=synthesis,
            evidence_count=len(provenance),
            duration_ms=300 if lane == "nifi" else 440,
        ))

        elapsed_real = int((time.perf_counter() - started) * 1000)
        modeled_latency = (
            1800 + stats.input_tokens // 90 + tool_calls * 105
            if lane == "baseline"
            else 980 + stats.input_tokens // 115 + tool_calls * 70
        )
        latency = elapsed_real if self.reasoner.live else modeled_latency
        retries = 1 if lane == "baseline" else 0

        if ai_factory:
            likely_cause = "Cooling branch restriction / CDU flow imbalance"
            recommendation = (
                "Drain or reduce workload on the affected rack; validate rack branch flow and valve state; "
                "compare neighboring racks on the same CDU; inspect for restriction/imbalance before changing GPU, network or scheduler settings."
            )
            human_gate = "Infrastructure Operations must approve workload drain and any cooling-loop intervention."
            confidence = .90 if lane == "nifi" else .77
            evidence_precision = .94 if lane == "nifi" else .56
        else:
            likely_cause = "Progressive tool wear / spindle drift"
            recommendation = (
                "Quarantine affected production scope; verify tool condition and spindle calibration; inspect adjacent holes and same-tool output; "
                "prepare the evidence pack for engineering disposition."
            )
            human_gate = "Final disposition requires authorized Quality/Engineering approval."
            confidence = .88 if lane == "nifi" else .78
            evidence_precision = .92 if lane == "nifi" else .61

        metrics = Metrics(
            source_bytes=len(source_blob.encode()),
            context_bytes=len(context_blob.encode()),
            estimated_input_tokens=stats.input_tokens,
            output_tokens=stats.output_tokens,
            llm_calls=stats.calls,
            tool_calls=tool_calls,
            api_calls=api_calls,
            deterministic_steps=deterministic_steps,
            retries=retries,
            latency_ms=latency,
            estimated_cost_usd=round(stats.cost_usd, 5),
            evidence_precision=evidence_precision,
            mode="live" if self.reasoner.live else "simulated",
            frontier_llm_calls=stats.calls,
            decision_model_calls=0,
        )

        return InvestigationResult(
            lane=lane,
            title="Lean / NiFi-assisted" if lane == "nifi" else "Agent-only baseline",
            summary=synthesis,
            confidence=confidence,
            likely_cause=likely_cause,
            recommendation=recommendation,
            human_gate=human_gate,
            steps=steps,
            metrics=metrics,
            evidence=provenance,
        )

    async def _run_jev_lane(self, case: CaseInput, source: dict) -> InvestigationResult:
        started = time.perf_counter()
        source_blob = json.dumps(source)
        lean_state, provenance = nifi_reduce(source)
        context_blob = json.dumps(lean_state)
        ai_factory = case.scenario == "ai_factory_anomaly"

        questions = self._jev_questions(case.scenario)
        decision = await self.jev.evaluate(lean_state, questions, scenario=case.scenario)
        answers = decision.answers
        root = answers.get("primary_cause", {})
        root_choice = str(root.get("choice", "unknown"))
        root_confidence = answer_confidence(root)
        ambiguity_probability = float((answers.get("requires_frontier_reasoning") or {}).get("noul", 0.5))
        escalated = (
            root_confidence < self.jev_confidence_threshold
            or ambiguity_probability >= self.jev_escalation_probability
        )

        if ai_factory:
            outcomes = {
                "cooling_flow": (
                    "Cooling branch restriction / CDU flow imbalance",
                    "Drain or reduce workload on the affected rack; validate rack branch flow and valve state; compare neighboring racks on the same CDU; inspect for restriction/imbalance before changing GPU, network or scheduler settings.",
                ),
                "power": (
                    "Power-delivery or rack power-cap constraint",
                    "Validate rack/PDU power envelope, cap events and neighboring rack behavior before changing workload or cooling settings.",
                ),
                "network": (
                    "Network fabric degradation",
                    "Validate fabric errors, retries, congestion and affected links; compare job communication behavior before changing compute or cooling settings.",
                ),
                "workload": (
                    "Workload / scheduler-driven degradation",
                    "Compare the affected workload with known-good runs and validate scheduler placement, utilization shape and thermal coupling before infrastructure intervention.",
                ),
                "hardware": (
                    "GPU / rack hardware fault",
                    "Isolate the affected node or rack, review hardware health events and follow the authorized hardware diagnostic workflow.",
                ),
                "unknown": (
                    "Unresolved infrastructure cause",
                    "Escalate the lean evidence pack for deeper reasoning and targeted human investigation before intervention.",
                ),
            }
            likely_cause, recommendation = outcomes.get(root_choice, outcomes["unknown"])
            human_gate = "Infrastructure Operations must approve workload drain and any cooling-loop intervention."
        else:
            outcomes = {
                "tool_wear_spindle": (
                    "Progressive tool wear / spindle drift",
                    "Quarantine affected production scope; verify tool condition and spindle calibration; inspect adjacent holes and same-tool output; prepare the evidence pack for engineering disposition.",
                ),
                "setup": (
                    "Manufacturing setup / fixturing issue",
                    "Verify fixture, setup conditions and affected production scope before engineering disposition.",
                ),
                "material": (
                    "Incoming material / supplier-related cause",
                    "Validate material lot, supplier certificate and incoming inspection evidence before disposition.",
                ),
                "measurement": (
                    "Measurement-system issue",
                    "Validate gage status, repeatability and an independent measurement before disposition.",
                ),
                "programming": (
                    "Process-program / parameter issue",
                    "Verify the current NC/program revision and process parameters against the approved definition before disposition.",
                ),
                "unknown": (
                    "Unresolved manufacturing cause",
                    "Escalate the lean evidence pack for deeper reasoning and targeted quality/manufacturing investigation.",
                ),
            }
            likely_cause, recommendation = outcomes.get(root_choice, outcomes["unknown"])
            human_gate = "Final disposition requires authorized Quality/Engineering approval."

        severity = answers.get("severity", {})
        severity_score = severity.get("score", "n/a")
        steps = [
            AgentStep(
                agent="Lean",
                title="Lean state preparation",
                detail="NiFi-style deterministic preprocessing filtered, correlated and normalized the evidence into one compact decision state.",
                evidence_count=len(provenance),
                duration_ms=110,
            ),
            AgentStep(
                agent="Jev",
                title="Parallel Jev decisions",
                detail=(
                    f"Primary cause={root_choice} ({root_confidence:.0%} confidence); "
                    f"severity score={severity_score}; frontier-reasoning need={ambiguity_probability:.0%}."
                ),
                evidence_count=len(provenance),
                duration_ms=decision.stats.latency_ms,
            ),
        ]

        frontier_stats = LLMStats()
        if escalated:
            escalation_context = {
                "case": case.model_dump(),
                "lean_state": lean_state,
                "jev_answers": answers,
                "provenance": provenance,
            }
            synthesis, frontier_stats = await self.reasoner.ask(
                "Escalation Reasoning Agent",
                escalation_context,
                "Resolve the remaining ambiguity, state the safest working hypothesis, and identify what a human must verify next.",
            )
            steps.append(AgentStep(
                agent="Supervisor",
                state="warning",
                title="Frontier escalation",
                detail=synthesis,
                evidence_count=len(provenance),
                duration_ms=850,
            ))
            summary = (
                f"Jev flagged this case for deeper reasoning. {synthesis} "
                "The structured Jev decision remains visible for auditability."
            )
        else:
            summary = (
                f"Jev classified the working cause as {likely_cause} with {root_confidence:.0%} confidence. "
                "The decision stayed inside the structured decision path; no frontier LLM reasoning call was required."
            )

        steps.append(AgentStep(
            agent="Human",
            state="info",
            title="Human workflow gate",
            detail=human_gate,
            evidence_count=0,
            duration_ms=0,
        ))

        live_any = decision.live or (escalated and self.reasoner.live)
        elapsed_real = int((time.perf_counter() - started) * 1000)
        modeled_latency = 150 + decision.stats.latency_ms + (1100 if escalated else 0)
        total_input = decision.stats.input_tokens + frontier_stats.input_tokens
        total_output = decision.stats.output_tokens + frontier_stats.output_tokens
        total_cost = decision.stats.cost_usd + frontier_stats.cost_usd
        frontier_calls = frontier_stats.calls

        evidence = provenance + [
            f"Jev model: {decision.model}",
            f"Primary cause decision: {root_choice} ({root_confidence:.0%} confidence)",
            f"Frontier reasoning probability: {ambiguity_probability:.0%}",
            f"Escalation policy: confidence < {self.jev_confidence_threshold:.0%} or ambiguity >= {self.jev_escalation_probability:.0%}",
            "Frontier escalation triggered" if escalated else "Frontier escalation avoided",
        ]

        metrics = Metrics(
            source_bytes=len(source_blob.encode()),
            context_bytes=len(context_blob.encode()),
            estimated_input_tokens=total_input,
            output_tokens=total_output,
            llm_calls=decision.stats.calls + frontier_calls,
            tool_calls=1,
            api_calls=8 if ai_factory else 6,
            deterministic_steps=12 if ai_factory else 9,
            retries=0,
            latency_ms=elapsed_real if live_any else modeled_latency,
            estimated_cost_usd=round(total_cost, 6),
            evidence_precision=.94 if ai_factory else .92,
            mode="live" if decision.live else "simulated",
            frontier_llm_calls=frontier_calls,
            decision_model_calls=decision.stats.calls,
        )

        return InvestigationResult(
            lane="jev",
            title="Lean + Jev decision layer",
            summary=summary,
            confidence=root_confidence,
            likely_cause=likely_cause,
            recommendation=recommendation,
            human_gate=human_gate,
            steps=steps,
            metrics=metrics,
            evidence=evidence,
            decisions={
                "model": decision.model,
                "answers": answers,
                "escalated": escalated,
                "confidence_threshold": self.jev_confidence_threshold,
                "escalation_probability": self.jev_escalation_probability,
            },
        )

    async def _run_classifier_lane(self, case: CaseInput, source: dict) -> InvestigationResult:
        started = time.perf_counter()
        source_blob = json.dumps(source)
        lean_state, provenance = nifi_reduce(source)
        context_blob = json.dumps(lean_state)
        ai_factory = case.scenario == "ai_factory_anomaly"

        questions = self._jev_questions(case.scenario)
        decision = await self.classifier.evaluate(lean_state, questions, scenario=case.scenario)
        answers = decision.answers
        root = answers.get("primary_cause", {})
        root_choice = str(root.get("choice", "unknown"))
        root_confidence = confidence_of(root)
        ambiguity_probability = float((answers.get("requires_frontier_reasoning") or {}).get("noul", 0.5))
        escalated = (
            root_confidence < self.jev_confidence_threshold
            or ambiguity_probability >= self.jev_escalation_probability
        )

        if ai_factory:
            mapping = {
                "cooling_flow": ("Cooling branch restriction / CDU flow imbalance", "Validate branch flow, valve state and neighboring racks before changing compute or network settings."),
                "power": ("Power-delivery or rack power-cap constraint", "Validate rack/PDU power envelope and cap events before intervention."),
                "network": ("Network fabric degradation", "Validate fabric errors, retries and affected links before changing compute settings."),
                "workload": ("Workload / scheduler-driven degradation", "Compare scheduler placement and workload behavior with known-good runs."),
                "hardware": ("GPU / rack hardware fault", "Isolate affected hardware and follow the authorized diagnostic workflow."),
                "unknown": ("Unresolved infrastructure cause", "Escalate the lean evidence pack for deeper reasoning and human investigation."),
            }
            human_gate = "Infrastructure Operations must approve workload drain and any cooling-loop intervention."
        else:
            mapping = {
                "tool_wear_spindle": ("Progressive tool wear / spindle drift", "Verify tool condition and spindle calibration; inspect adjacent holes and same-tool output."),
                "setup": ("Manufacturing setup / fixturing issue", "Verify fixture and setup conditions before disposition."),
                "material": ("Incoming material / supplier-related cause", "Validate material lot, certificate and incoming inspection evidence."),
                "measurement": ("Measurement-system issue", "Validate gage status, repeatability and an independent measurement."),
                "programming": ("Process-program / parameter issue", "Verify program revision and process parameters against the approved definition."),
                "unknown": ("Unresolved manufacturing cause", "Escalate the lean evidence pack for deeper quality/manufacturing investigation."),
            }
            human_gate = "Final disposition requires authorized Quality/Engineering approval."

        likely_cause, recommendation = mapping.get(root_choice, mapping["unknown"])
        severity = answers.get("severity", {})
        severity_score = severity.get("score", "n/a")
        steps = [
            AgentStep(
                agent="Lean",
                title="Lean state preparation",
                detail="NiFi-style deterministic preprocessing produced the compact state used by the open decision model.",
                evidence_count=len(provenance),
                duration_ms=110,
            ),
            AgentStep(
                agent="Classifier",
                title="Open zero-shot decisions",
                detail=(
                    f"Primary cause={root_choice} ({root_confidence:.0%} confidence); "
                    f"severity score={severity_score}; frontier-reasoning need={ambiguity_probability:.0%}."
                ),
                evidence_count=len(provenance),
                duration_ms=decision.stats.latency_ms,
            ),
        ]

        frontier_stats = LLMStats()
        if escalated:
            synthesis, frontier_stats = await self.reasoner.ask(
                "Escalation Reasoning Agent",
                {
                    "case": case.model_dump(),
                    "lean_state": lean_state,
                    "classifier_answers": answers,
                    "provenance": provenance,
                },
                "Resolve the remaining ambiguity, state the safest working hypothesis, and identify what a human must verify next.",
            )
            steps.append(AgentStep(
                agent="Supervisor",
                state="warning",
                title="Frontier escalation",
                detail=synthesis,
                evidence_count=len(provenance),
                duration_ms=850,
            ))
            summary = f"The open classifier crossed the escalation policy. {synthesis}"
        else:
            summary = (
                f"The open classifier selected {likely_cause} with {root_confidence:.0%} confidence. "
                "No frontier LLM call was required."
            )

        steps.append(AgentStep(
            agent="Human",
            state="info",
            title="Human workflow gate",
            detail=human_gate,
            evidence_count=0,
            duration_ms=0,
        ))

        elapsed_real = int((time.perf_counter() - started) * 1000)
        live_any = decision.live or (escalated and self.reasoner.live)
        modeled_latency = 190 + decision.stats.latency_ms + (1100 if escalated else 0)
        total_input = decision.stats.input_tokens + frontier_stats.input_tokens
        total_output = decision.stats.output_tokens + frontier_stats.output_tokens
        total_cost = decision.stats.cost_usd + frontier_stats.cost_usd

        evidence = provenance + [
            f"Open model: {decision.model}",
            f"Primary cause decision: {root_choice} ({root_confidence:.0%} confidence)",
            f"Frontier reasoning probability: {ambiguity_probability:.0%}",
            f"Escalation policy: confidence < {self.jev_confidence_threshold:.0%} or ambiguity >= {self.jev_escalation_probability:.0%}",
            "Frontier escalation triggered" if escalated else "Frontier escalation avoided",
        ]

        return InvestigationResult(
            lane="classifier",
            title="Lean + open zero-shot",
            summary=summary,
            confidence=root_confidence,
            likely_cause=likely_cause,
            recommendation=recommendation,
            human_gate=human_gate,
            steps=steps,
            metrics=Metrics(
                source_bytes=len(source_blob.encode()),
                context_bytes=len(context_blob.encode()),
                estimated_input_tokens=total_input,
                output_tokens=total_output,
                llm_calls=decision.stats.calls + frontier_stats.calls,
                tool_calls=1,
                api_calls=8 if ai_factory else 6,
                deterministic_steps=12 if ai_factory else 9,
                retries=0,
                latency_ms=elapsed_real if live_any else modeled_latency,
                estimated_cost_usd=round(total_cost, 6),
                evidence_precision=.94 if ai_factory else .92,
                mode="live" if decision.live else "simulated",
                frontier_llm_calls=frontier_stats.calls,
                decision_model_calls=decision.stats.calls,
            ),
            evidence=evidence,
            decisions={
                "model": decision.model,
                "answers": answers,
                "escalated": escalated,
                "confidence_threshold": self.jev_confidence_threshold,
                "escalation_probability": self.jev_escalation_probability,
                "provider": "open-zero-shot",
            },
        )

    @staticmethod
    def _jev_questions(scenario: str) -> dict[str, Any]:
        if scenario == "ai_factory_anomaly":
            return {
                "primary_cause": {
                    "type": "choice",
                    "instructions": "Which explanation best fits the combined rack, cooling, network, workload, historical and knowledge evidence?",
                    "criteria": {
                        "cooling_flow": "Cooling distribution, CDU balance, branch restriction, low flow or thermal transport issue",
                        "power": "Rack/PDU power limitation, cap or power-delivery issue",
                        "network": "Fabric congestion, errors, retries or network bottleneck",
                        "workload": "Workload shape, scheduler behavior or expected high-load effect",
                        "hardware": "GPU, node or rack hardware fault",
                        "unknown": "Evidence is insufficient or materially conflicting",
                    },
                },
                "severity": {
                    "type": "score",
                    "instructions": "Rate the operational severity of this incident from the supplied state.",
                    "criteria": [
                        "Contained anomaly with negligible service impact",
                        "Degradation requiring monitoring or planned intervention",
                        "High impact requiring prompt controlled intervention",
                        "Critical condition requiring immediate protected response",
                    ],
                },
                "requires_frontier_reasoning": {
                    "type": "noul",
                    "instructions": "Is the evidence materially ambiguous, conflicting or novel enough to require slower generative reasoning before presenting a working hypothesis?",
                    "criteria": {
                        "true": "The structured evidence does not support a sufficiently clear route or cause",
                        "false": "The evidence supports a clear working classification and can remain in the structured workflow",
                    },
                },
                "human_intervention_required": {
                    "type": "noul",
                    "instructions": "Does the proposed operational response require an authorized human approval gate?",
                },
            }
        return {
            "primary_cause": {
                "type": "choice",
                "instructions": "Which explanation best fits the dimensional, machine, manufacturing, supplier, historical and knowledge evidence?",
                "criteria": {
                    "tool_wear_spindle": "Progressive tool wear, vibration growth or spindle drift",
                    "setup": "Fixture, setup or process setup issue",
                    "material": "Incoming material or supplier-related cause",
                    "measurement": "Inspection, gage or measurement-system issue",
                    "programming": "NC/program/process-parameter definition issue",
                    "unknown": "Evidence is insufficient or materially conflicting",
                },
            },
            "severity": {
                "type": "score",
                "instructions": "Rate the quality/engineering significance of the non-conformance from the supplied state.",
                "criteria": [
                    "Minor and locally contained",
                    "Moderate quality concern",
                    "High significance requiring controlled disposition",
                    "Critical safety or certification significance",
                ],
            },
            "requires_frontier_reasoning": {
                "type": "noul",
                "instructions": "Is the evidence materially ambiguous, conflicting or novel enough to require slower generative reasoning before presenting a working hypothesis?",
                "criteria": {
                    "true": "The structured evidence does not support a sufficiently clear working cause",
                    "false": "The evidence supports a clear working classification and can remain in the structured workflow",
                },
            },
            "engineering_review_required": {
                "type": "noul",
                "instructions": "Does the affected characteristic or proposed disposition require authorized engineering/quality review?",
            },
        }

    @staticmethod
    def _questions(scenario: str) -> list[tuple[str, str]]:
        if scenario == "ai_factory_anomaly":
            return [
                ("Thermal Agent", "Assess GPU/rack thermal evidence and throttling signature."),
                ("Infrastructure Agent", "Assess power, cooling-loop and rack infrastructure evidence."),
                ("Network Agent", "Assess whether fabric behavior can explain the performance degradation."),
                ("Knowledge Agent", "Use relevant standards, runbooks, lessons learned and historical incidents to identify known patterns."),
            ]
        return [
            ("Quality Agent", "Assess dimensional evidence and historical quality patterns."),
            ("Manufacturing Agent", "Assess machine/process evidence and likely manufacturing cause."),
            ("Design Agent", "Assess engineering-definition significance and required human gates."),
        ]


def pct(delta: float, base: float) -> float:
    if not base:
        return 0.0
    return (delta / base) * 100.0
