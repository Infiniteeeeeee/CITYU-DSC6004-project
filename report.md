# Hourly EV Charging Demand and Peak Event Prediction

**DSC6004 course project — final report**

- **Dataset:** CHARGED (6 cities: AMS, JHB, LOA, MEL, SPO, SZH), hourly, 2023-04-01 → 2023-09-30 (~4,392 hours each)
- **Tasks:** (1) regression — forecast next-hour city-wide charging demand; (2) classification — predict peak charging events
- **Reproducibility:** `conda env` `dsc6004` (Python 3.11); run `scripts/` in order — `eda.py` → `build_features.py` → `train_regression.py` → `train_classification.py` → `analyze_errors.py`. All outputs land in `_output/`.

---

## 1. Research questions

1. Can historical EV charging data predict next-hour demand and peak events?
2. How accurately can next-hour demand be predicted?
3. Can machine learning identify potential peak charging periods?

## 2. Data

The CHARGED dataset provides city-scale hourly charging volume (the target, kWh) plus
duration, energy/session price, site/charger inventory, distances, weather, and POI
context for six cities across three continents. Each city is a 4,392-hour series
(Apr–Sep 2023).

**Data-quality summary (Phase 1):** no missing hours, no `NaN` cells, no duplicate
timestamps, and 0% zero-demand hours in every city. The cities span three orders of
magnitude in demand scale, which must be kept in mind when comparing absolute errors.

| city | sites | mean demand (kWh) | std (kWh) | max (kWh) |
|------|------:|------------------:|----------:|----------:|
| AMS  | 2,449 | 34,083 | 21,394 | 65,666 |
| JHB  |    47 |    275 |     91 |    534 |
| LOA  |   229 |  1,631 |    467 |  3,815 |
| MEL  |    63 |  2,973 |  1,229 |  8,141 |
| SPO  |    47 |    165 |     57 |    328 |
| SZH  | 1,445 | 227,154 | 37,473 | 367,490 |

## 3. Methodology

### 3.1 Feature engineering (`src/preprocess.py`)

For each city we build 33 features plus the `demand` target:

- **Calendar:** hour, day-of-week, is-weekend, month + cyclic `sin`/`cos` encodings of
  hour and day-of-week (so linear models can see periodicity).
- **Lags** of demand: 1, 2, 3, 24, 168 hours.
- **Rolling** statistics: 24 h and 168 h mean, 24 h std — computed on **past-only**
  (`shift(1)` before rolling) to prevent leakage of the current hour.
- **Weather:** 17 numeric columns (temperature, humidity, precip, wind, solar, etc.).

### 3.2 Split

Strictly time-ordered, **no shuffle**, to avoid future leakage:

| set | window | hours |
|-----|--------|------:|
| train | Apr–Jul | 2,760 |
| validation | Aug | 744 |
| test | Sep | 720 |

### 3.3 Models

**Regression** (next-hour demand): persistence (naive baseline: last hour), linear
regression, random forest (400 trees), and LSTM (PyTorch, 24-step window, 2 layers,
early stopping).

**Classification** (peak event): a peak is `demand > q-th percentile` of **train**
demand, for q ∈ {85, 90, 95}. Logistic regression vs random forest, both via
`predict_proba`. Because peaks are rare and RF probabilities are miscalibrated under
class imbalance, the decision threshold is **chosen on the validation set to maximize
F1**, then applied unchanged to the test set.

**Metrics:** MAE, RMSE, R² (regression); accuracy, precision, recall, F1, AUC-ROC
(classification).

## 4. Results

### 4.1 Regression — next-hour demand (Phase 3)

R² on the September test set:

| city | persistence | linear | random forest | LSTM |
|------|------------:|-------:|--------------:|-----:|
| AMS  |  **0.576**  | -1.604 | -16.307 | -49.132 |
| JHB  | 0.818 | **0.834** | 0.819 | 0.790 |
| LOA  | 0.747 | 0.719 | **0.829** | 0.765 |
| MEL  | 0.486 | **0.664** | 0.648 | 0.621 |
| SPO  | 0.755 | **0.791** | 0.787 | 0.787 |
| SZH  | 0.600 | 0.815 | **0.836** | 0.757 |

**Findings**

- On the **five stationary cities**, feature-based models beat persistence, with
  R² ≈ 0.66–0.84. The best model is **linear regression** in JHB/MEL/SPO and
  **random forest** in LOA/SZH; LSTM is competitive but never the best.
- Persistence is a strong baseline (R² 0.49–0.82), confirming strong hourly
  autocorrelation.
- **AMS is the exception** (see §6): all global models have *negative* R² there,
  while persistence alone survives (R² 0.576).

### 4.2 Classification — peak events (Phase 4)

Val-calibrated results at **q = 90** (the central scenario):

| city | model | threshold | recall | F1 | AUC |
|------|-------|----------:|-------:|---:|----:|
| LOA  | logistic | 0.27 | 0.76 | 0.58 | 0.97 |
| LOA  | random forest | 0.28 | 0.88 | **0.62** | 0.98 |
| MEL  | logistic | 0.27 | 0.91 | 0.57 | 0.87 |
| MEL  | random forest | 0.25 | 0.63 | 0.56 | 0.88 |
| SPO  | logistic | 0.17 | 0.66 | 0.64 | 0.90 |
| SPO  | random forest | 0.26 | 0.76 | **0.65** | 0.89 |

**Findings**

