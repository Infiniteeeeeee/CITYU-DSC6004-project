# 项目日志 / Handoff

> 用途：① 团队成员对接；② 下次与 Claude Code 对话时快速同步上下文。
> 学术版完整报告见 **`report.md`**，本文是「做了什么、环境怎么搭、结论是什么、还有啥没做」的速查版。

---

## 0. 项目一句话

DSC6004 课程项目 —— **Hourly EV Charging Demand and Peak Event Prediction**（6 人组）。
用 CHARGED 数据集（6 城市逐小时充电量）做两件事：**次小时需求预测（回归）** + **峰值事件预测（分类）**。

## 1. 环境（队友必读）

- **OS**：Windows 11，命令行用 **Git Bash**。
- **Python**：conda 环境 `dsc6004`（Python 3.11）。
  - 解释器绝对路径：`D:/miniconda/envs/dsc6004/python.exe`
  - torch 单独装 **CPU 版**；其余见 `requirements.txt`。
- **数据**：`data/`（已 git-ignore，~830MB），6 城 × 10 个 CSV。
  - 下载：`bash scripts/download_data.sh`（AMS 是 .rar，用 Windows bsdtar 解压）。

### ⚠️ 已知坑（省得队友重踩）

1. **不要用 `conda run -n dsc6004 python -c "多行代码"`** —— 会报 `newlines not implemented` + GBK 编码错。正确做法：把逻辑写进 `.py` 文件，再用 `"D:/miniconda/envs/dsc6004/python.exe" xxx.py` 跑。
2. pandas 的 `df.to_markdown()` 需要 `tabulate`（未装）→ 一律用 `.to_string()`。
3. **特征泄漏**：rolling 统计必须 `shift(1)` 之后再 `rolling()`（只算过去值，不含当前小时），否则测试 R² 虚高。

## 2. 已完成（6 个阶段，全部跑通）

| 阶段 | 脚本 | 产出 | 一句话结论 |
|------|------|------|-----------|
| P1 EDA | `eda.py` | `_output/eda_summary.md` + 3 图 | 数据干净：0 缺失 / 0 重复 / 0 零需求小时 |
| P2 特征 | `build_features.py` | `_output/features/{city}.csv` | 33 特征（日历+循环编码+滞后+滚动+天气） |
| P3 回归 | `train_regression.py` + `finalize_phase3.py` | `regression_results.csv`、`regression_summary.md`、`ams_case_study.md` | 5 城 R²≈0.66–0.84；AMS 非平稳 → 单独 case study |
| P4 分类 | `train_classification.py` + `finalize_phase4.py` | `classification_results.csv`、`classification_summary.md` | val 阈值校准后 AUC 0.87–0.98；AMS/JHB/SZH 退化记为局限性 |
| P5 可视化+误差 | `analyze_errors.py` | 5 图 + `error_analysis.md` | 相对误差 MEL 14% 最难；难点时段因城而异 |
| P6 报告 | （手写） | `report.md` | 整合全部结论的最终报告 |

### 运行顺序（一条龙）

```bash
cd "E:/agent-project/DSC6004-project"
PY="D:/miniconda/envs/dsc6004/python.exe"
$PY scripts/eda.py
$PY scripts/build_features.py
$PY scripts/train_regression.py
$PY scripts/finalize_phase3.py
$PY scripts/train_classification.py
$PY scripts/finalize_phase4.py
$PY scripts/analyze_errors.py
```

## 3. 核心结果速查

### 回归（次小时需求，R² @ 9 月测试集）

| city | persistence | linear | random_forest | LSTM | 最优 |
|------|----:|----:|----:|----:|------|
| AMS  | **0.576** | -1.60 | -16.31 | -49.13 | persistence |
| JHB  | 0.818 | **0.834** | 0.819 | 0.790 | linear |
| LOA  | 0.747 | 0.719 | **0.829** | 0.765 | RF |
| MEL  | 0.486 | **0.664** | 0.648 | 0.621 | linear |
| SPO  | 0.755 | **0.791** | 0.787 | 0.787 | linear |
| SZH  | 0.600 | 0.815 | **0.836** | 0.757 | RF |

### 分类（峰值事件，q=90，val 校准后）

- **正常城市**（LOA/MEL/SPO）：AUC 0.87–0.98，recall 0.63–0.91，F1 0.56–0.65；阈值从 0.5 降到 0.17–0.30。
- **退化城市**（如实记为局限，未硬凑）：
  - AMS：Aug–Sep 需求近恒定 → val/test 正样本 = 0，AUC NaN。
  - JHB：q=90 时 val 正样本 = 0（8 月无小时超训练 90 分位）→ 校准无定义。
  - SZH：9 月需求漂到训练分位以下 → q=90/95 test 正样本 = 0。

### 误差分析（相对误差 MAE%）

MEL **14.2%** > SPO 9.9% > LOA 5.6% > JHB/SZH 3.4% > AMS 0.1%。

## 4. 关键决策记录（谁拍的、为什么）

| 决策 | 选择 | 理由 |
|------|------|------|
| 深度学习模型 | 只用 **LSTM**（用户从清单里挑） | 作为高级模型代表，够用；XGBoost/LightGBM 未启用 |
| 峰值分位数 | **85 / 90 / 95 三档对比** | 稳健性（用户指定） |
| AMS 负 R² | **单独做 case study**（非代码 bug） | 4 月≈0 → 5 月爬坡 → 6–7 月稳定 → 8–9 月扁平，训练/测试是两个分布 |
| 分类召回差 | **加 val 阈值校准**（max F1 选阈值） | 修正 0.5 默认阈值下 RF 概率失准导致的低召回 |
| 退化城市 | **如实记为局限性** | 不硬凑指标，诚实对应提案 Section 8/9 |
| 数据切分 | 时间序 **4/1/1**（4–7 训练 / 8 验证 / 9 测试），**不 shuffle** | 防未来信息泄漏 |

## 5. 交付清单

```
report.md                             ← 最终学术报告
PROJECT_LOG.md                        ← 本文
src/{load,preprocess,models}.py       ← 可复用模块
scripts/{eda,build_features,train_regression,finalize_phase3,
         train_classification,finalize_phase4,analyze_errors}.py
_output/
  eda_summary.md / regression_summary.md / classification_summary.md
  ams_case_study.md / error_analysis.md
  regression/regression_results.csv
  classification/classification_results.csv
  features/{city}.csv
  figures/*.png                       ← EDA 3 张 + Phase 5 五张
```

## 6. 还没做（可选，交给队友/下次）

1. **git 版本控制**：目前目录未提交（或未 init）。需要就 `git init` + 首次 commit。
2. **目检图表**：`_output/figures/` 里的图未经人工目检，建议打开看渲染是否满意。
3. **转 Word/PDF**：若老师要 `.docx`，`report.md` 可用 Pandoc 一键转。
4. **未来工作**（写进 report 的展望，暂不实现）：滚动重训练跟踪 AMS/SZH 的 regime 漂移；加长/滚动验证窗口让阈值校准看到足够峰值。

## 7. 给下次对话的「三句话同步」

1. 项目在 `E:\agent-project\DSC6004-project`，环境 `dsc6004`（解释器 `D:/miniconda/envs/dsc6004/python.exe`），**6 阶段全跑通，报告在 `report.md`**。
2. 回归最优：JHB/MEL/SPO 用 linear，LOA/SZH 用 RF；AMS 非平稳只能用 persistence。
3. 分类：val 阈值校准已落地，AMS/JHB/SZH 因正样本过少记局限；误差最难是 MEL（14%）。
