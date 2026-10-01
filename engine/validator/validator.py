import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT = Path(__file__).resolve().parents[2]

class ManifestValidator:
    def __init__(self, root_dir: Path = ROOT):
        self.root_dir = Path(root_dir)

    def validate_file(self, manifest_path: Path) -> Tuple[bool, List[str]]:
        errors = []
        path = Path(manifest_path)
        if not path.exists():
            return False, [f"File non-existent: {manifest_path}"]

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            return False, [f"YAML parse error: {e}"]

        if not isinstance(data, dict):
            return False, ["Manifest is not a valid YAML dictionary"]

        required_keys = ["schema_version", "experiment", "design", "technology", "flow", "stages"]
        for k in required_keys:
            if k not in data:
                errors.append(f"Missing required top-level key: '{k}'")

        exp = data.get("experiment", {})
        if not isinstance(exp, dict):
            errors.append("'experiment' section must be a dictionary")
        else:
            exp_id = exp.get("id", "")
            if not re.match(r"^EXP-[0-9]{6}$", exp_id):
                errors.append(f"Invalid experiment ID format: '{exp_id}' (expected EXP-XXXXXX)")

        tech = data.get("technology", {})
        if isinstance(tech, dict):
            tech_id = tech.get("id")
            if tech_id:
                tech_dir = self.root_dir / "technologies" / tech_id
                if not tech_dir.exists():
                    errors.append(f"Referenced technology '{tech_id}' does not exist in technologies/")

        des = data.get("design", {})
        if isinstance(des, dict):
            des_name = des.get("name")
            if des_name:
                des_dir = self.root_dir / "designs" / des_name
                if not des_dir.exists():
                    errors.append(f"Referenced design '{des_name}' does not exist in designs/")

        status = data.get("status")
        valid_statuses = ["SUCCESS", "FAILED", "INCOMPLETE", "DRAFT"]
        if status and status not in valid_statuses:
            errors.append(f"Invalid experiment status '{status}'. Must be one of {valid_statuses}")

        valid = (len(errors) == 0)
        return valid, errors