- **AUC is high (0.87–0.98) and robust across q = 85/90/95** — the models rank peaks
  well even at the extreme 95th percentile.
- **Val calibration recovers recall** (0.63–0.91) by lowering the threshold from the
  default 0.5 to 0.17–0.30, correcting the earlier miscalibration failure.
- **q = 95 is the hardest** (F1 drops to ~0.17–0.52) but AUC stays high — a
  sample-size / precision problem, not a ranking problem.
- **Random forest ≥ logistic** in F1 at nearly every (city, q).

**Degenerate cases** (AMS, JHB, SZH) are recorded as limitations in §6, not forced
into a number.

### 4.3 Error analysis (Phase 5)

Per-city error of the best model on the September test, with **MAE%** (MAE ÷ mean
demand) for cross-city comparability:

| city | best model | MAE (kWh) | RMSE (kWh) | MAE% | bias |
|------|-----------|----------:|-----------:|-----:|-----:|
| AMS  | persistence | 62.5 | 97.7 | 0.1 | -0.7 |
| JHB  | linear | 11.6 | 17.3 | 3.4 | -2.5 |
| LOA  | random forest | 92.6 | 155.5 | 5.6 | -1.2 |
| MEL  | linear | 452.6 | 574.7 | **14.2** | 62.4 |
| SPO  | linear | 19.2 | 24.8 | **9.9** | -2.3 |
| SZH  | random forest | 7,313.3 | 11,651.2 | 3.4 | 3,409.8 |

**Findings**

- **Compare on MAE%, not MAE** — absolute error spans three orders of magnitude
  because demand does. Relative error ranks the cities **MEL (14%) > SPO (10%) >
  LOA (5.6%) > JHB/SZH (3.4%) > AMS (0.1%)**.
- **Hard periods are city-specific:** LOA and SZH worst in the small hours (0–4 a.m.),
  MEL worst at the morning rush (7–8 a.m.) and midday; JHB/SPO/AMS are flat with a
  slight evening bump.
- **No consistent weekday/weekend rule:** MEL and AMS are harder on weekends,
  JHB/LOA/SPO on weekdays, SZH peaks Fri–Sat.
- **Bias is small** (a few % of mean demand, usually slightly negative = under-predicting
  peaks), consistent with §4.2's need for a lowered threshold; SZH's RF over-predicts
  (+1.6%) as the one exception.

## 5. Answering the research questions

1. **Can historical data predict next-hour demand and peak events?** Yes — for the five
   stationary cities, R² ≈ 0.66–0.84 for demand and AUC 0.87–0.98 for peaks.
2. **How accurately?** Next-hour demand is predictable to within 3–14% MAE depending on
   city (best: AMS 0.1%, hardest: MEL 14%).
3. **Can ML identify peak periods?** Yes, at 90th percentile the models recover 63–91%
   of true peaks with F1 0.56–0.65, and ranking (AUC) is strong even at the 95th
   percentile.

## 6. Limitations

1. **Non-stationarity (AMS).** AMS demand ramps from ≈0 in April, swings through a May
   ramp-up, stabilises over Jun–Jul, then flattens to ~45,900 kWh/h in Aug–Sep. Train
   and test are two different regimes, so global models extrapolate badly (negative R²).
   Only persistence survives. This is a distribution-shift problem, not a modelling bug.
2. **Peak sparsity + short validation window.** Peaks are ~10% by construction; a
   1-month validation window can contain 0 of them (JHB at q=90), making val-based
   threshold calibration undefined.
3. **Distribution drift in the target month (SZH).** September demand drifts below the
   train percentile, so at q=90/95 the test set has 0 peaks (AUC undefined).
4. **Cross-city comparability.** Demand scales differ by three orders of magnitude;
   absolute errors are meaningless across cities and relative error (MAE%) is required.
5. **Fixed window.** Models are trained on a single Apr–Sep window; a rolling
   retraining scheme would track regime drift (AMS/SZH) but is out of scope here.

## 7. Conclusion

For the five stationary cities, next-hour EV charging demand is forecast well
(R² ≈ 0.66–0.84) with simple, interpretable models, and peak events are detectable
(AUC 0.87–0.98) once the decision threshold is calibrated on a validation set. The
project's main finding is negative but instructive: **time-series non-stationarity and
peak sparsity — not model choice — are the binding constraints**, as shown by the AMS
and SZH cases. These map directly to the proposal's error-analysis and limitations
sections and point to rolling retraining and longer calibration windows as the natural
next steps for deployment.

## 8. Reproducibility

```bash
# 1. environment
conda create -n dsc6004 python=3.11 -y && conda activate dsc6004
pip install -r requirements.txt          # torch installed separately (CPU)

# 2. data
bash scripts/download_data.sh            # fetches 6 cities × 10 CSVs into data/

# 3. pipeline
python scripts/eda.py                    # Phase 1  -> _output/eda_summary.md + figures
python scripts/build_features.py         # Phase 2  -> _output/features/{city}.csv
python scripts/train_regression.py       # Phase 3  -> _output/regression/regression_results.csv
python scripts/finalize_phase3.py        #            -> ams_case_study.md, regression_summary.md
python scripts/train_classification.py   # Phase 4  -> _output/classification/classification_results.csv
python scripts/finalize_phase4.py        #            -> classification_summary.md
python scripts/analyze_errors.py         # Phase 5  -> _output/figures/*.png, error_analysis.md
```

Key modules: `src/load.py` (data loading), `src/preprocess.py` (features + split),
`src/models.py` (regression & classification models + metrics).
