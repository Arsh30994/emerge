"""
Risk classification — Distil-BERT via Qualcomm AI Hub.

Primary API (Snapdragon / AI Hub):
    from qai_hub_models.models.distilbert_base_uncased import App
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
_TRAIN_LABELS = ["low"] * 8 + ["medium"] * 8 + ["high"] * 8 + ["critical"] * 8


class RiskClassifier:
    """Distil-BERT risk head with sklearn offline fallback."""

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or (
            Path(__file__).resolve().parents[2] / "models" / "risk_model.joblib"
        )
        self.backend = "sklearn-tfidf"
        self.demo_mode = True
        self.model: Any = None
        self._tokenizer = None
        self._bert = None
        self._torch = None
        self.pipeline: Pipeline | None = None
        self._try_load_ai_hub()
        if self.model is None and self._bert is None:
            self._load_or_train_sklearn()

    def _try_load_ai_hub(self) -> None:
        force = os.getenv("FORCE_DISTILBERT", "0") == "1"
        demo = os.getenv("SOULCARE_DEMO", "1") == "1"
        if demo and not force:
            logger.info("RiskClassifier sklearn fallback (FORCE_DISTILBERT=1 for Distil-BERT).")
            return

        # Exact import from hackathon brief
        try:
            from qai_hub_models.models.distilbert_base_uncased import App  # type: ignore

            self.model = App()
            self.backend = "qai-hub-distilbert-base-uncased"
            self.demo_mode = False
            logger.info("Loaded Distil-BERT via qai_hub_models.models.distilbert_base_uncased.App")
            return
        except Exception as exc:  # noqa: BLE001
            logger.info("AI Hub Distil-BERT App unavailable (%s); trying transformers.", exc)

        # Alternate AI Hub package name seen in catalog
        try:
            import qai_hub_models.models.distil_bert_base_uncased_hf as _qai  # noqa: F401, type: ignore

            logger.info("AI Hub distil_bert_base_uncased_hf package present")
        except Exception:  # noqa: BLE001
            pass

        model_id = os.getenv("DISTILBERT_MODEL", "distilbert-base-uncased")
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer  # type: ignore
            import torch  # type: ignore

            self._tokenizer = AutoTokenizer.from_pretrained(model_id)
            try:
                self._bert = AutoModelForSequenceClassification.from_pretrained(
                    model_id, num_labels=4
                )
            except Exception:
                self._bert = AutoModelForSequenceClassification.from_pretrained(model_id)
            self._bert.eval()
            self._torch = torch
            self.backend = "distilbert-transformers"
            self.demo_mode = False
            logger.info("Loaded Distil-BERT transformers model: %s", model_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Distil-BERT unavailable (%s); sklearn fallback.", exc)

    def _build_pipeline(self) -> Pipeline:
        return Pipeline(
            steps=[
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2), min_df=1, max_features=5000, stop_words="english"
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"),
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

    def assess_risk(self, text: str) -> dict[str, Any]:
        """Public API from hackathon brief."""
        return self.predict(text)

    def predict(self, text: str) -> dict[str, Any]:
        cleaned = (text or "").strip()
        if not cleaned:
            return self._pack("low", 1.0, {k: 0.0 for k in LEVELS} | {"low": 1.0})

        try:
            if self.model is not None:
                result = self._predict_qai(cleaned)
            elif self._bert is not None and self._tokenizer is not None:
                result = self._predict_bert(cleaned)
            else:
                result = self._predict_sklearn(cleaned)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Risk inference failed (%s); sklearn fallback.", exc)
            result = self._predict_sklearn(cleaned)

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

    def _predict_qai(self, text: str) -> dict[str, Any]:
        out: Any
        if hasattr(self.model, "assess_risk"):
            out = self.model.assess_risk(text)
        elif callable(self.model):
            out = self.model(text)
        else:
            raise RuntimeError("Distil-BERT App has no assess interface")

        if isinstance(out, dict) and "risk_level" in out:
            level = _LEGACY.get(str(out["risk_level"]), str(out["risk_level"]))
            score = float(out.get("risk_score", out.get("confidence", 0.5)))
            probs = out.get("probabilities") or {k: 0.0 for k in LEVELS}
            probs[level] = max(float(probs.get(level, 0)), score)
            return self._pack(level, score, probs, risk_score=score)
        # Assume logits / label string
        label = _LEGACY.get(str(out), str(out))
        if label not in LEVELS:
            label = "medium"
        return self._pack(label, 0.7, {k: 0.1 for k in LEVELS} | {label: 0.7})

    def _predict_sklearn(self, text: str) -> dict[str, Any]:
        assert self.pipeline is not None
        proba = self.pipeline.predict_proba([text])[0]
        classes = [_LEGACY.get(str(c), str(c)) for c in self.pipeline.classes_]
        probabilities = {level: 0.0 for level in LEVELS}
        for cls, p in zip(classes, proba):
            if cls in probabilities:
                probabilities[cls] = float(p)
        best = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
        weights = {"low": 0.1, "medium": 0.4, "high": 0.7, "critical": 1.0}
        score = sum(probabilities[k] * weights[k] for k in LEVELS)
        return self._pack(best, probabilities[best], probabilities, risk_score=score)

    def _predict_bert(self, text: str) -> dict[str, Any]:
        torch = self._torch
        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True, max_length=256, padding=True
        )
        with torch.no_grad():
            logits = self._bert(**inputs).logits[0]
            if logits.shape[-1] >= 4:
                probs = torch.softmax(logits[:4], dim=-1).cpu().numpy()
                probabilities = {LEVELS[i]: float(probs[i]) for i in range(4)}
            else:
                probs = torch.softmax(logits, dim=-1).cpu().numpy()
                pos = float(probs[-1])
                probabilities = {
                    "low": 1 - pos,
                    "medium": pos * 0.3,
                    "high": pos * 0.4,
                    "critical": pos * 0.3,
                }
                total = sum(probabilities.values()) or 1.0
                probabilities = {k: v / total for k, v in probabilities.items()}
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
        score = float(np.clip(risk_score if risk_score is not None else confidence, 0, 1))
        return {
            "label": level,
            "risk_level": level,
            "risk_score": round(score, 4),
            "confidence": round(float(confidence), 4),
            "probabilities": {k: round(float(v), 4) for k, v in probabilities.items()},
            "needs_helpline": level in {"high", "critical"},
            "backend": self.backend,
            "model": (
                "Distil-BERT (qai_hub_models)"
                if "distilbert" in self.backend or "distil" in self.backend
                else "TF-IDF + LogisticRegression fallback"
            ),
            "demo": self.demo_mode,
            "target_latency_ms": 50,
        }
