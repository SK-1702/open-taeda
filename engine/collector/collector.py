import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

DEFAULT_RUNS_DIR = Path("/home/user/eda_tools_universal/OpenLane/designs/picorv32a/runs")

def compute_sha256(file_path: Path) -> Optional[str]:
    if not file_path.exists() or not file_path.is_file():
        return None
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

class RunCollector:
    def __init__(self, runs_dir: Path = DEFAULT_RUNS_DIR):
        self.runs_dir = runs_dir

    def discover_runs(self) -> List[Path]:
        if not self.runs_dir.exists():
            return []
        runs = []
        for p in sorted(self.runs_dir.iterdir()):
            if p.is_dir() and not p.name.startswith(".") and p.name not in ["cross_pdk_analysis", "forensic_search_reports"]:
                # Needs config.tcl or reports/logs directory to be a candidate run
                if (p / "config.tcl").exists() or (p / "reports").exists() or (p / "logs").exists():
                    runs.append(p)
        return runs

    def collect_run_files(self, run_dir: Path) -> Dict[str, Any]:
        config_tcl = run_dir / "config.tcl"
        metrics_csv = run_dir / "reports" / "metrics.csv"
        manufacturability_rpt = run_dir / "reports" / "manufacturability.rpt"
        
        logs = list(run_dir.glob("**/logs/*/*.log")) + list(run_dir.glob("**/logs/*.log"))
        reports = list(run_dir.glob("**/reports/*/*.rpt")) + list(run_dir.glob("**/reports/*.rpt"))
        
        def_files = list(run_dir.glob("**/picorv32.def"))
        odb_files = list(run_dir.glob("**/picorv32.odb"))
        gds_files = list(run_dir.glob("**/picorv32.gds"))
        
        return {
            "run_dir": str(run_dir),
            "run_name": run_dir.name,
            "config_tcl": str(config_tcl) if config_tcl.exists() else None,
            "config_hash": compute_sha256(config_tcl) if config_tcl.exists() else None,
            "metrics_csv": str(metrics_csv) if metrics_csv.exists() else None,
            "manufacturability_rpt": str(manufacturability_rpt) if manufacturability_rpt.exists() else None,
            "log_files": [str(l) for l in logs],
            "report_files": [str(r) for r in reports],
            "artifacts": {
                "def": [str(d) for d in def_files],
                "odb": [str(o) for o in odb_files],
                "gds": [str(g) for g in gds_files],
            }
        }
