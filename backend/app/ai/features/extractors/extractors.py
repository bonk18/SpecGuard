from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from ...domain.plant_state import ZoneSnapshot, DataQualityStatus
from ...ingestion.validators import AssetValidator
from ..models import FeatureVector, FeatureValue, FeatureMetadata
from ..registry import registry

class BaseExtractor:
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        self.config = config
        self.validator = validator
        self.category = "base"

    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        raise NotImplementedError

class RawExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "raw"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        # Extract normalized sensor values
        for sensor_id, reading in snapshot.sensor_values.items():
            if reading.data_quality_status == DataQualityStatus.STALE:
                continue # or handle based on policy
                
            sensor_info = self.validator.sensor_mapping.get("sensors", {}).get(sensor_id, {})
            min_val = sensor_info.get("min_val", 0.0)
            max_val = sensor_info.get("max_val", 100.0)
            
            # Normalize
            if max_val > min_val:
                norm_value = (reading.value - min_val) / (max_val - min_val)
            else:
                norm_value = reading.value
                
            feature_name = f"{reading.category}_norm_{sensor_id}"
            
            if not registry.get_metadata(feature_name):
                registry.register(FeatureMetadata(
                    name=feature_name,
                    category=self.category,
                    unit="normalized",
                    description=f"Normalized {reading.category} for {sensor_id}",
                    source_types=["sensor"],
                    safety_relevance="Basic state indication"
                ))
                
            features.append(FeatureValue(
                name=feature_name,
                value=norm_value,
                timestamp=snapshot.timestamp,
                zone_id=snapshot.zone_id,
                source_sensors=[sensor_id],
                quality_flags=[reading.data_quality_status.value]
            ))
            
        # Add explicit features required by rules
        cat_map = {
            "hydrocarbon": ("max_hydrocarbon_lel_pct", max, 0.0),
            "h2s": ("max_h2s_ppm", max, 0.0),
            "oxygen": ("min_oxygen_pct", min, 21.0),
            "valve_position": ("max_valve_position", max, 0.0),
            "pressure": ("max_pressure_bar", max, 0.0),
            "vibration": ("max_vibration", max, 0.0),
            "ventilation_health": ("ventilation_health", min, 1.0),
            "fire": ("fire_detected", max, 0.0),
            "smoke": ("smoke_detected", max, 0.0),
            "unack_alarm": ("unack_alarm_count", sum, 0.0)
        }
        
        for cat, (feat_name, agg_func, default_val) in cat_map.items():
            vals = [r.value for r in snapshot.sensor_values.values() if r.category == cat]
            val = agg_func(vals) if vals else default_val
            
            if not registry.get_metadata(feat_name):
                registry.register(FeatureMetadata(
                    name=feat_name, category=self.category, unit="raw", description=feat_name, source_types=["sensor"], safety_relevance=feat_name
                ))
            features.append(FeatureValue(name=feat_name, value=float(val), timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
            
        # Pressure disagreement
        pressures = [r.value for r in snapshot.sensor_values.values() if r.category == "pressure"]
        p_dis = 1.0 if (len(pressures) >= 2 and max(pressures) - min(pressures) > 2.0) else 0.0
        if not registry.get_metadata("pressure_disagreement"):
            registry.register(FeatureMetadata(name="pressure_disagreement", category=self.category, unit="bool", description="Pressure disagreement", source_types=["sensor"], safety_relevance="Sensor divergence"))
        features.append(FeatureValue(name="pressure_disagreement", value=p_dis, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))

        # Add basic count features
        features.append(FeatureValue(
            name="worker_count",
            value=float(len(snapshot.workers_present)),
            timestamp=snapshot.timestamp,
            zone_id=snapshot.zone_id,
            source_sensors=[],
            quality_flags=[]
        ))
        if not registry.get_metadata("worker_count"):
            registry.register(FeatureMetadata(
                name="worker_count", category="raw", unit="count", description="Workers in zone",
                source_types=["worker"], safety_relevance="Exposure metric"
            ))

        features.append(FeatureValue(
            name="active_permit_count",
            value=float(len(snapshot.active_permits)),
            timestamp=snapshot.timestamp,
            zone_id=snapshot.zone_id
        ))
        if not registry.get_metadata("active_permit_count"):
             registry.register(FeatureMetadata(
                name="active_permit_count", category="raw", unit="count", description="Active permits",
                source_types=["permit"], safety_relevance="SIMOPS indicator"
            ))
            
        return features

class RollingExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "rolling"
        self.windows = config.get("rolling_windows", [30, 60, 300])

    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        if not history:
            return features
            
        for window in self.windows:
            cutoff = snapshot.timestamp.timestamp() - window
            
            # Gather valid values for each sensor in the window
            sensor_series: Dict[str, List[float]] = {}
            for hist_snap in history:
                if hist_snap.timestamp.timestamp() >= cutoff:
                    for s_id, reading in hist_snap.sensor_values.items():
                        if reading.data_quality_status != DataQualityStatus.STALE:
                            if s_id not in sensor_series:
                                sensor_series[s_id] = []
                            sensor_series[s_id].append(reading.value)
                            
            # Calculate stats
            for s_id, values in sensor_series.items():
                if len(values) >= self.config.get("min_samples_for_rolling", 3):
                    mean_val = np.mean(values)
                    feat_name = f"rolling_mean_{window}s_{s_id}"
                    
                    if not registry.get_metadata(feat_name):
                        registry.register(FeatureMetadata(
                            name=feat_name, category=self.category, unit="raw",
                            description=f"{window}s rolling mean for {s_id}",
                            source_types=["sensor"], window_seconds=window,
                            safety_relevance="Trend smoothing"
                        ))
                        
                    features.append(FeatureValue(
                        name=feat_name,
                        value=float(mean_val),
                        timestamp=snapshot.timestamp,
                        zone_id=snapshot.zone_id,
                        source_sensors=[s_id]
                    ))
        return features

class TrendExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "trend"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        if len(history) < 2:
            return features
            
        prev_snap = history[-2] # Last snapshot before current
        dt = (snapshot.timestamp - prev_snap.timestamp).total_seconds()
        
        if dt <= 0:
            return features
            
        for s_id, reading in snapshot.sensor_values.items():
            if s_id in prev_snap.sensor_values:
                prev_reading = prev_snap.sensor_values[s_id]
                if reading.data_quality_status != DataQualityStatus.STALE and prev_reading.data_quality_status != DataQualityStatus.STALE:
                    slope = (reading.value - prev_reading.value) / dt
                    feat_name = f"slope_{s_id}"
                    
                    if not registry.get_metadata(feat_name):
                         registry.register(FeatureMetadata(
                            name=feat_name, category=self.category, unit="rate/s",
                            description=f"First derivative for {s_id}",
                            source_types=["sensor"], safety_relevance="Rapid change indicator"
                        ))
                        
                    features.append(FeatureValue(
                        name=feat_name,
                        value=slope,
                        timestamp=snapshot.timestamp,
                        zone_id=snapshot.zone_id,
                        source_sensors=[s_id]
                    ))
                    
        # Map explicit category trends
        cat_map = {
            "hydrocarbon": "slope_hydrocarbon",
            "pressure": "slope_pressure",
            "temperature": "slope_temperature",
        }
        
        for cat, fname in cat_map.items():
            vals = [r.value for r in snapshot.sensor_values.values() if r.category == cat]
            prev_vals = [r.value for r in prev_snap.sensor_values.values() if r.category == cat]
            val = (max(vals) - max(prev_vals)) / dt if vals and prev_vals else 0.0
            
            if not registry.get_metadata(fname):
                registry.register(FeatureMetadata(name=fname, category=self.category, unit="rate/s", description=fname, source_types=["sensor"], safety_relevance=fname))
            features.append(FeatureValue(name=fname, value=float(val), timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
            
        return features

class CrossSensorExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "cross_sensor"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        # Example: Gas vs Oxygen reduction (if both are present in the zone)
        has_gas = False
        has_o2 = False
        gas_val = 0.0
        o2_val = 21.0
        
        for s_id, reading in snapshot.sensor_values.items():
            if reading.category == "hydrocarbon_lel_pct":
                has_gas = True
                gas_val = max(gas_val, reading.value)
            elif reading.category == "oxygen_pct":
                has_o2 = True
                o2_val = min(o2_val, reading.value)
                
        if has_gas and has_o2:
             feat_name = "gas_o2_mismatch"
             # Ratio of gas LEL to (21 - O2) - synthetic feature for demonstration
             reduction = max(0.1, 21.0 - o2_val)
             mismatch = gas_val / reduction
             
             if not registry.get_metadata(feat_name):
                 registry.register(FeatureMetadata(
                     name=feat_name, category=self.category, unit="ratio",
                     description="Ratio of Gas LEL to Oxygen reduction",
                     source_types=["hydrocarbon_lel_pct", "oxygen_pct"],
                     safety_relevance="Fire/Explosion precursor"
                 ))
             features.append(FeatureValue(
                 name=feat_name, value=mismatch, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id
             ))
             
        # Add Pressure vs Flow mismatch example
        # Need to know which sensors are linked, simplify by finding any pressure and flow in zone
        pressure_val = sum(r.value for r in snapshot.sensor_values.values() if r.category == "pressure_bar")
        flow_val = sum(r.value for r in snapshot.sensor_values.values() if r.category == "flow_rate")
        if flow_val > 0:
            features.append(FeatureValue(
                name="pressure_flow_ratio",
                value=pressure_val / flow_val,
                timestamp=snapshot.timestamp,
                zone_id=snapshot.zone_id
            ))
            if not registry.get_metadata("pressure_flow_ratio"):
                 registry.register(FeatureMetadata(name="pressure_flow_ratio", category="cross_sensor", unit="ratio", description="P/F ratio", source_types=["sensor"], safety_relevance="Blockage"))
                 
        return features

class EquipmentExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "equipment"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        for eq_id, state in snapshot.equipment_states.items():
            if state.health_score is not None:
                feat_name = f"health_score_{eq_id}"
                if not registry.get_metadata(feat_name):
                    registry.register(FeatureMetadata(
                        name=feat_name, category=self.category, unit="score",
                        description=f"Health score for {eq_id}", source_types=["equipment"],
                        safety_relevance="Equipment degradation"
                    ))
                features.append(FeatureValue(
                    name=feat_name, value=state.health_score, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id, source_sensors=[eq_id]
                ))
        return features

class PermitExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "permit"
        
    def _register_and_append(self, features, feat_name, value, timestamp, zone_id, description):
        if not registry.get_metadata(feat_name):
            registry.register(FeatureMetadata(name=feat_name, category=self.category, unit="bool", description=description, source_types=["permit"], safety_relevance=description))
        features.append(FeatureValue(name=feat_name, value=float(value), timestamp=timestamp, zone_id=zone_id))

    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        hot_work = any(p.permit_type == "HOT_WORK" for p in snapshot.active_permits.values())
        confined = any(p.permit_type == "CONFINED_SPACE" for p in snapshot.active_permits.values())
        line_break = any(p.permit_type == "LINE_BREAK" for p in snapshot.active_permits.values())
        shift_handover = any(p.permit_type == "SHIFT_HANDOVER" for p in snapshot.active_permits.values())
        process_active = any(p.permit_type == "PROCESS_ACTIVE" for p in snapshot.active_permits.values())
        
        self._register_and_append(features, "hot_work_active", hot_work, snapshot.timestamp, snapshot.zone_id, "Hot work active")
        self._register_and_append(features, "confined_space_active", confined, snapshot.timestamp, snapshot.zone_id, "Confined space active")
        self._register_and_append(features, "line_break_active", line_break, snapshot.timestamp, snapshot.zone_id, "Line break active")
        self._register_and_append(features, "shift_handover_active", shift_handover, snapshot.timestamp, snapshot.zone_id, "Shift handover active")
        self._register_and_append(features, "process_active", process_active, snapshot.timestamp, snapshot.zone_id, "Process active")
        
        # Isolation integrity: maintenance active but no isolation permit?
        has_maintenance = len(snapshot.active_maintenance) > 0
        has_isolation = any(p.permit_type == "ISOLATION" for p in snapshot.active_permits.values())
        incomplete_isolation = has_maintenance and not has_isolation
        
        feat_name_iso = "isolation_incomplete"
        if not registry.get_metadata(feat_name_iso):
             registry.register(FeatureMetadata(name=feat_name_iso, category=self.category, unit="bool", description="Maintenance without isolation", source_types=["permit", "maintenance"], safety_relevance="LOTO failure"))
        features.append(FeatureValue(
            name=feat_name_iso, value=1.0 if incomplete_isolation else 0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id
        ))
        
        return features

class DataQualityExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "data_quality"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        stale_count = sum(1 for r in snapshot.sensor_values.values() if r.data_quality_status == DataQualityStatus.STALE)
        
        feat_name = "stale_sensor_count"
        if not registry.get_metadata(feat_name):
            registry.register(FeatureMetadata(name=feat_name, category=self.category, unit="count", description="Number of stale sensors", source_types=["sensor"], safety_relevance="Blind spot indicator"))
            
        features.append(FeatureValue(
            name=feat_name, value=float(stale_count), timestamp=snapshot.timestamp, zone_id=snapshot.zone_id
        ))
        return features

class GeospatialExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "geospatial"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        # Extract adjacent zone risk
        # The true implementation would check the asset model for adjacent zones.
        # For this prototype, we mock this as 0.0 unless there is explicit data.
        feat_name = "adjacent_zone_risk"
        if not registry.get_metadata(feat_name):
            registry.register(FeatureMetadata(name=feat_name, category=self.category, unit="score", description="Adjacent zone hazard risk", source_types=["geospatial"], safety_relevance="Propagation"))
        features.append(FeatureValue(name=feat_name, value=0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
        
        # Exit obstructed
        feat_name_exit = "exit_obstructed"
        if not registry.get_metadata(feat_name_exit):
            registry.register(FeatureMetadata(name=feat_name_exit, category=self.category, unit="bool", description="Exit obstructed", source_types=["geospatial"], safety_relevance="Evacuation"))
        features.append(FeatureValue(name=feat_name_exit, value=0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
        
        return features

class MaintenanceExtractor(BaseExtractor):
    def __init__(self, config: Dict[str, Any], validator: AssetValidator):
        super().__init__(config, validator)
        self.category = "maintenance"
        
    def extract(self, snapshot: ZoneSnapshot, history: List[ZoneSnapshot]) -> List[FeatureValue]:
        features = []
        # Extract overdue maintenance
        feat_name = "maintenance_overdue"
        if not registry.get_metadata(feat_name):
            registry.register(FeatureMetadata(name=feat_name, category=self.category, unit="bool", description="Maintenance overdue", source_types=["maintenance"], safety_relevance="Degradation"))
        
        # We check if any active maintenance task is flagged as overdue
        overdue = any("OVERDUE" in str(m.status).upper() for m in snapshot.active_maintenance.values())
        features.append(FeatureValue(name=feat_name, value=1.0 if overdue else 0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
        
        # Maintenance active
        feat_name_maint = "maintenance_active"
        if not registry.get_metadata(feat_name_maint):
            registry.register(FeatureMetadata(name=feat_name_maint, category=self.category, unit="bool", description="Maintenance active", source_types=["maintenance"], safety_relevance="Intervention risk"))
        maint_active = len(snapshot.active_maintenance) > 0
        features.append(FeatureValue(name=feat_name_maint, value=1.0 if maint_active else 0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
                
        # ESD bypassed
        feat_name_esd = "esd_bypassed"
        if not registry.get_metadata(feat_name_esd):
            registry.register(FeatureMetadata(name=feat_name_esd, category=self.category, unit="bool", description="ESD bypassed", source_types=["maintenance"], safety_relevance="Safety barrier inactive"))
            
        esd = any("ESD" in str(m.task_id).upper() for m in snapshot.active_maintenance.values())
        features.append(FeatureValue(name=feat_name_esd, value=1.0 if esd else 0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
        
        # Shift handover active
        feat_name_shift = "shift_handover_active"
        if not registry.get_metadata(feat_name_shift):
             registry.register(FeatureMetadata(name=feat_name_shift, category=self.category, unit="bool", description="Shift handover", source_types=["worker"], safety_relevance="Transition risk"))
        features.append(FeatureValue(name=feat_name_shift, value=0.0, timestamp=snapshot.timestamp, zone_id=snapshot.zone_id))
        
        return features
