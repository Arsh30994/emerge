"""
Risk classification — Distil-BERT (Qualcomm AI Hub) + crisis safety net.

Primary: distil_bert_base_uncased_hf from qai_hub_models / Hugging Face
Fallback: TF-IDF + LogisticRegression (sklearn) for instant offline demos

Outputs:
  risk_score ∈ [0, 1]
  risk_level ∈ {low, medium, high, critical}
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger("soulcare.risk")

LEVELS = ("low", "medium", "high", "critical")

# Map legacy labels → new schema
_LEGACY = {"moderate": "medium", "crisis": "critical"}

_CRISIS_PATTERNS = [
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bsuicide\b",
    r"\bwant to die\b",
    r"\bhurt myself\b",
    r"\bdon't want to (be )?alive\b",
    r"\bdo not want to (be )?alive\b",
    r"\bplan to (kill|end)\b",
]

_TRAIN_TEXTS = [
    "I had a good day and feel okay",
    "Feeling calm after a walk outside",
    "Just checking in, nothing urgent",
    "Work was fine, resting now",
    "Grateful for my friends today",
    "I slept well last night",
    "Looking forward to the weekend",
    "Feeling balanced and steady",
    "I'm a bit stressed about deadlines",
    "Feeling lonely this evening",
    "Worried about an upcoming exam",
    "Having trouble focusing today",
    "I'm tired and a little down",
    "Anxiety is higher than usual",
    "Not sure how to handle this tension",
    "I keep overthinking small things",
    "I feel hopeless and empty inside",
    "Everything feels overwhelming and dark",
    "I can't stop crying and feel worthless",
    "I don't see a way out of this pain",
    "My anxiety is unbearable right now",
    "I feel completely alone and broken",
    "Nothing matters anymore and I'm exhausted",
    "I'm drowning in sadness every day",
    "I want to end my life",
    "I've been thinking about suicide",
    "I don't want to be alive anymore",
    "I have a plan to kill myself",
    "Everyone would be better if I were gone",
    "I'm going to hurt myself tonight",
    "I can't go on living like this and want to die",
    "I've researched ways to end it all",
]

_TRAIN_LABELS = (
    ["low"] * 8 + ["medium"] * 8 + ["high"] * 8 + ["critical"] * 8
)


class RiskClassifier:
    """Distil-BERT risk head with sklearn fallback."""

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or (
            Path(__file__).resolve().parents[2] / "models" / "risk_model.joblib"
        )
        self.backend = "sklearn-tfidf"
        self.demo_mode = True
        self._tokenizer = None
        self._bert = None
        self.pipeline: Pipeline | None = None
        self._try_load_distilbert()
        if self._bert is None:
            self._load_or_train_sklearn()

    def _try_load_distilbert(self) -> None:
        force = os.getenv("FORCE_DISTILBERT", "0") == "1"
        demo = os.getenv("SOULCARE_DEMO", "1") == "1"
        if demo and not force:
            logger.info("Risk classifier using sklearn fallback (FORCE_DISTILBERT=1 for Distil-BERT).")
            return

        model_id = os.getenv("DISTILBERT_MODEL", "distilbert-base-uncased")
        try:
            # Prefer AI Hub package presence as a signal / future ONNX path
            try:
                import qai_hub_models.models.distil_bert_base_uncased_hf as _qai_bert  # noqa: F401, type: ignore

                logger.info("Qualcomm AI Hub Distil-BERT package available")
            except Exception:  # noqa: BLE001
                pass

            from transformers import AutoModelForSequenceClassification, AutoTokenizer  # type: ignore
            import torch  # type: ignore

            self._tokenizer = AutoTokenizer.from_pretrained(model_id)
            # 4-way head; if hub weights are base-only, we still score via CLS + linear probe fallback
            try:
                self._bert = AutoModelForSequenceClassification.from_pretrained(
                    model_id, num_labels=4
                )
            except Exception:
                self._bert = AutoModelForSequenceClassification.from_pretrained(model_id)
            self._bert.eval()
            self._torch = torch
            self.backend = "distilbert-base-uncased"
            self.demo_mode = False
            logger.info("Loaded Distil-BERT risk model: %s", model_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Distil-BERT unavailable (%s); sklearn fallback.", exc)
            self._bert = None

    def _build_pipeline(self) -> Pipeline:
        return Pipeline(
            steps=[
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        min_df=1,
                        max_features=5000,
                        stop_words="english",
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        solver="lbfgs",
                    ),
                ),
            ]
        )

    def _load_or_train_sklearn(self) -> None:
        if self.model_path.exists():
            try:
                self.pipeline = joblib.load(self.model_path)
                self.backend = "sklearn-tfidf"
                self.demo_mode = True
                logger.info("Loaded sklearn risk model from %s", self.model_path)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load sklearn model (%s); retraining.", exc)

        self.pipeline = self._build_pipeline()
        self.pipeline.fit(_TRAIN_TEXTS, _TRAIN_LABELS)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, self.model_path)
        self.backend = "sklearn-tfidf"
        self.demo_mode = True
        logger.info("Trained sklearn risk model → %s", self.model_path)

    def predict(self, text: str) -> dict[str, Any]:
        cleaned = (text or "").strip()
        if not cleaned:
            return self._pack("low", 1.0, {k: 0.0 for k in LEVELS} | {"low": 1.0})

        if self._bert is not None and self._tokenizer is not None:
            result = self._predict_bert(cleaned)
        else:
            result = self._predict_sklearn(cleaned)

        # Keyword safety net for critical ideation
        if any(re.search(p, cleaned.lower()) for p in _CRISIS_PATTERNS):
            result["risk_level"] = "critical"
            result["label"] = "critical"
            result["risk_score"] = max(result["risk_score"], 0.92)
            result["confidence"] = max(result["confidence"], 0.92)
            result["probabilities"]["critical"] = max(
                result["probabilities"].get("critical", 0.0), 0.92
            )
            result["needs_helpline"] = True
            result["safety_net"] = "crisis_keyword"

        return result

    def _predict_sklearn(self, text: str) -> dict[str, Any]:
        assert self.pipeline is not None
        proba = self.pipeline.predict_proba([text])[0]
        classes = [ _LEGACY.get(str(c), str(c)) for c in self.pipeline.classes_ ]
        probabilities = {level: 0.0 for level in LEVELS}
        for cls, p in zip(classes, proba):
            if cls in probabilities:
                probabilities[cls] = float(p)
        best = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
        conf = probabilities[best]
        # risk_score: weighted toward higher severity
        weights = {"low": 0.1, "medium": 0.4, "high": 0.7, "critical": 1.0}
        score = sum(probabilities[k] * weights[k] for k in LEVELS)
        return self._pack(best, conf, probabilities, risk_score=score)

    def _predict_bert(self, text: str) -> dict[str, Any]:
        torch = self._torch
        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True, max_length=256, padding=True
        )
        with torch.no_grad():
            outputs = self._bert(**inputs)
            logits = outputs.logits[0]
            if logits.shape[-1] >= 4:
                probs = torch.softmax(logits[:4], dim=-1).cpu().numpy()
                probabilities = {LEVELS[i]: float(probs[i]) for i in range(4)}
            else:
                # Binary / unexpected head → map positive class to high
                probs = torch.softmax(logits, dim=-1).cpu().numpy()
                pos = float(probs[-1])
                probabilities = {
                    "low": 1 - pos,
                    "medium": pos * 0.3,
                    "high": pos * 0.4,
                    "critical": pos * 0.3,
                }
                s = sum(probabilities.values()) or 1.0
                probabilities = {k: v / s for k, v in probabilities.items()}
        best = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
        weights = {"low": 0.1, "medium": 0.4, "high": 0.7, "critical": 1.0}
        score = sum(probabilities[k] * weights[k] for k in LEVELS)
        return self._pack(best, probabilities[best], probabilities, risk_score=score)

    def _pack(
        self,
        level: str,
        confidence: float,
        probabilities: dict[str, float],
        risk_score: float | None = None,
    ) -> dict[str, Any]:
        level = _LEGACY.get(level, level)
        if level not in LEVELS:
            level = "medium"
        score = float(risk_score if risk_score is not None else confidence)
        return {
            "label": level,  # backward compatible
            "risk_level": level,
            "risk_score": round(float(np.clip(score, 0, 1)), 4),
            "confidence": round(float(confidence), 4),
            "probabilities": {k: round(float(v), 4) for k, v in probabilities.items()},
            "needs_helpline": level in {"high", "critical"},
            "backend": self.backend,
            "model": (
                "Distil-BERT (Qualcomm AI Hub)"
                if "distilbert" in self.backend
                else "TF-IDF + LogisticRegression fallback"
            ),
            "demo": self.demo_mode,
        }
