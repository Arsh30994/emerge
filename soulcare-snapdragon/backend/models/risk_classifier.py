"""
Risk classifier — TF-IDF + Logistic Regression.

Detects crisis / elevated-distress language so the app can surface
local helpline resources. All inference runs on-device.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger("soulcare.risk")

# Labels used throughout the API and UI
LABELS = ("low", "moderate", "high", "crisis")

# Seed corpus for demo / first-run training. In production you would
# replace this with a carefully curated, ethically sourced dataset.
_TRAIN_TEXTS = [
    # low
    "I had a good day and feel okay",
    "Feeling calm after a walk outside",
    "Just checking in, nothing urgent",
    "Work was fine, resting now",
    "Grateful for my friends today",
    "I slept well last night",
    "Looking forward to the weekend",
    "Feeling balanced and steady",
    # moderate
    "I'm a bit stressed about deadlines",
    "Feeling lonely this evening",
    "Worried about an upcoming exam",
    "Having trouble focusing today",
    "I'm tired and a little down",
    "Anxiety is higher than usual",
    "Not sure how to handle this tension",
    "I keep overthinking small things",
    # high
    "I feel hopeless and empty inside",
    "Everything feels overwhelming and dark",
    "I can't stop crying and feel worthless",
    "I don't see a way out of this pain",
    "My anxiety is unbearable right now",
    "I feel completely alone and broken",
    "Nothing matters anymore and I'm exhausted",
    "I'm drowning in sadness every day",
    # crisis — ideation / self-harm indicators (detection only)
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
    ["low"] * 8
    + ["moderate"] * 8
    + ["high"] * 8
    + ["crisis"] * 8
)


class RiskClassifier:
    """On-device crisis / distress classifier."""

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or Path(__file__).resolve().parents[2] / "models" / "risk_model.joblib"
        self.pipeline: Pipeline | None = None
        self._load_or_train()

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

    def _load_or_train(self) -> None:
        if self.model_path.exists():
            try:
                self.pipeline = joblib.load(self.model_path)
                logger.info("Loaded risk model from %s", self.model_path)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load risk model (%s); retraining.", exc)

        logger.info("Training risk classifier on seed corpus…")
        self.pipeline = self._build_pipeline()
        self.pipeline.fit(_TRAIN_TEXTS, _TRAIN_LABELS)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, self.model_path)
        logger.info("Saved risk model to %s", self.model_path)

    def predict(self, text: str) -> dict[str, Any]:
        """Return label, confidence, and per-class probabilities."""
        assert self.pipeline is not None
        cleaned = (text or "").strip()
        if not cleaned:
            return {
                "label": "low",
                "confidence": 1.0,
                "probabilities": {label: 0.0 for label in LABELS} | {"low": 1.0},
                "needs_helpline": False,
            }

        proba = self.pipeline.predict_proba([cleaned])[0]
        classes = list(self.pipeline.classes_)
        probabilities = {label: 0.0 for label in LABELS}
        for cls, p in zip(classes, proba):
            probabilities[str(cls)] = float(p)

        best_idx = int(np.argmax(proba))
        label = str(classes[best_idx])
        confidence = float(proba[best_idx])

        # Keyword safety net for crisis phrases the small corpus may miss
        crisis_keywords = (
            "kill myself",
            "end my life",
            "suicide",
            "want to die",
            "hurt myself",
            "don't want to live",
            "do not want to live",
        )
        lowered = cleaned.lower()
        if any(k in lowered for k in crisis_keywords):
            label = "crisis"
            confidence = max(confidence, 0.92)
            probabilities["crisis"] = max(probabilities.get("crisis", 0.0), 0.92)

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "needs_helpline": label in {"high", "crisis"},
        }
