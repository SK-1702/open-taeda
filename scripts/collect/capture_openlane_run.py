#!/usr/bin/env python3

"""
Open TAEDA OpenLane/OpenROAD Experiment Capture Engine
=======================================================

Purpose:
    Convert raw OpenLane run directories into normalized,
    provenance-preserving research data.

Important:
    This collector NEVER invents missing metrics.

Usage:

    python3 capture_openlane_run.py <run>

    python3 capture_openlane_run.py <runs_directory> --recursive

    python3 capture_openlane_run.py <run> --json-only

"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

OPEN_TAEDA_ROOT = Path(
    "/home/user/Research/open-taeda-v0.1-starter"
)

MANIFEST_DIR = OPEN_TAEDA_ROOT / "experiments" / "manifests"
EVIDENCE_DIR = OPEN_TAEDA_ROOT / "experiments" / "evidence"


# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def sha256_file(path: Path):
    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            data = f.read(1024 * 1024)

            if not data:
                break

            h.update(data)

    return h.hexdigest()


def file_size(path: Path):
    try:
        return path.stat().st_size
    except Exception:
        return None


def now():
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        return ""


def find_files(root: Path, patterns):
    result = []

    for pattern in patterns:
        result.extend(root.rglob(pattern))

    return sorted(set(result))


# ------------------------------------------------------------
# Tool detection
# ------------------------------------------------------------

def detect_tools(run: Path):

    tools = {}

    log_files = find_files(
        run,
        ["*.log", "*.rpt", "*.txt"]
    )

    text = ""

    for f in log_files:
        text += "\n" + read_text(f)

    patterns = {
        "openlane": r"OpenLane\s+([0-9A-Za-z.\-_]+)",
        "openroad": r"OpenROAD\s+([0-9A-Za-z.\-_]+)",
        "yosys": r"Yosys\s+([0-9A-Za-z.\-_]+)",
        "opensta": r"OpenSTA\s+([0-9A-Za-z.\-_]+)",
    }

    for name, pattern in patterns.items():

        m = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if m:
            tools[name] = m.group(1)

    return tools


# ------------------------------------------------------------
# Configuration discovery
# ------------------------------------------------------------

def discover_config(run: Path):

    candidates = [
        run / "config.json",
        run / "config.tcl",
        run / "config.yaml",
        run / "config.yml",
    ]

    result = {}

    for cfg in candidates:

        if not cfg.exists():
            continue

        result[str(cfg.relative_to(run))] = {
            "sha256": sha256_file(cfg),
            "size_bytes": file_size(cfg)
        }

        if cfg.suffix == ".json":

            try:
                result[str(cfg.relative_to(run))]["content"] = \
                    json.loads(read_text(cfg))
            except Exception:
                pass

    return result


# ------------------------------------------------------------
# Artifact discovery
# ------------------------------------------------------------

def discover_artifacts(run: Path):

    artifact_patterns = {

        "rtl": [
            "*.v",
            "*.sv",
            "*.vh"
        ],

        "def": [
            "*.def"
        ],

        "odb": [
            "*.odb"
        ],

        "gds": [
            "*.gds",
            "*.gds.gz"
        ],

        "lef": [
            "*.lef"
        ],

        "liberty": [
            "*.lib"
        ],

        "spef": [
            "*.spef"
        ],

        "sdc": [
            "*.sdc"
        ],

        "netlist": [
            "*netlist*.v",
            "*nl.v"
        ],

        "reports": [
            "*.rpt",
            "*.report"
        ],

        "logs": [
            "*.log"
        ]
    }

    result = []

    for category, patterns in artifact_patterns.items():

        for path in find_files(run, patterns):

            try:
                rel = str(path.relative_to(run))
            except ValueError:
                rel = str(path)

            result.append({
                "category": category,
                "path": rel,
                "size_bytes": file_size(path),
                "sha256": sha256_file(path)
            })

    return result


# ------------------------------------------------------------
# Stage detection
# ------------------------------------------------------------

STAGES = [
    "synthesis",
    "floorplan",
    "placement",
    "cts",
    "routing",
    "extraction",
    "sta",
    "power",
    "drc",
    "lvs"
]


def detect_stages(run: Path):

    result = []

    text = ""

    for f in find_files(run, ["*.log"]):
        text += "\n" + read_text(f)

    for index, stage in enumerate(STAGES, 1):

        pattern = rf"\b{re.escape(stage)}\b"

        found = bool(
            re.search(
                pattern,
                text,
                re.IGNORECASE
            )
        )

        result.append({
            "sequence": index,
            "stage": stage,
            "observed": found
        })

    return result


# ------------------------------------------------------------
# Numeric metric extraction
# ------------------------------------------------------------

def extract_number(text, patterns):

    for pattern in patterns:

        m = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if m:

            try:
                return float(
                    m.group(1)
                    .replace(",", "")
                )
            except Exception:
                pass

    return None


def collect_metrics(run: Path):

    result = {}

    # OpenLane normally has metrics.csv
    metrics_files = list(
        run.rglob("metrics.csv")
    )

    if metrics_files:

        metrics_file = metrics_files[-1]

        try:

            lines = read_text(
                metrics_file
            ).splitlines()

            if lines:

                headers = lines[0].split(",")

                if len(lines) > 1:

                    values = lines[-1].split(",")

                    for key, value in zip(
                        headers,
                        values
                    ):

                        value = value.strip()

                        try:
                            result[key] = float(value)
                        except ValueError:
                            result[key] = value

        except Exception:
            pass

    # Fallback: scan logs/reports
    text = ""

    for f in find_files(
        run,
        ["*.log", "*.rpt", "*.txt"]
    ):
        text += "\n" + read_text(f)

    aliases = {

        "cell_count": [
            r"Total\s+Cells\s*[:=]\s*([\d,]+)",
            r"Cell\s+Count\s*[:=]\s*([\d,]+)"
        ],

        "core_area": [
            r"Core\s+Area\s*[:=]\s*([\d.]+)",
            r"core_area\s*[:=]\s*([\d.]+)"
        ],

        "die_area": [
            r"Die\s+Area\s*[:=]\s*([\d.]+)"
        ],

        "utilization": [
            r"Utilization\s*[:=]\s*([\d.]+)"
        ],

        "wns": [
            r"WNS\s*[:=]\s*(-?[\d.]+)"
        ],

        "tns": [
            r"TNS\s*[:=]\s*(-?[\d.]+)"
        ],

        "hold_wns": [
            r"WHS\s*[:=]\s*(-?[\d.]+)"
        ],

        "hold_tns": [
            r"THS\s*[:=]\s*(-?[\d.]+)"
        ],

        "wirelength": [
            r"wirelength\s*[:=]\s*([\d.]+)"
        ],

        "vias": [
            r"\bVias\s*[:=]\s*([\d.]+)"
        ],

        "routing_overflow": [
            r"overflow\s*[:=]\s*([\d.]+)"
        ],

        "congestion": [
            r"congestion\s*[:=]\s*([\d.]+)"
        ],

        "power": [
            r"Total\s+Power\s*[:=]\s*([\d.]+)",
            r"total_power\s*[:=]\s*([\d.]+)"
        ],

        "clock_skew": [
            r"clock\s+skew\s*[:=]\s*(-?[\d.]+)"
        ]
    }

    for metric, patterns in aliases.items():

        if metric not in result:

            value = extract_number(
                text,
                patterns
            )

            if value is not None:
                result[metric] = value

    return result


# ------------------------------------------------------------
# Failure detection
# ------------------------------------------------------------

FAILURE_PATTERNS = {

    "OOM": [
        r"out of memory",
        r"cannot allocate memory",
        r"std::bad_alloc"
    ],

    "ASSERTION": [
        r"assertion failed",
        r"SIGABRT",
        r"signal 6"
    ],

    "SEGFAULT": [
        r"segmentation fault",
        r"SIGSEGV",
        r"signal 11"
    ],

    "MISSING_LEF": [
        r"missing.*LEF",
        r"LEF.*not found"
    ],

    "MISSING_CELL": [
        r"cell.*not found",
        r"Diode cell not found"
    ],

    "DRC": [
        r"DRC.*violation",
        r"DRC.*error"
    ],

    "LVS": [
        r"LVS.*failed",
        r"LVS.*error"
    ]
}


def detect_failures(run: Path):

    failures = []

    for log in find_files(
        run,
        ["*.log", "*.rpt", "*.txt"]
    ):

        text = read_text(log)

        for category, patterns in FAILURE_PATTERNS.items():

            for pattern in patterns:

                m = re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )

                if m:

                    failures.append({

                        "category": category,

                        "log": str(
                            log.relative_to(run)
                        ),

                        "matched_text":
                            m.group(0),

                        "pattern":
                            pattern
                    })

                    break

    return failures


# ------------------------------------------------------------
# Resource/runtime extraction
# ------------------------------------------------------------

def collect_runtime_information(run: Path):

    result = {}

    runtime_files = find_files(
        run,
        ["runtime.yaml", "runtime.json"]
    )

    for f in runtime_files:

        result[
            str(f.relative_to(run))
        ] = read_text(f)

    return result


# ------------------------------------------------------------
# Experiment classification
# ------------------------------------------------------------

def classify_experiment(
    run: Path,
    failures,
    metrics
):

    name = run.name.lower()

    if "sweep" in name:
        return "sweep"

    if "intervention" in name:
        return "intervention"

    if "recovery" in name:
        return "recovery"

    if "debug" in name:
        return "debug"

    if "compare" in name:
        return "comparative"

    if failures:
        return "baseline"

    return "baseline"


# ------------------------------------------------------------
# Capture one run
# ------------------------------------------------------------

def capture_run(run: Path):

    run = run.resolve()

    print()
    print("=" * 70)
    print("OPEN TAEDA EXPERIMENT CAPTURE")
    print("=" * 70)
    print("Run:", run)

    tools = detect_tools(run)

    config = discover_config(run)

    artifacts = discover_artifacts(run)

    stages = detect_stages(run)

    metrics = collect_metrics(run)

    failures = detect_failures(run)

    runtime = collect_runtime_information(run)

    experiment_type = classify_experiment(
        run,
        failures,
        metrics
    )

    record = {

        "capture": {

            "collector":
                "open-taeda-openlane-capture",

            "collector_version":
                "0.1",

            "captured_at":
                now()
        },

        "source": {

            "run_directory":
                str(run),

            "run_name":
                run.name
        },

        "experiment": {

            "type":
                experiment_type,

            "status":
                "FAILED"
                if failures
                else "CAPTURED"
        },

        "tools": tools,

        "configuration": config,

        "stages": stages,

        "metrics": metrics,

        "failures": failures,

        "runtime": runtime,

        "artifacts": artifacts,

        "provenance": {

            "source_path":
                str(run),

            "artifact_count":
                len(artifacts),

            "log_count":
                len([
                    x for x in artifacts
                    if x["category"] == "logs"
                ]),

            "report_count":
                len([
                    x for x in artifacts
                    if x["category"] == "reports"
                ])
        }
    }

    return record


# ------------------------------------------------------------
# Save capture
# ------------------------------------------------------------

def save_capture(run: Path, record):

    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_dir = (
        EVIDENCE_DIR / run.name
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output = (
        output_dir /
        "capture.json"
    )

    output.write_text(
        json.dumps(
            record,
            indent=2,
            sort_keys=True
        ),
        encoding="utf-8"
    )

    print()
    print("Capture written:")
    print(output)

    return output


# ------------------------------------------------------------
# Recursive mode
# ------------------------------------------------------------

def discover_runs(root: Path):

    runs = []

    for directory in root.iterdir():

        if not directory.is_dir():
            continue

        indicators = [
            directory / "config.json",
            directory / "config.tcl",
            directory / "logs",
            directory / "reports",
            directory / "results"
        ]

        if any(
            x.exists()
            for x in indicators
        ):
            runs.append(directory)

    return sorted(runs)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "path",
        help="OpenLane run directory or runs directory"
    )

    parser.add_argument(
        "--recursive",
        action="store_true"
    )

    parser.add_argument(
        "--json-only",
        action="store_true"
    )

    args = parser.parse_args()

    path = Path(args.path).resolve()

    if not path.exists():

        raise SystemExit(
            f"Path does not exist: {path}"
        )

    if args.recursive:

        runs = discover_runs(path)

    else:

        runs = [path]

    print()
    print(
        f"Discovered {len(runs)} experiment run(s)"
    )

    for run in runs:

        record = capture_run(run)

        output = save_capture(
            run,
            record
        )

        print(
            f"[OK] {run.name}"
        )

        print(
            f"     Metrics: "
            f"{len(record['metrics'])}"
        )

        print(
            f"     Artifacts: "
            f"{len(record['artifacts'])}"
        )

        print(
            f"     Failures: "
            f"{len(record['failures'])}"
        )


if __name__ == "__main__":
    main()
