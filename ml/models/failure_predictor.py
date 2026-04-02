"""
Failure Prediction Models — Training Script
=============================================
XGBoost Regressor: Predicts RUL (Remaining Useful Life)
XGBoost Classifier: Predicts will_fail_in_30_cycles

Hyperparameter tuning with Optuna (50 trials).
Uses 5 selected CMAPSS sensors with rolling feature engineering.

Usage:
    python ml/models/failure_predictor.py
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    mean_squared_error, accuracy_score, precision_score,
    recall_score, roc_auc_score, f1_score,
)
import xgboost as xgb
import optuna

import mlflow
import mlflow.xgboost

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "nasa_cmapss"
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)

SELECTED_SENSORS = ["s2", "s3", "s4", "s7", "s11"]
CMAPSS_COLUMNS = ["engine_id", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]


def load_raw_cmapss():
    """Load raw CMAPSS data and compute RUL."""
    all_dfs = []
    for fd in range(1, 5):
        fp = RAW_DIR / f"train_FD00{fd}.txt"
        if fp.exists():
            df = pd.read_csv(fp, sep=r"\s+", header=None, names=CMAPSS_COLUMNS)
            df["dataset"] = f"FD00{fd}"
            # Re-index engine_id per dataset to avoid collisions
            df["engine_id"] = df["engine_id"].astype(str) + f"_FD{fd}"
            all_dfs.append(df)
    if not all_dfs:
        return None
    combined = pd.concat(all_dfs, ignore_index=True)

    # Add RUL
    max_cycles = combined.groupby("engine_id")["cycle"].max().to_dict()
    combined["RUL"] = combined.apply(lambda r: max_cycles[r["engine_id"]] - r["cycle"], axis=1)
    return combined


def engineer_features(df):
    """Create rolling statistical features for selected sensors."""
    feature_dfs = []
    for engine_id in df["engine_id"].unique():
        eng = df[df["engine_id"] == engine_id].sort_values("cycle").copy()
        for sensor in SELECTED_SENSORS:
            eng[f"{sensor}_rmean5"] = eng[sensor].rolling(5, min_periods=1).mean()
            eng[f"{sensor}_rmean10"] = eng[sensor].rolling(10, min_periods=1).mean()
            eng[f"{sensor}_rstd5"] = eng[sensor].rolling(5, min_periods=1).std().fillna(0)
            eng[f"{sensor}_rstd10"] = eng[sensor].rolling(10, min_periods=1).std().fillna(0)
            eng[f"{sensor}_rmin10"] = eng[sensor].rolling(10, min_periods=1).min()
            eng[f"{sensor}_rmax10"] = eng[sensor].rolling(10, min_periods=1).max()
        feature_dfs.append(eng)
    return pd.concat(feature_dfs, ignore_index=True)


def get_feature_columns():
    """Get list of engineered feature column names."""
    cols = []
    for s in SELECTED_SENSORS:
        cols.extend([f"{s}_rmean5", f"{s}_rmean10", f"{s}_rstd5",
                     f"{s}_rstd10", f"{s}_rmin10", f"{s}_rmax10"])
    return cols


def nasa_scoring(y_true, y_pred):
    """NASA asymmetric scoring function."""
    diff = y_pred - y_true
    score = 0
    for d in diff:
        if d < 0:  # early prediction
            score += np.exp(-d / 13) - 1
        else:  # late prediction
            score += np.exp(d / 10) - 1
    return score


def train_models():
    logger.info("=" * 60)
    logger.info("Training Failure Prediction Models on CMAPSS")
    logger.info("=" * 60)

    raw_df = load_raw_cmapss()
    if raw_df is None:
        logger.error("No CMAPSS raw files found. Aborting.")
        return False

    logger.info(f"  Raw data: {len(raw_df)} rows, {raw_df['engine_id'].nunique()} engines")

    # Engineer features
    logger.info("  Engineering rolling features...")
    featured = engineer_features(raw_df)
    feature_cols = get_feature_columns()

    # Add binary classification target
    featured["will_fail_30"] = (featured["RUL"] <= 30).astype(int)

    # Drop early rows that have incomplete rolling windows
    featured = featured.dropna(subset=feature_cols)

    # Split by engine (70/15/15)
    engines = featured["engine_id"].unique()
    np.random.seed(42)
    np.random.shuffle(engines)
    n = len(engines)
    train_eng = engines[: int(0.7 * n)]
    val_eng = engines[int(0.7 * n): int(0.85 * n)]
    test_eng = engines[int(0.85 * n):]

    train = featured[featured["engine_id"].isin(train_eng)]
    val = featured[featured["engine_id"].isin(val_eng)]
    test = featured[featured["engine_id"].isin(test_eng)]

    # Scale features
    scaler = MinMaxScaler()
    X_train = scaler.fit_transform(train[feature_cols])
    X_val = scaler.transform(val[feature_cols])
    X_test = scaler.transform(test[feature_cols])
    y_train_rul = train["RUL"].values
    y_val_rul = val["RUL"].values
    y_test_rul = test["RUL"].values
    y_train_cls = train["will_fail_30"].values
    y_test_cls = test["will_fail_30"].values

    joblib.dump(scaler, ARTIFACTS_DIR / "feature_scaler.pkl")
    logger.info(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    logger.info(f"  Features: {len(feature_cols)} columns")

    # ── XGBoost Regressor with Optuna ───────────────────────
    mlflow.set_experiment("failure_prediction")
    logger.info("\n  Tuning XGBoost Regressor with Optuna (50 trials)...")

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "tree_method": "hist",
            "random_state": 42,
        }
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train_rul,
                  eval_set=[(X_val, y_val_rul)], verbose=False)
        pred = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val_rul, pred))
        return rmse

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=50, show_progress_bar=True)

    best_params = study.best_params
    best_params["tree_method"] = "hist"
    best_params["random_state"] = 42
    logger.info(f"  Best params: {best_params}")

    # Train best regressor
    with mlflow.start_run(run_name="xgb_regressor_best"):
        best_reg = xgb.XGBRegressor(**best_params)
        best_reg.fit(X_train, y_train_rul,
                     eval_set=[(X_val, y_val_rul)], verbose=False)
        pred_test = best_reg.predict(X_test)

        rmse = np.sqrt(mean_squared_error(y_test_rul, pred_test))
        nasa_score = nasa_scoring(y_test_rul, pred_test)

        mlflow.log_params(best_params)
        mlflow.log_metrics({"rmse": rmse, "nasa_score": nasa_score})
        mlflow.xgboost.log_model(best_reg, "xgb_regressor",
                                 registered_model_name="failure_predictor_v1")
        joblib.dump(best_reg, ARTIFACTS_DIR / "xgb_regressor.pkl")
        logger.info(f"  RMSE: {rmse:.2f} | NASA Score: {nasa_score:.2f}")

    # Log all Optuna trials
    with mlflow.start_run(run_name="optuna_trials_summary"):
        for i, trial in enumerate(study.trials):
            mlflow.log_metrics({f"trial_{i}_rmse": trial.value}, step=i)
        mlflow.log_params({"n_trials": len(study.trials), "best_trial": study.best_trial.number})

    # ── XGBoost Classifier ──────────────────────────────────
    logger.info("\n  Training XGBoost Classifier (will_fail_in_30_cycles)...")
    with mlflow.start_run(run_name="xgb_classifier"):
        cls_params = best_params.copy()
        cls_params["objective"] = "binary:logistic"
        cls_params["eval_metric"] = "auc"

        clf = xgb.XGBClassifier(**cls_params)
        clf.fit(X_train, y_train_cls,
                eval_set=[(X_val, val["will_fail_30"].values)], verbose=False)

        pred_cls = clf.predict(X_test)
        pred_proba = clf.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test_cls, pred_cls)
        prec = precision_score(y_test_cls, pred_cls, zero_division=0)
        rec = recall_score(y_test_cls, pred_cls, zero_division=0)
        f1 = f1_score(y_test_cls, pred_cls, zero_division=0)
        auc = roc_auc_score(y_test_cls, pred_proba) if len(np.unique(y_test_cls)) > 1 else 0

        mlflow.log_params(cls_params)
        mlflow.log_metrics({"accuracy": acc, "precision": prec, "recall": rec,
                            "f1": f1, "auc_roc": auc})
        mlflow.xgboost.log_model(clf, "xgb_classifier")

        joblib.dump(clf, ARTIFACTS_DIR / "xgb_classifier.pkl")
        logger.info(f"  Accuracy: {acc:.4f} | Precision: {prec:.4f}")
        logger.info(f"  Recall:   {rec:.4f} | F1: {f1:.4f} | AUC: {auc:.4f}")

    # Save feature config for inference
    config = {
        "selected_sensors": SELECTED_SENSORS,
        "feature_columns": feature_cols,
        "n_features": len(feature_cols),
    }
    with open(ARTIFACTS_DIR / "feature_config.json", "w") as f:
        json.dump(config, f, indent=2)

    logger.info(f"\n✅ All failure prediction models saved to {ARTIFACTS_DIR}")
    return True


import json

if __name__ == "__main__":
    logger.info("Zydus Pharma Oncology — Failure Prediction Training")
    logger.info(f"MLflow tracking: {MLFLOW_URI}")
    ok = train_models()
    if not ok:
        sys.exit(1)
