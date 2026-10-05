# Hourly EV Charging Demand and Peak Event Prediction

DSC6004 course project (6-student team). Forecast next-hour electric-vehicle charging
demand and predict peak charging events from the
[CHARGED](https://github.com/IntelligentSystemsLab/CHARGED) city-scale dataset.

- **Full report:** [`report.md`](report.md)
- **Team handoff / working log:** [`PROJECT_LOG.md`](PROJECT_LOG.md)
- **中文版 README:** [`README_zh.md`](README_zh.md)

## Research questions

1. Can historical EV charging data predict next-hour demand and peak events?
2. How accurately can next-hour demand be predicted?
3. Can machine learning identify potential peak charging periods?

## Data

- **Source:** CHARGED dataset — 6 cities: AMS, JHB, LOA, MEL, SPO, SZH.
- **Granularity:** hourly, `2023-04-01 00:00` → `2023-09-30 23:00` (~4,392 hours/city).
- **Files:** 10 CSVs per city — `volume.csv` (target, kWh), `duration.csv`,
  `e_price.csv`, `s_price.csv`, `sites.csv`, `chargers.csv`, `distance.csv`,
  `weather.csv`, `poi.csv`, `info.csv`.
- **Download:** `bash scripts/download_data.sh` (writes to `data/`, git-ignored).

## Environment & setup

Windows 11 + Git Bash; conda environment `dsc6004` (Python 3.11). torch is installed
separately (CPU build).

```bash
conda create -n dsc6004 python=3.11 -y && conda activate dsc6004
pip install -r requirements.txt
# torch (CPU): pip install torch --index-url https://download.pytorch.org/whl/cpu
```

> On Windows, run scripts directly with the interpreter path:
> `"D:/miniconda/envs/dsc6004/python.exe" scripts/<name>.py`.

## Project structure

```
data/               # downloaded data (git-ignored)
project_proposal/   # original proposal documents (.docx)
src/
  load.py           # data loading helpers
  preprocess.py     # feature engineering + time-ordered split
  models.py         # regression & classification models + metrics
scripts/
  download_data.sh
  eda.py            # Phase 1 — data quality + figures
  build_features.py # Phase 2 — feature matrices -> _output/features/
  train_regression.py      # Phase 3 — persistence/linear/RF/LSTM
  finalize_phase3.py       #       AMS case study + regression summary
  train_classification.py  # Phase 4 — peak events, val-threshold calibration
  finalize_phase4.py       #       classification summary
  analyze_errors.py        # Phase 5 — figures + error analysis
report.md           # final academic report
PROJECT_LOG.md      # team handoff / working log
_output/            # all generated artifacts (git-ignored)
```

## Quick start (full pipeline)

```bash
PY="D:/miniconda/envs/dsc6004/python.exe"
$PY scripts/eda.py                    # Phase 1 -> _output/eda_summary.md + figures
$PY scripts/build_features.py         # Phase 2 -> _output/features/{city}.csv
$PY scripts/train_regression.py       # Phase 3 -> _output/regression/regression_results.csv
$PY scripts/finalize_phase3.py        #        -> ams_case_study.md, regression_summary.md
$PY scripts/train_classification.py   # Phase 4 -> _output/classification/classification_results.csv
$PY scripts/finalize_phase4.py        #        -> classification_summary.md
$PY scripts/analyze_errors.py         # Phase 5 -> _output/figures/*.png, error_analysis.md
```

## Method

- **Forecasting (regression):** persistence (baseline) → linear regression →
  random forest → LSTM (PyTorch). Metrics: MAE, RMSE, R².
- **Peak prediction (classification):** a peak is `demand > q-th percentile` of
  **train** demand, for q ∈ {85, 90, 95}. Logistic regression vs random forest via
  `predict_proba`, with the decision threshold **calibrated on the validation set**
  (maximize F1). Metrics: accuracy, precision, recall, F1, AUC-ROC.
- **Features (33):** calendar + cyclic `sin`/`cos` encodings, lags (1/2/3/24/168 h),
  past-only rolling statistics (24 h/168 h mean, 24 h std), and 17 weather columns.
- **Split:** strictly time-ordered, no shuffle — Apr–Jul train, Aug validation,
  Sep test.

## Results (summary)

**Regression — R² on the September test set:**

| city | persistence | linear | random forest | LSTM | best |
|------|------------:|-------:|--------------:|-----:|------|
| AMS  | **0.576** | -1.604 | -16.307 | -49.132 | persistence |
| JHB  | 0.818 | **0.834** | 0.819 | 0.790 | linear |
| LOA  | 0.747 | 0.719 | **0.829** | 0.765 | random forest |
| MEL  | 0.486 | **0.664** | 0.648 | 0.621 | linear |
| SPO  | 0.755 | **0.791** | 0.787 | 0.787 | linear |
| SZH  | 0.600 | 0.815 | **0.836** | 0.757 | random forest |

**Classification — peak events at q = 90 (val-calibrated):**

| city | model | threshold | recall | F1 | AUC |
|------|-------|----------:|-------:|---:|----:|
| LOA  | random forest | 0.28 | 0.88 | 0.62 | 0.98 |
| MEL  | logistic | 0.27 | 0.91 | 0.57 | 0.87 |
| SPO  | random forest | 0.26 | 0.76 | 0.65 | 0.89 |

**Relative error (MAE%):** MEL 14.2% · SPO 9.9% · LOA 5.6% · JHB/SZH 3.4% · AMS 0.1%.

## Limitations

See `report.md` §6 and `_output/ams_case_study.md`. In brief: AMS is non-stationary
(April ramp-up + Aug–Sep flattening, so global models get negative R²); peaks are
sparse (~10%), so a 1-month validation window can contain zero positives; SZH drifts
below its train percentile in September. These are data limitations, not modelling bugs.
