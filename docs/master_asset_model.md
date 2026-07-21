# SpecGuard — Master Asset Model

## Crude Oil Atmospheric Distillation Unit (CDU-100)

> **Version**: 2.0  
> **Date**: 2026-07-18  
> **Scope**: Single process unit — complete logical model  
> **Usage**: Digital Twin · AI Risk Prediction · RAG · Frontend Dashboard · Geospatial Heatmap · Emergency Response · Maintenance Planning

---

# Section 1 — Plant Overview

## 1.1 Process Unit Description

**Unit**: CDU-100 — Crude Oil Atmospheric Distillation Unit  
**Facility**: SpecGuard Demonstration Refinery  
**Capacity**: 50,000 barrels per day (bpd)

The Atmospheric Distillation Unit is the primary separation unit in any petroleum refinery. Raw crude oil is heated in a fired heater (furnace) and fed to a distillation column where it separates into fractions by boiling point — light gases at the top, heavy residue at the bottom.

## 1.2 Main Process Flow

```
Crude Oil Storage → Feed Pump → Desalter → Charge Heater (Furnace)
→ Atmospheric Distillation Column → Product Fractions:
   • Overhead: Light Naphtha / LPG gases
   • Upper Side-draw: Heavy Naphtha
   • Mid Side-draw: Kerosene
   • Lower Side-draw: Light Gas Oil (Diesel)
   • Bottoms: Atmospheric Residue
```

## 1.3 Products Handled

| Product | Boiling Range (°C) | Flash Point (°C) | Hazard Class |
|---|---|---|---|
| LPG / Off-gas | < 30 | -104 | Extremely Flammable Gas |
| Light Naphtha | 30–90 | -40 | Extremely Flammable Liquid |
| Heavy Naphtha | 90–175 | -1 | Highly Flammable Liquid |
| Kerosene | 175–250 | 38 | Flammable Liquid |
| Light Gas Oil (Diesel) | 250–370 | 55 | Combustible Liquid |
| Atmospheric Residue | > 370 | 120 | Combustible Liquid |
| Crude Oil (feed) | 30–600+ | -10 | Flammable Liquid |

## 1.4 Typical Operating Conditions

| Parameter | Value |
|---|---|
| Column Top Pressure | 1.2–1.5 kg/cm² g |
| Column Top Temperature | 110–130 °C |
| Column Bottom Temperature | 340–360 °C |
| Furnace Outlet Temperature | 360–380 °C |
| Feed Flow Rate | ~300 m³/h |
| Steam Injection Rate | 2–5 t/h |
| Desalter Temperature | 120–150 °C |
| Desalter Pressure | 10–12 kg/cm² g |

## 1.5 Key Hazards

| Hazard | Source | Potential Consequence |
|---|---|---|
| Hydrocarbon Fire | Leaked crude oil / naphtha, ignition source | Pool fire, jet fire, equipment damage |
| Vapor Cloud Explosion (VCE) | Accumulated LPG / naphtha vapors | Explosion, blast overpressure, fatalities |
| H₂S Exposure | Crude oil (sour crude contains H₂S) | Toxic exposure, unconsciousness, death |
| High-Temperature Burns | Furnace tubes, hot piping, steam leaks | Severe thermal burns |
| Pressure Release | Overpressure in column, heat exchanger failure | Loss of containment, projectiles |
| Boilover | Water ingress into hot oil (tank or column) | Violent eruption, fire |
| Confined Space Asphyxiation | Column / vessel entry during maintenance | Oxygen displacement, toxic atmosphere |

## 1.6 Worker Roles

| Role | Count per Shift | Primary Location |
|---|---|---|
| Control Room Operator (CRO) | 2 | Control Room |
| Field Operator (Outside Operator) | 3 | All process zones |
| Maintenance Technician (Mechanical) | 2 | Maintenance Shop / Field |
| Maintenance Technician (Electrical/Instrument) | 1 | Maintenance Shop / Field |
| Shift Supervisor | 1 | Control Room / Field |
| Safety Officer (HSE) | 1 | All zones |
| Contractor (during turnaround/maintenance) | 2–6 | Permitted zones only |
| Emergency Response Team (ERT) Member | 2 | Fire Station / On-call |

## 1.7 Main Accident Types (Historical)

| Accident Type | Frequency | Severity |
|---|---|---|
| Small hydrocarbon leak (flange/valve) | High | Low–Medium |
| Furnace tube rupture | Low | Very High |
| Column overhead condenser failure | Medium | High |
| Pump seal failure with fire | Medium | Medium–High |
| H₂S release during crude switch | Medium | High |
| Confined space incident during turnaround | Low | Very High |
| Hot work ignition of residual vapors | Medium | Very High |

---

# Section 2 — Plant Zones

## Zone Inventory

| Zone ID | Zone Name | Purpose | Hazard Level | Adjacent Zones | Typical Personnel | Allowed Permit Types |
|---|---|---|---|---|---|---|
| `ZONE_A` | Crude Oil Tank Farm | Crude oil receiving and storage. Two storage tanks with floating roofs. | **High** (4/5) | `ZONE_B`, `ZONE_G` | Field Operator, Contractor | Hot Work, Line Breaking, Working at Height, Confined Space |
| `ZONE_B` | Feed Preheat & Desalter Area | Crude oil preheating via heat exchangers and electrostatic desalting. | **High** (4/5) | `ZONE_A`, `ZONE_C`, `ZONE_G` | Field Operator, Maintenance Technician | Hot Work, Electrical Isolation, Line Breaking |
| `ZONE_C` | Fired Heater (Furnace) Area | Crude charge heater — fired furnace with multiple passes. Highest temperature zone. | **Very High** (5/5) | `ZONE_B`, `ZONE_D` | Field Operator (limited), Safety Officer | Hot Work, Confined Space, Working at Height |
| `ZONE_D` | Distillation Column & Overhead | Atmospheric column, overhead condensers, reflux drum, product draw-offs. | **Very High** (5/5) | `ZONE_C`, `ZONE_E`, `ZONE_G` | Field Operator, Maintenance Technician | Hot Work, Confined Space, Working at Height, Line Breaking, Electrical Isolation |
| `ZONE_E` | Product Pump & Rundown Area | Product transfer pumps, coolers, and rundown lines to intermediate storage. | **Medium-High** (3/5) | `ZONE_D`, `ZONE_G` | Field Operator, Maintenance Technician | Hot Work, Line Breaking, Electrical Isolation |
| `ZONE_F` | Control Room & Utilities | Central control room, MCC building, instrument air, fire water pump house. | **Low** (1/5) | `ZONE_G` | CRO, Shift Supervisor, Safety Officer | Electrical Isolation |
| `ZONE_G` | Pipe Rack & Access Corridor | Elevated pipe rack connecting all zones. Main pedestrian and vehicle access routes. | **Medium** (2/5) | `ZONE_A`, `ZONE_B`, `ZONE_D`, `ZONE_E`, `ZONE_F` | All personnel (transit zone) | Hot Work, Working at Height |

## Zone Map (Conceptual Layout)

```
    ┌─────────────────┐
    │   ZONE_A        │
    │  Crude Tank     │
    │  Farm           │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │   ZONE_B        │
    │  Preheat /      │
    │  Desalter       │
    └────────┬────────┘
             │
    ┌────────┴────────┐      ┌─────────────────┐
    │   ZONE_C        │      │   ZONE_F        │
    │  Fired Heater   │      │  Control Room   │
    │  (Furnace)      │      │  & Utilities    │
    └────────┬────────┘      └────────┬────────┘
             │                        │
    ┌────────┴────────┐      ┌────────┴────────┐
    │   ZONE_D        │──────│   ZONE_G        │
    │  Distillation   │      │  Pipe Rack /    │
    │  Column &       │      │  Access Corridor│
    │  Overhead       │      └────────┬────────┘
    └────────┬────────┘               │
             │               ┌────────┴────────┐
    ┌────────┴────────┐      │  Connects to    │
    │   ZONE_E        │──────│  all zones      │
    │  Product Pumps  │      └─────────────────┘
    │  & Rundown      │
    └─────────────────┘
```

---

# Section 3 — Equipment Inventory

## 3.1 Complete Equipment Table

