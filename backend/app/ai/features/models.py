from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class FeatureMetadata(BaseModel):
    name: str
    category: str
    unit: str
    description: str
    source_types: List[str]
    window_seconds: Optional[int] = None
    safety_relevance: str

class FeatureValue(BaseModel):
    name: str
    value: float
    timestamp: datetime
    zone_id: str
    source_sensors: List[str] = Field(default_factory=list)
    quality_flags: List[str] = Field(default_factory=list)

class FeatureVector(BaseModel):
    timestamp: datetime
    zone_id: str
    features: Dict[str, FeatureValue] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Returns a flat dictionary mapping feature names to scalar values."""
        return {name: feat.value for name, feat in self.features.items()}
