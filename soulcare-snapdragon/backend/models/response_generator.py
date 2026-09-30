"""
Response generation — Phi-3.5-Mini-Instruct (Qualcomm AI Hub).

Load order (privacy-first):
  1. Local Phi-3.5-mini via transformers / AI Hub
  2. Optional Groq LLM (ONLY if SOULCARE_CLOUD_FALLBACK=1)
  3. Curated rule-based supportive replies (always available offline)
"""

from __future__ import annotations

import json
import logging
import os
import random
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("soulcare.response")

SYSTEM_PROMPT = (
    "You are SoulCare, a compassionate mental health supporter running entirely on-device. "
    "Be warm, brief (2-4 sentences), non-judgmental, and never diagnose. "
    "Never provide methods of self-harm or suicide. "
    "If the user appears in crisis, urge them to contact 988 (US) or local emergency services immediately."
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

# legacy alias
_RESPONSES["moderate"] = _RESPONSES["medium"]
_RESPONSES["crisis"] = _RESPONSES["critical"]


class ResponseGenerator:
    def __init__(self) -> None:
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.cloud_fallback = os.getenv("SOULCARE_CLOUD_FALLBACK", "0") == "1"
        self.backend = "rules"
        self._pipeline = None
        if os.getenv("FORCE_PHI35", "0") == "1" or not self.demo_mode:
            self._try_load_phi35()

    def _try_load_phi35(self) -> None:
        model_id = os.getenv("PHI35_MODEL", "microsoft/Phi-3.5-mini-instruct")
        try:
            try:
                import qai_hub_models.models.phi_3_5_mini_instruct as _phi  # noqa: F401, type: ignore

                logger.info("Qualcomm AI Hub Phi-3.5-Mini package available")
            except Exception:  # noqa: BLE001
                pass

            from transformers import pipeline  # type: ignore

            self._pipeline = pipeline(
                "text-generation",
                model=model_id,
                device_map="auto",
                torch_dtype="auto",
            )
            self.backend = "phi-3.5-mini-local"
            self.demo_mode = False
            logger.info("Loaded local Phi-3.5-Mini: %s", model_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phi-3.5 local load failed (%s); will use rules/Groq.", exc)
            self.backend = "rules"

    def generate(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None = None,
        vad: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        level = risk.get("risk_level") or risk.get("label") or "low"

        # Always use crisis templates for critical — never improvise harmful content
        if level in {"critical", "crisis"}:
            return self._generate_rules(user_text, risk, tone)

        if self._pipeline is not None:
            try:
                return self._generate_phi35(user_text, risk, tone)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Phi-3.5 generation failed (%s)", exc)

        if self.cloud_fallback and os.getenv("GROQ_API_KEY"):
            try:
                return self._generate_groq(user_text, risk, tone)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Groq LLM fallback failed (%s)", exc)

        return self._generate_rules(user_text, risk, tone)

    def _generate_rules(
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
        }

    def _generate_phi35(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        level = risk.get("risk_level") or risk.get("label")
        tone_note = f" Voice tone: {tone['tone']}." if tone and tone.get("tone") else ""
        prompt = (
            f"<|system|>\n{SYSTEM_PROMPT}\n"
            f"<|user|>\nRisk level: {level}.{tone_note}\nUser: {user_text}\n"
            f"<|assistant|>\n"
        )
        outputs = self._pipeline(prompt, max_new_tokens=120, do_sample=True, temperature=0.7)
        text = outputs[0]["generated_text"]
        reply = text.split("<|assistant|>")[-1].strip()
        tokens = len(reply.split())
        result = {
            "reply": reply,
            "backend": self.backend,
            "model": "Phi-3.5-Mini-Instruct (Qualcomm AI Hub / local)",
            "risk_level": level,
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": False,
            "tokens": tokens,
        }
        if risk.get("needs_helpline"):
            result["reply"] += f"\n\n{HELPLINE['disclaimer']} Resources: {HELPLINE['us']}"
        return result

    def _generate_groq(
        self,
        user_text: str,
        risk: dict[str, Any],
        tone: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Optional cloud fallback for non-Snapdragon demo machines."""
        level = risk.get("risk_level") or risk.get("label")
        tone_note = f" Voice tone: {tone['tone']}." if tone and tone.get("tone") else ""
        payload = {
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "temperature": 0.6,
            "max_tokens": 180,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Risk level: {level}.{tone_note}\nUser message: {user_text}",
                },
            ],
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"Groq HTTP {exc.code}: {detail}") from exc

        reply = body["choices"][0]["message"]["content"].strip()
        usage = body.get("usage") or {}
        tokens = usage.get("completion_tokens") or len(reply.split())
        if risk.get("needs_helpline"):
            reply += f"\n\n{HELPLINE['disclaimer']} Resources: {HELPLINE['us']}"
        return {
            "reply": reply,
            "backend": "groq-fallback",
            "model": payload["model"] + " (Groq fallback — not used on Snapdragon)",
            "risk_level": level,
            "helpline": HELPLINE if risk.get("needs_helpline") else None,
            "demo": False,
            "cloud_fallback": True,
            "tokens": tokens,
        }