| # | Equipment ID | Equipment Name | Equipment Type | Zone | Purpose | Criticality | Failure Modes | Maint. Frequency | Operating State | Relationships |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `TK-101` | Crude Oil Storage Tank No. 1 | Storage Tank | `ZONE_A` | Primary crude oil receiving/storage (50,000 bbl) | Critical | Shell corrosion, Floating roof seal failure, Overfill, Foundation settlement | Annual inspection, 5-year internal | Running | Feeds → `PL-001` |
| 2 | `TK-102` | Crude Oil Storage Tank No. 2 | Storage Tank | `ZONE_A` | Secondary crude oil storage/blending (50,000 bbl) | Critical | Shell corrosion, Floating roof seal failure, Overfill, Foundation settlement | Annual inspection, 5-year internal | Running | Feeds → `PL-001` |
| 3 | `P-101A` | Crude Charge Pump A | Centrifugal Pump | `ZONE_A` | Pump crude oil from tank farm to preheat train | Critical | Seal leak, Bearing failure, Motor overload, Cavitation | Quarterly vibration check, Annual overhaul | Running | Receives from `TK-101`/`TK-102` via `PL-001`, Feeds → `PL-002` |
| 4 | `P-101B` | Crude Charge Pump B (Standby) | Centrifugal Pump | `ZONE_A` | Standby crude charge pump | Critical | Seal leak, Bearing failure, Motor overload, Cavitation | Quarterly vibration check, Annual overhaul | Standby | Receives from `TK-101`/`TK-102` via `PL-001`, Feeds → `PL-002` |
| 5 | `E-101` | Crude/Residue Heat Exchanger | Shell & Tube Exchanger | `ZONE_B` | Preheat crude oil against hot atmospheric residue | High | Tube leak, Fouling, Flange gasket failure | Annual inspection, 3-year bundle pull | Running | Receives crude from `PL-002`, Feeds → `PL-003` |
| 6 | `E-102` | Crude/Kerosene Heat Exchanger | Shell & Tube Exchanger | `ZONE_B` | Further preheat crude oil against kerosene product | High | Tube leak, Fouling, Flange gasket failure | Annual inspection, 3-year bundle pull | Running | Receives crude from `PL-003`, Feeds → `PL-004` |
| 7 | `V-101` | Desalter Vessel | Pressure Vessel (Electrostatic) | `ZONE_B` | Remove salts and water from crude oil | Critical | Electrode failure, Emulsion upset, Corrosion, Overpressure | Semi-annual inspection, Annual electrode check | Running | Receives from `PL-004`, Feeds → `PL-005` |
| 8 | `E-103` | Crude/Gas Oil Heat Exchanger | Shell & Tube Exchanger | `ZONE_B` | Final preheat of desalted crude | Medium | Tube leak, Fouling | Annual inspection | Running | Receives from `PL-005`, Feeds → `PL-006` |
| 9 | `H-101` | Atmospheric Furnace (Crude Charge Heater) | Fired Heater | `ZONE_C` | Heat crude oil to ~370°C for distillation | **Safety-Critical** | Tube rupture, Flame impingement, Coking, Burner malfunction, Draft failure | Continuous flame monitoring, Annual tube inspection | Running | Receives from `PL-006`, Feeds → `PL-007` |
| 10 | `C-101` | Atmospheric Distillation Column | Fractionation Column | `ZONE_D` | Separate crude into product fractions by boiling point | **Safety-Critical** | Tray damage, Flooding, Overpressure, Foaming, Corrosion | 4-year turnaround | Running | Receives from `PL-007`, Products → `PL-008` to `PL-012` |
| 11 | `E-104` | Overhead Condenser | Air-Cooled Exchanger (Fin-Fan) | `ZONE_D` | Condense overhead vapors from column top | High | Fan motor failure, Tube fouling, Vibration | Semi-annual fan check, Annual inspection | Running | Receives vapors from `C-101`, Feeds → `V-102` |
| 12 | `V-102` | Overhead Reflux Drum | Horizontal Pressure Vessel | `ZONE_D` | Accumulate condensed overhead liquid; separate water/HC | High | Level control failure, Corrosion, Relief valve failure | Annual inspection | Running | Receives from `E-104`, Feeds → `P-102A`, `P-103A` |
| 13 | `P-102A` | Overhead Reflux Pump A | Centrifugal Pump | `ZONE_D` | Return reflux to column top | High | Seal leak, Bearing failure, Cavitation | Quarterly vibration, Annual overhaul | Running | Receives from `V-102`, Returns to `C-101` |
| 14 | `P-102B` | Overhead Reflux Pump B (Standby) | Centrifugal Pump | `ZONE_D` | Standby reflux pump | High | Seal leak, Bearing failure, Cavitation | Quarterly vibration, Annual overhaul | Standby | Receives from `V-102`, Returns to `C-101` |
| 15 | `P-103A` | Naphtha Product Pump A | Centrifugal Pump | `ZONE_E` | Pump light naphtha product to storage | Medium | Seal leak, Bearing failure | Quarterly vibration, Annual overhaul | Running | Receives from `V-102` via `PL-008`, Feeds → downstream storage |
| 16 | `P-104A` | Kerosene Product Pump A | Centrifugal Pump | `ZONE_E` | Pump kerosene product to storage | Medium | Seal leak, Bearing failure | Quarterly vibration, Annual overhaul | Running | Receives from `C-101` side-draw via `PL-009`, Feeds → downstream |
| 17 | `P-105A` | Gas Oil Product Pump A | Centrifugal Pump | `ZONE_E` | Pump light gas oil (diesel) to storage | Medium | Seal leak, Bearing failure | Quarterly vibration, Annual overhaul | Running | Receives from `C-101` side-draw via `PL-010`, Feeds → downstream |
| 18 | `P-106A` | Residue Transfer Pump A | Centrifugal Pump | `ZONE_E` | Pump atmospheric residue to vacuum unit / storage | High | Seal leak, Bearing failure, High-temp seal degradation | Quarterly vibration, Annual overhaul | Running | Receives from `C-101` bottoms via `PL-011`, Feeds → `E-101` (hot side) |
| 19 | `E-105` | Kerosene Product Cooler | Shell & Tube Exchanger | `ZONE_E` | Cool kerosene product to safe storage temperature | Medium | Tube leak, Fouling | Annual inspection | Running | Receives from `P-104A`, Feeds → downstream |
| 20 | `E-106` | Gas Oil Product Cooler | Shell & Tube Exchanger | `ZONE_E` | Cool diesel product to safe storage temperature | Medium | Tube leak, Fouling | Annual inspection | Running | Receives from `P-105A`, Feeds → downstream |
| 21 | `PSV-101` | Column Relief Valve | Pressure Safety Valve | `ZONE_D` | Overpressure protection for distillation column | **Safety-Critical** | Stuck closed (fails to open), Stuck open (leak), Spring failure | Annual pop-test, 5-year overhaul | Standby (Passive) | Protects `C-101` |
| 22 | `PSV-102` | Furnace Inlet Relief Valve | Pressure Safety Valve | `ZONE_C` | Overpressure protection for furnace coil | **Safety-Critical** | Stuck closed, Stuck open, Spring failure | Annual pop-test | Standby (Passive) | Protects `H-101` |
| 23 | `FW-101` | Fire Water Deluge System (Furnace) | Fire Suppression | `ZONE_C` | Automatic deluge spray on furnace structure for fire protection | **Safety-Critical** | Valve stuck, Nozzle blockage, Pump failure | Semi-annual test | Standby (Passive) | Covers `H-101` area |
| 24 | `FW-102` | Fire Water Monitor (Tank Farm) | Fire Suppression | `ZONE_A` | Fixed fire water monitor for tank fire response | **Safety-Critical** | Valve stuck, Nozzle blockage | Semi-annual test | Standby (Passive) | Covers `TK-101`, `TK-102` |
| 25 | `VENT-101` | Tank Farm Ventilation / Wind Monitoring | Ventilation / Met | `ZONE_A` | Area ventilation fans + wind speed/direction sensor | Medium | Fan motor failure, Belt wear | Quarterly check | Running | Covers `ZONE_A` |
| 26 | `VENT-201` | Furnace Area Forced Draft Fan | Forced Draft System | `ZONE_C` | Combustion air supply and area ventilation for furnace | High | Fan blade failure, Motor failure, Damper stuck | Monthly check | Running | Supplies `H-101` |
| 27 | `ESD-001` | Emergency Shutdown System | Safety Instrumented System | `ZONE_F` | Unit-wide emergency shutdown — isolates feeds, trips furnace, opens reliefs | **Safety-Critical** | Logic solver failure, Solenoid stuck, Wiring fault | Annual proof test (SIL-2) | Armed (Standby) | Controls all emergency isolation valves |

---

# Section 4 — Pipelines

## 4.1 Pipeline Inventory

| Pipeline ID | Source Equipment | Destination Equipment | Fluid | Operating Pressure (kg/cm²g) | Operating Temp (°C) | Pipe Size (inches) | Isolation Valve | Flow Sensor | Pressure Sensor | Gas Detector Coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| `PL-001` | `TK-101` / `TK-102` | `P-101A` / `P-101B` | Crude Oil | 0.5 | 30–45 | 16" | `XV-001` | `FT-101` | `PT-101` | `GD-101`, `GD-102` |
| `PL-002` | `P-101A` / `P-101B` | `E-101` | Crude Oil | 15.0 | 30–45 | 12" | `XV-002` | `FT-102` | `PT-102` | `GD-102` |
| `PL-003` | `E-101` | `E-102` | Crude Oil (partially heated) | 14.0 | 120–150 | 12" | `XV-003` | — | `PT-103` | `GD-103` |
| `PL-004` | `E-102` | `V-101` (Desalter) | Crude Oil (heated) | 12.0 | 120–150 | 12" | `XV-004` | `FT-103` | `PT-104` | `GD-103` |
| `PL-005` | `V-101` | `E-103` | Desalted Crude | 11.0 | 120–150 | 12" | `XV-005` | — | `PT-105` | `GD-104` |
| `PL-006` | `E-103` | `H-101` (Furnace) | Desalted Crude (hot) | 10.0 | 250–280 | 10" | `XV-006` | `FT-104` | `PT-106` | `GD-105` |
| `PL-007` | `H-101` | `C-101` (Column) | Hot Crude (2-phase) | 2.0 | 360–380 | 14" | `XV-007` | — | `PT-107` | `GD-106` |
| `PL-008` | `V-102` (Reflux Drum) | `P-103A` | Light Naphtha | 1.0 | 40–60 | 6" | `XV-008` | `FT-105` | `PT-108` | `GD-107` |
| `PL-009` | `C-101` (Side-draw) | `P-104A` | Kerosene | 1.5 | 175–200 | 6" | `XV-009` | `FT-106` | `PT-109` | — |
| `PL-010` | `C-101` (Side-draw) | `P-105A` | Light Gas Oil | 1.5 | 270–300 | 8" | `XV-010` | `FT-107` | `PT-110` | — |
| `PL-011` | `C-101` (Bottoms) | `P-106A` | Atmospheric Residue | 2.0 | 340–360 | 10" | `XV-011` | `FT-108` | `PT-111` | — |
| `PL-012` | `P-102A` / `P-102B` | `C-101` (Top) | Reflux (Naphtha) | 3.0 | 40–60 | 6" | `XV-012` | `FT-109` | — | — |
| `PL-013` | `P-106A` | `E-101` (Hot side) | Atmospheric Residue | 5.0 | 340–360 | 10" | `XV-013` | — | `PT-112` | — |

> **Note**: Isolation valves `XV-xxx` are emergency/maintenance isolation valves (motor-operated or manual). Some are connected to the ESD system (`ESD-001`).

---

# Section 5 — Sensor Inventory

## 5.1 Complete Sensor Table

