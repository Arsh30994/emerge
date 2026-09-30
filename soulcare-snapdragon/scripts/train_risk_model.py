"""Train / refresh the on-device risk classifier artifact."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from models.risk_classifier import RiskClassifier  # noqa: E402


def main() -> None:
    model_path = ROOT / "models" / "risk_model.joblib"
    if model_path.exists():
        model_path.unlink()
    clf = RiskClassifier(model_path=model_path)
    samples = [
        "I had a good day",
        "I feel hopeless and empty",
        "I want to end my life",
    ]
    for s in samples:
        print(s, "->", clf.predict(s)["label"])
    print("Saved:", model_path)


if __name__ == "__main__":
    main()
