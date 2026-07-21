import uuid
import yaml
from datetime import datetime, timezone
from typing import Dict, List, Any, Set
from .models import RiskAssessment
from ..rules.models import RuleEngineResult
from ..anomaly.models import AnomalyResult
from ..baseline.models import BaselineResult
from ...features.models import FeatureVector

class TemporalRiskState:
    def __init__(self):
        self.last_hazard_scores: Dict[str, Dict[str, float]] = {} # zone_id -> {hazard: score}
        self.persistence_tracking: Dict[str, Dict[str, List[datetime]]] = {} # zone_id -> {hazard: [times]}
        self.baseline_first_detected: Dict[str, datetime] = {}
        self.compound_first_detected: Dict[str, datetime] = {}

class RiskFusionEngine:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.state = TemporalRiskState()
        
    def _get_evidence_family(self, feature_name: str) -> str:
        families = self.config.get("evidence_families", {})
        for family, keywords in families.items():
            if any(k in feature_name.lower() for k in keywords):
                return family
        return "unknown"
        
    def _calculate_severity(self, score: float) -> str:
        for sev, (low, high) in self.config["severity_bands"].items():
            if low <= score <= high:
                return sev
        return "CRITICAL" if score > 80 else "NORMAL"

    def fuse(
        self,
        feature_vector: FeatureVector,
        rule_result: RuleEngineResult,
        anomaly_result: AnomalyResult,
        baseline_results: List[BaselineResult]
    ) -> RiskAssessment:
        
        now = feature_vector.timestamp
        zone = feature_vector.zone_id
        
        # Initialize tracking
        hazard_scores = {}
        used_families = set()
        contribution_breakdown = {}
        evidence = {}
        missing = []
        data_quality = []
        triggered_rules = []
        
        # 1. Rule-based scores and floors
        for rule in rule_result.triggered_rules:
            hazard = rule.hazard_type
            score = rule.score_contribution
            
            # Floor logic
            hazard_scores[hazard] = max(hazard_scores.get(hazard, 0.0), score)
            triggered_rules.append(rule.rule_id)
            
            # Track evidence
            for feat, val in rule.evidence.items():
                evidence[feat] = val
                used_families.add(self._get_evidence_family(feat))
                
            missing.extend(rule.missing_evidence)
            
        # 2. Anomaly contribution
        if anomaly_result:
            if anomaly_result.is_anomalous and "anomaly" not in used_families:
                norm_score = anomaly_result.normalized_score
                ac_conf = self.config["anomaly_contribution"]
                
                contrib = 0.0
                if norm_score >= ac_conf["high_threshold"]:
                    contrib = ac_conf["high_contribution"]
                elif norm_score >= ac_conf["moderate_threshold"]:
                    contrib = ac_conf["moderate_contribution"]
                elif norm_score >= ac_conf["low_threshold"]:
                    contrib = ac_conf["low_contribution"]
                    
                if contrib > 0:
                    contribution_breakdown["anomaly_contribution"] = contrib
                    # Apply to generic "UNKNOWN_STATE" if no rules triggered, or to all active hazards
                    if not hazard_scores:
                        hazard_scores["UNKNOWN_STATE"] = contrib
                    else:
                        for h in hazard_scores:
                            hazard_scores[h] += contrib
                            
                    used_families.add("anomaly")
                    evidence["anomaly_score"] = norm_score
                    
        # 3. Contextual modifiers
        mod_conf = self.config["contextual_modifiers"]
        total_mod = 0.0
        
        workers = feature_vector.features.get("worker_count", None)
        if workers and workers.value > 0 and "worker" not in used_families:
            total_mod += mod_conf["worker_present"] + (workers.value * mod_conf["worker_count_multiplier"])
            evidence["worker_count"] = workers.value
            
        hot_work = feature_vector.features.get("hot_work_active", None)
        if hot_work and hot_work.value == 1.0 and "permit" not in used_families:
            total_mod += mod_conf["active_hot_work"]
            evidence["hot_work_active"] = 1.0
            
        # Cap modifiers
        total_mod = min(total_mod, mod_conf["max_total_modifier"])
        if total_mod > 0:
            contribution_breakdown["contextual_modifiers"] = total_mod
            for h in hazard_scores:
                hazard_scores[h] += total_mod
                
        # 4. Decay and Hysteresis
        if zone not in self.state.last_hazard_scores:
            self.state.last_hazard_scores[zone] = {}
        
        final_scores = {}
        for h, current_score in hazard_scores.items():
            last_score = self.state.last_hazard_scores[zone].get(h, 0.0)
            
            # Decay if current score is lower
            if current_score < last_score:
                decay = self.config["temporal"]["decay_rate_per_minute"] * (1/60) # Assume 1 tick per sec for simplicity, or we should use time diff
                # We'll just apply fixed decay for this example
                current_score = max(current_score, last_score - decay)
                
            # Cap at 100
            final_scores[h] = min(100.0, current_score)
            self.state.last_hazard_scores[zone][h] = final_scores[h]
            
        # Overall Risk Score
        overall_score = max(final_scores.values()) if final_scores else 0.0
        primary_hazard = max(final_scores.items(), key=lambda x: x[1])[0] if final_scores else "NONE"
        secondary = [h for h in final_scores.keys() if h != primary_hazard]
        
        # 5. Confidence
        conf_conf = self.config["confidence"]
        confidence = conf_conf["base"]
        for m in missing:
            confidence -= conf_conf["missing_sensor_penalty"]
        
        # Data quality checks
        stale_count = 0
        for f in feature_vector.features.values():
            if "STALE" in str(f.name): # approximation
                stale_count += 1
        confidence -= stale_count * conf_conf["stale_sensor_penalty"]
        confidence = max(conf_conf["minimum_confidence"], confidence)
        
        # 6. Lead Time Tracking
        baseline_active = len(baseline_results) > 0
        
        if baseline_active:
            if zone not in self.state.baseline_first_detected:
                self.state.baseline_first_detected[zone] = now
        
        if overall_score >= 40: # Warning or above
            if zone not in self.state.compound_first_detected:
                self.state.compound_first_detected[zone] = now
                
        base_time = self.state.baseline_first_detected.get(zone)
        comp_time = self.state.compound_first_detected.get(zone)
        
        lead_time_vs_baseline = None
        if base_time and comp_time and comp_time < base_time:
            lead_time_vs_baseline = (base_time - comp_time).total_seconds()
            
        # Generate Explanation
        severity = self._calculate_severity(overall_score)
        if overall_score > 0:
            exp = f"{primary_hazard} risk is {severity} at {overall_score:.1f}/100. "
            if triggered_rules:
                exp += f"Triggered rules: {', '.join(triggered_rules)}. "
            if baseline_active:
                exp += "Baseline alarms are active."
            else:
                exp += "The single-sensor baseline has not yet triggered."
        else:
            exp = "Normal operating conditions."

        return RiskAssessment(
            assessment_id=str(uuid.uuid4()),
            timestamp=now.isoformat(),
            zone_id=zone,
            overall_risk_score=overall_score,
            severity=severity,
            confidence=confidence,
            primary_hazard=primary_hazard,
            secondary_hazards=secondary,
            hazard_scores=final_scores,
            baseline_alarm_status=baseline_active,
            baseline_detection_time=base_time.isoformat() if base_time else None,
            compound_detection_time=comp_time.isoformat() if comp_time else None,
            lead_time_vs_baseline=lead_time_vs_baseline,
            lead_time_vs_incident=None,
            lead_time_category="KNOWN_DIVERGENCE" if lead_time_vs_baseline else "NO_LEAD",
            lead_time_basis="Calculated versus traditional threshold baseline.",
            triggered_rules=triggered_rules,
            contribution_breakdown=contribution_breakdown,
            evidence=evidence,
            missing_evidence=missing,
            data_quality_issues=data_quality,
            explanation=exp,
            model_versions={"rules": "1.0", "fusion": "1.0"},
            configuration_version="1.0"
        )