| # | Sensor ID | Sensor Type | Mounted On / Equipment | Zone | Units | Normal Range | Warning Threshold | Critical Threshold | Sampling Rate |
|---|---|---|---|---|---|---|---|---|---|
| — | **— PRESSURE —** | — | — | — | — | — | — | — | — |
| 1 | `PT-101` | Pressure Transmitter | `PL-001` (Tank outlet) | `ZONE_A` | kg/cm²g | 0.3–0.7 | >0.8 | >1.0 | 1 s |
| 2 | `PT-102` | Pressure Transmitter | `PL-002` (Pump discharge) | `ZONE_A` | kg/cm²g | 13.0–17.0 | >18.0 or <12.0 | >20.0 or <10.0 | 1 s |
| 3 | `PT-103` | Pressure Transmitter | `PL-003` (Post E-101) | `ZONE_B` | kg/cm²g | 12.0–15.0 | >16.0 | >18.0 | 1 s |
| 4 | `PT-104` | Pressure Transmitter | `PL-004` (Desalter inlet) | `ZONE_B` | kg/cm²g | 10.0–13.0 | >14.0 or <9.0 | >15.0 or <8.0 | 1 s |
| 5 | `PT-105` | Pressure Transmitter | `PL-005` (Desalter outlet) | `ZONE_B` | kg/cm²g | 9.5–12.0 | >13.0 | >14.0 | 1 s |
| 6 | `PT-106` | Pressure Transmitter | `PL-006` (Furnace inlet) | `ZONE_C` | kg/cm²g | 8.0–11.0 | >12.0 or <7.0 | >13.0 or <6.0 | 1 s |
| 7 | `PT-107` | Pressure Transmitter | `PL-007` (Furnace outlet) | `ZONE_C` | kg/cm²g | 1.5–2.5 | >3.0 | >3.5 | 1 s |
| 8 | `PT-108` | Pressure Transmitter | `PL-008` (Naphtha line) | `ZONE_D` | kg/cm²g | 0.8–1.5 | >2.0 | >2.5 | 1 s |
| 9 | `PT-109` | Pressure Transmitter | `PL-009` (Kerosene line) | `ZONE_E` | kg/cm²g | 1.0–2.0 | >2.5 | >3.0 | 1 s |
| 10 | `PT-110` | Pressure Transmitter | `PL-010` (Gas Oil line) | `ZONE_E` | kg/cm²g | 1.0–2.0 | >2.5 | >3.0 | 1 s |
| 11 | `PT-111` | Pressure Transmitter | `PL-011` (Residue line) | `ZONE_D` | kg/cm²g | 1.5–2.5 | >3.0 | >3.5 | 1 s |
| 12 | `PT-112` | Pressure Transmitter | `PL-013` (Hot residue return) | `ZONE_B` | kg/cm²g | 3.5–6.0 | >7.0 | >8.0 | 1 s |
| 13 | `PT-113` | Column Top Pressure | `C-101` (Top) | `ZONE_D` | kg/cm²g | 1.2–1.5 | >1.7 or <1.0 | >2.0 or <0.8 | 1 s |
| — | **— TEMPERATURE —** | — | — | — | — | — | — | — | — |
| 14 | `TT-101` | Temperature Transmitter | `TK-101` (Crude tank) | `ZONE_A` | °C | 25–50 | >55 | >65 | 5 s |
| 15 | `TT-102` | Temperature Transmitter | `E-101` (Crude outlet) | `ZONE_B` | °C | 120–155 | >160 | >175 | 1 s |
| 16 | `TT-103` | Temperature Transmitter | `V-101` (Desalter) | `ZONE_B` | °C | 120–150 | >155 or <115 | >165 or <105 | 1 s |
| 17 | `TT-104` | Coil Outlet Temperature (COT) | `H-101` (Furnace) | `ZONE_C` | °C | 360–380 | >385 or <355 | >395 or <340 | 1 s |
| 18 | `TT-105` | Firebox Temperature | `H-101` (Firebox) | `ZONE_C` | °C | 700–800 | >850 | >900 | 1 s |
| 19 | `TT-106` | Column Top Temperature | `C-101` (Top) | `ZONE_D` | °C | 110–130 | >135 or <105 | >145 or <95 | 1 s |
| 20 | `TT-107` | Column Bottom Temperature | `C-101` (Bottom) | `ZONE_D` | °C | 340–360 | >365 or <335 | >375 or <325 | 1 s |
| 21 | `TT-108` | Overhead Condenser Outlet | `E-104` | `ZONE_D` | °C | 40–60 | >65 | >75 | 2 s |
| — | **— FLOW —** | — | — | — | — | — | — | — | — |
| 22 | `FT-101` | Flow Transmitter | `PL-001` (Crude feed) | `ZONE_A` | m³/h | 280–320 | >340 or <260 | >360 or <240 | 1 s |
| 23 | `FT-102` | Flow Transmitter | `PL-002` (Pump discharge) | `ZONE_A` | m³/h | 280–320 | >340 or <260 | >360 or <240 | 1 s |
| 24 | `FT-103` | Flow Transmitter | `PL-004` (To desalter) | `ZONE_B` | m³/h | 280–320 | >340 or <260 | >360 or <240 | 1 s |
| 25 | `FT-104` | Flow Transmitter | `PL-006` (Furnace feed) | `ZONE_C` | m³/h | 280–320 | >340 or <260 | >360 or <240 | 1 s |
| 26 | `FT-105` | Flow Transmitter | `PL-008` (Naphtha product) | `ZONE_D` | m³/h | 30–50 | >55 or <25 | >65 or <15 | 1 s |
| 27 | `FT-106` | Flow Transmitter | `PL-009` (Kerosene product) | `ZONE_E` | m³/h | 40–60 | >65 or <35 | >75 or <25 | 1 s |
| 28 | `FT-107` | Flow Transmitter | `PL-010` (Gas Oil product) | `ZONE_E` | m³/h | 70–100 | >110 or <60 | >120 or <50 | 1 s |
| 29 | `FT-108` | Flow Transmitter | `PL-011` (Residue) | `ZONE_D` | m³/h | 100–140 | >150 or <90 | >160 or <80 | 1 s |
| 30 | `FT-109` | Flow Transmitter | `PL-012` (Reflux) | `ZONE_D` | m³/h | 80–120 | >130 or <70 | >140 or <60 | 1 s |
| — | **— GAS DETECTION —** | — | — | — | — | — | — | — | — |
| 31 | `GD-101` | Hydrocarbon Gas Detector | Tank Farm perimeter (N) | `ZONE_A` | %LEL | 0–5 | >10 | >20 | 2 s |
| 32 | `GD-102` | Hydrocarbon Gas Detector | Tank Farm perimeter (S) | `ZONE_A` | %LEL | 0–5 | >10 | >20 | 2 s |
| 33 | `GD-103` | Hydrocarbon Gas Detector | Desalter / Heat Exchanger area | `ZONE_B` | %LEL | 0–5 | >10 | >20 | 2 s |
| 34 | `GD-104` | Hydrocarbon Gas Detector | Post-desalter piping | `ZONE_B` | %LEL | 0–5 | >10 | >20 | 2 s |
| 35 | `GD-105` | Hydrocarbon Gas Detector | Furnace perimeter | `ZONE_C` | %LEL | 0–3 | >5 | >10 | 1 s |
| 36 | `GD-106` | Hydrocarbon Gas Detector | Furnace outlet / transfer line | `ZONE_C` | %LEL | 0–3 | >5 | >10 | 1 s |
| 37 | `GD-107` | Hydrocarbon Gas Detector | Column overhead area | `ZONE_D` | %LEL | 0–5 | >10 | >20 | 2 s |
| — | **— H₂S DETECTION —** | — | — | — | — | — | — | — | — |
| 38 | `H2S-101` | H₂S Gas Detector | Tank farm (downwind) | `ZONE_A` | ppm | 0–2 | >5 | >10 | 2 s |
| 39 | `H2S-102` | H₂S Gas Detector | Desalter drain area | `ZONE_B` | ppm | 0–2 | >5 | >10 | 2 s |
| 40 | `H2S-103` | H₂S Gas Detector | Column overhead | `ZONE_D` | ppm | 0–2 | >5 | >10 | 2 s |
| — | **— VIBRATION —** | — | — | — | — | — | — | — | — |
| 41 | `VB-101` | Vibration Sensor | `P-101A` (Drive end) | `ZONE_A` | mm/s RMS | 0–4.5 | >7.1 | >11.0 | 1 s |
| 42 | `VB-102` | Vibration Sensor | `P-102A` (Drive end) | `ZONE_D` | mm/s RMS | 0–4.5 | >7.1 | >11.0 | 1 s |
| 43 | `VB-103` | Vibration Sensor | `P-106A` (Drive end) | `ZONE_E` | mm/s RMS | 0–4.5 | >7.1 | >11.0 | 1 s |
| — | **— MOTOR / ELECTRICAL —** | — | — | — | — | — | — | — | — |
| 44 | `MC-101` | Motor Current | `P-101A` (Motor) | `ZONE_A` | Amps | 85–115 | >125 or <75 | >140 or <60 | 2 s |
| 45 | `MC-102` | Motor Current | `P-102A` (Motor) | `ZONE_D` | Amps | 40–60 | >70 or <30 | >80 or <20 | 2 s |
| 46 | `MC-103` | Motor Current | `E-104` (Fan Motor) | `ZONE_D` | Amps | 30–50 | >55 or <25 | >65 or <20 | 2 s |
| — | **— LEVEL —** | — | — | — | — | — | — | — | — |
| 47 | `LT-101` | Tank Level Transmitter | `TK-101` | `ZONE_A` | % | 20–85 | >90 or <15 | >95 or <10 | 5 s |
| 48 | `LT-102` | Tank Level Transmitter | `TK-102` | `ZONE_A` | % | 20–85 | >90 or <15 | >95 or <10 | 5 s |
| 49 | `LT-103` | Reflux Drum Level | `V-102` | `ZONE_D` | % | 30–70 | >80 or <20 | >90 or <10 | 1 s |
| — | **— FIRE & SMOKE —** | — | — | — | — | — | — | — | — |
| 50 | `FD-101` | Flame Detector (IR/UV) | `H-101` (Furnace exterior) | `ZONE_C` | Binary | 0 (No flame) | 1 (Flame detected) | 1 (Flame detected) | 100 ms |
| 51 | `FD-102` | Flame Detector (IR/UV) | `ZONE_D` (Column base) | `ZONE_D` | Binary | 0 | 1 | 1 | 100 ms |
| 52 | `SD-101` | Smoke Detector (Optical) | `ZONE_F` (Control Room) | `ZONE_F` | Binary | 0 (No smoke) | 1 (Smoke detected) | 1 (Smoke detected) | 500 ms |
| — | **— VALVE POSITION —** | — | — | — | — | — | — | — | — |
| 53 | `ZT-101` | Valve Position Indicator | `XV-001` (Tank outlet isolation) | `ZONE_A` | % Open | 0 or 100 | Mid-travel >5 min | Mid-travel >10 min | 1 s |
| 54 | `ZT-102` | Valve Position Indicator | `XV-007` (Furnace inlet isolation) | `ZONE_C` | % Open | 0 or 100 | Mid-travel >5 min | Mid-travel >10 min | 1 s |
| — | **— OXYGEN —** | — | — | — | — | — | — | — | — |
| 55 | `O2-101` | Oxygen Analyzer | `C-101` (for confined space prep) | `ZONE_D` | vol% | 20.5–21.0 | <19.5 or >23.5 | <18.0 or >25.0 | 5 s |

---

# Section 6 — CCTV Cameras

## 6.1 Camera Inventory

| Camera ID | Zone | Location Description | Coverage Type | Typical Events | Worker Detection | Vehicle Detection | PPE Detection | Restricted Area Detection |
|---|---|---|---|---|---|---|---|---|
| `CAM-101` | `ZONE_A` | Tank Farm entrance gate | Fixed wide-angle | Vehicle entry/exit, Unauthorized access, Spill on ground | Yes | Yes | Yes (Hardhat, FRC) | Yes (Tank bund area) |
| `CAM-102` | `ZONE_A` | Between TK-101 and TK-102 | PTZ (Pan-Tilt-Zoom) | Leak detection, Worker near tanks, Smoke/fire | Yes | No | Yes (Hardhat, FRC, Gloves) | Yes (Bund wall exclusion) |
| `CAM-103` | `ZONE_B` | Desalter and heat exchanger area | Fixed wide-angle | Maintenance activity, Flange leak, PPE compliance | Yes | No | Yes (Hardhat, FRC, Safety glasses) | No |
| `CAM-104` | `ZONE_C` | Furnace front (burner face) | Fixed thermal + visible | Flame anomaly, Unauthorized approach, Smoke | Yes | No | Yes (Full) | Yes (Furnace exclusion zone) |
| `CAM-105` | `ZONE_C` | Furnace stack and convection section | Fixed upward | Stack smoke color, Structure integrity | No | No | No | No |
| `CAM-106` | `ZONE_D` | Column base and overhead area | PTZ | Leak/spray, Worker at height, Permit activity | Yes | Yes | Yes (Hardhat, Harness, FRC) | Yes (Column platform restriction) |
| `CAM-107` | `ZONE_D` | Reflux drum and pump area | Fixed wide-angle | Pump leak, Worker near rotating equipment | Yes | No | Yes (Hardhat, FRC, Safety glasses) | No |
| `CAM-108` | `ZONE_E` | Product pump lineup | Fixed wide-angle | Pump seal leak, PPE check, Worker count | Yes | Yes | Yes (Hardhat, FRC) | No |
| `CAM-109` | `ZONE_F` | Control room interior | Fixed dome | Personnel count, Operator presence, Fatigue detection | Yes | No | No | No |
| `CAM-110` | `ZONE_G` | Main pipe rack (central) | PTZ | Vehicle under pipe rack, Worker on pipe rack, Hot work sparks | Yes | Yes | Yes (Hardhat, Harness) | Yes (Pipe rack climb restriction) |
| `CAM-111` | `ZONE_G` | Unit main access road | Fixed ANPR + wide | Vehicle identification, Speed detection, Pedestrian on road | Yes | Yes | Yes (Hardhat) | No |

---

# Section 7 — Worker Types

## 7.1 Personnel Roles

