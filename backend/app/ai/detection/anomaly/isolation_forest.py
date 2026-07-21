import os
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .models import AnomalyResult, FeatureContribution
from ...features.models import FeatureVector

class IsolationForestDetector:
    def __init__(self, config: Dict[str, Any], version: str = "1.0.0"):
        self.config = config
        self.version = version
        self.model = IsolationForest(
            n_estimators=config.get("n_estimators", 100),
            contamination=config.get("contamination", 0.01),
            random_state=config.get("random_state", 42)
        )
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted = False
        
    def fit(self, df: pd.DataFrame, feature_cols: List[str]):
        """Train the model on normal data."""
        self.feature_names = feature_cols
        X = df[feature_cols].fillna(0.0).values
        
        # Fit scaler
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        # Fit Isolation Forest
        self.model.fit(X_scaled)
        self.is_fitted = True
        
    def predict(self, feature_vector: FeatureVector) -> AnomalyResult:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction.")
            
        # Extract features
        x = np.zeros((1, len(self.feature_names)))
        for i, f_name in enumerate(self.feature_names):
            if f_name in feature_vector.features:
                x[0, i] = feature_vector.features[f_name].value
                
        # Scale
        x_scaled = self.scaler.transform(x)
        
        # Raw score: lower is more anomalous (sklearn IF returns negative for anomalies)
        # We want: 1.0 is highly anomalous, 0.0 is normal.
        raw_score = self.model.decision_function(x_scaled)[0]
        # sklearn decision_function is around 0.5 to -0.5. 
        # Negative means anomaly.
        
        # Normalize to 0-1 (approximate)
        # Assuming scores range roughly from -0.5 to 0.5
        norm_score = np.clip(0.5 - raw_score, 0, 1.0)
        
        is_anomalous = self.model.predict(x_scaled)[0] == -1
        
        # Calculate approximate feature contributions based on deviation from mean
        deviations = np.abs(x_scaled[0])
        total_dev = np.sum(deviations) + 1e-9
        contributions = deviations / total_dev
        
        # Sort features by contribution
        top_indices = np.argsort(contributions)[::-1]
        
        feature_contribs = []
        top_features = []
        
        for i in top_indices[:5]: # Top 5
            name = self.feature_names[i]
            contrib = float(contributions[i])
            if contrib > 0.1: # Only include if it contributes significantly
                top_features.append(name)
                feature_contribs.append(FeatureContribution(
                    feature_name=name,
                    contribution_score=contrib,
                    is_approximate=True
                ))
                
        return AnomalyResult(
            raw_model_score=float(raw_score),
            normalized_score=float(norm_score),
            is_anomalous=bool(is_anomalous),
            model_version=self.version,
            feature_contributions=feature_contribs,
            data_quality_status="VALID",
            confidence=0.8, # Placeholder confidence
            top_deviating_features=top_features
        )
        
    def save(self, path: str):
        os.makedirs(path, exist_ok=True)
        joblib.dump(self.model, os.path.join(path, "model.joblib"))
        joblib.dump(self.scaler, os.path.join(path, "scaler.joblib"))
        joblib.dump(self.feature_names, os.path.join(path, "features.joblib"))
        
    @classmethod
    def load(cls, path: str, config: Dict[str, Any]):
        instance = cls(config)
        instance.model = joblib.load(os.path.join(path, "model.joblib"))
        instance.scaler = joblib.load(os.path.join(path, "scaler.joblib"))
        instance.feature_names = joblib.load(os.path.join(path, "features.joblib"))
        instance.is_fitted = True
        return instance
