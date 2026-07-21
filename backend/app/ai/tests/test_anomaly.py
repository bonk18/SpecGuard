import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from ..features.models import FeatureVector, FeatureValue
from ..detection.anomaly.isolation_forest import IsolationForestDetector

@pytest.fixture
def detector(tmp_path):
    config = {
        "n_estimators": 50,
        "contamination": 0.1,
        "random_state": 42
    }
    det = IsolationForestDetector(config)
    
    # Create dummy training data (normal only)
    np.random.seed(42)
    data = {
        "f1": np.random.normal(10, 1, 100),
        "f2": np.random.normal(50, 5, 100)
    }
    df = pd.DataFrame(data)
    
    det.fit(df, ["f1", "f2"])
    return det

def test_anomaly_detector_normal(detector):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    fv.features["f1"] = FeatureValue(name="f1", value=10.1, timestamp=now, zone_id="Z1")
    fv.features["f2"] = FeatureValue(name="f2", value=49.5, timestamp=now, zone_id="Z1")
    
    result = detector.predict(fv)
    assert not result.is_anomalous
    assert 0.0 <= result.normalized_score <= 1.0

def test_anomaly_detector_abnormal(detector):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    # Anomalous values far from mean
    fv.features["f1"] = FeatureValue(name="f1", value=20.0, timestamp=now, zone_id="Z1")
    fv.features["f2"] = FeatureValue(name="f2", value=100.0, timestamp=now, zone_id="Z1")
    
    result = detector.predict(fv)
    assert result.is_anomalous
    assert result.normalized_score > 0.5
    assert len(result.feature_contributions) > 0
    
def test_missing_features(detector):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    # Only f1 is provided, f2 is missing (will default to 0 during scaling)
    fv.features["f1"] = FeatureValue(name="f1", value=10.1, timestamp=now, zone_id="Z1")
    
    # Model should still predict without crashing
    result = detector.predict(fv)
    assert result is not None

def test_serialization(detector, tmp_path):
    path = str(tmp_path / "model_dir")
    detector.save(path)
    
    loaded_detector = IsolationForestDetector.load(path, config={})
    assert loaded_detector.is_fitted
    assert len(loaded_detector.feature_names) == 2
    
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    fv.features["f1"] = FeatureValue(name="f1", value=10.1, timestamp=now, zone_id="Z1")
    fv.features["f2"] = FeatureValue(name="f2", value=49.5, timestamp=now, zone_id="Z1")
    
    res1 = detector.predict(fv)
    res2 = loaded_detector.predict(fv)
    
    assert res1.raw_model_score == res2.raw_model_score
