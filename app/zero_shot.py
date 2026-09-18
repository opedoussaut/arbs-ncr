from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ZeroShotStats:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


@dataclass
class ZeroShotResponse:
    model: str
    answers: dict[str, Any]
    stats: ZeroShotStats
    live: bool


class ZeroShotClient:
    """Open zero-shot control lane.

    Default is deterministic simulation so the PoC stays lightweight.
    Set ZERO_SHOT_MODE=local and install transformers + torch to run an
    actual Hugging Face zero-shot classifier such as facebook/bart-large-mnli.
    """

    def __init__(self):
        self.mode = os.getenv("ZERO_SHOT_MODE", "simulated").strip().lower()
        self.model = os.getenv("ZERO_SHOT_MODEL", "facebook/bart-large-mnli").strip()
        self._pipeline = None

    @property
    def live(self) -> bool:
        return self.mode == "local"

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "ZERO_SHOT_MODE=local requires optional packages: transformers and torch"
            ) from exc
        self._pipeline = pipeline("zero-shot-classification", model=self.model)
        return self._pipeline

    async def evaluate(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
        *,
        scenario: str,
    ) -> ZeroShotResponse:
        started = time.perf_counter()
        state_text = json.dumps(state, default=str, separators=(",", ":"))

        if not self.live:
            await asyncio.sleep(0.025)
            answers = self._simulate_answers(state_text, scenario)
            inp = max(1, len(state_text) // 4)
            out = max(1, len(json.dumps(answers)) // 4)
            return ZeroShotResponse(
                model="zero-shot-simulated",
                answers=answers,
                stats=ZeroShotStats(
                    input_tokens=inp,
                    output_tokens=out,
                    calls=1,
                    cost_usd=0.0,
                    latency_ms=max(90, int((time.perf_counter() - started) * 1000)),
                ),
                live=False,
            )

        # transformers pipeline is synchronous; keep FastAPI responsive.
        answers = await asyncio.to_thread(self._evaluate_local, state_text, questions)
        return ZeroShotResponse(
            model=self.model,
            answers=answers,
            stats=ZeroShotStats(
                input_tokens=max(1, len(state_text) // 4),
                output_tokens=max(1, len(json.dumps(answers)) // 4),
                calls=1,
                cost_usd=0.0,
                latency_ms=int((time.perf_counter() - started) * 1000),
            ),
            live=True,
        )

    def _evaluate_local(self, state_text: str, questions: dict[str, Any]) -> dict[str, Any]:
        clf = self._ensure_pipeline()
        answers: dict[str, Any] = {}
        for name, question in questions.items():
            qtype = question.get("type")
            if qtype == "choice":
                criteria = question.get("criteria") or {}
                labels = list(criteria.keys())
                hypotheses = [criteria[k] for k in labels]
                r = clf(state_text, hypotheses, multi_label=False)
                score_by_hypothesis = dict(zip(r["labels"], r["scores"]))
                probs = {label: float(score_by_hypothesis.get(criteria[label], 0.0)) for label in labels}
                choice = max(probs, key=probs.get)
                answers[name] = {
                    "type": "choice",
                    "choice": choice,
                    "confidence": probs[choice],
                    "probabilities": probs,
                }
            elif qtype == "score":
                levels = list(question.get("criteria") or [])
                r = clf(state_text, levels, multi_label=False)
                p = dict(zip(r["labels"], r["scores"]))
                probs = {str(i): float(p.get(level, 0.0)) for i, level in enumerate(levels)}
                expected = sum(float(probs[str(i)]) * i for i in range(len(levels)))
                answers[name] = {
                    "type": "score",
                    "score": expected,
                    "confidence": max(probs.values()) if probs else 0.0,
                    "probabilities": probs,
                }
            elif qtype == "noul":
                criteria = question.get("criteria") or {}
                yes = criteria.get("true") or question.get("instructions") or "yes"
                no = criteria.get("false") or f"not: {yes}"
                r = clf(state_text, [yes, no], multi_label=False)
                p = dict(zip(r["labels"], r["scores"]))
                answers[name] = {"type": "noul", "noul": float(p.get(yes, 0.5))}
        return answers

    @staticmethod
    def _simulate_answers(state_text: str, scenario: str) -> dict[str, Any]:
        # Stable jitter prevents the open control lane from mirroring Jev exactly.
        h = int(hashlib.sha256(state_text.encode()).hexdigest()[:8], 16)
        jitter = ((h % 17) - 8) / 100.0
        if scenario == "ai_factory_anomaly":
            conf = min(0.92, max(0.66, 0.82 + jitter))
            ambiguity = min(0.46, max(0.12, 0.29 - jitter / 2))
            return {
                "primary_cause": {
                    "type": "choice",
                    "choice": "cooling_flow",
                    "confidence": conf,
                    "probabilities": {
                        "cooling_flow": conf,
                        "power": (1-conf)*0.24,
                        "network": (1-conf)*0.22,
                        "workload": (1-conf)*0.19,
                        "hardware": (1-conf)*0.15,
                        "unknown": (1-conf)*0.20,
                    },
                },
                "severity": {"type": "score", "score": 2.03, "confidence": 0.72},
                "requires_frontier_reasoning": {"type": "noul", "noul": ambiguity},
                "human_intervention_required": {"type": "noul", "noul": 0.96},
            }
        conf = min(0.91, max(0.64, 0.80 + jitter))
        ambiguity = min(0.49, max(0.13, 0.31 - jitter / 2))
        return {
            "primary_cause": {
                "type": "choice",
                "choice": "tool_wear_spindle",
                "confidence": conf,
                "probabilities": {
                    "tool_wear_spindle": conf,
                    "setup": (1-conf)*0.25,
                    "material": (1-conf)*0.17,
                    "measurement": (1-conf)*0.18,
                    "programming": (1-conf)*0.18,
                    "unknown": (1-conf)*0.22,
                },
            },
            "severity": {"type": "score", "score": 2.18, "confidence": 0.70},
            "requires_frontier_reasoning": {"type": "noul", "noul": ambiguity},
            "engineering_review_required": {"type": "noul", "noul": 0.97},
        }


def confidence_of(answer: dict[str, Any]) -> float:
    if not answer:
        return 0.0
    if answer.get("confidence") is not None:
        return float(answer["confidence"])
    if answer.get("type") == "noul":
        p = float(answer.get("noul", 0.5))
        return max(p, 1.0 - p)
    probabilities = answer.get("probabilities") or {}
    return max((float(v) for v in probabilities.values()), default=0.0)