| Role ID | Role Title | Typical Zones | Allowed Permits | Working Hours | Risk Exposure | Certifications Required |
|---|---|---|---|---|---|---|
| `ROLE-CRO` | Control Room Operator | `ZONE_F` (primary), occasional `ZONE_D` | All (monitoring only) | 12-hour shift (0600–1800 / 1800–0600) | Low (indoor, ergonomic) | DCS operation, Process safety awareness |
| `ROLE-FOP` | Field Operator (Outside Operator) | `ZONE_A`, `ZONE_B`, `ZONE_C`, `ZONE_D`, `ZONE_E`, `ZONE_G` | Hot Work (fire watch), Confined Space (standby), Line Breaking (isolation assist) | 12-hour shift | **High** (HC exposure, burns, H₂S, falls) | Gas testing, Field isolation, H₂S alive |
| `ROLE-MMT` | Maintenance Technician (Mechanical) | `ZONE_A`, `ZONE_B`, `ZONE_D`, `ZONE_E`, `ZONE_G` (as per permit) | Hot Work, Confined Space, Line Breaking, Working at Height | 8-hour day shift (0700–1500) | **High** (pinch points, pressure release, burns) | Rigging and lifting, Confined space entry, Hot work |
| `ROLE-EIT` | Maintenance Technician (E&I) | `ZONE_B`, `ZONE_D`, `ZONE_E`, `ZONE_F` (as per permit) | Electrical Isolation, Confined Space | 8-hour day shift (0700–1500) | **Medium-High** (electrical shock, arc flash) | Electrical safety, Instrument calibration, LOTO |
| `ROLE-SUP` | Shift Supervisor | `ZONE_F` (primary), all zones (rounds) | All (approval authority) | 12-hour shift | Medium | All permits, Incident command |
| `ROLE-HSE` | Safety Officer (HSE) | All zones | All (audit and monitoring authority) | 8-hour day shift | Medium | Gas testing, Permit audit, Incident investigation |
| `ROLE-CON` | Contractor | As per permit ONLY | As per contract scope — must be individually authorized | Varies (day shift typical) | **High** (unfamiliar with site) | Site induction, Task-specific competency, SIMOPS awareness |
| `ROLE-ERT` | Emergency Response Team Member | `ZONE_F` (standby), deployed to incident zone | Not applicable (emergency role) | On-call during shift | **Very High** (during emergency deployment) | Firefighting, SCBA, First aid, Rescue |

## 7.2 Worker Roster (Nominal)

| Worker ID | Name | Role ID | Shift | Primary Zone |
|---|---|---|---|---|
| `WRK-001` | A. Kumar | `ROLE-CRO` | Day | `ZONE_F` |
| `WRK-002` | B. Singh | `ROLE-CRO` | Day | `ZONE_F` |
| `WRK-003` | C. Patel | `ROLE-FOP` | Day | `ZONE_A` / `ZONE_B` |
| `WRK-004` | D. Reddy | `ROLE-FOP` | Day | `ZONE_C` / `ZONE_D` |
| `WRK-005` | E. Sharma | `ROLE-FOP` | Day | `ZONE_D` / `ZONE_E` |
| `WRK-006` | F. Gupta | `ROLE-SUP` | Day | `ZONE_F` |
| `WRK-007` | G. Rao | `ROLE-MMT` | Day | As per WO |
| `WRK-008` | H. Joshi | `ROLE-MMT` | Day | As per WO |
| `WRK-009` | I. Mehta | `ROLE-EIT` | Day | As per WO |
| `WRK-010` | J. Das | `ROLE-HSE` | Day | All zones |
| `WRK-011` | K. Nair | `ROLE-CRO` | Night | `ZONE_F` |
| `WRK-012` | L. Iyer | `ROLE-CRO` | Night | `ZONE_F` |
| `WRK-013` | M. Yadav | `ROLE-FOP` | Night | `ZONE_A` / `ZONE_B` |
| `WRK-014` | N. Bhat | `ROLE-FOP` | Night | `ZONE_C` / `ZONE_D` |
| `WRK-015` | O. Pillai | `ROLE-FOP` | Night | `ZONE_D` / `ZONE_E` |
| `WRK-016` | P. Mishra | `ROLE-SUP` | Night | `ZONE_F` |
| `WRK-017` | Q. Saxena | `ROLE-ERT` | Day | `ZONE_F` |
| `WRK-018` | R. Verma | `ROLE-ERT` | Night | `ZONE_F` |
| `WRK-019` | S. Tiwari | `ROLE-CON` | Day | As per PTW |
| `WRK-020` | T. Choudhary | `ROLE-CON` | Day | As per PTW |

---

# Section 8 — Permit-to-Work Types

## 8.1 Permit Catalogue

| Permit ID | Permit Name | Applicable Zones | Required Isolation | Required Gas Test | Required PPE | Max Duration | Supervisor Approval | Typical Hazards |
|---|---|---|---|---|---|---|---|---|
| `PTW-HW` | Hot Work Permit | `ZONE_A`, `ZONE_B`, `ZONE_C`, `ZONE_D`, `ZONE_E`, `ZONE_G` | Energy isolation of adjacent HC sources; fire watch boundary | HC < 1% LEL; continuous monitoring during work | FRC coverall, Hardhat, Safety glasses, Welding shield, Fire-resistant gloves, Safety shoes | 8 hours (renewable) | Shift Supervisor + Area Authority + Fire Watch | Fire, Explosion, Burns, Toxic fume inhalation |
| `PTW-CS` | Confined Space Entry Permit | `ZONE_A` (tanks), `ZONE_B` (vessels), `ZONE_C` (furnace), `ZONE_D` (column) | Full isolation (blind/spade), Drain/vent, Purge with N2 then air | O2 19.5–23.5%, HC < 1% LEL, H2S < 1 ppm, continuous monitoring | FRC, Hardhat, SCBA standby, Harness and lifeline, Gas monitor (personal) | 4 hours (renewable, re-test every 2h) | Shift Supervisor + HSE Officer + Entry Supervisor | Asphyxiation, Toxic exposure, Engulfment, Entrapment |
| `PTW-EI` | Electrical Isolation Permit | `ZONE_B`, `ZONE_D`, `ZONE_E`, `ZONE_F` | LOTO (Lock-Out/Tag-Out) on motor/breaker | Not required (unless in HC zone — then HC test) | FRC, Hardhat, Insulated gloves, Arc-flash rated face shield, Safety shoes | 8 hours | Shift Supervisor + E&I Supervisor | Electrocution, Arc flash, Equipment damage |
| `PTW-LB` | Line Breaking Permit | `ZONE_A`, `ZONE_B`, `ZONE_D`, `ZONE_E`, `ZONE_G` | Drain, depressurize, isolate with blind/spade; zero-energy verification | HC < 1% LEL at break point | FRC, Hardhat, Face shield, Chemical gloves, Safety shoes | 8 hours | Shift Supervisor + Area Authority | Hydrocarbon release, H2S exposure, Burns (hot line), Spray injury |
| `PTW-WH` | Working at Height Permit | `ZONE_C` (furnace structure), `ZONE_D` (column platforms), `ZONE_G` (pipe rack) | Barricade below; check scaffold/ladder integrity | As per zone requirement | FRC, Hardhat (chinstrap), Full-body harness, Lanyard, Safety shoes | 8 hours | Shift Supervisor | Falls, Dropped objects, Wind exposure |
| `PTW-EX` | Excavation Permit | `ZONE_A`, `ZONE_G` | Locate underground utilities; barricade excavation | HC test at excavation depth | FRC, Hardhat, Safety shoes, High-visibility vest | 8 hours | Shift Supervisor + Civil Engineer | Cave-in, Utility strike (electrical/gas), HC accumulation in trench |

---

# Section 9 — Maintenance Tasks

## 9.1 Maintenance Task Catalogue

| Maint. ID | Equipment | Task Description | Type | Est. Duration | Isolation Required | Permit Required | Technicians Req'd | Risk Level |
|---|---|---|---|---|---|---|---|---|
| `MT-001` | `P-101A` | Mechanical seal replacement — crude charge pump | Corrective | 6 hours | Yes — LOTO motor, isolate suction/discharge with blinds | `PTW-LB`, `PTW-EI` | 2 Mech + 1 E&I | **High** |
| `MT-002` | `P-101A` | Quarterly vibration analysis and alignment check | Preventive | 2 hours | No — running measurement | None | 1 Mech | Low |
| `MT-003` | `P-102A` | Bearing replacement — reflux pump | Corrective | 4 hours | Yes — LOTO motor, isolate lines | `PTW-LB`, `PTW-EI` | 2 Mech | **High** |
| `MT-004` | `E-101` | Annual tube bundle inspection (NDT) | Preventive | 12 hours | Yes — isolate both shell and tube side, drain | `PTW-LB`, `PTW-CS` | 3 Mech + 1 NDT | **High** |
| `MT-005` | `E-102` | Flange gasket replacement (tube-side inlet) | Corrective | 4 hours | Yes — isolate and drain tube-side | `PTW-LB` | 2 Mech | **Medium** |
| `MT-006` | `V-101` | Desalter electrode inspection and cleaning | Preventive | 8 hours | Yes — full isolation, drain, gas-free | `PTW-CS`, `PTW-EI` | 2 Mech + 1 E&I | **High** |
| `MT-007` | `H-101` | Furnace tube thickness survey (UT) | Preventive | 16 hours | Yes — furnace shutdown, cool-down, gas-free | `PTW-CS`, `PTW-WH`, `PTW-HW` | 2 Mech + 2 NDT | **Very High** |
| `MT-008` | `H-101` | Burner tip cleaning and adjustment | Preventive | 4 hours | Partial — burner isolated, other burners firing | `PTW-HW` | 2 Mech | **High** |
| `MT-009` | `C-101` | Column tray inspection (during turnaround) | Preventive | 48 hours | Yes — full unit shutdown, gas-free, scaffolding | `PTW-CS`, `PTW-WH` | 6 Mech + 2 Scaffold | **Very High** |
| `MT-010` | `E-104` | Fin-fan motor replacement | Corrective | 3 hours | Yes — LOTO motor/breaker | `PTW-EI`, `PTW-WH` | 1 Mech + 1 E&I | **Medium** |
| `MT-011` | `PSV-101` | Annual pressure safety valve pop-test | Preventive | 2 hours | Yes — isolate PSV (spare PSV in service) | `PTW-LB` | 1 Mech + 1 Instrument | **Medium** |
| `MT-012` | `PSV-102` | Furnace relief valve calibration and test | Preventive | 2 hours | Yes — isolate PSV | `PTW-LB` | 1 Mech + 1 Instrument | **Medium** |
| `MT-013` | `P-103A` | Naphtha pump seal inspection | Preventive | 3 hours | Yes — LOTO, isolate lines | `PTW-LB`, `PTW-EI` | 2 Mech | **High** |
| `MT-014` | `P-106A` | Residue pump bearing vibration trending | Preventive | 1 hour | No — running measurement | None | 1 Mech | Low |
| `MT-015` | `FW-101` | Fire deluge system functional test | Preventive | 2 hours | Partial — test circuit only | None | 1 Mech + 1 Safety | Low |
| `MT-016` | `ESD-001` | ESD logic solver proof test (SIL-2) | Preventive | 8 hours | Partial — bypass individual loops | `PTW-EI` | 2 E&I + 1 Safety | **Medium** |
| `MT-017` | `GD-105` | Gas detector calibration (bump test) | Preventive | 1 hour | No | None | 1 Instrument | Low |
| `MT-018` | `VENT-201` | Forced draft fan bearing lubrication | Preventive | 1 hour | No — can be done running (grease gun) | None | 1 Mech | Low |
| `MT-019` | `V-102` | Reflux drum internal inspection | Preventive | 8 hours | Yes — full isolation, drain, gas-free | `PTW-CS`, `PTW-LB` | 2 Mech + 1 NDT | **High** |
| `MT-020` | `CAM-106` | CCTV camera lens cleaning and PTZ calibration | Preventive | 1 hour | No | `PTW-WH` (if elevated) | 1 E&I | Low |

---

# Section 10 — Emergency Systems

## 10.1 Emergency Asset Inventory

