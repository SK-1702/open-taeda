"""
Open TAEDA — Structured Result Data & Forensics Register
=========================================================

Extracted from the 26-Document Forensic RTL-to-GDS Research Analysis Suite.
Feeds structured result data (PDK Defects, Interventions, Engineering Incidents,
Comparability Matrix, and Four Truths) directly into Open TAEDA database tables
and website requirement panels.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "ota.db"

# ----------------------------------------------------------------------
# 1. PDK DEFECT & LIMITATION REGISTER (Doc 09, 23)
# ----------------------------------------------------------------------
PDK_DEFECTS = [
    {
        "id": "PDK-DEF-001",
        "technology_id": "icsprout55",
        "pdk_name": "ICsprout55",
        "stage": "Routing / Antenna",
        "limitation": "ANTENNADIFFAREA property missing from standard cell LEF pin definitions",
        "severity": "High",
        "root_cause": "Incomplete PDK LEF antenna property extraction during library characterization",
        "workaround": "Manual diode cell insertion script patch and custom SDC antenna rules",
        "correction": "Updated LEF pin property definitions with ANTENNADIFFAREA bounds",
        "impact": "Causes OpenROAD detailed routing failure (GRT-0244) during antenna repair stage"
    },
    {
        "id": "PDK-DEF-002",
        "technology_id": "icsprout55",
        "pdk_name": "ICsprout55",
        "stage": "Extraction / STA",
        "limitation": "RC parasitic model table bounds limited to M1-M4 layers",
        "severity": "Medium",
        "root_cause": "Open-source Liberty/LEF tech file collateral lacking M5 metal RC corner models",
        "workaround": "Restricted upper routing layers to M4 in flow configuration (RT_MAX_LAYER=M4)",
        "correction": "Documented technology model constraint in manifest provenance",
        "impact": "Interconnect delay overestimation for top-level long nets"
    },
    {
        "id": "PDK-DEF-003",
        "technology_id": "sky130",
        "pdk_name": "Sky130",
        "stage": "Physical Verification (DRC)",
        "limitation": "Magic DRC false positive on tap cell placement boundary rules",
        "severity": "Low",
        "root_cause": "Magic tech file boundary rule checking strictness on non-grid aligned tap cells",
        "workaround": "KLayout DRC cross-verification firewall and TAP_DECAP_INSERTION override",
        "correction": "Updated magic DRC tech file rule deck for sky130fd_sc_hd",
        "impact": "Spurious DRC warnings during signoff verification"
    },
    {
        "id": "PDK-DEF-004",
        "technology_id": "asap7",
        "pdk_name": "ASAP7",
        "stage": "Placement / Floorplan",
        "limitation": "Standard cell grid height quantization (7.5T) vs 4x scaled DEF grid",
        "severity": "High",
        "root_cause": "ASAP7 7nm FinFET research PDK scaled by 4x for academic EDA tool compatibility",
        "workaround": "GCELL_GRID_PX / GCELL_GRID_PY snap alignment configuration",
        "correction": "Applied 4x metric scaling factor normalization engine across signoff metrics",
        "impact": "Placement density distortion if cell grid snapping is unaligned"
    },
    {
        "id": "PDK-DEF-005",
        "technology_id": "gt3",
        "pdk_name": "GT3",
        "stage": "CTS / Routing",
        "limitation": "Missing Liberty timing arcs for specialized low-power clock gating cells",
        "severity": "Medium",
        "root_cause": "Research 3nm GAAFET PDK Liberty model lacking setup/hold timing arcs for ICG cells",
        "workaround": "Bypassed automatic ICG cell mapping during Yosys synthesis",
        "correction": "Created dummy timing arc annotations for STA verification",
        "impact": "Clock Tree Synthesis requires fallback to standard buffer trees"
    },
    {
        "id": "PDK-DEF-006",
        "technology_id": "gt2n",
        "pdk_name": "GT2N",
        "stage": "Synthesis / STA",
        "limitation": "Subthreshold leakage model temperature coefficients missing for cryogenic corners",
        "severity": "Low",
        "root_cause": "Sub-2nm research PDK model calibrated only at nominal 25C and 125C corners",
        "workaround": "Restricted power signoff scenarios to nominal thermal corners",
        "correction": "Documented thermal corner limitation in research dataset",
        "impact": "Cryogenic power predictions flagged as non-comparable"
    }
]

# ----------------------------------------------------------------------
# 2. MASTER FORENSIC INTERVENTION REGISTER (Doc 10, 22)
# ----------------------------------------------------------------------
MASTER_INTERVENTIONS = [
    {
        "id": "INT-001",
        "experiment_id": "EXP-000041",
        "parent_id": "EXP-000038",
        "type": "Technology Patch",
        "classification": "C = WORKAROUND / RELAXATION / CONFIGURATION CHANGE",
        "description": "Diode cell insertion patch and LEF pin ANTENNADIFFAREA property correction for ICsprout55 antenna routing failure",
        "before_state": "EXP-000038 FAILED at Routing stage with GRT-0244 antenna violation error",
        "after_state": "EXP-000041 SUCCESS fully routed, 28 diode cells inserted, 0 DRC violations",
        "result": "Resolved routing failure; preserved parent-child lineage link in database"
    },
    {
        "id": "INT-002",
        "experiment_id": "EXP-000022",
        "parent_id": "EXP-000020",
        "type": "Floorplan Relaxation",
        "classification": "C = WORKAROUND / RELAXATION / CONFIGURATION CHANGE",
        "description": "Lowered FP_CORE_UTIL from 0.60 to 0.40 and adjusted placement target density PL_TARGET_DENSITY=0.45 on ASAP7 7nm",
        "before_state": "EXP-000020 FAILED at Detailed Placement due to routing congestion overflow (>15%)",
        "after_state": "EXP-000022 SUCCESS signoff clean, WNS = +0.12ns, 0 routing violations",
        "result": "Landmark 7nm signoff achievement; demonstrated density threshold for FinFET routability"
    },
    {
        "id": "INT-003",
        "experiment_id": "EXP-000054",
        "parent_id": "EXP-000048",
        "type": "Constraint Relaxation",
        "classification": "C = WORKAROUND / RELAXATION / CONFIGURATION CHANGE",
        "description": "Relaxed target clock period from 2.5ns to 3.2ns for NanGate45 high-density floorplan run",
        "before_state": "EXP-000048 FAILED with WNS = -0.45ns setup timing violation",
        "after_state": "EXP-000054 SUCCESS signoff clean, WNS = +0.08ns, zero setup violations",
        "result": "Established optimal frequency ceiling for 45nm standard cell library"
    },
    {
        "id": "INT-004",
        "experiment_id": "EXP-000010",
        "parent_id": "EXP-000005",
        "type": "Flow Override",
        "classification": "D = CHECK / REPAIR DISABLED",
        "description": "Disabled automatic Magic DRC in flow (MAGIC_DRC_USE_GDS=0) and enabled KLayout DRC firewall verification",
        "before_state": "EXP-000005 INCOMPLETE due to Magic DRC script timeout on tap cell density",
        "after_state": "EXP-000010 SUCCESS completed layout verification via KLayout DRC firewall",
        "result": "Bypassed tool-specific script freeze without compromising DRC verification integrity"
    }
]

# ----------------------------------------------------------------------
# 3. ENGINEERING INCIDENT LOG (Doc 11, 19)
# ----------------------------------------------------------------------
ENGINEERING_INCIDENTS = [
    {
        "id": "INC-001",
        "experiment_id": "EXP-000038",
        "stage": "Routing",
        "tool": "OpenROAD / Detailed Router",
        "error_code": "GRT-0244",
        "error_text": "Detailed routing failed during antenna repair: ANTENNADIFFAREA missing for pin",
        "severity": "Fatal Stage Failure",
        "root_cause_class": "A = REAL PHYSICAL / TECHNOLOGY EFFECT",
        "remediation": "Applied INT-001 (LEF pin property correction and diode insertion)"
    },
    {
        "id": "INC-002",
        "experiment_id": "EXP-000020",
        "stage": "Placement",
        "tool": "OpenROAD / Re-Placer",
        "error_code": "GPL-0102",
        "error_text": "Global placement congestion overflow exceeding 15% threshold on M2/M3 layers",
        "severity": "Fatal Stage Failure",
        "root_cause_class": "B = TOOL / MODEL / IMPLEMENTATION ISSUE",
        "remediation": "Applied INT-002 (Lowered FP_CORE_UTIL from 0.60 to 0.40)"
    },
    {
        "id": "INC-003",
        "experiment_id": "EXP-000048",
        "stage": "STA Signoff",
        "tool": "OpenSTA",
        "error_code": "STA-0042",
        "error_text": "Setup timing slack WNS = -0.45ns on critical path clk -> reg_data_out[31]",
        "severity": "Timing Violation Failure",
        "root_cause_class": "A = REAL PHYSICAL / TECHNOLOGY EFFECT",
        "remediation": "Applied INT-003 (Relaxed clock target from 2.5ns to 3.2ns)"
    },
    {
        "id": "INC-004",
        "experiment_id": "EXP-000060",
        "stage": "Physical Verification",
        "tool": "Magic DRC",
        "error_code": "DRC-0001",
        "error_text": "Magic DRC failed with 142 metal1 spacing violations on macro boundaries",
        "severity": "DRC Verification Failure",
        "root_cause_class": "B = TOOL / MODEL / IMPLEMENTATION ISSUE",
        "remediation": "Re-ran with macro halo margin padding and KLayout DRC firewall"
    }
]

# ----------------------------------------------------------------------
# 4. DO-NOT-COMPARE REGISTER & COMPARABILITY MATRIX (Doc 24)
# ----------------------------------------------------------------------
COMPARABILITY_RULES = [
    {
        "metric_group": "Cell Count & Area",
        "raw_metric": "Raw Synthesized Cell Count",
        "comparability_class": "C1 — Conditional",
        "conditions": "Same RTL revision and synthesis intent; standard cell track height & architecture must be reported.",
        "prohibited_comparison": "Directly declaring a technology superior based solely on cell count without normalizing track architecture.",
        "allowed_reporting": "Report raw cell count + normalized gate equivalents (GE) + standard cell track height."
    },
    {
        "metric_group": "Cell Count & Area",
        "raw_metric": "Raw Die / Core Area",
        "comparability_class": "C2 — Normalizable",
        "conditions": "Floorplan core utilization, aspect ratio, and IO ring margins must be identical.",
        "prohibited_comparison": "Comparing die area of a 0.60 utilization run on Sky130 with a 0.40 utilization run on ASAP7.",
        "allowed_reporting": "Report raw area (μm²) + core utilization (%) + normalized active cell area."
    },
    {
        "metric_group": "Timing & Performance",
        "raw_metric": "Worst Negative Slack (WNS)",
        "comparability_class": "C1 — Conditional",
        "conditions": "Identical logical clock period target (SDC), PVT corner, and Liberty timing model scenario.",
        "prohibited_comparison": "Comparing WNS of a 10ns clock run on Sky130 against a 2ns clock run on ASAP7.",
        "allowed_reporting": "Report WNS ($ns$) + Target Clock Period ($ns$) + Achieved Frequency ($MHz$) + PVT Corner."
    },
    {
        "metric_group": "Power Dissipation",
        "raw_metric": "Total Power",
        "comparability_class": "C2 — Normalizable",
        "conditions": "Identical supply voltage, clock frequency, switching activity assumptions, and thermal corner.",
        "prohibited_comparison": "Comparing total power across different operating voltages or switching activity factors.",
        "allowed_reporting": "Report total power ($mW$) + dynamic/leakage split + operating voltage ($V$) + frequency ($MHz$)."
    },
    {
        "metric_group": "Physical Verification",
        "raw_metric": "Raw DRC Violation Count",
        "comparability_class": "C0 — Not Comparable",
        "conditions": "DRC rule decks across different foundries have completely different rule counts and strictness scopes.",
        "prohibited_comparison": "Comparing raw DRC error count of Sky130 Magic DRC against ASAP7 KLayout DRC deck.",
        "allowed_reporting": "Report DRC status (Clean / Violating) + DRC deck name & rule count scope."
    },
    {
        "metric_group": "Routing & Interconnect",
        "raw_metric": "Total Routed Wirelength",
        "comparability_class": "C1 — Conditional",
        "conditions": "Must account for metal layer count differences (Sky130 5-layer vs ASAP7 7-layer vs NanGate45 10-layer).",
        "prohibited_comparison": "Comparing total wirelength without reporting layer stack allocation.",
        "allowed_reporting": "Report total wirelength (μm) + layer-by-layer metal usage breakdown."
    }
]

# ----------------------------------------------------------------------
# 5. FOUR TRUTHS & CLAIM-EVIDENCE MATRIX DATA (Doc 20, 26)
# ----------------------------------------------------------------------
FOUR_TRUTHS_RULES = {
    "design_truth": {
        "title": "Design Truth",
        "description": "What the RTL design actually contains, independent of tools or target technology.",
        "items": ["RTL Source Revision / Commit Hash", "Top Module Identity", "Sequential & Combinational Cell Taxonomy", "Clock Domain Architecture", "IO Port Count"]
    },
    "technology_truth": {
        "title": "Technology Truth",
        "description": "What the PDK, standard cell library, and technology collateral actually provide.",
        "items": ["PDK Feature Size & Architecture (Planar / FinFET / GAAFET)", "Metal Layer Stack & Pitch Rules", "Standard Cell Library Characterization", "Known PDK Defects & Limitations", "Liberty Timing & Power Corners"]
    },
    "tool_truth": {
        "title": "Tool Truth",
        "description": "What the EDA tools actually executed, generated, and reported.",
        "items": ["Tool & Version Identification (OpenLane, OpenROAD, Yosys, OpenSTA)", "Exact Stage Execution Timeline & Command Hashes", "Tool Warnings, Errors & Crash Logs", "Runtime & Peak Memory Footprint"]
    },
    "physical_truth": {
        "title": "Physical / Experimental Truth",
        "description": "What physical layout artifacts and signoff verification results were actually produced.",
        "items": ["DEF / ODB Physical Netlist Layouts", "SPEF Parasitic Extraction Models", "Signoff DRC, LVS & Antenna Verification Status", "Measured WNS / TNS & Power Breakdown"]
    }
}


def sync_research_data_to_db():
    """Populates ota.db with structured result data from the 26 forensic studies."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Populate failures table
    for inc in ENGINEERING_INCIDENTS:
        cur.execute("""
            INSERT OR REPLACE INTO failures (failure_id, experiment_id, origin, mechanism, signature, severity, root_cause_class, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inc["id"], inc["experiment_id"], inc["tool"], inc["error_code"],
            inc["error_text"], inc["severity"], inc["root_cause_class"], "Verified"
        ))

    # Populate interventions table
    for inter in MASTER_INTERVENTIONS:
        cur.execute("""
            INSERT OR REPLACE INTO interventions (intervention_id, failure_id, type, description, classification, before_state, after_state, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inter["id"], f"INC-{inter['id'].replace('INT-', '')}", inter["type"],
            inter["description"], inter["classification"], inter["before_state"],
            inter["after_state"], inter["result"]
        ))

    conn.commit()
    conn.close()
    print("Database ota.db updated with structured forensic result data.")


if __name__ == "__main__":
    sync_research_data_to_db()
