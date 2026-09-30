"""
SoulCare Agentic AI — multi-step on-device companion agent.

The agent observes context, selects tools, executes them locally,
then synthesizes a supportive reply. No cloud required on Snapdragon builds.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("soulcare.agent")

SYSTEM_POLICY = (
    "You are SoulCare Agent: a compassionate, privacy-first mental health companion. "
    "Never diagnose. Never provide self-harm methods. Escalate crisis to 988 / local emergency help."
)


@dataclass
class AgentStep:
    thought: str
    tool: str
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


class SoulCareAgent:
    """
    Lightweight agentic loop:
      observe → plan tools → act → respond
    """

    def __init__(
        self,
        risk_predict: Callable[[str], dict[str, Any]],
        respond: Callable[..., dict[str, Any]],
    ) -> None:
        self.risk_predict = risk_predict
        self.respond = respond
        self.tools = {
            "assess_risk": self._tool_assess_risk,
            "mood_checkin": self._tool_mood_checkin,
            "breathing_guide": self._tool_breathing,
            "grounding_54321": self._tool_grounding,
            "helpline_resources": self._tool_helpline,
            "reflective_prompt": self._tool_reflective,
            "safety_plan_nudge": self._tool_safety_plan,
        }

    def run(
        self,
        user_text: str,
        history: list[dict[str, Any]] | None = None,
        tone: dict[str, Any] | None = None,
        vad: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        history = history or []
        steps: list[AgentStep] = []

        # 1) Always assess risk first
        steps.append(self._exec("assess_risk", {"text": user_text}, "Measure distress / crisis signals."))
        risk = steps[-1].output

        level = risk.get("risk_level") or risk.get("label") or "low"
        planned = self._plan(level, user_text, tone)

        for tool_name in planned:
            if tool_name == "assess_risk":
                continue
            steps.append(
                self._exec(
                    tool_name,
                    {"text": user_text, "risk": risk, "tone": tone},
                    f"Selected because risk={level}.",
                )
            )

        # Final response uses responder + agent context
        tool_summaries = [s.output.get("summary") or s.output for s in steps if s.tool != "assess_risk"]
        enriched_tone = dict(tone or {})
        enriched_tone["agent_tools"] = [s.tool for s in steps]

        response = self.respond(user_text, risk, tone)
        # Weave in agent suggestions when not critical templates-only
        if level not in {"critical", "crisis"} and tool_summaries:
            extras = []
            for out in tool_summaries:
                if isinstance(out, dict) and out.get("suggestion"):
                    extras.append(out["suggestion"])
            if extras:
                response = dict(response)
                response["reply"] = response.get("reply", "") + "\n\n" + extras[0]
                response["agentic"] = True

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "user_text": user_text,
            "risk": risk,
            "tone": tone,
            "vad": vad,
            "response": response,
            "agent": {
                "policy": SYSTEM_POLICY,
                "steps": [
                    {
                        "thought": s.thought,
                        "tool": s.tool,
                        "input": s.input,
                        "output": s.output,
                        "latency_ms": round(s.latency_ms, 2),
                    }
                    for s in steps
                ],
                "tools_used": [s.tool for s in steps],
                "latency_ms": round(elapsed_ms, 2),
                "history_turns": len(history),
            },
        }

    def _plan(self, level: str, text: str, tone: dict[str, Any] | None) -> list[str]:
        plan = ["assess_risk"]
        lowered = (text or "").lower()
        if level in {"critical", "crisis"}:
            return plan + ["helpline_resources", "safety_plan_nudge"]
        if level == "high":
            plan += ["helpline_resources", "grounding_54321", "breathing_guide"]
        elif level == "medium":
            plan += ["breathing_guide", "reflective_prompt"]
        else:
            plan += ["mood_checkin", "reflective_prompt"]

        if tone and tone.get("tone") in {"anxious", "distressed"}:
            if "breathing_guide" not in plan:
                plan.append("breathing_guide")
        if any(w in lowered for w in ("panic", "breath", "heart racing")):
            if "breathing_guide" not in plan:
                plan.append("breathing_guide")
        return plan

    def _exec(self, tool: str, payload: dict[str, Any], thought: str) -> AgentStep:
        t0 = time.perf_counter()
        fn = self.tools[tool]
        output = fn(payload)
        return AgentStep(
            thought=thought,
            tool=tool,
            input={k: v for k, v in payload.items() if k != "risk"},
            output=output,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    def _tool_assess_risk(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.risk_predict(payload.get("text") or "")
        result = dict(result)
        result["summary"] = f"Risk level {result.get('risk_level')} (score {result.get('risk_score')})"
        return result

    def _tool_mood_checkin(self, payload: dict[str, Any]) -> dict[str, Any]:
        options = ["calm", "okay", "low", "anxious", "overwhelmed"]
        return {
            "summary": "Offered mood check-in",
            "suggestion": "Quick check-in: on a scale of calm → overwhelmed, where are you right now?",
            "options": options,
        }

    def _tool_breathing(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "4-7-8 breathing guide",
            "exercise": {
                "name": "4-7-8 Breath",
                "steps": [
                    "Inhale through your nose for 4",
                    "Hold gently for 7",
                    "Exhale slowly for 8",
                    "Repeat 3 cycles",
                ],
            },
            "suggestion": "If it helps, try one slow 4-7-8 breath with me: inhale 4 · hold 7 · exhale 8.",
        }

    def _tool_grounding(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "5-4-3-2-1 grounding",
            "exercise": {
                "name": "5-4-3-2-1 Grounding",
                "steps": [
                    "Name 5 things you can see",
                    "4 things you can feel",
                    "3 things you can hear",
                    "2 things you can smell",
                    "1 thing you can taste",
                ],
            },
            "suggestion": "We can ground together: name 5 things you see, 4 you feel, 3 you hear.",
        }

    def _tool_helpline(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "Shared crisis resources",
            "resources": {
                "us": "988 Suicide & Crisis Lifeline",
                "intl": "https://www.iasp.info/suicidalthoughts/",
            },
            "suggestion": "If you feel unsafe, please contact 988 (US) or local emergency services now — you matter.",
        }

    def _tool_reflective(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompts = [
            "What feels most heavy about this right now?",
            "What would 'a little better' look like in the next hour?",
            "Who is one person that usually helps you feel less alone?",
        ]
        pick = random.choice(prompts)
        return {"summary": "Reflective prompt", "suggestion": pick, "prompt": pick}

    def _tool_safety_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "Safety plan nudge",
            "suggestion": (
                "If you can: move to a safer space, reach a trusted person, and contact 988. "
                "I can stay with you here while you get human help."
            ),
            "steps": [
                "Contact 988 or emergency services",
                "Reach a trusted person",
                "Remove immediate means of harm if safe to do so",
            ],
        }