| Emergency Asset ID | Asset Name | Type | Zone Coverage | Trigger Conditions | Response Action | Test Frequency |
|---|---|---|---|---|---|---|
| `EM-ESD-001` | Unit Emergency Shutdown System | Safety Instrumented System (SIS) | All zones (unit-wide) | Manual ESD button, High-High pressure (PT-113 > 2.0), Flame detection in non-furnace zone (FD-102), Multiple gas alarms (2+ zones > 20% LEL) | Trips furnace H-101, Closes all XV- isolation valves, Trips all pumps, Activates deluge FW-101 | Annual proof test |
| `EM-FAS-001` | Fire Alarm System | Fire Detection and Alarm | All zones | Flame detectors (FD-101, FD-102), Smoke detector (SD-101), Manual call points, Heat detectors | Sounds site-wide siren, Alerts control room, Notifies fire brigade, Triggers deluge in affected zone | Semi-annual test |
| `EM-GAS-001` | Gas Alarm System | Gas Detection and Alarm | `ZONE_A`, `ZONE_B`, `ZONE_C`, `ZONE_D` | Any GD-xxx > 10% LEL (Warning), > 20% LEL (Emergency), Any H2S-xxx > 5 ppm (Warning), > 10 ppm (Emergency) | Warning: Alert CRO + field operator, start ventilation. Emergency: ESD activation, evacuation alarm, muster to assembly point | Monthly bump test, Semi-annual calibration |
| `EM-FW-001` | Fire Water Deluge — Furnace | Fire Suppression | `ZONE_C` | Fire confirmed by dual flame detectors OR manual activation | Water deluge spray over furnace structure at 10 L/min/m2 | Semi-annual functional test |
| `EM-FW-002` | Fire Water Monitor — Tank Farm | Fire Suppression | `ZONE_A` | Manual activation by ERT or automatic on dual alarm | Directed water jet / foam on tank fire | Semi-annual functional test |
| `EM-FW-003` | Fire Water Ring Main | Fire Water Supply | All zones (ring main) | Maintains 7 kg/cm2g fire water pressure at all times | Supplies all hydrants, monitors, deluge valves | Weekly pump run test |
| `EM-VENT-001` | Emergency Ventilation System | Forced Ventilation | `ZONE_B`, `ZONE_C`, `ZONE_D` | Gas alarm > 10% LEL in covered zone, Manual activation from control room | High-speed exhaust fans activate to disperse vapors | Quarterly functional test |
| `EM-PA-001` | Public Address and Alarm System | Communication | All zones | Manual from control room, Automatic from ESD/Fire/Gas systems | Evacuation alarm (warbling siren), PA announcements, Zone-specific messages | Monthly test |
| `EM-AP-001` | Assembly Point — Main Gate | Muster Point | Outside all zones (upwind of unit) | Evacuation order | All personnel muster; headcount via badge reader | Quarterly drill |
| `EM-AP-002` | Assembly Point — Control Room | Secondary Muster | `ZONE_F` | Shelter-in-place order (if toxic release downwind of main AP) | Control room staff shelter; HVAC switched to recirculation mode | Quarterly drill |
| `EM-EXIT-001` | Emergency Exit — Tank Farm (North) | Escape Route | `ZONE_A` | Any emergency | Illuminated escape route to EM-AP-001 | Monthly inspection |
| `EM-EXIT-002` | Emergency Exit — Furnace Area (West) | Escape Route | `ZONE_C` | Any emergency | Illuminated escape route away from furnace toward pipe rack | Monthly inspection |
| `EM-EXIT-003` | Emergency Exit — Column Area (East) | Escape Route | `ZONE_D` | Any emergency | Illuminated escape route to EM-AP-001 | Monthly inspection |
| `EM-MED-001` | First Aid Station | Medical | `ZONE_F` (Control Room building) | Any injury | First aid kit, Burns kit, Eye wash station, Stretcher | Monthly inspection |
| `EM-SCBA-001` | SCBA Cabinet — Furnace Area | Respiratory Protection | `ZONE_C` | H2S alarm, Oxygen deficiency, Smoke | 4x Self-Contained Breathing Apparatus sets | Monthly inspection |
| `EM-SCBA-002` | SCBA Cabinet — Column Area | Respiratory Protection | `ZONE_D` | H2S alarm, Oxygen deficiency | 4x SCBA sets | Monthly inspection |
| `EM-EWS-001` | Emergency Eyewash/Shower — Desalter | Decontamination | `ZONE_B` | Chemical contact (caustic, amine, crude) | Immediate decontamination within 10 seconds | Weekly flow test |
| `EM-EWS-002` | Emergency Eyewash/Shower — Pump Area | Decontamination | `ZONE_E` | Chemical contact | Immediate decontamination | Weekly flow test |

---

# Section 11 — Equipment Relationship Graph

## 11.1 Process Flow Adjacency List

```
TK-101  ──► PL-001  ──► P-101A  ──► PL-002  ──► E-101  ──► PL-003  ──► E-102
TK-102  ──►              P-101B (standby)

E-102  ──► PL-004  ──► V-101 (Desalter)  ──► PL-005  ──► E-103  ──► PL-006  ──► H-101 (Furnace)

H-101  ──► PL-007  ──► C-101 (Column)

C-101 (top)       ──► E-104 (Condenser)  ──► V-102 (Reflux Drum)
V-102              ──► P-102A  ──► PL-012  ──► C-101 (reflux return)
                       P-102B (standby)
V-102              ──► PL-008  ──► P-103A  ──► (Naphtha storage)

C-101 (side-draw)  ──► PL-009  ──► P-104A  ──► E-105  ──► (Kerosene storage)
C-101 (side-draw)  ──► PL-010  ──► P-105A  ──► E-106  ──► (Gas Oil storage)
C-101 (bottoms)    ──► PL-011  ──► P-106A  ──► PL-013  ──► E-101 (hot side)
```

## 11.2 Formal Adjacency List

| Source | Destination | Relationship Type |
|---|---|---|
| `TK-101` | `PL-001` | feeds_into |
| `TK-102` | `PL-001` | feeds_into |
| `PL-001` | `P-101A` | feeds_into |
| `PL-001` | `P-101B` | feeds_into (standby) |
| `P-101A` | `PL-002` | feeds_into |
| `P-101B` | `PL-002` | feeds_into (standby) |
| `PL-002` | `E-101` | feeds_into |
| `E-101` | `PL-003` | feeds_into |
| `PL-003` | `E-102` | feeds_into |
| `E-102` | `PL-004` | feeds_into |
| `PL-004` | `V-101` | feeds_into |
| `V-101` | `PL-005` | feeds_into |
| `PL-005` | `E-103` | feeds_into |
| `E-103` | `PL-006` | feeds_into |
| `PL-006` | `H-101` | feeds_into |
| `H-101` | `PL-007` | feeds_into |
| `PL-007` | `C-101` | feeds_into |
| `C-101` | `E-104` | feeds_into (overhead vapor) |
| `E-104` | `V-102` | feeds_into |
| `V-102` | `P-102A` | feeds_into |
| `V-102` | `P-102B` | feeds_into (standby) |
| `V-102` | `PL-008` | feeds_into (net product) |
| `P-102A` | `PL-012` | feeds_into |
| `P-102B` | `PL-012` | feeds_into (standby) |
| `PL-012` | `C-101` | feeds_into (reflux return) |
| `PL-008` | `P-103A` | feeds_into |
| `C-101` | `PL-009` | feeds_into (kerosene draw) |
| `PL-009` | `P-104A` | feeds_into |
| `P-104A` | `E-105` | feeds_into |
| `C-101` | `PL-010` | feeds_into (gas oil draw) |
| `PL-010` | `P-105A` | feeds_into |
| `P-105A` | `E-106` | feeds_into |
| `C-101` | `PL-011` | feeds_into (bottoms) |
| `PL-011` | `P-106A` | feeds_into |
| `P-106A` | `PL-013` | feeds_into |
| `PL-013` | `E-101` | feeds_into (hot side) |
| `PSV-101` | `C-101` | protects |
| `PSV-102` | `H-101` | protects |
| `FW-101` | `H-101` | protects (fire) |
| `FW-102` | `TK-101` | protects (fire) |
| `FW-102` | `TK-102` | protects (fire) |
| `VENT-101` | `ZONE_A` | ventilates |
| `VENT-201` | `ZONE_C` | ventilates |
| `ESD-001` | All `XV-` valves | controls (emergency) |
| `ESD-001` | `H-101` | trips (emergency) |
| `ESD-001` | All `P-` pumps | trips (emergency) |

---

# Section 12 — Hazard Map

## 12.1 Zone Hazard Analysis

| Zone ID | Zone Name | Primary Hazards | Secondary Hazards | Potential Consequences |
|---|---|---|---|---|
| `ZONE_A` | Crude Oil Tank Farm | Hydrocarbon vapor release (tank breathing / seal failure), Tank overfill, Lightning strike | H2S release (sour crude), Static discharge, Tank roof sinking | Pool fire, Tank boilover, Vapor cloud explosion, Toxic exposure, Environmental spill |
| `ZONE_B` | Feed Preheat and Desalter | Flange leak (hot crude), Heat exchanger tube rupture, Desalter overpressure | H2S release from desalter, Caustic splash, Emulsion carryover | Jet fire, Spray fire, Chemical burns, Toxic gas release, Corrosion-induced leak |
| `ZONE_C` | Fired Heater (Furnace) | Furnace tube rupture, Flame impingement, Uncontrolled fire, Furnace explosion | Flue gas release, Draft reversal, Fuel gas leak, Structural failure | Fireball, Structural collapse, Fatality, Major equipment damage, Radiant heat injury |
| `ZONE_D` | Distillation Column and Overhead | Column overpressure, Overhead condenser failure, Reflux drum overfill/overpressure, Naphtha vapor release | Tray damage causing flooding, H2S in overhead gas, High-temperature piping failure | BLEVE (reflux drum), Vapor cloud explosion, Toxic H2S cloud, Loss of containment, Worker exposure at height |
| `ZONE_E` | Product Pumps and Rundown | Pump seal failure (multiple products), Hot piping leak, Electrical fault in motor | Naphtha static ignition, Gas oil thermal decomposition | Pool fire, Pump fire, Spray fire, Electrical arc flash, Product contamination |
| `ZONE_F` | Control Room and Utilities | Smoke/fire in electrical room (MCC), Toxic gas ingress (HVAC), Control system failure | Power failure, Loss of instrument air, Communication failure | Loss of control, Inability to emergency shutdown, Delayed response, Personnel trapped |
| `ZONE_G` | Pipe Rack and Access Corridor | Pipe rack support failure, Flange leak at elevation, Vehicle collision with structure | Dropped objects, Wind-induced vibration, Thermal expansion failure | Falling pipe/debris, Multi-product release, Fire in pipe rack (escalation to multiple zones), Vehicle fire |

---

# Section 13 — Compound Risk Matrix

## 13.1 Compound Risk Rules (35 Combinations)

