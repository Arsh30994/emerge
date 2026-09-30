"""
Response generation — Phi-3.5-Mini-Instruct via Qualcomm AI Hub.

Primary API (Snapdragon / AI Hub):
    from qai_hub_models.models.phi_3_5_mini_instruct import App
"""

from __future__ import annotations

import logging
import os
import random
from typing import Any

logger = logging.getLogger("soulcare.response")

SYSTEM_PROMPT = (
    "You are a compassionate, non-judgmental mental health supporter. "
    "Provide empathetic, supportive responses. "
    "If user shows crisis signals, gently encourage professional help. "
    "Never diagnose. Never provide methods of self-harm or suicide. "
    "Keep replies brief (2-4 sentences). SoulCare runs 100% on-device."
)

HELPLINE = {
    "us": "988 Suicide & Crisis Lifeline (call/text 988)",
    "intl": "https://www.iasp.info/suicidalthoughts/ for local resources",
    "disclaimer": (
        "SoulCare is a supportive companion, not a therapist or emergency service. "
        "If you are in immediate danger, call your local emergency number."
    ),
}

_RESPONSES: dict[str, list[str]] = {
    "low": [
        "I'm glad you're checking in. What's been supporting you lately?",
        "Sounds like things are relatively steady. I'm here if you want to unpack anything.",
        "Thanks for sharing. Would you like to talk about what's on your mind?",
    ],
    "medium": [
        "That sounds stressful. You're not alone in feeling this way — want to go a bit deeper?",
        "I hear the pressure you're under. Taking a slow breath together can help. What's weighing most?",
        "It's okay to feel stretched thin. What usually helps you reset, even a little?",
    ],
    "high": [
        "I'm really glad you told me this. What you're feeling matters, and support is available.",
        "That sounds incredibly heavy. You don't have to carry it alone — I'm here, and so are people who can help.",
        "Thank you for trusting me with this. Let's take one small step: is there someone safe you can reach out to?",
    ],
    "critical": [
        (
            "I'm concerned about your safety and care about you. "
            "Please reach out for immediate help: 988 (US) or find local resources at "
            "https://www.iasp.info/suicidalthoughts/. You are not alone."
        ),
        (
            "Your life matters. If you're thinking about suicide or self-harm, "
            "contact emergency services or 988 right now. I'll stay with you in this conversation, "
            "but real-time human help is the priority."
        ),
    ],
}
_RESPONSES["moderate"] = _RESPONSES["medium"]
_RESPONSES["crisis"] = _RESPONSES["critical"]


class ResponseGenerator:
    """Phi-3.5-Mini response generator with offline rule fallback (no cloud)."""

    def __init__(self) -> None:
        self.system_prompt = SYSTEM_PROMPT
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.backend = "rules"
        self.model: Any = None
        self._pipeline = None
        if os.getenv("FORCE_PHI35", "0") == "1" or not self.demo_mode:
            self._try_load()

    def _try_load(self) -> None:
        # Exact import from hackathon brief
        try:
            from qai_hub_models.models.phi_3_5_mini_instruct import App  # type: ignore

            self.model = App()
            self.backend = "qai-hub-phi-3.5-mini"
            self.demo_mode = False
            logger.info("Loaded Phi-3.5-Mini via qai_hub_models.models.phi_3_5_mini_instruct.App")
            return
        except Exception as exc:  # noqa: BLE001
            logger.info("AI Hub Phi-3.5 App unavailable (%s); trying transformers.", exc)

        model_id = os.getenv("PHI35_MODEL", "microsoft/Phi-3.5-mini-instruct")
        try:
            from transformers import pipeline  # type: ignore

            self._pipeline = pipeline(
                "text-generation",
                model=model_id,
                device_map="auto",
                torch_dtype="auto",
            )
            self.backend = "phi-3.5-mini-transformers"
            self.demo_mode = False
            logger.info("Loaded local Phi-3.5-Mini transformers: %s", model_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phi-3.5 unavailable (%s); using rule-based responses.", exc)
            self.backend = "rules"

    def generate_response(self, user_message: str, risk_context: dict[str, Any]) -> str:
        """Public API from hackathon brief."""
        return self.generate(user_message, risk_context).get("reply", "")

    def generate(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None = None,
        vad: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        level = risk.get("risk_level") or risk.get("label") or "low"
        if level in {"critical", "crisis"}:
            return self._rules(user_text, risk, tone)

        try:
            if self.model is not None:
                return self._run_qai(user_text, risk, tone)
            if self._pipeline is not None:
                return self._run_transformers(user_text, risk, tone)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Response generation failed: %s", exc)

        return self._rules(user_text, risk, tone)

    def _run_qai(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        level = risk.get("risk_level") or risk.get("label")
        tone_note = f" Voice tone: {tone['tone']}." if tone and tone.get("tone") else ""
        prompt = (
            f"{self.system_prompt}\n"
            f"Risk level: {level}.{tone_note}\n"
            f"User: {user_text}\nAssistant:"
        )
        if hasattr(self.model, "generate_response"):
            reply = self.model.generate_response(user_text, risk)
        elif hasattr(self.model, "generate"):
            reply = self.model.generate(prompt)
        elif callable(self.model):
            reply = self.model(prompt)
        else:
            raise RuntimeError("Phi-3.5 App has no generate interface")
        reply = str(reply).strip()
        if risk.get("needs_helpline"):
            reply += f"\n\n{HELPLINE['disclaimer']} Resources: {HELPLINE['us']}"
        return {
            "reply": reply,
            "backend": self.backend,
            "model": "Phi-3.5-Mini-Instruct (qai_hub_models)",
            "risk_level": level,
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": False,
            "tokens": len(reply.split()),
            "target_latency_ms": 1500,
        }

    def _run_transformers(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        level = risk.get("risk_level") or risk.get("label")
        tone_note = f" Voice tone: {tone['tone']}." if tone and tone.get("tone") else ""
        prompt = (
            f"<|system|>\n{self.system_prompt}\n"
            f"<|user|>\nRisk level: {level}.{tone_note}\nUser: {user_text}\n"
            f"<|assistant|>\n"
        )
        outputs = self._pipeline(prompt, max_new_tokens=120, do_sample=True, temperature=0.7)
        text = outputs[0]["generated_text"]
        reply = text.split("<|assistant|>")[-1].strip()
        if risk.get("needs_helpline"):
            reply += f"\n\n{HELPLINE['disclaimer']} Resources: {HELPLINE['us']}"
        return {
            "reply": reply,
            "backend": self.backend,
            "model": "Phi-3.5-Mini-Instruct (local transformers)",
            "risk_level": level,
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": False,
            "tokens": len(reply.split()),
            "target_latency_ms": 1500,
        }

    def _rules(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        level = risk.get("risk_level") or risk.get("label") or "low"
        if level == "moderate":
            level = "medium"
        if level == "crisis":
            level = "critical"
        base = random.choice(_RESPONSES.get(level, _RESPONSES["low"]))
        parts = [base]
        if tone and tone.get("tone") and level not in {"critical"}:
            parts.insert(0, f"I'm sensing a {tone['tone']} tone in your voice.")
        if risk.get("needs_helpline"):
            parts.append(HELPLINE["disclaimer"])
            parts.append(f"Resources: {HELPLINE['us']} · {HELPLINE['intl']}")
        return {
            "reply": " ".join(parts),
            "backend": "rules",
            "model": "curated-supportive-templates",
            "risk_level": level,
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": True,
            "tokens": len(base.split()),
            "target_latency_ms": 1500,
        }
