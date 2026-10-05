"""Phase 4 — peak-event classification with validation-set threshold calibration.

For each city and each percentile q in {85, 90, 95}:
  - peak label = (demand > q-th percentile of TRAIN demand)
  - models: logistic regression vs random forest (predict_proba)
  - decision threshold chosen on VAL (maximize F1), applied to TEST
  - metrics: accuracy, precision, recall, F1 (at val threshold) + AUC-ROC

Outputs: _output/classification/classification_results.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.load import CITIES  # noqa: E402
from src.models import (  # noqa: E402
    TARGET,
    best_threshold,
    clf_metrics,
    fit_logistic_clf,
    fit_rf_clf,
)
from src.preprocess import split_train_val_test  # noqa: E402

FEAT_DIR = ROOT / "_output" / "features"
OUT = ROOT / "_output" / "classification"
OUT.mkdir(parents=True, exist_ok=True)

PERCENTILES = [85, 90, 95]
CLEAN_CITIES = ["JHB", "LOA", "MEL", "SPO", "SZH"]


def load_features(city: str) -> pd.DataFrame:
    return pd.read_csv(FEAT_DIR / f"{city}.csv", index_col=0, parse_dates=True)


def main() -> None:
    rows = []
    for city in CITIES:
        df = load_features(city)
        train, val, test = split_train_val_test(df)
        Xtr = train.drop(columns=[TARGET])
        Xva = val.drop(columns=[TARGET])
        Xte = test.drop(columns=[TARGET])

        for q in PERCENTILES:
            thr = float(np.percentile(train[TARGET], q))
            ytr = (train[TARGET] > thr).astype(int)
            yva = (val[TARGET] > thr).astype(int)
            yte = (test[TARGET] > thr).astype(int)

            for name, fit in [("logistic", fit_logistic_clf), ("random_forest", fit_rf_clf)]:
                proba_fn = fit(Xtr, ytr)
                proba_va = proba_fn(Xva)
                proba_te = proba_fn(Xte)
                t, val_f1 = best_threshold(yva, proba_va)
                pred_te = (proba_te >= t).astype(int)
                m = clf_metrics(yte, pred_te, proba_te)
                rows.append(
                    {
                        "city": city, "percentile": q, "model": name,
                        "n_pos_val": int(yva.sum()), "n_pos_test": int(yte.sum()),
                        "threshold": round(t, 3), "val_f1": round(val_f1, 3), **m,
                    }
                )
                print(
                    f"[{city}] q={q}  {name:12s}  thr={t:.2f}  valF1={val_f1:.3f}  "
                    f"recall={m['recall']:.3f}  f1={m['f1']:.3f}  auc={m['auc']:.3f}  "
                    f"(pos_val={int(yva.sum())}, pos_test={int(yte.sum())})"
                )

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "classification_results.csv", index=False)

    print("\n" + "=" * 72)
    print("SUMMARY (5 cities) — F1 / recall / AUC at q=90 (val-calibrated)")
    print("=" * 72)
    clean = res[res.city.isin(CLEAN_CITIES)]
    for metric in ["f1", "recall", "auc"]:
        sub = clean[clean.percentile == 90]
        piv = sub.pivot(index="city", columns="model", values=metric).round(3)
        print(f"\n--- q=90  {metric} ---")
        print(piv.to_string())

    print(f"\nResults saved to {OUT / 'classification_results.csv'}")


if __name__ == "__main__":
    main()