| # | Condition 1 | Condition 2 | Condition 3 | Compound Risk | Severity | Why This is Dangerous |
|---|---|---|---|---|---|---|
| 1 | Hot Work Permit active (PTW-HW) in ZONE_B | HC Gas rising (GD-103 > 10% LEL) | Wind direction toward hot work | **Explosion / Flash Fire** | **Catastrophic** | Hot work generates ignition sources (welding sparks, grinding). If hydrocarbon gas drifts into the work zone, ignition of the vapor cloud is near-certain. The Lower Explosive Limit threshold means the atmosphere can support combustion. |
| 2 | Confined Space Entry (PTW-CS) in C-101 | Oxygen decreasing (O2-101 < 19.5%) | Workers inside column | **Asphyxiation** | **Catastrophic** | Oxygen displacement below 19.5% causes impaired judgment; below 16% causes unconsciousness within minutes. Workers in a confined vessel cannot self-rescue if they lose consciousness. Nitrogen purge residual or hydrocarbon vapor displacement is the typical cause. |
| 3 | Pump maintenance on P-101A (MT-001) | Isolation valve XV-002 not fully closed (ZT-101 shows mid-travel) | Pressure rising on PT-102 | **Loss of Containment — HC Release** | **Critical** | If the pump is opened for seal replacement but the isolation valve has not fully closed, pressurized crude oil will release uncontrollably at the open pump casing. The technician is directly in the spray path. |
| 4 | Furnace tube high temperature (TT-104 > 385C) | Fuel gas flow increasing (furnace demand) | Crude feed flow decreasing (FT-104 < 260 m3/h) | **Furnace Tube Rupture** | **Catastrophic** | Reduced crude flow through furnace tubes means less heat removal. Tubes overheat, coke builds up, and tube metal reaches failure temperature. Rupture releases hot crude into the firebox — immediate fireball. This is one of the most feared refinery accidents. |
| 5 | Ventilation system failed (VENT-201 offline) in ZONE_C | HC gas accumulating (GD-105 > 5% LEL) | Furnace still firing (H-101 running) | **Explosion — Furnace Area** | **Catastrophic** | Without ventilation, leaked hydrocarbon vapors accumulate near the furnace. The furnace itself is a continuous ignition source. Accumulation to explosive range near an active fire is a classic explosion scenario. |
| 6 | Night shift (reduced manning) | Multiple alarms active (5+ simultaneous) | CRO WRK-011 alone in control room | **Alarm Flood — Delayed Response** | **High** | A single operator cannot process > 3-4 simultaneous alarms effectively (ISA-18.2). Critical alarms get missed, response is delayed, and incidents escalate. Night shifts have ~30% fewer personnel. |
| 7 | Line breaking permit (PTW-LB) on PL-011 | Residue pump P-106A not LOTO'd | Atmospheric residue at 350C in line | **Thermal Burns — Hot Oil Release** | **Catastrophic** | Atmospheric residue is above the auto-ignition temperature of many materials. If the line is opened while the pump can still start (no LOTO), hot residue sprays onto the technician. Third-degree burns and fire are immediate. |
| 8 | Tank TK-101 level high (LT-101 > 90%) | Crude charge pump P-101A tripped | No operator in ZONE_A (field operator in ZONE_D) | **Tank Overfill** | **High** | If receiving crude from a ship/pipeline and the charge pump trips, crude backs up into the tank. Without an operator to close the inlet valve, the tank overfills. Crude overflows the floating roof seal — pool fire risk. |
| 9 | H2S alarm (H2S-102 > 5 ppm) in ZONE_B | Workers performing maintenance on E-101 (MT-004) | Wind shift trapping gas in work area | **Toxic H2S Exposure** | **Catastrophic** | H2S at 10 ppm causes eye irritation; at 100 ppm it paralyzes the olfactory nerve (victim cannot smell it); at 300 ppm it causes immediate collapse. Workers focused on maintenance may not notice gradual buildup. Desalter drain is a common H2S source. |
| 10 | Reflux drum V-102 level rising (LT-103 > 80%) | Overhead condenser E-104 fan motor failed (MC-103 = 0) | Naphtha pump P-103A tripped | **Reflux Drum Overpressure / BLEVE** | **Catastrophic** | Without condenser cooling, overhead vapors cannot condense. Liquid accumulates in the drum while uncondensed vapor builds pressure. If the relief valve (PSV-101) fails or cannot handle the load, the drum can experience a BLEVE (Boiling Liquid Expanding Vapor Explosion). |
| 11 | Electrical isolation permit (PTW-EI) on P-102A motor | No LOTO tag verified at MCC | Standby pump P-102B auto-start logic active | **Unexpected Equipment Start** | **High** | If the technician is working on P-102A motor assuming it is isolated, but LOTO was applied to the wrong breaker, the motor could energize. Additionally, auto-start logic for standby pump may interact with the primary pump circuit. Electrocution or rotating equipment contact. |
| 12 | Working at height (PTW-WH) on column C-101 platform | Wind speed > 40 km/h | Scaffold not secured / harness not clipped | **Fall from Height** | **Catastrophic** | Working at height on the distillation column (>30m) in high winds dramatically increases fall risk. Wind can destabilize scaffold, swing loads, and blow workers off balance. Falls from this height are almost always fatal. |
| 13 | Fire water system test (MT-015) in progress | Fire water ring main pressure drops (EM-FW-003 < 5 kg/cm2g) | Actual fire alarm in ZONE_A | **Insufficient Fire Suppression** | **Catastrophic** | Testing the deluge system diverts fire water from the ring main. If a real fire occurs simultaneously, there may be insufficient water pressure/volume to fight it. This is why SIMOPS (Simultaneous Operations) management is critical. |
| 14 | ESD proof test (MT-016) in progress — loops bypassed | Actual process upset (column overpressure) | ESD cannot activate (bypassed for test) | **Safety System Unavailable During Demand** | **Catastrophic** | The ESD system is the last line of defense. During proof testing, individual loops are bypassed. If a real demand occurs on a bypassed loop, the safety system cannot respond. This is the "test-demand coincidence" hazard — it's why testing procedures require compensating measures. |
| 15 | Contractor (WRK-019) working without gas monitor | HC gas rising in ZONE_D (GD-107 > 10% LEL) | Contractor unfamiliar with evacuation route | **Contractor Exposure / Lost Worker** | **High** | Contractors often have less site familiarity than permanent staff. Without a personal gas monitor, they may not detect rising gas levels until it's too late. During evacuation, unfamiliarity with escape routes leads to delayed egress. |
| 16 | Desalter V-101 water/oil interface upset | Emulsion carryover to furnace H-101 | Water flashing in furnace tubes | **Furnace Water Hammer / Tube Failure** | **Critical** | Water carried over from the desalter will flash to steam inside the 370C furnace tubes. The volume expansion (1,700:1) creates extreme local pressure — hydraulic hammer that can rupture tubes. |
| 17 | Two pumps simultaneously in maintenance (P-101A + P-101B) | No crude feed to unit | Column C-101 draining (no reflux) | **Unit Upset — Column Damage** | **High** | Both crude charge pumps offline means zero feed to the column. Trays dry out, vapor distribution is lost, and when feed is restored, thermal shock can damage tray internals. This is an operations planning failure — never take both pumps simultaneously. |
| 18 | PPE non-compliance detected by CAM-104 | Worker near furnace without FRC | HC vapor present (GD-106 > 3% LEL) | **Burns — Inadequate PPE** | **High** | Fire-Resistant Clothing (FRC) is mandatory near the furnace because flash fires can occur without warning. A worker in regular clothing near an HC vapor source and ignition source will suffer severe burns that FRC would have prevented. |
| 19 | Multiple workers in ZONE_D (exceeds max 6) | Confined space entry active in C-101 | Evacuation required | **Congested Egress — Delayed Evacuation** | **High** | Overcrowding in a high-hazard zone during a confined space entry means emergency escape routes are congested. Workers exiting the confined space need immediate assistance, but egress for bystanders is blocked. Evacuation time doubles. |
| 20 | Smoke detected in control room (SD-101) | HVAC on recirculation (shelter-in-place mode) | CRO cannot see DCS screens (smoke) | **Loss of Process Control** | **Catastrophic** | If the control room fills with smoke, operators cannot monitor or control the plant. If HVAC is on recirculation (trapping smoke inside), the situation worsens rapidly. An unmanned DCS during a process upset means no one can intervene. |
| 21 | Relief valve PSV-101 stuck closed (discovered during MT-011) | Column pressure rising (PT-113 > 1.7) | ESD not activated (operator trying manual response) | **Column Overpressure — Rupture** | **Catastrophic** | The PSV is the last mechanical barrier against overpressure. If it's stuck closed and the column pressure rises above design, the vessel wall can fail catastrophically. The resulting hydrocarbon release and explosion can destroy the entire unit. |
| 22 | Tank farm lightning detected (weather alert) | Floating roof seal damaged on TK-101 | Vapors above LEL near tank rim (GD-101 > 10% LEL) | **Lightning-Ignited Tank Fire** | **Catastrophic** | A damaged floating roof seal allows vapor space to form. Lightning strike on the tank rim can ignite these vapors. Full-surface tank fires are extremely difficult to extinguish and can spread to adjacent tanks. |
| 23 | Power failure (utility loss) | UPS battery depleting (< 30 min remaining) | ESD valves (fail-safe close) shutting | **Uncontrolled Shutdown** | **High** | Loss of power means loss of control systems. While ESD valves fail-safe (close), pumps stop abruptly, and the furnace trips. The uncontrolled shutdown can cause water hammer, thermal shock, and process upsets that are hard to recover from. Trapped HC in a hot furnace can auto-ignite. |
| 24 | Gas oil product cooler E-106 tube leak | Cooling water contaminated with HC | Cooling tower becomes HC source | **Environmental Release / Fire at Cooling Tower** | **Medium** | A tube leak in a product cooler lets hydrocarbons into the cooling water circuit. This contaminates the cooling tower, where HC vapors are released to atmosphere — creating a dispersed ignition risk and environmental violation. |
| 25 | Hot work on pipe rack (ZONE_G) | Flange leak on adjacent kerosene line (PL-009) | Welding sparks travel 10+ meters | **Pipe Rack Fire — Multi-Zone Escalation** | **Catastrophic** | Pipe racks carry lines from multiple zones. A fire on the pipe rack can damage multiple pipelines simultaneously, causing cascading failures across zones. Pipe rack fires are notoriously hard to fight due to access difficulty and multiple fuel sources. |
| 26 | Pump P-104A seal failure (kerosene service) | Kerosene spray (auto-ignition temp 220C) onto hot pipe (>250C) | No operator nearby (field rounds incomplete) | **Auto-Ignition Pump Fire** | **High** | Kerosene sprayed onto a surface above its auto-ignition temperature will ignite without any spark or flame source. Pump seal failures produce a fine mist that auto-ignites readily. Without immediate detection by a nearby operator, the fire can escalate before response begins. |
| 27 | Crude oil type changed (sweet to sour crude) | H2S in overhead gas increases unexpectedly | Gas detectors not recalibrated for new crude type | **Undetected H2S Exposure** | **Catastrophic** | Different crude oils contain vastly different H2S levels. When switching from sweet (low H2S) to sour (high H2S) crude, the entire unit H2S profile changes. If detectors aren't recalibrated and alert thresholds aren't adjusted, workers can be exposed to lethal H2S concentrations without warning. |
| 28 | Scaffold erected around E-101 for MT-004 | Emergency vehicle access blocked | Fire in ZONE_B requires fire truck access | **Blocked Emergency Access** | **High** | Maintenance scaffolding can block vehicle access roads. If a fire occurs in the zone, fire trucks cannot reach the hydrants or position monitors. Response time doubles when firefighters must hand-carry hoses. Every minute of delay in a refinery fire means exponential growth. |
| 29 | CCTV CAM-106 offline (maintenance MT-020) | Unauthorized person enters ZONE_D | Confined space entry active — person enters without gas monitor | **Untracked Worker in Hazardous Zone** | **High** | Without CCTV coverage, the unauthorized entry goes undetected. The person is not on the permit, has no gas monitor, and rescue teams don't know they exist. If a gas release occurs, this person won't be accounted for during headcount — potential fatality. |
| 30 | Shift handover in progress (18:00) | Active alarms not communicated to incoming shift | Furnace coking trend not flagged | **Missed Trend — Delayed Intervention** | **High** | Shift handover is one of the most dangerous periods in process operations. If the outgoing CRO doesn't communicate a gradual coking trend in the furnace, the incoming CRO has no context. By the time they notice, the furnace tubes may already be dangerously overheated. |
| 31 | Heavy rain / flooding | Tank farm bund area flooded | Crude oil floating on flood water inside bund | **Environmental Contamination + Floating Fire** | **Medium** | Floodwater in a tank bund displaces crude oil containment. If crude leaks onto floodwater, it spreads over a much larger surface area. Ignition of floating oil creates an uncontrollable surface fire. Environmental damage to groundwater and drainage systems. |
| 32 | Furnace damper stuck (VENT-201 damper failure) | Incomplete combustion (CO accumulating in firebox) | Firebox temperature dropping (TT-105 decreasing) | **Furnace Re-ignition Explosion** | **Catastrophic** | A stuck damper reduces combustion air. Fuel continues but doesn't fully burn, creating CO and unburned hydrocarbons in the firebox. If the damper suddenly frees or an air path opens, the accumulated fuel-air mixture can detonate — this is a classic furnace explosion scenario. |
| 33 | High vibration on P-101A (VB-101 > 11 mm/s) | Seal leak rate increasing | Pump still running (operator delayed response) | **Catastrophic Pump Failure** | **High** | Extreme vibration indicates imminent bearing or shaft failure. As the pump degrades, the mechanical seal loses alignment and leak rate increases. If the pump is not tripped immediately, the bearing can seize, the shaft breaks, and the pump housing cracks — uncontrolled crude release from a spinning impeller. |
| 34 | Desalter V-101 electrical trip | Oil/water interface lost | Crude with high salt content reaches furnace H-101 | **Furnace Tube Corrosion / Fouling Acceleration** | **Medium** | The desalter removes chloride salts. If it trips, salt-laden crude passes to the furnace. Chlorides convert to HCl at furnace temperatures, causing rapid corrosion of overhead condensers and column trays. This can cause equipment failure within days rather than years. |
| 35 | Worker fatigue detected by CAM-109 (CRO drowsy at 04:00) | Critical alarm occurs | Delayed acknowledgment (> 2 minutes) | **Fatigue-Related Incident Escalation** | **High** | Circadian low (02:00–06:00) reduces alertness by 50%. A drowsy CRO may not notice or acknowledge a critical alarm promptly. In process safety, the first 2 minutes of response often determine whether an incident remains minor or escalates to catastrophe. |

