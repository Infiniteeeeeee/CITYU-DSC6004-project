"""Phase 3 — train & evaluate regression models for all 6 cities.

Models: persistence, linear regression, random forest, LSTM.
Metrics: MAE, RMSE, R² (Adjusted R² for linear regression).

Outputs: _output/regression_results.csv (+ per-city actual-vs-predicted plot).
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
    eval_metrics,
    run_linear,
    run_lstm,
    run_persistence,
    run_rf,
)
from src.preprocess import build_features, split_train_val_test  # noqa: E402

FEAT_DIR = ROOT / "_output" / "features"
OUT_DIR = ROOT / "_output" / "regression"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_FEATURES = 33  # number of engineered features (used for Adjusted R²)


def load_features(city: str) -> pd.DataFrame:
    df = pd.read_csv(FEAT_DIR / f"{city}.csv", index_col=0, parse_dates=True)
    return df


def main() -> None:
    models = {
        "persistence": run_persistence,
        "linear": run_linear,
        "random_forest": run_rf,
        "lstm": run_lstm,
    }

    all_rows = []
    for city in CITIES:
        df = load_features(city)
        train, val, test = split_train_val_test(df)
        print(f"[{city}] train={len(train)} val={len(val)} test={len(test)}")

        city_preds = {}
        for name, fn in models.items():
            pred, idx = fn(train, val, test)
            city_preds[name] = (pred, idx)
            y_true = test[TARGET].values
            n_feat = N_FEATURES if name == "linear" else None
            m = eval_metrics(y_true, pred, n_features=n_feat)
            all_rows.append({"city": city, "model": name, **m})
            print(
                f"   {name:14s} MAE={m['MAE']:9.1f}  RMSE={m['RMSE']:9.1f}  "
                f"R2={m['R2']:.4f}"
            )

    results = pd.DataFrame(all_rows)
    results.to_csv(OUT_DIR / "regression_results.csv", index=False)

    # --- wide comparison table ---
    wide = results.pivot(index="city", columns="model", values=["MAE", "RMSE", "R2"])
    print("\n=== MAE (kWh) ===")
    print(wide["MAE"].round(1).to_string())
    print("\n=== RMSE (kWh) ===")
    print(wide["RMSE"].round(1).to_string())
    print("\n=== R2 ===")
    print(wide["R2"].round(4).to_string())

    print(f"\nResults saved to {OUT_DIR / 'regression_results.csv'}")


if __name__ == "__main__":
    main()
