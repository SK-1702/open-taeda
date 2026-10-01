import pytest
from pathlib import Path
from engine.parser import RunParser

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path("/home/user/eda_tools_universal/OpenLane/designs/picorv32a/runs")

def test_parser_sample_run():
    sample = RUNS_DIR / "nangate45_picorv32_research_exp7"
    if sample.exists():
        parser = RunParser(sample)
        tech = parser.extract_technology_id()
        status = parser.extract_status()
        assert tech == "nangate45"
        assert status == "SUCCESS"
