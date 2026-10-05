"""Regression models for next-hour EV charging demand forecasting.

Each `run_<model>(train, val, test)` returns `(test_pred, test_index)`
with predictions aligned to the test timestamps.

Metrics: MAE, RMSE, R² (and Adjusted R² for feature-based models).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

import torch
import torch.nn as nn

TARGET = "demand"

# Curated per-timestep features for the LSTM sequence model.
LSTM_FEATURES = [
    "demand", "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "temp", "humidity", "precip", "windspeed", "cloudcover", "solarradiation",
]


def eval_metrics(y_true, y_pred, n_features: int | None = None) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    out = {"MAE": mae, "RMSE": rmse, "R2": r2}
    if n_features is not None:
        n = len(y_true)
        out["Adj_R2"] = 1 - (1 - r2) * (n - 1) / max(n - n_features - 1, 1)
    return out


def _xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return df.drop(columns=[TARGET]), df[TARGET]


# --- persistence (naive baseline: next hour = last hour) ---
def run_persistence(train, val, test):
    return test["lag_1"].values, test.index


# --- linear regression ---
def run_linear(train, val, test):
    Xtr, ytr = _xy(train)
    Xte = test.drop(columns=[TARGET])
    scaler = StandardScaler().fit(Xtr)
    model = LinearRegression().fit(scaler.transform(Xtr), ytr)
    return model.predict(scaler.transform(Xte)), test.index


# --- random forest ---
def run_rf(train, val, test, n_estimators: int = 400):
    Xtr, ytr = _xy(train)
    Xte = test.drop(columns=[TARGET])
    model = RandomForestRegressor(
        n_estimators=n_estimators, n_jobs=-1, random_state=0
    ).fit(Xtr, ytr)
    return model.predict(Xte), test.index


# --- LSTM ---
def _build_sequences(df, window, x_scaler, y_scaler):
    X = x_scaler.transform(df[LSTM_FEATURES].values)
    y = y_scaler.transform(df[[TARGET]].values).ravel()
    Xs = np.stack([X[i - window : i] for i in range(window, len(df))])
    ys = y[window:]
    return Xs, ys


def run_lstm(
    train, val, test,
    window: int = 24, hidden: int = 64, num_layers: int = 2,
    epochs: int = 40, batch: int = 64, lr: float = 1e-3, seed: int = 0,
):
    torch.manual_seed(seed)
    np.random.seed(seed)

    n_feat = len(LSTM_FEATURES)
    x_scaler = StandardScaler().fit(train[LSTM_FEATURES].values)
    y_scaler = StandardScaler().fit(train[[TARGET]].values)

    Xtr, ytr = _build_sequences(train, window, x_scaler, y_scaler)
    Xva, yva = _build_sequences(val, window, x_scaler, y_scaler)

    model = _LSTM(n_feat, hidden, num_layers)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    Xtr_t = torch.tensor(Xtr, dtype=torch.float32)
    ytr_t = torch.tensor(ytr, dtype=torch.float32)
    Xva_t = torch.tensor(Xva, dtype=torch.float32)
    yva_t = torch.tensor(yva, dtype=torch.float32)

    best_val = float("inf")
    best_state = None
    patience = 8
    waited = 0

    for _ in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr_t))
        for i in range(0, len(Xtr_t), batch):
            idx = perm[i : i + batch]
            optimizer.zero_grad()
            out = model(Xtr_t[idx]).squeeze(-1)
            loss = loss_fn(out, ytr_t[idx])
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            vloss = loss_fn(model(Xva_t).squeeze(-1), yva_t).item()
        if vloss < best_val - 1e-4:
            best_val, waited = vloss, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            waited += 1
            if waited >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    # one-step-ahead on test: warm-start with the last `window` hours of val
    test_warm = pd.concat([val.iloc[-window:], test])
    Xtw, _ = _build_sequences(test_warm, window, x_scaler, y_scaler)
    model.eval()
    with torch.no_grad():
        pred_scaled = model(torch.tensor(Xtw, dtype=torch.float32)).squeeze(-1).numpy()
    pred = y_scaler.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()
    return pred, test.index


class _LSTM(torch.nn.Module):
    def __init__(self, n_feat: int, hidden: int, num_layers: int, dropout: float = 0.2):
        super().__init__()
        self.lstm = torch.nn.LSTM(
            n_feat, hidden, num_layers, batch_first=True, dropout=dropout
        )
        self.fc = torch.nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


# ---------------------------------------------------------------------------
# Peak-event classification
# ---------------------------------------------------------------------------

def clf_metrics(y_true, y_pred, y_proba) -> dict:
    """Classification metrics; AUC is NaN when the test set has only one class."""
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if len(set(y_true)) == 2:
        out["auc"] = float(roc_auc_score(y_true, y_proba))
    else:
        out["auc"] = float("nan")
    return out


def best_threshold(y_val, proba_val):
    """Pick the decision threshold maximizing F1 on the validation set."""
    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(0.01, 0.99, 99):
        f1 = f1_score(y_val, (proba_val >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return best_t, best_f1


def fit_logistic_clf(Xtr, ytr):
    scaler = StandardScaler().fit(Xtr)
    model = LogisticRegression(max_iter=2000, random_state=0).fit(
        scaler.transform(Xtr), ytr
    )

    def proba(X):
        return model.predict_proba(scaler.transform(X))[:, 1]

    return proba


def fit_rf_clf(Xtr, ytr, n_estimators: int = 400):
    model = RandomForestClassifier(
        n_estimators=n_estimators, n_jobs=-1, random_state=0
    ).fit(Xtr, ytr)

    def proba(X):
        return model.predict_proba(X)[:, 1]

    return proba