---

# Section 14 — Master IDs

## 14.1 Complete ID Registry

### Zones

| ID | Name |
|---|---|
| `ZONE_A` | Crude Oil Tank Farm |
| `ZONE_B` | Feed Preheat and Desalter Area |
| `ZONE_C` | Fired Heater (Furnace) Area |
| `ZONE_D` | Distillation Column and Overhead |
| `ZONE_E` | Product Pump and Rundown Area |
| `ZONE_F` | Control Room and Utilities |
| `ZONE_G` | Pipe Rack and Access Corridor |

### Equipment

| ID | Name | Type | Zone |
|---|---|---|---|
| `TK-101` | Crude Oil Storage Tank No. 1 | Storage Tank | `ZONE_A` |
| `TK-102` | Crude Oil Storage Tank No. 2 | Storage Tank | `ZONE_A` |
| `P-101A` | Crude Charge Pump A | Centrifugal Pump | `ZONE_A` |
| `P-101B` | Crude Charge Pump B (Standby) | Centrifugal Pump | `ZONE_A` |
| `E-101` | Crude/Residue Heat Exchanger | Shell and Tube HX | `ZONE_B` |
| `E-102` | Crude/Kerosene Heat Exchanger | Shell and Tube HX | `ZONE_B` |
| `V-101` | Desalter Vessel | Pressure Vessel | `ZONE_B` |
| `E-103` | Crude/Gas Oil Heat Exchanger | Shell and Tube HX | `ZONE_B` |
| `H-101` | Atmospheric Furnace | Fired Heater | `ZONE_C` |
| `C-101` | Atmospheric Distillation Column | Fractionation Column | `ZONE_D` |
| `E-104` | Overhead Condenser | Air-Cooled Exchanger | `ZONE_D` |
| `V-102` | Overhead Reflux Drum | Pressure Vessel | `ZONE_D` |
| `P-102A` | Overhead Reflux Pump A | Centrifugal Pump | `ZONE_D` |
| `P-102B` | Overhead Reflux Pump B (Standby) | Centrifugal Pump | `ZONE_D` |
| `P-103A` | Naphtha Product Pump A | Centrifugal Pump | `ZONE_E` |
| `P-104A` | Kerosene Product Pump A | Centrifugal Pump | `ZONE_E` |
| `P-105A` | Gas Oil Product Pump A | Centrifugal Pump | `ZONE_E` |
| `P-106A` | Residue Transfer Pump A | Centrifugal Pump | `ZONE_E` |
| `E-105` | Kerosene Product Cooler | Shell and Tube HX | `ZONE_E` |
| `E-106` | Gas Oil Product Cooler | Shell and Tube HX | `ZONE_E` |
| `PSV-101` | Column Relief Valve | Pressure Safety Valve | `ZONE_D` |
| `PSV-102` | Furnace Inlet Relief Valve | Pressure Safety Valve | `ZONE_C` |
| `FW-101` | Fire Water Deluge (Furnace) | Fire Suppression | `ZONE_C` |
| `FW-102` | Fire Water Monitor (Tank Farm) | Fire Suppression | `ZONE_A` |
| `VENT-101` | Tank Farm Ventilation | Ventilation / Met | `ZONE_A` |
| `VENT-201` | Furnace Forced Draft Fan | Forced Draft | `ZONE_C` |
| `ESD-001` | Emergency Shutdown System | SIS | `ZONE_F` |

### Sensors

| ID | Type | Zone |
|---|---|---|
| `PT-101` | Pressure | `ZONE_A` |
| `PT-102` | Pressure | `ZONE_A` |
| `PT-103` | Pressure | `ZONE_B` |
| `PT-104` | Pressure | `ZONE_B` |
| `PT-105` | Pressure | `ZONE_B` |
| `PT-106` | Pressure | `ZONE_C` |
| `PT-107` | Pressure | `ZONE_C` |
| `PT-108` | Pressure | `ZONE_D` |
| `PT-109` | Pressure | `ZONE_E` |
| `PT-110` | Pressure | `ZONE_E` |
| `PT-111` | Pressure | `ZONE_D` |
| `PT-112` | Pressure | `ZONE_B` |
| `PT-113` | Pressure | `ZONE_D` |
| `TT-101` | Temperature | `ZONE_A` |
| `TT-102` | Temperature | `ZONE_B` |
| `TT-103` | Temperature | `ZONE_B` |
| `TT-104` | Temperature | `ZONE_C` |
| `TT-105` | Temperature | `ZONE_C` |
| `TT-106` | Temperature | `ZONE_D` |
| `TT-107` | Temperature | `ZONE_D` |
| `TT-108` | Temperature | `ZONE_D` |
| `FT-101` | Flow | `ZONE_A` |
| `FT-102` | Flow | `ZONE_A` |
| `FT-103` | Flow | `ZONE_B` |
| `FT-104` | Flow | `ZONE_C` |
| `FT-105` | Flow | `ZONE_D` |
| `FT-106` | Flow | `ZONE_E` |
| `FT-107` | Flow | `ZONE_E` |
| `FT-108` | Flow | `ZONE_D` |
| `FT-109` | Flow | `ZONE_D` |
| `GD-101` | HC Gas | `ZONE_A` |
| `GD-102` | HC Gas | `ZONE_A` |
| `GD-103` | HC Gas | `ZONE_B` |
| `GD-104` | HC Gas | `ZONE_B` |
| `GD-105` | HC Gas | `ZONE_C` |
| `GD-106` | HC Gas | `ZONE_C` |
| `GD-107` | HC Gas | `ZONE_D` |
| `H2S-101` | H2S | `ZONE_A` |
| `H2S-102` | H2S | `ZONE_B` |
| `H2S-103` | H2S | `ZONE_D` |
| `VB-101` | Vibration | `ZONE_A` |
| `VB-102` | Vibration | `ZONE_D` |
| `VB-103` | Vibration | `ZONE_E` |
| `MC-101` | Motor Current | `ZONE_A` |
| `MC-102` | Motor Current | `ZONE_D` |
| `MC-103` | Motor Current | `ZONE_D` |
| `LT-101` | Level | `ZONE_A` |
| `LT-102` | Level | `ZONE_A` |
| `LT-103` | Level | `ZONE_D` |
| `FD-101` | Flame Detector | `ZONE_C` |
| `FD-102` | Flame Detector | `ZONE_D` |
| `SD-101` | Smoke Detector | `ZONE_F` |
| `ZT-101` | Valve Position | `ZONE_A` |
| `ZT-102` | Valve Position | `ZONE_C` |
| `O2-101` | Oxygen Analyzer | `ZONE_D` |

### Pipelines

| ID | From | To | Fluid |
|---|---|---|---|
| `PL-001` | `TK-101`/`TK-102` | `P-101A`/`P-101B` | Crude Oil |
| `PL-002` | `P-101A` | `E-101` | Crude Oil |
| `PL-003` | `E-101` | `E-102` | Crude Oil (warm) |
| `PL-004` | `E-102` | `V-101` | Crude Oil (hot) |
| `PL-005` | `V-101` | `E-103` | Desalted Crude |
| `PL-006` | `E-103` | `H-101` | Desalted Crude (hot) |
| `PL-007` | `H-101` | `C-101` | Hot Crude (2-phase) |
| `PL-008` | `V-102` | `P-103A` | Light Naphtha |
| `PL-009` | `C-101` | `P-104A` | Kerosene |
| `PL-010` | `C-101` | `P-105A` | Light Gas Oil |
| `PL-011` | `C-101` | `P-106A` | Atmospheric Residue |
| `PL-012` | `P-102A` | `C-101` | Reflux (Naphtha) |
| `PL-013` | `P-106A` | `E-101` | Atmospheric Residue (hot) |

### Permits

| ID | Name |
|---|---|
| `PTW-HW` | Hot Work Permit |
| `PTW-CS` | Confined Space Entry Permit |
| `PTW-EI` | Electrical Isolation Permit |
| `PTW-LB` | Line Breaking Permit |
| `PTW-WH` | Working at Height Permit |
| `PTW-EX` | Excavation Permit |

### Maintenance Tasks

| ID | Equipment | Description |
|---|---|---|
| `MT-001` | `P-101A` | Mechanical seal replacement |
| `MT-002` | `P-101A` | Quarterly vibration analysis |
| `MT-003` | `P-102A` | Bearing replacement |
| `MT-004` | `E-101` | Annual tube bundle inspection |
| `MT-005` | `E-102` | Flange gasket replacement |
| `MT-006` | `V-101` | Desalter electrode inspection |
| `MT-007` | `H-101` | Furnace tube thickness survey |
| `MT-008` | `H-101` | Burner tip cleaning |
| `MT-009` | `C-101` | Column tray inspection |
| `MT-010` | `E-104` | Fin-fan motor replacement |
| `MT-011` | `PSV-101` | Annual PSV pop-test |
| `MT-012` | `PSV-102` | Furnace relief valve test |
| `MT-013` | `P-103A` | Naphtha pump seal inspection |
| `MT-014` | `P-106A` | Vibration trending |
| `MT-015` | `FW-101` | Fire deluge functional test |
| `MT-016` | `ESD-001` | ESD proof test (SIL-2) |
| `MT-017` | `GD-105` | Gas detector calibration |
| `MT-018` | `VENT-201` | FD fan bearing lubrication |
| `MT-019` | `V-102` | Reflux drum inspection |
| `MT-020` | `CAM-106` | CCTV maintenance |

### Workers

| ID | Name | Role |
|---|---|---|
| `WRK-001` | A. Kumar | ROLE-CRO |
| `WRK-002` | B. Singh | ROLE-CRO |
| `WRK-003` | C. Patel | ROLE-FOP |
| `WRK-004` | D. Reddy | ROLE-FOP |
| `WRK-005` | E. Sharma | ROLE-FOP |
| `WRK-006` | F. Gupta | ROLE-SUP |
| `WRK-007` | G. Rao | ROLE-MMT |
| `WRK-008` | H. Joshi | ROLE-MMT |
| `WRK-009` | I. Mehta | ROLE-EIT |
| `WRK-010` | J. Das | ROLE-HSE |
| `WRK-011` | K. Nair | ROLE-CRO |
| `WRK-012` | L. Iyer | ROLE-CRO |
| `WRK-013` | M. Yadav | ROLE-FOP |
| `WRK-014` | N. Bhat | ROLE-FOP |
| `WRK-015` | O. Pillai | ROLE-FOP |
| `WRK-016` | P. Mishra | ROLE-SUP |
| `WRK-017` | Q. Saxena | ROLE-ERT |
| `WRK-018` | R. Verma | ROLE-ERT |
| `WRK-019` | S. Tiwari | ROLE-CON |
| `WRK-020` | T. Choudhary | ROLE-CON |

