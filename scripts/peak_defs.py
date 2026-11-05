"""Sensitivity of the peak definition: +2sd vs x4 median vs static P95."""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, average_precision_score, precision_recall_fscore_support
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

d = pd.read_csv(os.path.join(PANEL, "panel_LOA.csv.gz"), parse_dates=["timestamp"])
d = d[d.is_eligible == 1].dropna(subset=FEATS + ["y"]).reset_index(drop=True)
wide = d.pivot_table(index="timestamp", columns="site_id", values="y", aggfunc="first")

# (b) rolling median x4
thr4 = pd.DataFrame(np.nan, index=wide.index, columns=wide.columns)
for h in range(24):
    s = wide.iloc[h::24]
    med = s.shift(1).rolling(28, min_periods=14).median()
    thr4.iloc[h::24] = (med * 4).values
peak4 = (wide > thr4) & thr4.notna()

# (c) static P95 computed on Apr-Jul positive values
train_period = wide.index < "2023-08-01"
thr95 = {}
for c in wide.columns:
    pos = wide.loc[train_period, c]
    pos = pos[pos > 0]
    thr95[c] = np.percentile(pos, 95) if len(pos) > 50 else np.nan
peak95 = wide.gt(pd.Series(thr95), axis=1)

labels = pd.DataFrame({
    "peak_2sd": d.set_index(["timestamp", "site_id"])["peak"],
}).reset_index()
for name, mat in [("peak_x4", peak4), ("peak_p95", peak95)]:
    long = mat.stack().rename(name).reset_index()
    long.columns = ["timestamp", "site_id", name]
    labels = labels.merge(long, on=["timestamp", "site_id"], how="left")

d = d.merge(labels, on=["timestamp", "site_id"], how="left")

tr = d.timestamp < "2023-08-31"
te = d.timestamp >= "2023-09-01"
rows = []
for name in ["peak_2sd", "peak_x4", "peak_p95"]:
    ytr, yte = d.loc[tr, name].values, d.loc[te, name].values
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                         min_samples_leaf=40, random_state=0).fit(d.loc[tr, FEATS].values, ytr)
    p = clf.predict_proba(d.loc[te, FEATS].values)[:, 1]
    ths = np.quantile(p, np.linspace(0.5, 0.999, 100))
    best = (0.5, -1)
    for th in ths:
        _, _, f1, _ = precision_recall_fscore_support(yte, (p >= th).astype(int), average="binary", zero_division=0)
        if f1 > best[1]:
            best = (th, f1)
    pr, rc, f1, _ = precision_recall_fscore_support(yte, (p >= best[0]).astype(int), average="binary", zero_division=0)
    rows.append(dict(definition=name, event_rate_all=d[name].mean(), event_rate_train=ytr.mean(),
                     event_rate_test=yte.mean(), Brier=brier_score_loss(yte, p),
                     PR_AUC=average_precision_score(yte, p), F1=f1, precision=pr, recall=rc))

res = pd.DataFrame(rows)
res.to_csv(os.path.join(OUT, "peak_definitions.csv"), index=False)
print(res.round(3).to_string(index=False))

fig, ax = plt.subplots(figsize=(7.5, 4.0))
x = np.arange(len(res))
ax.bar(x - 0.2, res["event_rate_test"] * 100, width=0.4, label=L("测试集事件率(%)", "test event rate %"), color="#2b8cbe")
ax.bar(x + 0.2, res["PR_AUC"], width=0.4, label="PR-AUC", color="#d7301f")
ax.set_xticks(x); ax.set_xticklabels(["均值+2σ", "中位数×4", "训练期P95"] if CJK else ["mean+2sd", "median x4", "train P95"])
ax.set_title(L("三种峰值定义的敏感性（LOA）", "Peak definition sensitivity (LOA)"))
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_peak_defs.png"), dpi=150); plt.close()
print("saved")
