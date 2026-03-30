"""
Zydus Pharma Oncology — Data Preparation Script
================================================
Processes NASA CMAPSS and SECOM datasets for ML training.

Usage:
    python ml/data_prep/prepare_all.py

Input:
    data/raw/nasa_cmapss/train_FD001.txt ... train_FD004.txt
    data/raw/secom/secom.data, secom_labels.data

Output:
    data/processed/cmapss_train.parquet, cmapss_val.parquet, cmapss_test.parquet
    data/processed/secom_train.parquet, secom_val.parquet, secom_test.parquet
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path


# ── Paths ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

CMAPSS_DIR = RAW_DIR / "nasa_cmapss"
SECOM_DIR = RAW_DIR / "secom"

# Create output directory
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NASA CMAPSS Processing
# ============================================================

CMAPSS_COLUMNS = (
    ["engine_id", "cycle", "op1", "op2", "op3"]
    + [f"s{i}" for i in range(1, 22)]
)

SENSOR_COLS = [f"s{i}" for i in range(1, 22)]
WINDOW_SIZE = 30


def load_cmapss_file(filepath):
    """Load a single CMAPSS text file."""
    df = pd.read_csv(
        filepath,
        sep=r"\s+",
        header=None,
        names=CMAPSS_COLUMNS,
    )
    return df


def add_rul(df):
    """Calculate Remaining Useful Life for each row."""
    max_cycles = df.groupby("engine_id")["cycle"].max().reset_index()
    max_cycles.columns = ["engine_id", "max_cycle"]
    df = df.merge(max_cycles, on="engine_id")
    df["RUL"] = df["max_cycle"] - df["cycle"]
    df.drop(columns=["max_cycle"], inplace=True)
    return df


def normalize_sensors(df, scaler=None):
    """Normalize sensor columns to 0-1 range."""
    if scaler is None:
        scaler = MinMaxScaler()
        df[SENSOR_COLS] = scaler.fit_transform(df[SENSOR_COLS])
    else:
        df[SENSOR_COLS] = scaler.transform(df[SENSOR_COLS])
    return df, scaler


def create_sliding_windows(df, window_size=WINDOW_SIZE):
    """Create sliding windows of sensor data for each engine."""
    windows = []
    rul_labels = []

    for engine_id in df["engine_id"].unique():
        engine_data = df[df["engine_id"] == engine_id].sort_values("cycle")
        sensor_values = engine_data[SENSOR_COLS].values
        rul_values = engine_data["RUL"].values

        if len(sensor_values) < window_size:
            # Pad with first row if sequence is shorter than window
            padding = np.repeat(
                sensor_values[0:1], window_size - len(sensor_values), axis=0
            )
            sensor_values = np.vstack([padding, sensor_values])
            rul_values = np.concatenate(
                [np.full(window_size - len(rul_values), rul_values[0]), rul_values]
            )

        for i in range(window_size, len(sensor_values) + 1):
            window = sensor_values[i - window_size : i]
            windows.append(window.flatten())
            rul_labels.append(rul_values[i - 1])

    # Create column names for flattened windows
    col_names = [
        f"t{t}_{s}" for t in range(window_size) for s in SENSOR_COLS
    ]
    col_names.append("RUL")

    data = np.column_stack([np.array(windows), np.array(rul_labels)])
    return pd.DataFrame(data, columns=col_names)


def split_data(df, train_ratio=0.7, val_ratio=0.15):
    """Split data into train/val/test sets."""
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    # Shuffle before splitting
    df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

    train = df_shuffled[:train_end]
    val = df_shuffled[train_end:val_end]
    test = df_shuffled[val_end:]

    return train, val, test


def process_cmapss():
    """Process all NASA CMAPSS datasets."""
    print("=" * 60)
    print("Processing NASA CMAPSS datasets...")
    print("=" * 60)

    all_dfs = []
    files_found = 0

    for fd_num in range(1, 5):
        filepath = CMAPSS_DIR / f"train_FD00{fd_num}.txt"
        if filepath.exists():
            print(f"  Loading {filepath.name}...")
            df = load_cmapss_file(filepath)
            df["dataset"] = f"FD00{fd_num}"
            all_dfs.append(df)
            files_found += 1
        else:
            print(f"  ⚠ {filepath.name} not found — skipping")

    if files_found == 0:
        print("\n  ✗ No CMAPSS files found in", CMAPSS_DIR)
        print("    Please download from: https://data.nasa.gov/dataset/CMAPSS-Jet-Engine-Simulated-Data/")
        print("    Place train_FD001.txt through train_FD004.txt in data/raw/nasa_cmapss/")
        return None

    # Combine all datasets
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\n  Combined: {len(combined)} rows from {files_found} files")

    # Add RUL
    combined = add_rul(combined)
    print(f"  RUL range: 0 to {combined['RUL'].max():.0f} cycles")

    # Normalize sensors
    combined, scaler = normalize_sensors(combined)
    print(f"  Normalized {len(SENSOR_COLS)} sensor columns")

    # Create sliding windows
    print(f"  Creating {WINDOW_SIZE}-timestep sliding windows...")
    windowed = create_sliding_windows(combined)
    print(f"  Generated {len(windowed)} windows")

    # Split
    train, val, test = split_data(windowed)

    # Save
    train.to_parquet(PROCESSED_DIR / "cmapss_train.parquet", index=False)
    val.to_parquet(PROCESSED_DIR / "cmapss_val.parquet", index=False)
    test.to_parquet(PROCESSED_DIR / "cmapss_test.parquet", index=False)

    n_features = len(windowed.columns) - 1  # exclude RUL

    print(f"\nNASA CMAPSS:")
    print(f"  Train: {len(train)} rows | Val: {len(val)} rows | Test: {len(test)} rows")
    print(f"  Features: {n_features} columns | RUL range: 0 to {int(combined['RUL'].max())} cycles")

    return {"train": len(train), "val": len(val), "test": len(test), "features": n_features}


# ============================================================
# SECOM Processing
# ============================================================

def process_secom():
    """Process SECOM semiconductor manufacturing dataset."""
    print("\n" + "=" * 60)
    print("Processing SECOM dataset...")
    print("=" * 60)

    data_path = SECOM_DIR / "secom.data"
    labels_path = SECOM_DIR / "secom_labels.data"

    if not data_path.exists() or not labels_path.exists():
        print(f"\n  ✗ SECOM files not found in {SECOM_DIR}")
        print("    Please download from: https://archive.ics.uci.edu/ml/datasets/SECOM")
        print("    Place secom.data and secom_labels.data in data/raw/secom/")
        return None

    # Load data
    print("  Loading secom.data...")
    data = pd.read_csv(data_path, sep=r"\s+", header=None)
    print(f"  Raw data shape: {data.shape}")

    # Load labels
    print("  Loading secom_labels.data...")
    labels_df = pd.read_csv(labels_path, sep=r"\s+", header=None, names=["label", "timestamp"])
    labels = labels_df["label"].values
    # Convert labels: -1 (pass) → 0, 1 (fail) → 1
    labels = np.where(labels == -1, 0, labels)

    original_cols = data.shape[1]

    # Remove columns with > 50% missing values
    missing_ratio = data.isnull().mean()
    cols_to_keep = missing_ratio[missing_ratio <= 0.5].index.tolist()
    data = data[cols_to_keep]
    removed_cols = original_cols - len(cols_to_keep)
    print(f"  Removed {removed_cols} columns with >50% missing values")
    print(f"  Remaining columns: {len(cols_to_keep)}")

    # Fill missing values with column median
    data = data.fillna(data.median())
    print("  Filled remaining NaN with column medians")

    # Normalize to 0-1
    scaler = MinMaxScaler()
    data_normalized = pd.DataFrame(
        scaler.fit_transform(data),
        columns=[f"feature_{i}" for i in range(data.shape[1])],
    )

    # Add label column
    data_normalized["label"] = labels

    # Split
    train, val, test = split_data(data_normalized)

    # Save
    train.to_parquet(PROCESSED_DIR / "secom_train.parquet", index=False)
    val.to_parquet(PROCESSED_DIR / "secom_val.parquet", index=False)
    test.to_parquet(PROCESSED_DIR / "secom_test.parquet", index=False)

    failure_rate = (labels.sum() / len(labels)) * 100
    n_features = data_normalized.shape[1] - 1  # exclude label

    print(f"\nSECOM:")
    print(f"  Train: {len(train)} rows | Val: {len(val)} rows | Test: {len(test)} rows")
    print(f"  Features: {n_features} columns | Failure rate: {failure_rate:.1f}%")

    return {"train": len(train), "val": len(val), "test": len(test), "features": n_features}


# ============================================================
# Main
# ============================================================

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Zydus Pharma Oncology — Data Preparation Pipeline      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    cmapss_result = process_cmapss()
    secom_result = process_secom()

    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if cmapss_result:
        print(f"\nNASA CMAPSS:")
        print(f"  Train: {cmapss_result['train']} rows | Val: {cmapss_result['val']} rows | Test: {cmapss_result['test']} rows")
        print(f"  Features: {cmapss_result['features']} columns")
    else:
        print("\nNASA CMAPSS: ✗ Not processed (files missing)")

    if secom_result:
        print(f"\nSECOM:")
        print(f"  Train: {secom_result['train']} rows | Val: {secom_result['val']} rows | Test: {secom_result['test']} rows")
        print(f"  Features: {secom_result['features']} columns")
    else:
        print("\nSECOM: ✗ Not processed (files missing)")

    print(f"\nAll files saved to {PROCESSED_DIR}/")
    print()

    # Exit with error if nothing was processed
    if not cmapss_result and not secom_result:
        print("⚠ No datasets were processed. Please download the datasets first.")
        sys.exit(1)


if __name__ == "__main__":
    main()
