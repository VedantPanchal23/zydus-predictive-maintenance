import pytest
import numpy as np
import pandas as pd
from ml.drift_evaluator import calculate_feature_psi, evaluate_dataset_drift
from ml.retrain_pipeline import execute_retraining_cycle, fetch_historical_training_data
from connectors.opcua_server import ZydusOPCUAServer

def test_calculate_feature_psi_identical():
    baseline = np.random.normal(50, 5, 500)
    target = baseline.copy()
    psi = calculate_feature_psi(baseline, target)
    assert psi < 0.05

def test_calculate_feature_psi_significant_drift():
    baseline = np.random.normal(50, 5, 500)
    target = np.random.normal(75, 10, 500)
    psi = calculate_feature_psi(baseline, target)
    assert psi >= 0.25

def test_evaluate_dataset_drift():
    df_base = pd.DataFrame({
        "temp": np.random.normal(50, 5, 300),
        "vibe": np.random.normal(20, 2, 300),
    })
    df_curr = pd.DataFrame({
        "temp": np.random.normal(80, 8, 300),
        "vibe": np.random.normal(20, 2, 300),
    })
    res = evaluate_dataset_drift(df_base, df_curr)
    assert res["drift_status"] in ("MODERATE_DRIFT", "SIGNIFICANT_DRIFT")
    assert "temp" in res["feature_psi"]
    assert res["max_psi"] > 0

def test_retraining_pipeline_cycle():
    result = execute_retraining_cycle(equipment_code="GRAN-LINE-01", force_promotion=True)
    assert result["equipment_code"] == "GRAN-LINE-01"
    assert result["action"] == "PROMOTE_ML_CHAMPION"
    assert result["promoted"] is True
    assert "candidate_score" in result
    assert "status_reason" in result

@pytest.mark.asyncio
async def test_opcua_server_initialization():
    srv = ZydusOPCUAServer(endpoint="opc.tcp://127.0.0.1:4841/zydus/test/")
    await srv.init()
    assert "GRAN-LINE-01" in srv.nodes
    assert "vibration_hz" in srv.nodes["GRAN-LINE-01"]
    assert "LINAC-01" in srv.nodes
