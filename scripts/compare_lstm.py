"""Fair comparison: LSTM vs Ridge vs HGB on exactly the same test rows."""
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
OUT = os.path.join(ROOT, "results")
PANEL = os.path.join(ROOT, "panel")

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]

rows = []
for city in ["LOA", "MEL"]:
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"), parse_dates=["timestamp"])
    d = d.dropna(subset=FEATS + ["y"])
    tr = d[d.timestamp < "2023-08-31"]
    te = d[d.timestamp >= "2023-09-01"]

    lp = pd.read_csv(os.path.join(OUT, f"lstm_pred_{city}.csv"), parse_dates=["timestamp"])
    lp["timestamp"] = pd.to_datetime(lp["timestamp"])
    matched = te.merge(lp, on=["timestamp", "site_id"], how="inner", suffixes=("", "_lstm"))
    print(f"{city}: matched rows {len(matched):,} of {len(te):,}")

    y_cap = np.percentile(tr["y"], 99.9)
    sc = StandardScaler().fit(tr[FEATS].values)
    ridge = Ridge(alpha=1.0).fit(sc.transform(tr[FEATS].values), tr["y"].values)
    hgb = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                        min_samples_leaf=40, random_state=0).fit(tr[FEATS].values, np.log1p(tr["y"].values))

    y = matched["y"].values
    preds = {
        "LSTM": matched["pred"].values,
        "Ridge": np.clip(ridge.predict(sc.transform(matched[FEATS].values)), 0, y_cap),
        "HGB": np.clip(np.expm1(hgb.predict(matched[FEATS].values)), 0, y_cap),
        "t-24": matched["lag24"].values,
    }
    for model, p in preds.items():
        rows.append(dict(city=city, model=model, n=len(y),
                         WAPE=np.abs(y - p).sum() / max(y.sum(), 1e-9),
                         MAE=mean_absolute_error(y, p)))

res = pd.DataFrame(rows)
res.to_csv(os.path.join(OUT, "compare_lstm.csv"), index=False)
print(res.round(3).to_string(index=False))

fig, ax = plt.subplots(figsize=(7.5, 4.0))
cities = ["LOA", "MEL"]
models = ["t-24", "Ridge", "HGB", "LSTM"]
colors = ["grey", "#d7301f", "#2b8cbe", "#31a354"]
x = np.arange(len(cities))
for i, (m, c) in enumerate(zip(models, colors)):
    vals = [res[(res.city == cc) & (res.model == m)]["WAPE"].iloc[0] for cc in cities]
    ax.bar(x + (i - 1.5) * 0.2, vals, width=0.2, color=c, label=m)
    for xi, v in zip(x + (i - 1.5) * 0.2, vals):
        ax.text(xi, v + 0.008, f"{v:.3f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(cities)
ax.set_ylabel("WAPE"); ax.set_title(L("同一测试集上的模型对比（9 月）", "Models on identical test rows (Sep)"))
ax.legend(frameon=False, ncol=4, fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_lstm_compare.png"), dpi=150); plt.close()
print("saved")
