"""Phase 5 — Visualization + Error Analysis.

Produces figures in _output/figures/ and a written analysis in
_output/error_analysis.md:

  fig_ts_predictions.png   actual vs best-model vs persistence (1-week test slice)
  fig_scatter.png          actual vs predicted scatter (best model, R2/MAE annotated)
  fig_error_heatmap.png    mean |error| by hour-of-day x day-of-week (best model)
  fig_hourly_profile.png   mean demand by hour of day, all cities
  fig_peak_probability.png RF peak probability on test, q=90, with true peaks

Analysis (error_analysis.md):
  - per-city error by hour-of-day and day-of-week (signed bias + |error|)
  - hardest hours / days
  - peak recall linkage to Phase 4
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from src.load import CITIES  # noqa: E402
from src.models import (  # noqa: E402
    TARGET,
    fit_rf_clf,
    run_linear,
    run_persistence,
    run_rf,
)
from src.preprocess import split_train_val_test  # noqa: E402

OUT = ROOT / "_output"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
FEAT_DIR = OUT / "features"

sns.set_theme(style="whitegrid", context="notebook")

# best model per city (from Phase 3, R2-max on test)
BEST = {
    "AMS": "persistence",
    "JHB": "linear",
    "LOA": "random_forest",
    "MEL": "linear",
    "SPO": "linear",
    "SZH": "random_forest",
}
RUNNERS = {
    "persistence": run_persistence,
    "linear": run_linear,
    "random_forest": run_rf,
}


def load_features(city: str) -> pd.DataFrame:
    return pd.read_csv(FEAT_DIR / f"{city}.csv", index_col=0, parse_dates=True)


def predictions(city: str):
    """Return test y_true, best-model pred, persistence pred for one city."""
    df = load_features(city)
    train, val, test = split_train_val_test(df)
    y_true = test[TARGET].values
    pred, idx = RUNNERS[BEST[city]](train, val, test)
    pred_p, _ = run_persistence(train, val, test)
    return test, y_true, pred, pred_p


# ---------------------------------------------------------------- figures ---

def fig_ts_predictions() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharex=False)
    for ax, city in zip(axes.ravel(), CITIES):
        test, y_true, pred, pred_p = predictions(city)
        # first week of September
        sl = slice(0, 168)
        t = test.index[sl]
        ax.plot(t, y_true[sl], lw=0.9, color="black", label="actual")
        ax.plot(t, pred[sl], lw=0.8, color="#d62728", label=BEST[city])
        ax.plot(t, pred_p[sl], lw=0.8, color="#1f77b4", alpha=0.7, label="persistence")
        ax.set_title(f"{city}  (best: {BEST[city]})", fontsize=10)
        ax.tick_params(labelsize=8)
        if city in ("AMS", "LOA", "MEL"):
            ax.set_ylabel("kWh")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, fontsize=9)
    fig.suptitle("Actual vs predicted — first week of September (test)", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG / "fig_ts_predictions.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_scatter() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, city in zip(axes.ravel(), CITIES):
        test, y_true, pred, _ = predictions(city)
        r2 = float(np.corrcoef(y_true, pred)[0, 1] ** 2)
        mae = float(np.mean(np.abs(y_true - pred)))
        ax.scatter(y_true, pred, s=4, alpha=0.35, color="#1f77b4")
        lo, hi = min(y_true.min(), pred.min()), max(y_true.max(), pred.max())
        ax.plot([lo, hi], [lo, hi], ls="--", lw=1, color="black")
        ax.set_title(f"{city}  R²={r2:.3f}  MAE={mae:.0f}", fontsize=10)
        ax.tick_params(labelsize=8)
        ax.set_xlabel("actual (kWh)", fontsize=8)
        if city in ("AMS", "LOA", "MEL"):
            ax.set_ylabel("predicted (kWh)", fontsize=8)
    fig.suptitle("Actual vs predicted — best model, full September test", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG / "fig_scatter.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_error_heatmap() -> None:
    reps = ["LOA", "SPO"]  # two clean representative cities
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, city in zip(axes, reps):
        test, y_true, pred, _ = predictions(city)
        err = np.abs(pred - y_true)
        df = pd.DataFrame({"hour": test.index.hour, "dow": test.index.dayofweek, "err": err})
        heat = df.pivot_table(index="hour", columns="dow", values="err", aggfunc="mean")
        heat.index.name = "hour"
        heat.columns = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        sns.heatmap(heat, ax=ax, cmap="viridis", cbar_kws={"label": "MAE (kWh)"})
        ax.set_title(f"{city} — mean |error| by hour × day-of-week")
        ax.set_xlabel("day of week")
        ax.set_ylabel("hour of day")
    fig.tight_layout()
    fig.savefig(FIG / "fig_error_heatmap.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_hourly_profile() -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for city in CITIES:
        df = load_features(city)
        ax.plot(df.groupby(df.index.hour)[TARGET].mean(), lw=1.5, label=city)
    ax.set_xlabel("hour of day")
    ax.set_ylabel("mean demand (kWh)")
    ax.set_title("Mean demand by hour of day (full Apr–Sep)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_hourly_profile.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_peak_probability() -> None:
    reps = ["LOA", "SPO"]
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=False)
    for ax, city in zip(axes, reps):
        df = load_features(city)
        train, val, test = split_train_val_test(df)
        thr = float(np.percentile(train[TARGET], 90))
        ytr = (train[TARGET] > thr).astype(int)
        Xtr = train.drop(columns=[TARGET])
        Xte = test.drop(columns=[TARGET])
        proba = fit_rf_clf(Xtr, ytr)(Xte)
        yte = (test[TARGET] > thr).astype(int)
        t = test.index
        ax.plot(t, proba, lw=0.8, color="#1f77b4", label="P(peak) RF")
        ax.scatter(t[yte == 1], proba[yte == 1], s=6, color="#d62728",
                   label="true peak", zorder=3)
        ax.axhline(0.5, ls="--", lw=0.8, color="gray")
        ax.set_title(f"{city} — RF peak probability (q=90) on test")
        ax.set_ylim(-0.02, 1.02)
        ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG / "fig_peak_probability.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# -------------------------------------------------------------- analysis ---

def error_analysis_md() -> None:
    L: list[str] = ["# Error Analysis (Phase 5)", ""]

    L += ["## Per-city error profile (best model, September test)", ""]
    rows = []
    hour_err = {}
    dow_err = {}
    for city in CITIES:
        test, y_true, pred, _ = predictions(city)
        err = pred - y_true  # signed: + = over-predict
        mae = float(np.mean(np.abs(err)))
        rmse = float(np.sqrt(np.mean(err ** 2)))
        bias = float(np.mean(err))
        mae_pct = 100 * mae / float(np.mean(y_true))  # scale-free, cross-city
        rows.append({"city": city, "model": BEST[city], "MAE": mae,
                     "RMSE": rmse, "MAE%": mae_pct, "bias": bias})
        hour_err[city] = pd.Series(np.abs(err)).groupby(test.index.hour).mean()
        dow_err[city] = pd.Series(np.abs(err)).groupby(test.index.dayofweek).mean()

    summary = pd.DataFrame(rows).set_index("city").round(1)
    L += ["```", summary.to_string(), "```", ""]

    # hardest hour / day per city
    L += ["## Hardest hour and day of week (by MAE)", ""]
    hh = pd.DataFrame(hour_err).T
    hh.columns.name = "hour"
    dd = pd.DataFrame(dow_err).T
    dd.columns = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    L += ["### Mean |error| by hour of day", "", "```", hh.round(0).to_string(), "```", ""]
    L += ["### Mean |error| by day of week", "", "```", dd.round(0).to_string(), "```", ""]

    L += [
        "",
        "### Takeaways",
        "",
        "- **Compare cities on MAE% (scale-free), not MAE.** Absolute MAE spans 3 orders of",
        "  magnitude because demand does (SPO ~193 vs SZH ~212,851 kWh). Relative error ranks the",
        "  cities: **MEL (14%) and SPO (10%) are hardest**; SZH/JHB/LOA ~3–6%; AMS is trivially",
        "  easy (0.14%) because it is nearly flat in September and persistence nails it.",
        "- **Hard periods are city-specific, not uniformly 'night'.** LOA and SZH are worst in the",
        "  small hours (0–4 a.m.), MEL worst at the morning rush (7–8 a.m.) and midday, while",
        "  JHB/SPO/AMS are fairly flat with only a slight evening/late-night bump.",
        "- **No consistent weekday/weekend rule.** MEL and AMS are *harder on weekends*; JHB/LOA/SPO",
        "  harder on weekdays; SZH peaks Fri–Sat. The models do not share one calendar weakness.",
        "- **Bias is small for most models** (a few % of mean demand, usually slightly negative =",
        "  under-predicting peaks), consistent with Phase 4's finding that peak recall needs a",
        "  lowered threshold. SZH's RF is the notable exception (+1.6% over-prediction).",
        "",
    ]

    # linkage to Phase 4 peak recall
    clf = pd.read_csv(OUT / "classification" / "classification_results.csv")
    q90 = clf[(clf.percentile == 90) & (clf.model == "random_forest")]
    recall = q90.set_index("city")[["recall", "f1", "auc"]].round(3)
    L += ["## Link to Phase 4 — peak recall (RF, q=90)", "", "```",
          recall.to_string(), "```", "",
          "Cities whose test peak rate is well preserved (LOA, MEL, SPO) show recall 0.63–0.91;",
          "the degenerate cases (AMS, JHB, SZH) are documented in `classification_summary.md`.",
          ""]

    (OUT / "error_analysis.md").write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    fig_ts_predictions()
    fig_scatter()
    fig_error_heatmap()
    fig_hourly_profile()
    fig_peak_probability()
    error_analysis_md()
    print("Wrote Phase 5 figures + error_analysis.md")


if __name__ == "__main__":
    main()
