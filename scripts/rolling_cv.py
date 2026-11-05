"""Rolling-origin CV (4 folds) for regression and peak classification, LOA+MEL."""
import os

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (mean_absolute_error, r2_score, brier_score_loss, log_loss,
                             average_precision_score, precision_recall_fscore_support)
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
OUT = os.path.join(ROOT, "results"); os.makedirs(OUT, exist_ok=True)
PANEL = os.path.join(ROOT, "panel")

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]
FEATS_LIN = [f for f in FEATS if f != "doy"]

df = pd.concat([pd.read_csv(os.path.join(PANEL, f"panel_{c}.csv.gz"), parse_dates=["timestamp"])
                for c in ["LOA", "MEL"]], ignore_index=True)
df = df.dropna(subset=FEATS + ["y"]).reset_index(drop=True)
print("rows:", len(df))

FOLDS = [("2023-06-01", "2023-06-30"), ("2023-07-01", "2023-07-31"),
         ("2023-08-01", "2023-08-31"), ("2023-09-01", "2023-09-30")]

rows = []
for fold, (te_start, te_end) in enumerate(FOLDS, start=1):
    te_start = pd.Timestamp(te_start); te_end = pd.Timestamp(te_end)
    tr = df["timestamp"] < (te_start - pd.Timedelta(days=1))
    te = (df["timestamp"] >= te_start) & (df["timestamp"] <= te_end)
    # calibration window = last two months before the test month
    cal_start = te_start - pd.DateOffset(months=2) - pd.Timedelta(days=1)
    cal = (df["timestamp"] >= cal_start) & (df["timestamp"] < te_start - pd.Timedelta(days=1))

    dtr, dte, dcal = df[tr], df[te], df[cal]
    ytr = dtr["y"].values
    y_cap = np.percentile(ytr, 99.9)
    sc = StandardScaler().fit(dtr[FEATS_LIN].values)
    ridge = Ridge(alpha=1.0).fit(sc.transform(dtr[FEATS_LIN].values), ytr)
    hgb = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                        min_samples_leaf=40, random_state=0).fit(dtr[FEATS].values, np.log1p(ytr))

    for city in ["LOA", "MEL"]:
        m = dte["city"] == city
        y = dte.loc[m, "y"].values
        preds = {
            "t-24": dte.loc[m, "lag24"].values,
            "ridge": np.clip(ridge.predict(sc.transform(dte.loc[m, FEATS_LIN].values)), 0, y_cap),
            "hgb": np.clip(np.expm1(hgb.predict(dte.loc[m, FEATS].values)), 0, y_cap),
        }
        for model, p in preds.items():
            rows.append(dict(fold=fold, test_month=str(te_start.date()), city=city, model=model,
                             MAE=mean_absolute_error(y, p),
                             WAPE=np.abs(y - p).sum() / max(np.abs(y).sum(), 1e-9),
                             R2=r2_score(y, p)))

    # ---- classification (eligible sites only) ----
    elig = df["is_eligible"] == 1
    trc, tec, calc = tr & elig, te & elig, cal & elig
    Xtr, ytrc = df.loc[trc, FEATS].values, df.loc[trc, "peak"].values
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                         min_samples_leaf=40, random_state=0).fit(Xtr, ytrc)
    p_cal = clf.predict_proba(df.loc[calc, FEATS].values)[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(p_cal, df.loc[calc, "peak"].values)

    for city in ["LOA", "MEL"]:
        m = tec & (df["city"] == city)
        y = df.loc[m, "peak"].values
        p_raw = clf.predict_proba(df.loc[m, FEATS].values)[:, 1]
        p = iso.predict(p_raw)
        base = ytrc.mean()
        ths = np.quantile(p, np.linspace(0.5, 0.999, 200))
        best = (0.5, -1)
        for th in ths:
            _, _, f1, _ = precision_recall_fscore_support(y, (p >= th).astype(int), average="binary", zero_division=0)
            if f1 > best[1]:
                best = (th, f1)
        pr, rc, f1, _ = precision_recall_fscore_support(y, (p >= best[0]).astype(int), average="binary", zero_division=0)
        rows.append(dict(fold=fold, test_month=str(te_start.date()), city=city, model="peak_hgb",
                         MAE=np.nan, WAPE=np.nan, R2=np.nan,
                         Brier=brier_score_loss(y, p), PR_AUC=average_precision_score(y, p),
                         event_rate=y.mean(), F1=f1, precision=pr, recall=rc))
    print(f"fold {fold} done: train={len(dtr):,} test={len(dte):,}")

res = pd.DataFrame(rows)
res.to_csv(os.path.join(OUT, "rolling_cv.csv"), index=False)

reg = res.dropna(subset=["WAPE"])
print(reg.pivot_table(index=["city", "model"], columns="fold", values="WAPE").round(3).to_string())

# ---- figure: WAPE by fold ----
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
for ax, city in zip(axes, ["LOA", "MEL"]):
    sub = reg[reg.city == city]
    for model, color, marker in [("t-24", "grey", "o"), ("ridge", "#d7301f", "s"), ("hgb", "#2b8cbe", "^")]:
        s = sub[sub.model == model].sort_values("fold")
        ax.plot(s["fold"], s["WAPE"], marker=marker, color=color, label=model)
    ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["Jun", "Jul", "Aug", "Sep"])
    ax.set_xlabel(L("测试月", "test month")); ax.set_ylabel("WAPE")
    ax.set_title(city); ax.legend(frameon=False); ax.grid(alpha=.25)
fig.suptitle(L("滚动 4 折：WAPE 随测试月变化", "Rolling-origin CV: WAPE"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_cv_wape.png"), dpi=150); plt.close()

# ---- figure: classification metrics ----
fig, ax = plt.subplots(figsize=(7.5, 4.0))
cls = res[res.model == "peak_hgb"]
for city, color in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    s = cls[cls.city == city].sort_values("fold")
    ax.plot(s["fold"], s["PR_AUC"], marker="o", color=color, label=f"{city} PR-AUC")
    ax.plot(s["fold"], s["Brier"] * 10, marker="x", ls="--", color=color, label=f"{city} Brier×10")
ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["Jun", "Jul", "Aug", "Sep"])
ax.set_xlabel(L("测试月", "test month"))
ax.set_title(L("滚动 4 折：峰值分类", "Rolling CV: peak classification"))
ax.legend(fontsize=7, frameon=False, ncol=2); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_cv_class.png"), dpi=150); plt.close()
print("saved", OUT)
