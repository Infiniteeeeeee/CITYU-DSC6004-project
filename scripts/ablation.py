"""Ablation: per-city vs pooled(LOA+MEL) vs pooled(+SZH)."""
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
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
COLS = ["timestamp", "city", "site_id", "y"] + FEATS

def load(city):
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"), usecols=COLS, parse_dates=["timestamp"])
    return d.dropna(subset=FEATS + ["y"])

data = {c: load(c) for c in ["LOA", "MEL"]}
szh = load("SZH")
rng = np.random.default_rng(0)
if len(szh) > 1_500_000:
    szh = szh.sample(1_500_000, random_state=0)
print("rows:", {k: len(v) for k, v in data.items()}, "szh:", len(szh))

def wape(y, p):
    return np.abs(y - p).sum() / max(np.abs(y).sum(), 1e-9)

rows = []
for fold, (te_start, te_end) in ((3, ("2023-08-01", "2023-08-31")), (4, ("2023-09-01", "2023-09-30"))):
    te_start, te_end = pd.Timestamp(te_start), pd.Timestamp(te_end)
    for city in ["LOA", "MEL"]:
        d = data[city]
        tr = d[d.timestamp < te_start - pd.Timedelta(days=1)]
        te = d[(d.timestamp >= te_start) & (d.timestamp <= te_end)]
        y_cap = np.percentile(tr["y"], 99.9)
        yte = te["y"].values

        variants = {"per-city": tr}
        variants["pooled(LOA+MEL)"] = pd.concat([data["LOA"], data["MEL"]], ignore_index=True)
        variants["pooled(+SZH)"] = pd.concat([data["LOA"], data["MEL"], szh], ignore_index=True)

        for name, dtr in variants.items():
            dtr = dtr[dtr.timestamp < te_start - pd.Timedelta(days=1)]
            ytr = dtr["y"].values
            sc = StandardScaler().fit(dtr[FEATS].values)
            ridge = Ridge(alpha=1.0).fit(sc.transform(dtr[FEATS].values), ytr)
            hgb = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08,
                                                max_leaf_nodes=31, min_samples_leaf=40,
                                                random_state=0).fit(dtr[FEATS].values, np.log1p(ytr))
            p_ridge = np.clip(ridge.predict(sc.transform(te[FEATS].values)), 0, y_cap)
            p_hgb = np.clip(np.expm1(hgb.predict(te[FEATS].values)), 0, y_cap)
            rows.append(dict(fold=fold, city=city, variant=name, model="ridge",
                             WAPE=wape(yte, p_ridge), MAE=mean_absolute_error(yte, p_ridge)))
            rows.append(dict(fold=fold, city=city, variant=name, model="hgb",
                             WAPE=wape(yte, p_hgb), MAE=mean_absolute_error(yte, p_hgb)))
    print("fold", fold, "done")

res = pd.DataFrame(rows)
res.to_csv(os.path.join(OUT, "ablation_pooling.csv"), index=False)
print(res.round(3).to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=False)
for ax, city in zip(axes, ["LOA", "MEL"]):
    sub = res[res.city == city]
    variants = ["per-city", "pooled(LOA+MEL)", "pooled(+SZH)"]
    x = np.arange(len(variants))
    for i, (model, color) in enumerate([("ridge", "#d7301f"), ("hgb", "#2b8cbe")]):
        vals = []
        for v in variants:
            vals.append(sub[(sub.variant == v) & (sub.model == model)]["WAPE"].mean())
        ax.bar(x + (i - 0.5) * 0.35, vals, width=0.35, color=color, label=model)
        for xi, v in zip(x + (i - 0.5) * 0.35, vals):
            ax.text(xi, v + 0.01, f"{v:.3f}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(["单城训练", "两城池化", "加 SZH"], fontsize=8)
    ax.set_ylabel("WAPE（8/9 月均值）"); ax.set_title(city)
    ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_ablation_pooling.png"), dpi=150); plt.close()
print("saved")
