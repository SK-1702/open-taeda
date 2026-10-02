"""
Open TAEDA — Cross-PDK Forensic Research Analysis Loader
=========================================================

Parses and indexes the 26 detailed RTL-to-GDS forensic analysis documents from:
/home/user/eda_tools_universal/OpenLane/designs/picorv32a/runs/cross_pdk_analysis
"""

from __future__ import annotations

import glob
import html
import os
import re
from pathlib import Path
import docx

ANALYSIS_DIR = Path("/home/user/eda_tools_universal/OpenLane/designs/picorv32a/runs/cross_pdk_analysis")

DOCUMENT_META = {
    "01": {
        "title": "01 — Experiment Metadata & Controlled Variables",
        "category": "Provenance & Metadata",
        "description": "Master identity, scope, controlled variables, reproducibility locks, and full audit record across Sky130, ICsprout55, NanGate45, and ASAP7."
    },
    "02": {
        "title": "02 — Floorplan Comparison & Forensic Analysis",
        "category": "Physical Implementation",
        "description": "Floorplan geometry, die/core area, aspect ratio, density targets, row organization, IO placement, power distribution network (PDN), and blockage allocation."
    },
    "03": {
        "title": "03 — Placement Results & Attribution Analysis",
        "category": "Physical Implementation",
        "description": "Global/detailed placement behavior, cell counts, HPWL wirelength, placement density, buffer insertion, and cell resizing across technologies."
    },
    "04": {
        "title": "04 — Clock Tree Synthesis (CTS) Comparative Study",
        "category": "Timing & Clocking",
        "description": "Clock buffer insertion, clock tree cell distribution, skew, insertion delay, clock latency, clock fanout, and CTS impact on setup/hold timing."
    },
    "05": {
        "title": "05 — Routing Results & Violation Analysis",
        "category": "Routing & Interconnect",
        "description": "Global and detailed routing, routed wirelength, metal layer utilization, via counts, congestion hotspots, routing overflow, and antenna repair mechanisms."
    },
    "06": {
        "title": "06 — Timing Results (WNS, TNS & Signoff STA)",
        "category": "Timing & Clocking",
        "description": "Worst Negative Slack (WNS), Total Negative Slack (TNS), setup/hold violation endpoints, critical path delays, net vs cell delays, and frequency headroom."
    },
    "07": {
        "title": "07 — Power Results (Dynamic vs. Leakage)",
        "category": "Power & Thermal",
        "description": "Total power dissipation, internal, switching, and subthreshold leakage power breakdown, power density, and voltage scaling behavior across node sizes."
    },
    "08": {
        "title": "08 — Physical Verification (DRC, LVS & Antenna)",
        "category": "Signoff & Verification",
        "description": "Signoff DRC violation breakdown, LVS netlist-vs-layout equivalence status, antenna rule violations, metal density checks, and manufacturability readiness."
    },
    "09": {
        "title": "09 — PDK Forensics & Technology Capture Manual",
        "category": "Technology & PDK",
        "description": "Comprehensive audit of technology LEF, Liberty cell models, tech files, design rules, layer stacks, known PDK bugs, and open-source collateral limits."
    },
    "10": {
        "title": "10 — Master Forensic Intervention Register",
        "category": "Interventions & Overrides",
        "description": "Catalog of all design modifications, flow overrides, layer restrictions, constraint relaxations, macro displacements, and workaround scripts applied during experiments."
    },
    "11": {
        "title": "11 — Engineering Incident Log",
        "category": "Incident Forensics",
        "description": "Exhaustive incident log recording every tool crash, out-of-memory (OOM) error, syntax exception, missing LEF cell bug, script error, and anomaly encountered."
    },
    "12": {
        "title": "12 — Reproducibility & Provenance Locking",
        "category": "Provenance & Metadata",
        "description": "Protocol for environment locking, container provenance, tool version hash locking, design constraint freezing, and full multi-level reproducibility verification."
    },
    "13": {
        "title": "13 — Evidence Hierarchy & Claim Validation",
        "category": "Scientific Methodology",
        "description": "Scientific evidence strength classification, claim validation criteria, proof requirements, and research-grade evidence ranking framework."
    },
    "14": {
        "title": "14 — Independent Verification Firewall",
        "category": "Signoff & Verification",
        "description": "Verification firewall protocol requiring third-party tool validation (Magic, Netgen, KLayout, OpenSTA) before marking implementation results clean."
    },
    "15": {
        "title": "15 — Golden Reference Comparison Baseline",
        "category": "Scientific Methodology",
        "description": "Comparison of actual EDA physical implementation outputs against ideal theoretical PDK scaling metrics and golden reference design baselines."
    },
    "16": {
        "title": "16 — Cross-PDK Results Normalization",
        "category": "Scientific Methodology",
        "description": "Normalization methodologies for area, cell count, frequency, power, wirelength, and runtime across feature sizes from 130nm down to 2nm."
    },
    "17": {
        "title": "17 — Technology Physics to P&R Behavior Causal Analysis",
        "category": "Technology & PDK",
        "description": "Causal links connecting transistor architecture (planar vs FinFET), metal pitch, DRC rule complexity, and pin access constraints to P&R tool behavior."
    },
    "18": {
        "title": "18 — Tool Behavior Forensics & Attribution Manual",
        "category": "Tool Forensics",
        "description": "Disambiguation protocol isolating tool algorithm artifacts from PDK collateral flaws, flow configuration errors, and design RTL characteristics."
    },
    "19": {
        "title": "19 — Failure Analysis & Negative Results Protocol",
        "category": "Incident Forensics",
        "description": "Methodology for evaluating, documenting, and extracting scientific research value from failed physical synthesis runs and aborted EDA stages."
    },
    "20": {
        "title": "20 — Claim-to-Evidence Matrix",
        "category": "Scientific Methodology",
        "description": "Evidence-control matrix mapping every research assertion to exact log lines, reports, DEF netlists, and physical measurement artifacts."
    },
    "21": {
        "title": "21 — Standard Visual Screenshot Protocol",
        "category": "Scientific Methodology",
        "description": "Standardized protocol for capturing, cropping, and cataloging GUI canvas screenshots (layout, density maps, routing congestion, clock trees)."
    },
    "22": {
        "title": "22 — Before-and-After Intervention Evidence Protocol",
        "category": "Interventions & Overrides",
        "description": "Paired visual and metric evidence protocol for tracking floorplan, constraint, or routing state changes before and after applying an intervention."
    },
    "23": {
        "title": "23 — PDK Defect & Limitation Register",
        "category": "Technology & PDK",
        "description": "Comprehensive register of known PDK collateral defects, missing Liberty timing arcs, corrupt LEF pin definitions, missing antenna rules, and workaround patches."
    },
    "24": {
        "title": "24 — 'Do Not Compare' Register & Comparability Matrix",
        "category": "Scientific Methodology",
        "description": "Strict scientific boundary matrix defining illegal cross-PDK comparisons (e.g. mismatched floorplan constraints, unroutable utilization targets, unequal stage signoffs)."
    },
    "25": {
        "title": "25 — Master Research Dataset Specification",
        "category": "Scientific Methodology",
        "description": "Unified database schema, metric field dictionary, artifact tree structure, and checksum manifest specification for the complete research dataset."
    },
    "26": {
        "title": "26 — Four Truths & Ten Research Questions Framework",
        "category": "Scientific Methodology",
        "description": "Core scientific doctrine organizing research findings into Design Truth, Technology Truth, Tool Truth, and Physical Truth across 10 fundamental research questions."
    }
}


