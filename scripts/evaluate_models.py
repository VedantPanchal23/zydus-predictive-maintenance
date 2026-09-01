"""Lightweight evaluation script to compute current ML metrics.

This script loads raw CMAPSS data, engineers features using the same logic
as the training pipeline, then loads artifacts from `ml/artifacts` and
computes classification and regression metrics. Results are printed and
written to `ml/artifacts/validation_results.json`.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_squared_error,
)

from ml.models.failure_predictor import (
    load_raw_cmapss,
    engineer_features,
    get_feature_columns,
    nasa_scoring,
)


def main():
    project_root = Path(__file__).resolve().parent.parent
    artifacts_dir = project_root / "ml" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    raw = load_raw_cmapss()
    if raw is None:
        print("No CMAPSS raw data found under data/raw/nasa_cmapss. Aborting.")
        sys.exit(2)

    featured = engineer_features(raw)
    feature_cols = get_feature_columns()
    featured = featured.dropna(subset=feature_cols)
    featured["will_fail_30"] = (featured["RUL"] <= 30).astype(int)

    engines = featured["engine_id"].unique()
    np.random.seed(42)
    np.random.shuffle(engines)
    n = len(engines)
    train_eng = engines[: int(0.7 * n)]
    val_eng = engines[int(0.7 * n) : int(0.85 * n)]
    test_eng = engines[int(0.85 * n) :]

    test = featured[featured["engine_id"].isin(test_eng)].copy()
    if test.empty:
        print("Test split is empty. Cannot evaluate.")
        sys.exit(2)

    X_test = test[feature_cols].values
    y_test_cls = test["will_fail_30"].values
    y_test_rul = test["RUL"].values

    out = {"classifier": None, "regressor": None}

    # Load scaler if available
    scaler_path = artifacts_dir / "feature_scaler.pkl"
    if scaler_path.exists():
        scaler = joblib.load(scaler_path)
        try:
            # If scaler expects a DataFrame with names, preserve names
            if hasattr(scaler, "feature_names_in_"):
                Xf = pd.DataFrame(X_test, columns=list(scaler.feature_names_in_[: X_test.shape[1]]))
                X_test_scaled = scaler.transform(Xf)
            else:
                X_test_scaled = scaler.transform(X_test)
        except Exception:
            X_test_scaled = X_test
    else:
        X_test_scaled = X_test

    # Classifier
    clf_path = artifacts_dir / "xgb_classifier.pkl"
    if clf_path.exists():
        clf = joblib.load(clf_path)
        try:
            preds = clf.predict(X_test_scaled)
            probs = clf.predict_proba(X_test_scaled)[:, 1]
            acc = accuracy_score(y_test_cls, preds)
            prec = precision_score(y_test_cls, preds, zero_division=0)
            rec = recall_score(y_test_cls, preds, zero_division=0)
            f1 = f1_score(y_test_cls, preds, zero_division=0)
            auc = roc_auc_score(y_test_cls, probs) if len(np.unique(y_test_cls)) > 1 else 0
            out["classifier"] = {
                "accuracy": float(acc),
                "precision": float(prec),
                "recall": float(rec),
                "f1": float(f1),
                "auc_roc": float(auc),
            }
        except Exception as exc:
            out["classifier"] = {"error": str(exc)}

    # Regressor
    reg_path = artifacts_dir / "xgb_regressor.pkl"
    if reg_path.exists():
        reg = joblib.load(reg_path)
        try:
            pred_rul = reg.predict(X_test_scaled)
            rmse = float(np.sqrt(mean_squared_error(y_test_rul, pred_rul)))
            nasa = float(nasa_scoring(y_test_rul, pred_rul))
            out["regressor"] = {"rmse": rmse, "nasa_score": nasa}
        except Exception as exc:
            out["regressor"] = {"error": str(exc)}

    # Write results
    out_path = artifacts_dir / "validation_results.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
