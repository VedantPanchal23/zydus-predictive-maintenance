"""
Anomaly Detection Models — Training Script
============================================
Model 1: Isolation Forest (sklearn) on SECOM data
Model 2: LSTM Autoencoder (PyTorch) on CMAPSS data

Uses 5 representative features/sensors for compatibility with
real-time inference on 5-sensor equipment.

Usage:
    python ml/models/anomaly_detector.py
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.preprocessing import MinMaxScaler

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

import mlflow
import mlflow.sklearn
import mlflow.pytorch

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)

# 5 most informative CMAPSS sensors (from literature)
SELECTED_SENSORS = ["s2", "s3", "s4", "s7", "s11"]
N_SENSORS = len(SELECTED_SENSORS)
WINDOW_SIZE = 30


# ════════════════════════════════════════════════════════════
#  LSTM Autoencoder Architecture
# ════════════════════════════════════════════════════════════
class LSTMAutoencoder(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, latent_size=16):
        super().__init__()
        self.input_size = input_size
        # Encoder
        self.encoder_lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.encoder_fc = nn.Linear(hidden_size, latent_size)
        # Decoder
        self.decoder_fc = nn.Linear(latent_size, hidden_size)
        self.decoder_lstm = nn.LSTM(hidden_size, input_size, batch_first=True)
        self.output_fc = nn.Linear(input_size, input_size)

    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        _, (h, _) = self.encoder_lstm(x)
        z = self.encoder_fc(h.squeeze(0))
        h_dec = self.decoder_fc(z)
        decoder_input = h_dec.unsqueeze(1).repeat(1, seq_len, 1)
        decoded, _ = self.decoder_lstm(decoder_input)
        output = self.output_fc(decoded)
        return output


# ════════════════════════════════════════════════════════════
#  Model 1 — Isolation Forest
# ════════════════════════════════════════════════════════════
def train_isolation_forest():
    logger.info("=" * 60)
    logger.info("Training Isolation Forest on SECOM data")
    logger.info("=" * 60)

    train_path = PROCESSED_DIR / "secom_train.parquet"
    test_path = PROCESSED_DIR / "secom_test.parquet"
    if not train_path.exists():
        logger.error(f"SECOM data not found at {train_path}. Run prepare_all.py first.")
        return False

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)

    feature_cols = [c for c in train_df.columns if c != "label"]
    # Select top 5 features by variance for dimension compatibility
    variances = train_df[feature_cols].var().sort_values(ascending=False)
    top5_features = variances.head(N_SENSORS).index.tolist()
    logger.info(f"Selected top-5 features: {top5_features}")

    X_train = train_df[top5_features].values
    X_test = test_df[top5_features].values
    y_test = test_df["label"].values

    # Save scaler for these features
    scaler = MinMaxScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    n_estimators = 200
    contamination = 0.1

    mlflow.set_experiment("anomaly_detection")
    with mlflow.start_run(run_name="isolation_forest"):
        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train)

        y_pred = model.predict(X_test)
        y_pred_binary = (y_pred == -1).astype(int)

        precision = precision_score(y_test, y_pred_binary, zero_division=0)
        recall = recall_score(y_test, y_pred_binary, zero_division=0)
        f1 = f1_score(y_test, y_pred_binary, zero_division=0)

        mlflow.log_params({
            "contamination": contamination,
            "n_estimators": n_estimators,
            "n_features": N_SENSORS,
        })
        mlflow.log_metrics({"precision": precision, "recall": recall, "f1": f1})
        mlflow.sklearn.log_model(model, "isolation_forest")

        # Save artifact
        joblib.dump(model, ARTIFACTS_DIR / "isolation_forest.pkl")
        joblib.dump(scaler, ARTIFACTS_DIR / "if_scaler.pkl")
        logger.info(f"  Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
        logger.info(f"  Saved to {ARTIFACTS_DIR / 'isolation_forest.pkl'}")

    return True


# ════════════════════════════════════════════════════════════
#  Model 2 — LSTM Autoencoder
# ════════════════════════════════════════════════════════════
def train_lstm_autoencoder():
    logger.info("=" * 60)
    logger.info("Training LSTM Autoencoder on CMAPSS data")
    logger.info("=" * 60)

    train_path = PROCESSED_DIR / "cmapss_train.parquet"
    val_path = PROCESSED_DIR / "cmapss_val.parquet"
    test_path = PROCESSED_DIR / "cmapss_test.parquet"
    if not train_path.exists():
        logger.error(f"CMAPSS data not found at {train_path}. Run prepare_all.py first.")
        return False

    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)

    def extract_windows(df):
        """Extract (N, 30, 5) windows from flattened parquet data."""
        cols = [f"t{t}_{s}" for t in range(WINDOW_SIZE) for s in SELECTED_SENSORS]
        available = [c for c in cols if c in df.columns]
        if len(available) < WINDOW_SIZE * N_SENSORS:
            logger.warning(f"Only {len(available)} of {WINDOW_SIZE * N_SENSORS} columns found")
            cols = available
        data = df[cols].values
        n_samples = len(data)
        n_features_found = len(cols) // WINDOW_SIZE
        return data.reshape(n_samples, WINDOW_SIZE, n_features_found)

    X_train = extract_windows(train_df)
    X_val = extract_windows(val_df)
    X_test = extract_windows(test_df)
    actual_features = X_train.shape[2]

    # Use only normal data for autoencoder training (low RUL = degraded)
    if "RUL" in train_df.columns:
        normal_mask = train_df["RUL"].values > 100
        X_train_normal = X_train[normal_mask]
        if len(X_train_normal) < 100:
            X_train_normal = X_train
    else:
        X_train_normal = X_train

    logger.info(f"  Train windows: {X_train_normal.shape} | Val: {X_val.shape}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"  Device: {device}")

    train_tensor = torch.FloatTensor(X_train_normal).to(device)
    val_tensor = torch.FloatTensor(X_val).to(device)

    train_loader = DataLoader(TensorDataset(train_tensor), batch_size=64, shuffle=True)
    val_loader = DataLoader(TensorDataset(val_tensor), batch_size=64)

    # Hyperparameters
    hidden_size = 64
    latent_size = 16
    lr = 0.001
    epochs = 50
    patience = 5

    model = LSTMAutoencoder(actual_features, hidden_size, latent_size).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    mlflow.set_experiment("anomaly_detection")
    with mlflow.start_run(run_name="lstm_autoencoder"):
        mlflow.log_params({
            "epochs": epochs, "batch_size": 64,
            "hidden_size": hidden_size, "latent_size": latent_size,
            "lr": lr, "input_size": actual_features, "window_size": WINDOW_SIZE,
        })

        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(epochs):
            model.train()
            train_loss = 0
            for (batch,) in train_loader:
                optimizer.zero_grad()
                output = model(batch)
                loss = criterion(output, batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            train_loss /= len(train_loader)

            model.eval()
            val_loss = 0
            with torch.no_grad():
                for (batch,) in val_loader:
                    output = model(batch)
                    val_loss += criterion(output, batch).item()
            val_loss /= len(val_loader)

            if (epoch + 1) % 5 == 0 or epoch == 0:
                logger.info(f"  Epoch {epoch+1}/{epochs} | Train: {train_loss:.6f} | Val: {val_loss:.6f}")
            mlflow.log_metrics({"train_loss": train_loss, "val_loss": val_loss}, step=epoch)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                torch.save(model.state_dict(), ARTIFACTS_DIR / "lstm_autoencoder.pth")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"  Early stopping at epoch {epoch+1}")
                    break

        # Compute anomaly threshold from validation errors
        model.load_state_dict(torch.load(ARTIFACTS_DIR / "lstm_autoencoder.pth", weights_only=True))
        model.eval()
        val_errors = []
        with torch.no_grad():
            for (batch,) in val_loader:
                output = model(batch)
                errors = torch.mean((output - batch) ** 2, dim=(1, 2))
                val_errors.extend(errors.cpu().numpy())

        threshold = float(np.mean(val_errors) + 2 * np.std(val_errors))
        threshold_data = {
            "threshold": threshold,
            "mean_error": float(np.mean(val_errors)),
            "std_error": float(np.std(val_errors)),
            "input_size": actual_features,
            "window_size": WINDOW_SIZE,
            "hidden_size": hidden_size,
            "latent_size": latent_size,
        }
        with open(ARTIFACTS_DIR / "lstm_threshold.json", "w") as f:
            json.dump(threshold_data, f, indent=2)

        # Compute metrics: classify val samples as anomaly if error > threshold
        y_pred = (np.array(val_errors) > threshold).astype(int)
        if "RUL" in val_df.columns:
            y_true = (val_df["RUL"].values[:len(y_pred)] <= 30).astype(int)
            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
        else:
            precision = recall = f1 = 0.0

        mlflow.log_metrics({
            "threshold": threshold, "best_val_loss": best_val_loss,
            "precision": precision, "recall": recall, "f1": f1,
        })
        mlflow.pytorch.log_model(model, "lstm_autoencoder")

        logger.info(f"  Threshold: {threshold:.6f}")
        logger.info(f"  Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
        logger.info(f"  Saved to {ARTIFACTS_DIR}")

    return True


# ════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("Zydus Pharma Oncology — Anomaly Detection Training")
    logger.info(f"MLflow tracking: {MLFLOW_URI}")

    ok1 = train_isolation_forest()
    ok2 = train_lstm_autoencoder()

    if ok1 and ok2:
        logger.info("\n✅ All anomaly detection models trained and saved!")
    else:
        logger.error("\n❌ Some models failed to train. Check errors above.")
        sys.exit(1)
