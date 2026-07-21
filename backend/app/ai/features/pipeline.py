from typing import List, Dict, Any
from collections import deque
from ..domain.plant_state import ZoneSnapshot, PlantSnapshot
from ..ingestion.validators import AssetValidator
from .models import FeatureVector
from .extractors.extractors import (
    RawExtractor, RollingExtractor, TrendExtractor, 
    CrossSensorExtractor, EquipmentExtractor, PermitExtractor, DataQualityExtractor,
    GeospatialExtractor, MaintenanceExtractor
)

class FeaturePipeline:
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        self.config = config
        self.validator = validator
        self.extractors = [
            RawExtractor(config, validator),
            RollingExtractor(config, validator),
            TrendExtractor(config, validator),
            CrossSensorExtractor(config, validator),
            EquipmentExtractor(config, validator),
            PermitExtractor(config, validator),
            DataQualityExtractor(config, validator),
            GeospatialExtractor(config, validator),
            MaintenanceExtractor(config, validator)
        ]
        
    def transform(self, history: List[PlantSnapshot]) -> Dict[str, List[FeatureVector]]:
        """Process a batch of PlantSnapshots and return feature vectors grouped by zone."""
        results: Dict[str, List[FeatureVector]] = {}
        
        # We need zone-specific history
        zone_histories: Dict[str, List[ZoneSnapshot]] = {}
        
        for plant_snap in history:
            for zone_id, zone_snap in plant_snap.zones.items():
                if zone_id not in zone_histories:
                    zone_histories[zone_id] = []
                    results[zone_id] = []
                    
                zone_histories[zone_id].append(zone_snap)
                
                # Extract features for this zone at this timestamp
                vector = FeatureVector(
                    timestamp=zone_snap.timestamp,
                    zone_id=zone_id
                )
                
                for extractor in self.extractors:
                    features = extractor.extract(zone_snap, zone_histories[zone_id])
                    for feat in features:
                        vector.features[feat.name] = feat
                        
                results[zone_id].append(vector)
                
        return results

class StreamingFeaturePipeline:
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        self.config = config
        self.validator = validator
        self.pipeline = FeaturePipeline(config, validator)
        max_history = max(config.get("rolling_windows", [300])) * 2 # buffer size based on max window
        self.history: deque = deque(maxlen=int(max_history))
        
    def update(self, plant_snap: PlantSnapshot) -> Dict[str, FeatureVector]:
        self.history.append(plant_snap)
        
        # To avoid re-processing the whole history, we only pass the history up to now,
        # and we only want the result for the current timestamp.
        # But we can just use the transform method and take the last element.
        # Alternatively, we build a specific single-step transform to be more efficient.
        
        # For simplicity and correctness in this example, we'll re-use transform logic but only for the latest snapshot.
        vectors: Dict[str, FeatureVector] = {}
        
        # Group history by zone
        zone_histories: Dict[str, List[ZoneSnapshot]] = {}
        for snap in self.history:
            for zone_id, zone_snap in snap.zones.items():
                if zone_id not in zone_histories:
                    zone_histories[zone_id] = []
                zone_histories[zone_id].append(zone_snap)
                
        # Extract only for the latest snapshot
        for zone_id, zone_snap in plant_snap.zones.items():
            vector = FeatureVector(timestamp=zone_snap.timestamp, zone_id=zone_id)
            for extractor in self.pipeline.extractors:
                features = extractor.extract(zone_snap, zone_histories.get(zone_id, []))
                for feat in features:
                    vector.features[feat.name] = feat
            vectors[zone_id] = vector
            
        return vectors
