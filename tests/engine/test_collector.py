import pytest
from pathlib import Path
from engine.collector import RunCollector

ROOT = Path(__file__).resolve().parents[2]

def test_run_collector_discovery():
    collector = RunCollector()
    runs = collector.discover_runs()
    assert isinstance(runs, list)
    assert len(runs) > 0
