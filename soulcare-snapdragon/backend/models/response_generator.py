"""
Response generation — privacy-first supportive replies.

Default path: curated rule-based responses (fast, offline, no cloud).
Optional path: local Phi-3-mini via transformers when FORCE_PHI3=1.
"""

from __future__ import annotations

import logging
import os
import random
from typing import Any

logger = logging.getLogger("soulcare.response")

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
    "moderate": [
        "That sounds stressful. You're not alone in feeling this way — want to go a bit deeper?",
        "I hear the pressure you're under. Taking a slow breath together can help. What's weighing most?",
        "It's okay to feel stretched thin. What usually helps you reset, even a little?",
    ],
    "high": [
        "I'm really glad you told me this. What you're feeling matters, and support is available.",
        "That sounds incredibly heavy. You don't have to carry it alone — I'm here, and so are people who can help.",
        "Thank you for trusting me with this. Let's take one small step: is there someone safe you can reach out to?",
    ],
    "crisis": [
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

_TONE_NUDGES = {
    "calm": "Your voice sounds relatively settled.",
    "reflective": "I'm sensing a thoughtful, quieter tone.",
    "anxious": "I'm picking up some tension in your voice — that's okay.",
    "distressed": "Your voice sounds strained; we can go gently.",
}


class ResponseGenerator:
    """Generate supportive, on-device responses."""

    def __init__(self) -> None:
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.backend = "rules"
        self._pipeline = None
        if os.getenv("FORCE_PHI3", "0") == "1":
            self._try_load_phi3()

    def _try_load_phi3(self) -> None:
        try:
            from transformers import pipeline  # type: ignore

            model_id = os.getenv("PHI3_MODEL", "microsoft/Phi-3-mini-4k-instruct")
            self._pipeline = pipeline(
                "text-generation",
                model=model_id,
                device_map="auto",
                torch_dtype="auto",
            )
            self.backend = "phi3-local"
            self.demo_mode = False
            logger.info("Loaded local Phi-3 model: %s", model_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phi-3 unavailable (%s); using rule-based responses.", exc)
            self.backend = "rules"

    def generate(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        label = risk.get("label", "low")
        if self._pipeline is not None and label != "crisis":
            try:
                return self._generate_phi3(user_text, risk, tone)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Phi-3 generation failed (%s); falling back to rules.", exc)

        return self._generate_rules(user_text, risk, tone)

    def _generate_rules(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        label = risk.get("label", "low")
        base = random.choice(_RESPONSES.get(label, _RESPONSES["low"]))
        parts = [base]

        if tone and tone.get("tone") in _TONE_NUDGES and label != "crisis":
            parts.insert(0, _TONE_NUDGES[tone["tone"]])

        if risk.get("needs_helpline"):
            parts.append(HELPLINE["disclaimer"])
            parts.append(f"Resources: {HELPLINE['us']} · {HELPLINE['intl']}")

        return {
            "reply": " ".join(parts),
            "backend": self.backend,
            "risk_label": label,
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": self.demo_mode or self.backend == "rules",
        }

    def _generate_phi3(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        tone_note = ""
        if tone and tone.get("tone"):
            tone_note = f" Voice tone estimate: {tone['tone']}."

        prompt = (
            "<|system|>\nYou are SoulCare, a warm, non-clinical mental health companion. "
            "Be brief (2-4 sentences), empathetic, never diagnose, and encourage professional "
            "help for crisis. Never provide methods of self-harm.\n"
            f"<|user|>\nRisk level: {risk.get('label')}.{tone_note}\nUser: {user_text}\n"
            "<|assistant|>\n"
        )
        outputs = self._pipeline(prompt, max_new_tokens=120, do_sample=True, temperature=0.7)
        text = outputs[0]["generated_text"]
        reply = text.split("<|assistant|>")[-1].strip()
        result = {
            "reply": reply,
            "backend": self.backend,
            "risk_label": risk.get("label"),
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": False,
        }
        if risk.get("needs_helpline"):
            result["reply"] += f"\n\n{HELPLINE['disclaimer']} Resources: {HELPLINE['us']}"
        return result
