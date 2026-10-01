import pytest
from pathlib import Path
from engine.validator import ManifestValidator

ROOT = Path(__file__).resolve().parents[2]

def test_manifest_validation():
    validator = ManifestValidator(ROOT)
    exp1 = ROOT / "experiments" / "manifests" / "EXP-000001.yaml"
    if exp1.exists():
        valid, errors = validator.validate_file(exp1)
        assert valid, f"EXP-000001 validation failed: {errors}"
