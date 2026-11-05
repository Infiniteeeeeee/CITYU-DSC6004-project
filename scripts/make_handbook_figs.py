"""Explanatory figures for the handbook edition (concepts, timelines, confusion matrices)."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "figures", "handbook")
os.makedirs(OUT, exist_ok=True)

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

# ---------------- 1. peak definition on a real series ----------------
vol = pd.read_csv(os.path.join(DATA, "LOA", "volume.csv"), index_col=0, parse_dates=True)
vol.columns = vol.columns.astype(int)
sites = pd.read_csv(os.path.join(DATA, "LOA", "sites.csv")).set_index("site_id")
cand = vol.columns[(vol > 0).sum(axis=0) > 3000]
# pick a medium-size site with a visible daily rhythm
score = vol[cand].std() / (vol[cand].mean() + 1e-9)
sid = int(cand[np.argmin(np.abs(score - 0.9))])
x = vol[sid]

thr = pd.Series(np.nan, index=x.index)
for h in range(24):
    s = x.iloc[h::24]
    m = s.shift(1).rolling(28, min_periods=14).mean()
    sd = s.shift(1).rolling(28, min_periods=14).std()
    thr.iloc[h::24] = (m + 2 * sd).values

seg = slice("2023-07-01", "2023-07-14")
fig, ax = plt.subplots(figsize=(12, 4.2))
ax.plot(x.loc[seg].index, x.loc[seg].values, lw=1.3, color="#2b8cbe", label=L("小时电量", "hourly volume"))
ax.plot(thr.loc[seg].index, thr.loc[seg].values, lw=1.2, ls="--", color="#d7301f",
        label=L("阈值 = 过去 28 天同小时均值 + 2σ", "threshold = rolling 28d mean + 2sd"))
peaks = x.loc[seg][x.loc[seg] > thr.loc[seg]]
ax.scatter(peaks.index, peaks.values, s=28, color="#d7301f", zorder=5, label=L("峰值事件", "peak event"))
ax.set_ylabel(L("电量 (kWh)", "volume (kWh)")); ax.set_xlabel("")
ax.set_title(L(f"峰值事件是如何定义的（LOA 站点 {sid}，2023-07-01 ~ 07-14）",
               f"How a peak event is defined (LOA site {sid})"))
ax.legend(frameon=False, fontsize=8); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_peak_definition.png"), dpi=150); plt.close()
print("peak definition:", sid, "events in window:", len(peaks))

# ---------------- 2. rolling-origin timeline ----------------
fig, ax = plt.subplots(figsize=(11, 3.6))
months = ["4月", "5月", "6月", "7月", "8月", "9月"]
folds = [("Fold 1", 2, "6月"), ("Fold 2", 3, "7月"), ("Fold 3", 4, "8月"), ("Fold 4", 5, "9月")]
for i, (name, test_idx, label) in enumerate(folds):
    y = len(folds) - i
    ax.barh(y, test_idx, left=0, height=0.55, color="#9ecae1", edgecolor="white")
    ax.barh(y, 1, left=test_idx, height=0.55, color="#d7301f", edgecolor="white")
    ax.text(-0.15, y, name, ha="right", va="center", fontsize=9)
    ax.text(test_idx + 0.5, y, L("测试月 ", "test ") + label, ha="center", va="center", fontsize=8, color="white")
ax.set_xlim(0, 6); ax.set_ylim(0.3, 4.9)
ax.set_xticks(np.arange(6) + 0.5); ax.set_xticklabels(months)
ax.set_yticks([]); ax.set_xlabel("")
ax.set_title(L("滚动原点验证：蓝=训练，红=测试，段间留 1 天间隔", "Rolling-origin validation"))
for spine in ["left", "right", "top"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_timeline.png"), dpi=150); plt.close()

# ---------------- 3. pipeline diagram ----------------
fig, ax = plt.subplots(figsize=(12, 3.4))
ax.set_xlim(0, 12); ax.set_ylim(0, 3.4); ax.axis("off")
steps = [
    ("原始数据\n6 城 × 10 表", "#deebf7"),
    ("数据核查\n缺失/断档/表头", "#deebf7"),
    ("构建面板\n站点 × 小时", "#c6dbef"),
    ("特征工程\n滞后/滚动/日历", "#c6dbef"),
    ("时间切分\n滚动 4 折", "#c7e9c0"),
    ("建模\n基线/Ridge/HGB/LSTM", "#c7e9c0"),
    ("评估\nWAPE/Brier/校准", "#fdd0a2"),
    ("误差分析\n分位/自助/ACF", "#fdd0a2"),
]
w, gap = 1.25, 0.17
for i, (text, color) in enumerate(steps):
    x = 0.15 + i * (w + gap)
    box = FancyBboxPatch((x, 1.15), w, 1.0, boxstyle="round,pad=0.03,rounding_size=0.08",
                         facecolor=color, edgecolor="#555", linewidth=0.8)
    ax.add_patch(box)
    ax.text(x + w / 2, 1.65, text, ha="center", va="center", fontsize=8.2)
    if i < len(steps) - 1:
        ax.add_patch(FancyArrowPatch((x + w + 0.01, 1.65), (x + w + gap - 0.02, 1.65),
                                     arrowstyle="-|>", mutation_scale=10, color="#555"))
ax.text(0.15, 2.75, L("从原始数据到结论：本项目的八个步骤", "Project pipeline"), fontsize=11, weight="bold")
ax.text(0.15, 0.55, L("每一步的脚本见附录 C；图表与结果表均保存在 figures/ 与 results/ 目录。",
                      "Scripts in Appendix C; figures and result tables live in figures/ and results/"),
        fontsize=8, color="#555")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_pipeline.png"), dpi=150); plt.close()

# ---------------- 4. LSTM architecture ----------------
fig, ax = plt.subplots(figsize=(11, 3.6))
ax.set_xlim(0, 11); ax.set_ylim(0, 3.6); ax.axis("off")
def box(x, y, w, h, text, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.08",
                                facecolor=color, edgecolor="#555", linewidth=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5)
box(0.2, 1.2, 2.2, 1.1, L("输入：过去 24 小时\n电量（按站点 z-score）", "Input: last 24h\nz-scored volume"), "#deebf7")
box(2.9, 1.2, 2.0, 1.1, L("LSTM\n单层 64 维", "LSTM\n1 layer, 64"), "#c6dbef")
box(5.3, 2.3, 2.2, 0.9, L("日历特征\n时刻 sin/cos + 星期", "Calendar\nsin/cos + dow"), "#e5f5e0")
box(5.3, 0.4, 2.2, 0.9, L("站点静态属性\n桩数/面积/POI", "Site statics"), "#e5f5e0")
box(8.0, 1.2, 2.2, 1.1, L("全连接层\n输出下一小时", "FC layer\nnext hour"), "#fdd0a2")
for (x1, y1, x2, y2) in [(2.4, 1.75, 2.9, 1.75), (4.9, 1.75, 5.3, 2.6), (4.9, 1.75, 5.3, 0.9), (7.5, 1.75, 8.0, 1.75)]:
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color="#555"))
ax.text(0.2, 3.1, L("LSTM 的结构：序列分支 + 静态分支拼接", "LSTM architecture"), fontsize=11, weight="bold")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_lstm_arch.png"), dpi=150); plt.close()

# ---------------- 5. peak rate by month ----------------
panel = pd.concat([pd.read_csv(os.path.join(ROOT, "panel", f"panel_{c}.csv.gz"),
                               usecols=["city", "timestamp", "peak", "is_eligible"],
                               parse_dates=["timestamp"]) for c in ["LOA", "MEL"]])
panel = panel[panel.is_eligible == 1]
panel["month"] = panel.timestamp.dt.month
g = panel.groupby(["city", "month"])["peak"].mean().unstack(0)
fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(6)
for city, color in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    ax.bar(x + (0.2 if city == "LOA" else -0.2), g[city].values * 100, width=0.38, color=color, label=city)
ax.set_xticks(x); ax.set_xticklabels(["4月", "5月", "6月", "7月", "8月", "9月"])
ax.set_ylabel(L("峰值事件占比 (%)", "peak event rate (%)"))
ax.set_title(L("峰值率随月份漂移：8 月最平静，9 月最活跃（LOA）", "Monthly peak rate drift"))
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_peak_month.png"), dpi=150); plt.close()
print(g.round(3).to_string())

# ---------------- 6/7. confusion matrices (fold 4) ----------------
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]

for city in ["LOA", "MEL"]:
    d = pd.read_csv(os.path.join(ROOT, "panel", f"panel_{city}.csv.gz"), parse_dates=["timestamp"])
    d = d[(d.is_eligible == 1)].dropna(subset=FEATS + ["y"])
    tr = d[d.timestamp < "2023-08-31"]
    cal = d[(d.timestamp >= "2023-07-01") & (d.timestamp < "2023-08-31")]
    te = d[d.timestamp >= "2023-09-01"]
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                         min_samples_leaf=40, random_state=0).fit(tr[FEATS].values, tr["peak"].values)
    p_cal = clf.predict_proba(cal[FEATS].values)[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(p_cal, cal["peak"].values)
    p = iso.predict(clf.predict_proba(te[FEATS].values)[:, 1])
    y = te["peak"].values
    ths = np.quantile(p, np.linspace(0.5, 0.999, 200))
    best = (0.5, -1)
    for th in ths:
        _, _, f1, _ = precision_recall_fscore_support(y, (p >= th).astype(int), average="binary", zero_division=0)
        if f1 > best[1]:
            best = (th, f1)
    cm = confusion_matrix(y, (p >= best[0]).astype(int))
    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_xticklabels([L("预测：非峰值", "pred: no"), L("预测：峰值", "pred: peak")])
    ax.set_yticks([0, 1]); ax.set_yticklabels([L("真实：非峰值", "true: no"), L("真实：峰值", "true: peak")])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=11,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_title(f"{city} " + L("峰值分类混淆矩阵（9 月）", "confusion matrix (Sep)"))
    plt.colorbar(im, ax=ax, shrink=.85)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, f"hb_confusion_{city}.png"), dpi=150); plt.close()
    pr, rc, f1, _ = precision_recall_fscore_support(y, (p >= best[0]).astype(int), average="binary", zero_division=0)
    print(city, "threshold", round(best[0], 3), "P/R/F1", round(pr, 3), round(rc, 3), round(f1, 3), "cm", cm.tolist())
print("saved to", OUT)
