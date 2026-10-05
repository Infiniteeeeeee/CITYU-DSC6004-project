# 逐小时电动汽车充电需求与峰值事件预测

DSC6004 课程项目（6 人小组）。基于
[CHARGED](https://github.com/IntelligentSystemsLab/CHARGED) 城市级数据集，预测下一小时的
电动汽车充电需求，并预测充电峰值事件。

- **完整报告：** [`report.md`](report.md)（英文）
- **团队交接 / 工作日志：** [`PROJECT_LOG.md`](PROJECT_LOG.md)（中文）
- **English README:** [`README.md`](README.md)

## 研究问题

1. 历史电动汽车充电数据能否预测下一小时的需求与峰值事件？
2. 下一小时的需求能被预测到多准？
3. 机器学习能否识别潜在的充电高峰时段？

## 数据

- **来源：** CHARGED 数据集 — 6 个城市：AMS、JHB、LOA、MEL、SPO、SZH。
- **粒度：** 逐小时，`2023-04-01 00:00` → `2023-09-30 23:00`（每城约 4,392 小时）。
- **文件：** 每城 10 个 CSV — `volume.csv`（目标，kWh）、`duration.csv`、
  `e_price.csv`、`s_price.csv`、`sites.csv`、`chargers.csv`、`distance.csv`、
  `weather.csv`、`poi.csv`、`info.csv`。
- **下载：** `bash scripts/download_data.sh`（写入 `data/`，已 git-ignore）。

## 环境与安装

Windows 11 + Git Bash；conda 环境 `dsc6004`（Python 3.11）。torch 单独安装（CPU 版）。

```bash
conda create -n dsc6004 python=3.11 -y && conda activate dsc6004
pip install -r requirements.txt
# torch (CPU)：pip install torch --index-url https://download.pytorch.org/whl/cpu
```

> 在 Windows 上，直接用解释器路径运行脚本：
> `"D:/miniconda/envs/dsc6004/python.exe" scripts/<name>.py`。

## 项目结构

```
data/               # 下载的数据（已 git-ignore）
project_proposal/   # 原始提案文档（.docx）
src/
  load.py           # 数据加载辅助函数
  preprocess.py     # 特征工程 + 时间序切分
  models.py         # 回归 & 分类模型 + 评估指标
scripts/
  download_data.sh
  eda.py            # 阶段 1 — 数据质量 + 图
  build_features.py # 阶段 2 — 特征矩阵 -> _output/features/
  train_regression.py      # 阶段 3 — persistence/线性/RF/LSTM
  finalize_phase3.py       #       AMS 案例研究 + 回归汇总
  train_classification.py  # 阶段 4 — 峰值事件，验证集阈值校准
  finalize_phase4.py       #       分类汇总
  analyze_errors.py        # 阶段 5 — 图 + 误差分析
report.md           # 最终学术报告（英文）
PROJECT_LOG.md      # 团队交接 / 工作日志（中文）
_output/            # 所有生成的产物（已 git-ignore）
```

## 快速开始（完整流程）

```bash
PY="D:/miniconda/envs/dsc6004/python.exe"
$PY scripts/eda.py                    # 阶段 1 -> _output/eda_summary.md + 图
$PY scripts/build_features.py         # 阶段 2 -> _output/features/{city}.csv
$PY scripts/train_regression.py       # 阶段 3 -> _output/regression/regression_results.csv
$PY scripts/finalize_phase3.py        #        -> ams_case_study.md、regression_summary.md
$PY scripts/train_classification.py   # 阶段 4 -> _output/classification/classification_results.csv
$PY scripts/finalize_phase4.py        #        -> classification_summary.md
$PY scripts/analyze_errors.py         # 阶段 5 -> _output/figures/*.png、error_analysis.md
```

## 方法

- **预测（回归）：** persistence（朴素基线）→ 线性回归 → 随机森林 → LSTM（PyTorch）。
  指标：MAE、RMSE、R²。
- **峰值预测（分类）：** 峰值为 `demand > 训练集需求第 q 分位数`，q ∈ {85, 90, 95}。
  逻辑回归 vs 随机森林，均通过 `predict_proba` 输出概率；由于峰值稀疏且类别不平衡下
  RF 概率失准，决策阈值**在验证集上校准**（最大化 F1），再原样应用到测试集。
  指标：accuracy、precision、recall、F1、AUC-ROC。
- **特征（33 个）：** 日历 + 循环 `sin`/`cos` 编码、滞后项（1/2/3/24/168 小时）、
  仅用过去值的滚动统计（24h/168h 均值、24h 标准差）、17 个天气列。
- **切分：** 严格按时间顺序、不 shuffle — 4–7 月训练、8 月验证、9 月测试。

## 结果（摘要）

**回归 — 9 月测试集上的 R²：**

| 城市 | persistence | 线性回归 | 随机森林 | LSTM | 最优 |
|------|------------:|-------:|--------------:|-----:|------|
| AMS  | **0.576** | -1.604 | -16.307 | -49.132 | persistence |
| JHB  | 0.818 | **0.834** | 0.819 | 0.790 | 线性回归 |
| LOA  | 0.747 | 0.719 | **0.829** | 0.765 | 随机森林 |
| MEL  | 0.486 | **0.664** | 0.648 | 0.621 | 线性回归 |
| SPO  | 0.755 | **0.791** | 0.787 | 0.787 | 线性回归 |
| SZH  | 0.600 | 0.815 | **0.836** | 0.757 | 随机森林 |

**分类 — q = 90 时的峰值事件（验证集校准后）：**

| 城市 | 模型 | 阈值 | recall | F1 | AUC |
|------|-------|----------:|-------:|---:|----:|
| LOA  | 随机森林 | 0.28 | 0.88 | 0.62 | 0.98 |
| MEL  | 逻辑回归 | 0.27 | 0.91 | 0.57 | 0.87 |
| SPO  | 随机森林 | 0.26 | 0.76 | 0.65 | 0.89 |

**相对误差（MAE%）：** MEL 14.2% · SPO 9.9% · LOA 5.6% · JHB/SZH 3.4% · AMS 0.1%。

## 局限性

见 `report.md` §6 与 `_output/ams_case_study.md`。简要：AMS 非平稳（4 月爬坡 + 8–9 月
趋于平坦，导致全局模型 R² 为负）；峰值稀疏（约 10%），1 个月的验证窗口可能不含任何正样本；
SZH 在 9 月需求下漂、低于其训练分位数。这些是数据本身的局限，而非建模 bug。
