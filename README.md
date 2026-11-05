# EV Charging Demand & Peak-Event Forecasting (CHARGED)

<a id="english"></a>
**English** | [中文](#chinese)

Reproducible analysis of next-hour EV charging demand and peak-event identification on the
[CHARGED](https://github.com/IntelligentSystemsLab/CHARGED) dataset (Scientific Data, 2025).
Two cities with genuine intraday dynamics are modelled — **Los Angeles (LOA)** and **Melbourne (MEL)** —
using a causal site-hour panel, rolling-origin validation, and a comparison of naive baselines, Ridge,
gradient-boosted trees and an LSTM.

## Key results

| Task | Metric | Baseline (t-24) | Best model |
|---|---|---|---|
| Next-hour demand, LOA | WAPE | 0.281 | **0.153** (LSTM; Ridge 0.167) |
| Next-hour demand, MEL | WAPE | 0.442 | **0.306** (LSTM; Ridge 0.324) |
| Peak classification, LOA | PR-AUC | 0.084 (base rate) | **0.386** (F1 0.425) |
| Peak classification, MEL | PR-AUC | 0.046 (base rate) | **0.187** (F1 0.287) |

Main error source: near-zero-demand hours (the lowest demand decile has WAPE 2.4–3.3 on LOA and 87–354 on MEL).

## Repository layout

```
.
├── README.md                # this file (bilingual)
├── requirements.txt         # pinned Python packages
├── .gitignore               # excludes data/ and panel/
├── PLAN.md                  # research plan and design decisions
├── RESULTS.md               # full experiment log with figures
├── scripts/                 # all code
├── figures/                 # generated figures (zh + en); en/ holds the English versions
├── results/                 # metric tables and diagnostic figures
├── report/                  # four Word deliverables
├── data/                    # NOT committed — download with scripts/download_data.py
└── panel/                   # NOT committed — rebuilt by scripts/build_panel.py
```

| Script | Purpose |
|---|---|
| `download_data.py` | Fetch the raw CHARGED tables (≈830 MB) from the public repository |
| `fix_headers.py` | Repair the malformed upstream headers (idempotent; `--revert` available) |
| `validate_data.py` | Schema and consistency checks for all six cities |
| `build_panel.py` | Build the site-hour panel with causal features and peak labels |
| `run_models.py` | Single-split run (`metrics_regression.csv`, `metrics_classification.csv`) |
| `rolling_cv.py` | Rolling 4-fold regression and peak classification |
| `ablation.py` | Single-city vs pooled vs +Shenzhen |
| `peak_defs.py` | Sensitivity to three peak definitions |
| `interpret.py` | Permutation importance, partial dependence, error by site size |
| `error_analysis.py` | Decile errors, residual ACF, bootstrap confidence intervals |
| `lstm_model.py` | LSTM training on GPU (optional, needs PyTorch) |
| `compare_lstm.py` | Aligned comparison on identical test rows |
| `make_figures.py`, `make_figures_en.py` | Data-characterisation figures |
| `make_handbook_figs*.py` | Concept diagrams used in the handbook |
| `make_remove_zero.py` | Optional: rebuild the `_remove_zero` variant locally (not used by the pipeline) |

## Quickstart

```bash
# 1. Environment (Python 3.12)
pip install -r requirements.txt

# 2. Raw data (not stored in git)
python scripts/download_data.py --cities LOA MEL SZH JHB SPO
python scripts/fix_headers.py --apply
python scripts/validate_data.py

# 3. Panel (~5 min)
python scripts/build_panel.py --cities LOA MEL SZH JHB SPO

# 4. Experiments (~20 min total)
python scripts/rolling_cv.py
python scripts/ablation.py
python scripts/peak_defs.py
python scripts/interpret.py
python scripts/error_analysis.py

# 5. Optional: LSTM (GPU, ~20 min). Needs the CUDA build of PyTorch.
python scripts/lstm_model.py
python scripts/compare_lstm.py
```

## Data

The raw dataset is **not committed** — it is ≈830 MB and GitHub rejects files over 100 MB.
`scripts/download_data.py` fetches the plain CSVs from the upstream repository.

> **Important:** the upstream files have malformed headers — `info.csv` for LOA/MEL/SPO/SZH is missing a
> comma (`total_siteBSCAN_eps`), and several `sites.csv`/`chargers.csv` name the key `site` instead of
> `site_id`. Always run `python scripts/fix_headers.py --apply` after downloading.

Two Amsterdam files (`duration.csv`, `distance.csv`) are only shipped inside `csv-larger-than-100MB.rar`
upstream. They are **not needed** for the main results; Amsterdam is excluded because 94% of its sites show
no intraday variation. Extract that archive with 7-Zip or WinRAR only if you need the full Amsterdam
distance matrix.

## Expected outputs

| File | Content |
|---|---|
| `metrics_regression.csv` | Single-split regression metrics |
| `rolling_cv.csv` | Rolling 4-fold metrics for regression and classification |
| `ablation_pooling.csv` | Pooling ablation |
| `peak_definitions.csv` | Three peak definitions |
| `compare_lstm.csv` | LSTM vs Ridge vs HGB on identical rows |
| `err_decile.csv`, `err_acf.csv`, `err_bootstrap.csv` | Error analysis |
| `importance.csv`, `pdp.csv` | Interpretability |

Sanity-check numbers: LOA WAPE 0.153, MEL WAPE 0.306, LOA PR-AUC 0.386, MEL PR-AUC 0.187.

## Design notes

- **Causal features only**: lags and rolling statistics are shifted by one hour; thresholds are fitted on the
  training period only. `sites.csv` aggregates (`total_*`, `avg_power`) are never used as features.
- **Rolling-origin validation**: training starts in April and expands monthly; June–September are test months
  in turn, with a one-day gap.
- **Peak label**: same-hour rolling 28-day mean + 2σ (causal). Two alternatives (×4 median, training-period P95)
  are provided for sensitivity analysis — the definition changes the event rate by roughly five times.
- **Weather dropped**: charging and weather timestamps are not on the same clock (13-hour offset in LOA, 0 in
  MEL), so weather is excluded rather than misaligned.
- **Random seeds** are fixed (0) in every script.

## Environment

Python 3.12.14 · pandas 3.0.1 · numpy 2.3.5 · scikit-learn 1.9.1 · matplotlib 3.11.2 ·
python-docx 1.2.0 · PyTorch 2.14.1+cu126 (optional, RTX 3060 6 GB).

## Reports

`report/` contains four Word deliverables: a 15-page Chinese report, a 32-page Chinese handbook,
a 13-page English report and a 28-page English handbook. They are generated by `make_report.py`,
`make_report_en.py`, `make_handbook.py` and `make_handbook_en.py`.

## Citation

If you use the data, cite the original dataset:

> Guo, Z., You, L., Zhu, R., Zhang, Y., & Yuen, C. (2025). A City-scale and Harmonized Dataset for Global
> Electric Vehicle Charging Demand Analysis. *Scientific Data*, 12, 1254.
> https://doi.org/10.1038/s41597-025-05584-7

---

<a id="chinese"></a>
# 中文版 / Chinese Version

[English](#english) | **中文**

本项目基于 [CHARGED](https://github.com/IntelligentSystemsLab/CHARGED) 数据集（Scientific Data, 2025），
对**下一小时电动汽车充电需求**与**高峰事件识别**做可复现的分析。建模只选了两个具有真实日内节律的城市
——**洛杉矶（LOA）**与**墨尔本（MEL）**，使用因果的“站点—小时”面板、滚动原点验证，并比较了朴素基线、
Ridge、梯度提升树与 LSTM。

## 主要结果

| 任务 | 指标 | 基线（昨日同时刻） | 最佳模型 |
|---|---|---|---|
| 下一小时需求，LOA | WAPE | 0.281 | **0.153**（LSTM；Ridge 0.167） |
| 下一小时需求，MEL | WAPE | 0.442 | **0.306**（LSTM；Ridge 0.324） |
| 峰值分类，LOA | PR-AUC | 0.084（基准率） | **0.386**（F1 0.425） |
| 峰值分类，MEL | PR-AUC | 0.046（基准率） | **0.187**（F1 0.287） |

主要误差来源：接近零需求的小时（最低需求十分位的 WAPE 在 LOA 为 2.4~3.3，MEL 为 87~354）。

## 仓库结构

```
.
├── README.md                # 本文件（中英双语）
├── requirements.txt         # 固定版本的 Python 依赖
├── .gitignore               # 排除 data/ 与 panel/
├── PLAN.md                  # 研究方案与设计决策
├── RESULTS.md               # 完整实验记录（含图）
├── scripts/                 # 全部代码
├── figures/                 # 生成的图（中文 + en/ 英文版）
├── results/                 # 指标表与诊断图
├── report/                  # 四份 Word 文档
├── data/                    # 不入库 —— 用 scripts/download_data.py 下载
└── panel/                   # 不入库 —— 用 scripts/build_panel.py 重建
```

| 脚本 | 作用 |
|---|---|
| `download_data.py` | 从公开仓库拉取原始数据（约 830 MB） |
| `fix_headers.py` | 修复上游损坏的表头（幂等，可 `--revert`） |
| `validate_data.py` | 六城数据的结构与一致性检查 |
| `build_panel.py` | 构建带因果特征与峰值标签的站点—小时面板 |
| `run_models.py` | 单次切分实验（产出 `metrics_regression.csv`、`metrics_classification.csv`） |
| `rolling_cv.py` | 滚动 4 折回归与峰值分类 |
| `ablation.py` | 单城 / 池化 / 加深圳的消融 |
| `peak_defs.py` | 三种峰值定义的敏感性 |
| `interpret.py` | 置换重要性、部分依赖、按站点规模的误差 |
| `error_analysis.py` | 十分位误差、残差 ACF、自助置信区间 |
| `lstm_model.py` | GPU 上的 LSTM 训练（可选，需 PyTorch） |
| `compare_lstm.py` | 同一测试行上的对齐比较 |
| `make_figures.py`、`make_figures_en.py` | 数据特征图（中/英） |
| `make_handbook_figs*.py` | 手册用的示意图 |
| `make_remove_zero.py` | 可选：本地重建 `_remove_zero` 版本（主流程未使用） |

## 快速开始

```bash
# 1. 环境（Python 3.12）
pip install -r requirements.txt

# 2. 原始数据（不在仓库中）
python scripts/download_data.py --cities LOA MEL SZH JHB SPO
python scripts/fix_headers.py --apply
python scripts/validate_data.py

# 3. 构建面板（约 5 分钟）
python scripts/build_panel.py --cities LOA MEL SZH JHB SPO

# 4. 实验（合计约 20 分钟）
python scripts/rolling_cv.py
python scripts/ablation.py
python scripts/peak_defs.py
python scripts/interpret.py
python scripts/error_analysis.py

# 5. 可选：LSTM（GPU，约 20 分钟），需要 CUDA 版 PyTorch
python scripts/lstm_model.py
python scripts/compare_lstm.py
```

## 数据说明

原始数据**不入库**——体积约 830 MB，且 GitHub 拒绝超过 100 MB 的文件。
`scripts/download_data.py` 会从上游仓库下载普通 CSV。

> **重要**：上游文件的表头是坏的——LOA/MEL/SPO/SZH 的 `info.csv` 少一个逗号
> （`total_siteBSCAN_eps`），部分 `sites.csv`/`chargers.csv` 用 `site` 而不是 `site_id`。
> 下载后**必须**先运行 `python scripts/fix_headers.py --apply`。

阿姆斯特丹的 `duration.csv` 与 `distance.csv` 只存在于上游的 `csv-larger-than-100MB.rar` 中，
**主结果不需要**（AMS 因 94% 站点日内无波动被排除）。只有需要重画 AMS 距离矩阵时，才用 7-Zip
或 WinRAR 解压该压缩包。

## 预期输出

| 文件 | 内容 |
|---|---|
| `metrics_regression.csv` | 单次切分的回归指标 |
| `rolling_cv.csv` | 滚动 4 折的回归与分类指标 |
| `ablation_pooling.csv` | 池化消融 |
| `peak_definitions.csv` | 三种峰值定义 |
| `compare_lstm.csv` | 同测试行上 LSTM / Ridge / HGB 对比 |
| `err_decile.csv`、`err_acf.csv`、`err_bootstrap.csv` | 误差分析 |
| `importance.csv`、`pdp.csv` | 可解释性 |

核对用的关键数字：LOA WAPE 0.153、MEL WAPE 0.306、LOA PR-AUC 0.386、MEL PR-AUC 0.187。

## 设计说明

- **只用因果特征**：滞后与滚动统计统一 `shift(1)`；阈值只用训练期拟合；`sites.csv` 中的
  `total_*`、`avg_power` 等全期聚合字段绝不作为特征。
- **滚动原点验证**：训练从 4 月起逐月扩展，6—9 月依次作为测试月，段间留 1 天间隔。
- **峰值标签**：同小时滚动 28 天均值 + 2σ（因果）。另提供 ×4 中位数、训练期 P95 两种口径做敏感性分析
  ——换一个定义，事件率会相差约 5 倍。
- **弃用天气**：充电与天气的时间戳不在同一时钟上（LOA 相差 13 小时，MEL 为 0），宁可不用也不做错位对齐。
- **随机种子**：所有脚本固定为 0。

## 运行环境

Python 3.12.14 · pandas 3.0.1 · numpy 2.3.5 · scikit-learn 1.9.1 · matplotlib 3.11.2 ·
python-docx 1.2.0 · PyTorch 2.14.1+cu126（可选，RTX 3060 6 GB）。

## 报告

`report/` 下有四份 Word 文档：15 页中文报告、32 页中文操作手册、13 页英文报告、28 页英文手册。
它们分别由 `make_report.py`、`make_handbook.py`、`make_report_en.py`、`make_handbook_en.py` 生成。

## 引用

如果使用本数据，请引用原始数据集：

> Guo, Z., You, L., Zhu, R., Zhang, Y., & Yuen, C. (2025). A City-scale and Harmonized Dataset for Global
> Electric Vehicle Charging Demand Analysis. *Scientific Data*, 12, 1254.
> https://doi.org/10.1038/s41597-025-05584-7
