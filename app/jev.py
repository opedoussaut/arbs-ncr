from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class JevStats:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


@dataclass
class JevResponse:
    model: str
    answers: dict[str, Any]
    stats: JevStats
    live: bool


class JevClient:
    """Small direct HTTP adapter for TypeSafe AI's System One / Jev API."""

    def __init__(self):
        self.key = os.getenv("TYPESAFE_API_KEY", "").strip()
        self.model = os.getenv("TYPESAFE_MODEL", "jev-latest").strip() or "jev-latest"
        base = os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai").rstrip("/")
        self.url = os.getenv("TYPESAFE_API_URL", f"{base}/v1/systemone").strip()
        self.timeout = float(os.getenv("TYPESAFE_TIMEOUT_SECONDS", "20"))
        self.input_price = float(os.getenv("TYPESAFE_INPUT_USD_PER_MTOK", "0.042"))

    @property
    def live(self) -> bool:
        return bool(self.key)

    async def evaluate(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
        *,
        scenario: str,
    ) -> JevResponse:
        started = time.perf_counter()
        if not self.key:
            await asyncio.sleep(0.02)
            answers = self._simulate_answers(scenario)
            input_tokens = max(1, len(json.dumps({"state": state, "questions": questions}, default=str)) // 4)
            output_tokens = max(1, len(json.dumps(answers)) // 4)
            latency_ms = max(70, int((time.perf_counter() - started) * 1000))
            return JevResponse(
                model="jev-simulated",
                answers=answers,
                stats=JevStats(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    calls=1,
                    cost_usd=self._cost(input_tokens),
                    latency_ms=latency_ms,
                ),
                live=False,
            )

        payload = {"model": self.model, "state": state, "questions": questions}
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()

        result = body.get("result", body) if isinstance(body, dict) else {}
        answers = result.get("answers", {})
        usage = result.get("usage", {}) or {}
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        return JevResponse(
            model=str(result.get("model", self.model)),
            answers=answers,
            stats=JevStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                calls=1,
                cost_usd=self._cost(input_tokens),
                latency_ms=int((time.perf_counter() - started) * 1000),
            ),
            live=True,
        )

    def _cost(self, input_tokens: int) -> float:
        return (input_tokens / 1_000_000) * self.input_price

    @staticmethod
    def _simulate_answers(scenario: str) -> dict[str, Any]:
        if scenario == "ai_factory_anomaly":
            return {
                "primary_cause": {"type": "choice", "choice": "cooling_flow", "confidence": 0.95, "probabilities": {"cooling_flow": 0.95, "power": 0.015, "network": 0.01, "workload": 0.01, "hardware": 0.005, "unknown": 0.01}},
                "severity": {"type": "score", "score": 2.12, "confidence": 0.88, "probabilities": {"0": 0.01, "1": 0.08, "2": 0.69, "3": 0.22}},
                "requires_frontier_reasoning": {"type": "noul", "noul": 0.12},
                "human_intervention_required": {"type": "noul", "noul": 0.98},
            }
        return {
            "primary_cause": {"type": "choice", "choice": "tool_wear_spindle", "confidence": 0.91, "probabilities": {"tool_wear_spindle": 0.91, "setup": 0.025, "material": 0.015, "measurement": 0.015, "programming": 0.015, "unknown": 0.02}},
            "severity": {"type": "score", "score": 2.28, "confidence": 0.86, "probabilities": {"0": 0.01, "1": 0.06, "2": 0.57, "3": 0.36}},
            "requires_frontier_reasoning": {"type": "noul", "noul": 0.18},
            "engineering_review_required": {"type": "noul", "noul": 0.99},
        }


def answer_confidence(answer: dict[str, Any]) -> float:
    if not answer:
        return 0.0
    if answer.get("confidence") is not None:
        return float(answer["confidence"])
    if answer.get("type") == "noul":
        p = float(answer.get("noul", 0.5))
        return max(p, 1.0 - p)
    probabilities = answer.get("probabilities") or {}
    if probabilities:
        return max(float(v) for v in probabilities.values())
    return 0.0
