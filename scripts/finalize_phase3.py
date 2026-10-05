"""Finalize Phase 3 outputs:
  - _output/figures/ams_nonstationarity.png  (AMS daily demand, shows regime shift)
  - _output/ams_case_study.md                (AMS non-stationarity write-up)
  - _output/regression_summary.md            (clean 5-city comparison + AMS note)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.load import city_total  # noqa: E402

OUT = ROOT / "_output"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

CLEAN_CITIES = ["JHB", "LOA", "MEL", "SPO", "SZH"]  # stationary cities


def ams_figure() -> None:
    d = city_total("AMS")
    daily = d.resample("D").mean()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(daily.index, daily.values, lw=0.8, color="#1f77b4")
    ax.set_title("AMS daily mean demand — non-stationary regimes")
    ax.set_ylabel("kWh")
    ax.set_ylim(0, daily.max() * 1.15)

    # annotate the three regimes
    ann = [
        ("ramp-up\n(≈0 → 50k)", "2023-04-15", 0.55),
        ("stable", "2023-06-15", 0.55),
        ("flattens\n(std → ~150)", "2023-08-15", 0.55),
    ]
    for label, x, y in ann:
        ax.annotate(label, xy=(pd.Timestamp(x), daily.max() * y),
                    ha="center", fontsize=8, color="#d62728")
    fig.tight_layout()
    fig.savefig(FIG / "ams_nonstationarity.png", dpi=110)
    plt.close(fig)


def ams_writeup() -> None:
    d = city_total("AMS")
    monthly = d.groupby(d.index.month).agg(["mean", "std"]).round(0)
    lines = [
        "# AMS Case Study — Non-stationarity breaks train/test",
        "",
        "## What the data shows",
        "",
        "AMS hourly demand is strongly non-stationary over Apr–Sep 2023:",
        "",
        "```",
        monthly.to_string(),
        "```",
        "",
        "- **April ≈ 0** (mean 1,173 kWh/h): charging sites were still coming online.",
        "- **May ramp-up** (std 8,687): demand swings wildly as coverage grows.",
        "- **June–July stable** (std ~7–8k): normal operating regime.",
        "- **Aug–Sep flatten** (std collapses to 150–285): demand becomes almost constant.",
        "",
        "## Why the models fail here",
        "",
        "The train set (Apr–Jul) and test set (Sep) are two different distributions:",
        "train contains the near-zero April and the May ramp, while September is a flat",
        "~45,900 kWh/h regime. Linear regression / random forest / LSTM learn the *level*",
        "and *trend* of the training regime and extrapolate badly onto September, giving",
        "negative R². Only **persistence** (predict last hour) survives, because it needs",
        "no global pattern — just local continuity.",
        "",
        "This maps directly to the proposal's Section 8 (Error Analysis) and Section 9",
        "(Limitations: 'limited representativeness', 'model can only use patterns present",
        "in the data').",
    ]
    (OUT / "ams_case_study.md").write_text("\n".join(lines), encoding="utf-8")


def regression_summary() -> None:
    res = pd.read_csv(OUT / "regression" / "regression_results.csv")

    def block(cities, title):
        sub = res[res.city.isin(cities)]
        wide = sub.pivot(index="city", columns="model", values="R2").round(4)
        best = sub.loc[sub.groupby("city")["R2"].idxmax()][["city", "model"]]
        return [f"### {title}", "", "```", wide.to_string(), "```", "",
                "Best model per city:", "", "```",
                best.set_index("city").to_string(), "```", ""]

    lines = ["# Regression Results (Phase 3)", "",
             "Models: persistence / linear / random forest / LSTM.",
             "Metric shown: R² on the September test set.", ""]
    lines += block(CLEAN_CITIES, "Main comparison — 5 stationary cities")
    lines += [
        "### AMS — excluded from main comparison (see `ams_case_study.md`)",
        "",
        "AMS is non-stationary (April ramp-up + Aug–Sep flattening), so its metrics are",
        "not comparable; it is reported separately as a case study.",
    ]
    (OUT / "regression_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    ams_figure()
    ams_writeup()
    regression_summary()
    print("Wrote ams_nonstationarity.png, ams_case_study.md, regression_summary.md")