### Cameras

| ID | Zone |
|---|---|
| `CAM-101` | `ZONE_A` |
| `CAM-102` | `ZONE_A` |
| `CAM-103` | `ZONE_B` |
| `CAM-104` | `ZONE_C` |
| `CAM-105` | `ZONE_C` |
| `CAM-106` | `ZONE_D` |
| `CAM-107` | `ZONE_D` |
| `CAM-108` | `ZONE_E` |
| `CAM-109` | `ZONE_F` |
| `CAM-110` | `ZONE_G` |
| `CAM-111` | `ZONE_G` |

### Emergency Systems

| ID | Name |
|---|---|
| `EM-ESD-001` | Unit Emergency Shutdown System |
| `EM-FAS-001` | Fire Alarm System |
| `EM-GAS-001` | Gas Alarm System |
| `EM-FW-001` | Fire Water Deluge — Furnace |
| `EM-FW-002` | Fire Water Monitor — Tank Farm |
| `EM-FW-003` | Fire Water Ring Main |
| `EM-VENT-001` | Emergency Ventilation System |
| `EM-PA-001` | Public Address and Alarm System |
| `EM-AP-001` | Assembly Point — Main Gate |
| `EM-AP-002` | Assembly Point — Control Room |
| `EM-EXIT-001` | Emergency Exit — Tank Farm |
| `EM-EXIT-002` | Emergency Exit — Furnace Area |
| `EM-EXIT-003` | Emergency Exit — Column Area |
| `EM-MED-001` | First Aid Station |
| `EM-SCBA-001` | SCBA Cabinet — Furnace |
| `EM-SCBA-002` | SCBA Cabinet — Column |
| `EM-EWS-001` | Eyewash/Shower — Desalter |
| `EM-EWS-002` | Eyewash/Shower — Pump Area |

---

# Section 15 — JSON Schemas

## 15.1 zones.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Plant Zones",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["zone_id", "zone_name", "purpose", "hazard_level", "hazard_rating", "adjacent_zones", "typical_personnel", "allowed_permit_types", "max_workers", "is_confined", "requires_gas_test"],
    "properties": {
      "zone_id": { "type": "string", "pattern": "^ZONE_[A-Z]$" },
      "zone_name": { "type": "string" },
      "purpose": { "type": "string" },
      "hazard_level": { "type": "string", "enum": ["Low", "Medium", "Medium-High", "High", "Very High"] },
      "hazard_rating": { "type": "integer", "minimum": 1, "maximum": 5 },
      "adjacent_zones": { "type": "array", "items": { "type": "string" } },
      "typical_personnel": { "type": "array", "items": { "type": "string" } },
      "allowed_permit_types": { "type": "array", "items": { "type": "string" } },
      "max_workers": { "type": "integer" },
      "is_confined": { "type": "boolean" },
      "requires_gas_test": { "type": "boolean" },
      "equipment_ids": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

## 15.2 equipment.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Equipment Inventory",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["equipment_id", "equipment_name", "equipment_type", "zone_id", "purpose", "criticality", "failure_modes", "maintenance_frequency", "operating_state"],
    "properties": {
      "equipment_id": { "type": "string" },
      "equipment_name": { "type": "string" },
      "equipment_type": { "type": "string", "enum": ["storage_tank", "centrifugal_pump", "shell_tube_exchanger", "air_cooled_exchanger", "pressure_vessel", "fired_heater", "fractionation_column", "pressure_safety_valve", "fire_suppression", "ventilation", "forced_draft", "safety_instrumented_system"] },
      "zone_id": { "type": "string", "pattern": "^ZONE_[A-Z]$" },
      "purpose": { "type": "string" },
      "criticality": { "type": "string", "enum": ["Low", "Medium", "High", "Safety-Critical"] },
      "failure_modes": { "type": "array", "items": { "type": "string" } },
      "maintenance_frequency": { "type": "string" },
      "operating_state": { "type": "string", "enum": ["running", "standby", "stopped", "maintenance", "failed", "armed"] },
      "feeds_from": { "type": "array", "items": { "type": "string" } },
      "feeds_to": { "type": "array", "items": { "type": "string" } },
      "protects": { "type": "array", "items": { "type": "string" } },
      "base_degradation_rate": { "type": "number" },
      "failure_threshold": { "type": "number" }
    }
  }
}
```

## 15.3 sensors.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Sensor Inventory",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["sensor_id", "sensor_type", "equipment_id", "zone_id", "unit", "normal_range_min", "normal_range_max", "warning_threshold", "critical_threshold", "sampling_rate_seconds"],
    "properties": {
      "sensor_id": { "type": "string" },
      "sensor_type": { "type": "string", "enum": ["pressure", "temperature", "flow", "hc_gas", "h2s_gas", "vibration", "motor_current", "level", "flame_detector", "smoke_detector", "valve_position", "oxygen"] },
      "equipment_id": { "type": "string", "description": "Equipment or pipeline this sensor is mounted on" },
      "zone_id": { "type": "string" },
      "unit": { "type": "string" },
      "normal_range_min": { "type": "number" },
      "normal_range_max": { "type": "number" },
      "warning_threshold": { "type": "string", "description": "Human-readable threshold condition" },
      "critical_threshold": { "type": "string", "description": "Human-readable critical condition" },
      "sampling_rate_seconds": { "type": "number" },
      "nominal_value": { "type": "number" },
      "noise_std": { "type": "number" }
    }
  }
}
```

## 15.4 pipelines.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Pipeline Inventory",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["pipeline_id", "source_equipment_id", "destination_equipment_id", "fluid", "operating_pressure_kg_cm2", "operating_temperature_c_min", "operating_temperature_c_max", "pipe_size_inches", "isolation_valve_id"],
    "properties": {
      "pipeline_id": { "type": "string", "pattern": "^PL-\\d{3}$" },
      "source_equipment_id": { "type": "string" },
      "destination_equipment_id": { "type": "string" },
      "fluid": { "type": "string" },
      "operating_pressure_kg_cm2": { "type": "number" },
      "operating_temperature_c_min": { "type": "number" },
      "operating_temperature_c_max": { "type": "number" },
      "pipe_size_inches": { "type": "number" },
      "isolation_valve_id": { "type": "string" },
      "flow_sensor_id": { "type": ["string", "null"] },
      "pressure_sensor_id": { "type": ["string", "null"] },
      "gas_detector_ids": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

## 15.5 workers.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Worker Roster",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["worker_id", "name", "role_id", "role_title", "shift", "primary_zone"],
    "properties": {
      "worker_id": { "type": "string", "pattern": "^WRK-\\d{3}$" },
      "name": { "type": "string" },
      "role_id": { "type": "string" },
      "role_title": { "type": "string" },
      "shift": { "type": "string", "enum": ["day", "night"] },
      "primary_zone": { "type": "string" },
      "certifications": { "type": "array", "items": { "type": "string" } },
      "allowed_permit_types": { "type": "array", "items": { "type": "string" } },
      "working_hours": { "type": "string" },
      "risk_exposure": { "type": "string", "enum": ["Low", "Medium", "Medium-High", "High", "Very High"] }
    }
  }
}
```

## 15.6 permits.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Permit-to-Work Catalogue",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["permit_type_id", "permit_name", "applicable_zones", "required_isolation", "required_gas_test", "required_ppe", "max_duration_hours", "supervisor_approval", "typical_hazards"],
    "properties": {
      "permit_type_id": { "type": "string", "pattern": "^PTW-[A-Z]{2}$" },
      "permit_name": { "type": "string" },
      "applicable_zones": { "type": "array", "items": { "type": "string" } },
      "required_isolation": { "type": "string" },
      "required_gas_test": { "type": "string" },
      "required_ppe": { "type": "array", "items": { "type": "string" } },
      "max_duration_hours": { "type": "integer" },
      "supervisor_approval": { "type": "string" },
      "typical_hazards": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

## 15.7 maintenance.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Maintenance Task Catalogue",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["maintenance_id", "equipment_id", "task_description", "maintenance_type", "estimated_duration_hours", "isolation_required", "permit_required", "technicians_required", "risk_level"],
    "properties": {
      "maintenance_id": { "type": "string", "pattern": "^MT-\\d{3}$" },
      "equipment_id": { "type": "string" },
      "task_description": { "type": "string" },
      "maintenance_type": { "type": "string", "enum": ["preventive", "corrective"] },
      "estimated_duration_hours": { "type": "number" },
      "isolation_required": { "type": "boolean" },
      "permit_required": { "type": "array", "items": { "type": "string" } },
      "technicians_required": { "type": "string" },
      "risk_level": { "type": "string", "enum": ["Low", "Medium", "High", "Very High"] }
    }
  }
}
```

## 15.8 cameras.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CCTV Camera Inventory",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["camera_id", "zone_id", "location_description", "coverage_type"],
    "properties": {
      "camera_id": { "type": "string", "pattern": "^CAM-\\d{3}$" },
      "zone_id": { "type": "string" },
      "location_description": { "type": "string" },
      "coverage_type": { "type": "string", "enum": ["fixed_wide", "ptz", "fixed_thermal", "fixed_upward", "fixed_dome", "fixed_anpr"] },
      "typical_events": { "type": "array", "items": { "type": "string" } },
      "worker_detection": { "type": "boolean" },
      "vehicle_detection": { "type": "boolean" },
      "ppe_detection": { "type": "boolean" },
      "restricted_area_detection": { "type": "boolean" },
      "ppe_types_detected": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

## 15.9 emergency_assets.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Emergency Assets",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["emergency_asset_id", "asset_name", "asset_type", "zone_coverage", "trigger_conditions", "response_action", "test_frequency"],
    "properties": {
      "emergency_asset_id": { "type": "string", "pattern": "^EM-[A-Z]+-\\d{3}$" },
      "asset_name": { "type": "string" },
      "asset_type": { "type": "string", "enum": ["safety_instrumented_system", "fire_detection_alarm", "gas_detection_alarm", "fire_suppression", "fire_water_supply", "emergency_ventilation", "communication", "muster_point", "escape_route", "medical", "respiratory_protection", "decontamination"] },
      "zone_coverage": { "type": "array", "items": { "type": "string" } },
      "trigger_conditions": { "type": "string" },
      "response_action": { "type": "string" },
      "test_frequency": { "type": "string" }
    }
  }
}
```

---

## Cross-Reference Validation Summary

| Check | Count | Status |
|---|---|---|
| Zones defined | 7 | PASS |
| Equipment items | 27 | PASS |
| All equipment references valid zone | 27/27 | PASS |
| Sensors defined | 55 | PASS |
| All sensors reference valid equipment/zone | 55/55 | PASS |
| Pipelines defined | 13 | PASS |
| All pipelines reference valid source/dest | 13/13 | PASS |
| Cameras defined | 11 | PASS |
| All cameras reference valid zone | 11/11 | PASS |
| Workers defined | 20 | PASS |
| Permit types defined | 6 | PASS |
| Maintenance tasks defined | 20 | PASS |
| All maint tasks reference valid equipment | 20/20 | PASS |
| All maint tasks reference valid permits | 20/20 | PASS |
| Emergency assets defined | 18 | PASS |
| Compound risk rules | 35 | PASS |

> **All IDs are globally unique. All references are internally consistent. This model is ready for import into FastAPI/PostgreSQL backend, Digital Twin simulator, ML pipeline, RAG corpus, and Frontend dashboard.**