def load_doc_as_html(filepath: Path) -> str:
    """Parses a docx file into clean HTML with dark-theme styling tags."""
    try:
        doc = docx.Document(filepath)
    except Exception as e:
        return f"<div class='alert alert-error'>Failed to load document: {e}</div>"

    html_parts = []

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        escaped = html.escape(text)

        # Detect headers based on formatting patterns or paragraph text
        if re.match(r"^\d+\.\s+[A-Z]", text) or text.isupper() and len(text) < 80 or "SECTION" in text.upper():
            html_parts.append(f"<h2 class='doc-section-h2'>{escaped}</h2>")
        elif re.match(r"^\d+\.\d+\s+", text) or text.startswith("Document ") or text.startswith("PicoRV32"):
            html_parts.append(f"<h3 class='doc-section-h3'>{escaped}</h3>")
        elif text.startswith("•") or text.startswith("- ") or text.startswith("* "):
            clean_item = re.sub(r"^[•\-\*]\s*", "", escaped)
            html_parts.append(f"<li class='doc-bullet-item'>{clean_item}</li>")
        elif text.startswith("Note:") or text.startswith("IMPORTANT:") or text.startswith("WARNING:"):
            html_parts.append(f"<div class='doc-callout'>{escaped}</div>")
        else:
            html_parts.append(f"<p class='doc-body-p'>{escaped}</p>")

    # Render tables
    for table in doc.tables:
        t_html = ["<div class='table-responsive my-3'><table class='table table-dark table-striped table-bordered align-middle'>"]
        for i, row in enumerate(table.rows):
            tag = "th" if i == 0 else "td"
            cell_styles = "class='bg-secondary text-light fw-bold'" if i == 0 else ""
            t_html.append("<tr>")
            for cell in row.cells:
                t_html.append(f"<{tag} {cell_styles}>{html.escape(cell.text.strip())}</{tag}>")
            t_html.append("</tr>")
        t_html.append("</table></div>")
        html_parts.append("".join(t_html))

    return "\n".join(html_parts)


def get_all_analysis_docs() -> list[dict]:
    """Returns a sorted list of all 26 analysis document records."""
    docs = []
    docx_files = sorted(ANALYSIS_DIR.glob("*.docx"))

    for filepath in docx_files:
        filename = filepath.name
        match = re.match(r"^(\d{2})_", filename)
        doc_id = match.group(1) if match else "00"

        meta = DOCUMENT_META.get(doc_id, {
            "title": filename.replace(".docx", "").replace("_", " "),
            "category": "General Analysis",
            "description": "Detailed RTL-to-GDS forensic research study."
        })

        # Calculate file size & word count estimate
        size_kb = round(filepath.stat().st_size / 1024, 1)

        docs.append({
            "id": doc_id,
            "filename": filename,
            "filepath": str(filepath),
            "title": meta["title"],
            "category": meta["category"],
            "description": meta["description"],
            "size_kb": size_kb,
        })

    return docs


def get_analysis_doc_by_id(doc_id: str) -> dict | None:
    """Gets details and HTML content for a specific document ID (e.g. '01' to '26')."""
    docx_files = sorted(ANALYSIS_DIR.glob(f"{doc_id}_*.docx"))
    if not docx_files:
        return None

    filepath = docx_files[0]
    meta = DOCUMENT_META.get(doc_id, {
        "title": filepath.name.replace(".docx", ""),
        "category": "General Analysis",
        "description": "Detailed RTL-to-GDS forensic research study."
    })

    content_html = load_doc_as_html(filepath)

    return {
        "id": doc_id,
        "filename": filepath.name,
        "filepath": str(filepath),
        "title": meta["title"],
        "category": meta["category"],
        "description": meta["description"],
        "size_kb": round(filepath.stat().st_size / 1024, 1),
        "content_html": content_html
    }
