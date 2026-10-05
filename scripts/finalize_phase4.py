"""Finalize Phase 4 outputs:
  - _output/classification_summary.md  (val-calibrated peak classification results)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

OUT = ROOT / "_output"
RES = pd.read_csv(OUT / "classification" / "classification_results.csv")

CLEAN_CITIES = ["LOA", "MEL", "SPO"]          # val-calibration works
DEGEN_CITIES = ["JHB", "SZH", "AMS"]          # too few positives in val/test

MODEL_NAMES = {"logistic": "Logistic", "random_forest": "Random Forest"}


def _piv(cities, q, value):
    sub = RES[(RES.city.isin(cities)) & (RES.percentile == q)]
    wide = sub.pivot(index="city", columns="model", values=value)
    return wide.rename(columns=MODEL_NAMES).round(3)


def _fmt(df: pd.DataFrame) -> str:
    return df.to_string()


def main() -> None:
    L: list[str] = []

    L += [
        "# Peak-Event Classification Results (Phase 4)",
        "",
        "**Task:** predict `demand > q-th percentile of TRAIN demand` for q ∈ {85, 90, 95}.",
        "",
        "**Models:** logistic regression vs random forest (both `predict_proba`).",
        "",
        "**Threshold:** chosen on the **validation set** (August) to maximize F1, then",
        "applied unchanged to the test set (September). This corrects the poor recall at the",
        "default 0.5 threshold seen earlier (RF probabilities are miscalibrated under class",
        "imbalance).",
        "",
    ]

    # --- main comparison ---
    L += ["## Main comparison — cities where calibration works", ""]
    for q in [85, 90, 95]:
        L += [f"### q = {q}", "", "```", _fmt(_piv(CLEAN_CITIES, q, "f1")), "```", "",
              "**Recall**", "", "```", _fmt(_piv(CLEAN_CITIES, q, "recall")), "```", "",
              "**AUC-ROC**", "", "```", _fmt(_piv(CLEAN_CITIES, q, "auc")), "```", ""]

    L += [
        "### Reading",
        "",
        "- **AUC is high (0.87–0.98) and robust across q** — the models rank peaks well.",
        "- **Val calibration recovers recall** (0.63–0.91) while keeping F1 ≥ 0.56: thresholds",
        "  land at 0.17–0.30 instead of 0.5.",
        "- **q=95 is the hardest** (fewer positives, F1 drops to ~0.17–0.52) but AUC stays high,",
        "  confirming it is a sample-size / precision problem rather than a ranking problem.",
        "- **Random forest ≥ logistic** in F1 at every (city, q) except MEL q=90/95.",
        "",
    ]

    # --- degenerate cases ---
    L += [
        "## Degenerate cases — recorded as limitations (not tuned)",
        "",
        "For these cities the val and/or test set has too few positive hours, so val-based",
        "threshold calibration cannot select a meaningful threshold. We report them as-is and",
        "treat them as a data limitation rather than forcing a number.",
        "",
        "```",
        RES[RES.city.isin(DEGEN_CITIES)]
        .pivot_table(index=["city", "percentile"], columns="model",
                     values=["n_pos_val", "n_pos_test", "auc", "f1"], aggfunc="max")
        .round(3).to_string(),
        "```",
        "",
        "- **AMS** — Aug–Sep demand is ~constant (see `ams_case_study.md`), so both val and test",
        "  have **0 positives** at every q: no peak ever exceeds the train percentile. AUC = NaN.",
        "  This is the non-stationarity problem from Phase 3 surfacing in the classification task.",
        "- **JHB** — peaks are extremely spiky, so at q=90 the **val has 0 positives** (August has",
        "  no hour above the Apr–Jul 90th percentile). Calibration is undefined; test recall is",
        "  recoverable (0.94–1.0) but precision collapses, giving F1 ≈ 0.05–0.08.",
        "- **SZH** — September demand drifts below the train percentile, so at q=90/95 the **test",
        "  has 0 positives**. AUC = NaN; at q=85 only 2 positives survive.",
        "",
        "### Why this matters",
        "",
        "The classification task inherits the same distribution shift seen in Phase 3: peaks are",
        "rare by construction (~10%), a 1-month val window can contain 0 of them, and AMS/SZH",
        "drift so much that train and test are different regimes. This is a genuine limitation of",
        "the dataset and time horizon (Section 8–9 of the proposal), not a modelling bug.",
        "",
        "### Practical takeaway",
        "",
        "For deployment you would (a) use a longer / rolling validation window so the threshold",
        "estimator sees enough peaks, and (b) retrain on a rolling basis to track regime drift",
        "(AMS/SZH). Both are out of scope for the fixed Apr–Sep 2023 window.",
        "",
    ]

    (OUT / "classification_summary.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote {OUT / 'classification_summary.md'}")


if __name__ == "__main__":
    main()
