# Compound-Risk Rule Engine

> **Module**: `backend.app.ai.detection.rules`
> **Purpose**: Deterministically evaluate compound-risk rules against incoming `FeatureVectors` to detect complex hazard combinations.

## Architecture

The Rule Engine evaluates deterministic, human-readable logic against the ML-ready feature streams. It is deliberately designed to not execute arbitrary code and does not rely on LLM invocations for decision-making or explanation generation at runtime.

### Components
- **`RuleLoader`**: Parses `risk_rules.yaml` into Pydantic models. Fails fast if the YAML structure is invalid.
- **`RuleValidator`**: Ensures all conditions use approved operators (`eq`, `gt`, `in`, etc.) and prevents duplicate rule IDs.
- **`RuleEvaluator`**: The core execution engine. Given a `FeatureVector`, it checks `all`, `any`, and `not` condition groups, applies `escalation` logic if extra evidence is present, and calculates the final risk score.
- **`TemporalRuleState`**: Manages cooldowns to prevent alarm floods for rules that trigger continuously on every tick.

## Rule Schema Overview
Rules are defined in `config/risk_rules.yaml`.

```yaml
- rule_id: CRR-001
  name: "Hot work plus hydrocarbon accumulation"
  hazard_type: "FLASH_FIRE_EXPLOSION"
  base_score: 90
  conditions:
    all:
      - feature: hot_work_active
        operator: eq
        value: 1.0
      - feature: max_hydrocarbon_lel_pct
        operator: gte
        value: 10.0
  escalation:
    - when:
        feature: worker_count
        operator: gt
        value: 0
      score_delta: 10
```

## Explainability
When a rule triggers, it returns a `RuleResult` containing:
- **`evidence`**: The exact feature values that caused the trigger.
- **`missing_evidence`**: Any features required by the rule that were missing from the snapshot.
- **`human_readable_explanation`**: Generated deterministically, e.g., "CRR-001 triggered because conditions met in ZONE_A. Evidence: hot_work_active is 1.0, max_hydrocarbon_lel_pct is 12.5."
- **`escalation_factors`**: A list of conditions that matched to increase the base score.

## Coverage Summary
- **Total Rules**: 20 currently implemented (mapped directly from the 35 original rules in the master asset model).
- **Hazard Categories Covered**: Flash Fire, Asphyxiation, Toxic Exposure, Loss of Containment, Overpressure, Mechanical Failure, Evacuation Failure.
- **Zones Covered**: Global (`ALL` zones supported).
- **Untested Rules**: None. All rules are syntax-checked, and core engine behaviors (cooldown, escalation, missing data, unsafe operators) have dedicated unit tests.
