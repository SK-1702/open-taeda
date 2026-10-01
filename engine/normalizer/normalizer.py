import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from engine.collector import RunCollector, compute_sha256
from engine.parser import RunParser

class ManifestNormalizer:
    def __init__(self, manifests_dir: Path):
        self.manifests_dir = Path(manifests_dir)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def get_next_exp_id(self) -> str:
        existing = sorted(self.manifests_dir.glob("EXP-*.yaml"))
        max_id = 0
        for f in existing:
            name = f.stem # EXP-000001
            try:
                num = int(name.replace("EXP-", ""))
                if num > max_id:
                    max_id = num
            except ValueError:
                pass
        return f"EXP-{max_id + 1:06d}"

    def build_manifest(self, run_dir: Path, exp_id: Optional[str] = None, campaign: str = "TAEDA-CROSS-PDK") -> Dict[str, Any]:
        collector = RunCollector()
        collected = collector.collect_run_files(run_dir)
        parser = RunParser(run_dir)

        if not exp_id:
            exp_id = self.get_next_exp_id()

        tech_id = parser.extract_technology_id()
        design_info = parser.extract_design_info()
        status = parser.extract_status()
        stages = parser.extract_stages()
        failure = parser.extract_failure_forensics()
        interventions = parser.extract_interventions()

        cfg = parser.config
        metrics_raw = parser.metrics
        manufacturability = parser.manufacturability

        # Normalize metrics
        norm_metrics = {}
        if metrics_raw:
            if "TotalCells" in metrics_raw:
                try: norm_metrics["cell_count"] = int(metrics_raw["TotalCells"])
                except ValueError: pass
            if "CoreArea_um^2" in metrics_raw:
                try: norm_metrics["core_area_um2"] = float(metrics_raw["CoreArea_um^2"])
                except ValueError: pass
            if "DIEAREA_mm^2" in metrics_raw:
                try: norm_metrics["die_area_mm2"] = float(metrics_raw["DIEAREA_mm^2"])
                except ValueError: pass
            if "wns" in metrics_raw and metrics_raw["wns"] != "-1":
                try: norm_metrics["wns_ns"] = float(metrics_raw["wns"])
                except ValueError: pass
            if "tns" in metrics_raw and metrics_raw["tns"] != "-1":
                try: norm_metrics["tns_ns"] = float(metrics_raw["tns"])
                except ValueError: pass
            if "wire_length" in metrics_raw:
                try: norm_metrics["wirelength_um"] = float(metrics_raw["wire_length"])
                except ValueError: pass
            if "vias" in metrics_raw:
                try: norm_metrics["vias_count"] = int(metrics_raw["vias"])
                except ValueError: pass
            if "Magic_violations" in metrics_raw and metrics_raw["Magic_violations"] != "-1":
                try: norm_metrics["drc_errors"] = int(metrics_raw["Magic_violations"])
                except ValueError: pass
            if "DiodeCells" in metrics_raw:
                try: norm_metrics["diode_count"] = int(metrics_raw["DiodeCells"])
                except ValueError: pass
            if "pin_antenna_violations" in metrics_raw and metrics_raw["pin_antenna_violations"] != "-1":
                try: norm_metrics["pin_antenna_violations"] = int(metrics_raw["pin_antenna_violations"])
                except ValueError: pass
            if "net_antenna_violations" in metrics_raw and metrics_raw["net_antenna_violations"] != "-1":
                try: norm_metrics["net_antenna_violations"] = int(metrics_raw["net_antenna_violations"])
                except ValueError: pass

        if manufacturability:
            if "DRC violations" in manufacturability:
                try: norm_metrics["drc_errors"] = int(manufacturability["DRC violations"])
                except ValueError: pass
            if "Antenna violations" in manufacturability:
                try: norm_metrics["antenna_violations"] = int(manufacturability["Antenna violations"])
                except ValueError: pass

        # Flow & tool versions
        flow_name = "openroad_rtl2gds"
        flow_ver = "OpenLane v1.0.2"
        yosys_ver = "Yosys 0.38"
        openroad_ver = "OpenROAD 26Q2-2115-g14b1ef1329"

        # Determine exp type
        exp_type = "baseline"
        if interventions:
            exp_type = "intervention"
        elif "u50" in run_dir.name.lower() or "u60" in run_dir.name.lower() or "u70" in run_dir.name.lower() or "u80" in run_dir.name.lower() or "u90" in run_dir.name.lower():
            exp_type = "sweep"
        elif "exp" in run_dir.name.lower():
            exp_type = "comparative"

        manifest = {
            "schema_version": "0.1",
            "experiment": {
                "id": exp_id,
                "name": run_dir.name,
                "campaign": campaign,
                "type": exp_type,
                "source_run_path": str(run_dir),
            },
            "design": {
                "id": design_info["id"],
                "name": design_info["name"],
                "revision": "v1.0",
                "top": design_info["top"],
            },
            "technology": {
                "id": tech_id,
                "revision": "v1.0",
            },
            "flow": {
                "name": flow_name,
                "version": flow_ver,
            },
            "tools": {
                "yosys": yosys_ver,
                "openroad": openroad_ver,
                "opensta": "OpenSTA 2.6",
            },
            "environment": {
                "os": "Linux 6.8.0-45-generic x86_64",
                "architecture": "x86_64",
            },
            "inputs": {
                "rtl": f"designs/{design_info['name']}/rtl.yaml",
                "constraints": f"designs/{design_info['name']}/constraints/main.sdc",
            },
            "configuration": {
                "clock_period_ns": float(cfg.get("CLOCK_PERIOD", 20.0)),
                "core_utilization": float(cfg.get("FP_CORE_UTIL", cfg.get("CORE_UTILIZATION", 50.0))),
                "aspect_ratio": float(cfg.get("FP_ASPECT_RATIO", 1.0)),
                "grt_repair_antennas": cfg.get("GRT_REPAIR_ANTENNAS", "1"),
                "fill_cell": cfg.get("FILL_CELL", "default"),
                "config_hash": collected["config_hash"],
            },
            "stages": stages,
            "metrics": norm_metrics,
            "artifacts": {
                "def": collected["artifacts"]["def"][0] if collected["artifacts"]["def"] else None,
                "odb": collected["artifacts"]["odb"][0] if collected["artifacts"]["odb"] else None,
                "gds": collected["artifacts"]["gds"][0] if collected["artifacts"]["gds"] else None,
                "metrics_csv": collected["metrics_csv"],
            },
            "evidence": {
                "manufacturability_report": collected["manufacturability_rpt"],
                "logs_count": len(collected["log_files"]),
                "reports_count": len(collected["report_files"]),
            },
            "status": status,
        }

        if failure:
            manifest["failure"] = failure
        if interventions:
            manifest["interventions"] = interventions

        return manifest

    def save_manifest(self, manifest: Dict[str, Any]) -> Path:
        exp_id = manifest["experiment"]["id"]
        out_file = self.manifests_dir / f"{exp_id}.yaml"
        with open(out_file, "w") as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
        return out_file
