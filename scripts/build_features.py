"""Phase 2 — build & persist feature matrices for all 6 cities.

Outputs _output/features/{city}.csv and prints a summary
(feature count, rows, train/val/test sizes, NaN handling).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.load import CITIES  # noqa: E402
from src.preprocess import build_features, split_train_val_test  # noqa: E402

OUT = ROOT / "_output" / "features"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    rows = []
    for city in CITIES:
        df = build_features(city)
        df.to_csv(OUT / f"{city}.csv")
        train, val, test = split_train_val_test(df)
        rows.append(
            {
                "city": city,
                "n_features": df.shape[1] - 1,
                "n_rows": df.shape[0],
                "train": len(train),
                "val": len(val),
                "test": len(test),
            }
        )

    summary = pd.DataFrame(rows).set_index("city")
    print(summary.to_string())
    summary.to_csv(OUT / "summary.csv")
    print(f"\nFeatures saved to {OUT}")


if __name__ == "__main__":
    main()
