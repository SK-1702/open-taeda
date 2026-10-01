import pytest
from pathlib import Path
from website.def_parser import parse_def_file
from engine.normalizer import ManifestNormalizer

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = ROOT / "experiments" / "manifests"

def test_def_parser():
    sample_def = Path("/home/user/eda_tools_universal/OpenLane/designs/picorv32a/runs/asap7_picorv32_research_exp6/results/routing/picorv32.def")
    if sample_def.exists():
        res = parse_def_file(sample_def)
        assert "diearea" in res
        assert len(res["diearea"]) == 4
        assert res["total_components"] > 0

def test_manifest_parent_relationship():
    exp22 = MANIFESTS_DIR / "EXP-000022.yaml"
    if exp22.exists():
        import yaml
        with open(exp22, "r") as f:
            data = yaml.safe_load(f)
        assert data["experiment"].get("parent_experiment") == "EXP-000020"
        assert len(data.get("interventions", [])) > 0
