import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.collector import RunCollector
from engine.parser import RunParser
from engine.normalizer import ManifestNormalizer
from engine.validator import ManifestValidator
from engine.comparator import DatabaseManager

DB = ROOT / "database" / "ota.db"
SCHEMA = ROOT / "database" / "schema" / "schema.sql"
MANIFESTS_DIR = ROOT / "experiments" / "manifests"

def db_init():
    db_mgr = DatabaseManager(DB)
    db_mgr.sync_manifests()
    print(f"Initialized & synced research database at {DB}")

def list_registry(kind):
    path = ROOT / ("technologies" if kind == "technology" else "designs")
    print(f"{kind.title()}s:")
    for p in sorted(path.iterdir()):
        if p.is_dir():
            print(f"  - {p.name}")

def discover_runs():
    collector = RunCollector()
    runs = collector.discover_runs()
    print(f"Discovered {len(runs)} raw experiment runs:")
    for r in runs:
        parser = RunParser(r)
        status = parser.extract_status()
        tech = parser.extract_technology_id()
        print(f"  - {r.name:35s} | Tech: {tech:10s} | Status: {status}")

def collect_runs():
    collector = RunCollector()
    normalizer = ManifestNormalizer(MANIFESTS_DIR)
    runs = collector.discover_runs()
    generated = []
    for r in runs:
        parser = RunParser(r)
        status = parser.extract_status()
        manifest = normalizer.build_manifest(r)
        out_path = normalizer.save_manifest(manifest)
        generated.append(out_path)
        print(f"Generated manifest: {out_path.name} for run {r.name} ({status})")
    print(f"Successfully generated {len(generated)} experiment manifests in {MANIFESTS_DIR}")

def publish_run(run_dir_path: str, push: bool = False):
    run_dir = Path(run_dir_path).resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise SystemExit(f"Error: Run directory '{run_dir_path}' does not exist.")

    print(f"Ingesting raw OpenLane experiment run from: {run_dir}")
    parser = RunParser(run_dir)
    status = parser.extract_status()
    tech = parser.extract_technology_id()
    print(f"Detected Technology: {tech} | Status: {status}")

    # Check if run already exists in existing manifests
    manifest_files = sorted(MANIFESTS_DIR.glob("*.yaml"))
    existing_exp_id = None
    for mfile in manifest_files:
        try:
            with open(mfile, "r") as f:
                import yaml
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    src_path = data.get("experiment", {}).get("source_run_path")
                    if src_path and Path(src_path).resolve() == run_dir:
                        existing_exp_id = data.get("experiment", {}).get("id")
                        break
        except Exception:
            pass

    normalizer = ManifestNormalizer(MANIFESTS_DIR)
    manifest = normalizer.build_manifest(run_dir, exp_id=existing_exp_id)
    exp_id = manifest["experiment"]["id"]
    out_path = normalizer.save_manifest(manifest)
    print(f"Normalized experiment manifest: {out_path} ({exp_id})")

    validator = ManifestValidator(ROOT)
    valid, errors = validator.validate_file(out_path)
    if not valid:
        print(f"FAIL: Manifest validation failed for {exp_id}:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("PASS: Manifest validated against repository schema.")

    # Sync research database
    db_init()

    # Git stage, commit, push
    if (ROOT / ".git").exists():
        subprocess.run(["git", "add", str(out_path), str(DB)], cwd=ROOT, check=False)
        commit_msg = f"research: publish {exp_id} {run_dir.name} ({status})"
        status_res = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if status_res.returncode != 0:
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=ROOT, check=True)
            print(f"Committed publication record: {commit_msg}")
        else:
            print(f"No changes to commit for {exp_id} (already up to date).")

        if push:
            subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
            print(f"Pushed {exp_id} to GitHub main branch.")
    else:
        print("Git repository not initialized. Staging skipped.")

def validate_manifest(path):
    validator = ManifestValidator(ROOT)
    valid, errors = validator.validate_file(Path(path))
    if not valid:
        print(f"FAIL: Validation failed for {path}")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"PASS: {path} manifest structure and references are valid")

def publish(push=False):
    print("Open TAEDA Publisher v0.1")
    print("[1/4] Validate experiment manifests")
    validator = ManifestValidator(ROOT)
    manifests = sorted(MANIFESTS_DIR.glob("*.yaml"))
    if not manifests:
        print("Warning: No experiment manifests found in experiments/manifests/")
    for m in manifests:
        validate_manifest(m)
    
    print("[2/4] Build research database")
    db_init()
    
    print("[3/4] Git status")
    subprocess.run(["git", "status", "--short"], cwd=ROOT, check=False)
    
    print("[4/4] Publication status")
    if push:
        if not (ROOT / ".git").exists():
            raise SystemExit("Not a Git repository. Run git init and configure a GitHub remote first.")
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if status.returncode != 0:
            subprocess.run(["git", "commit", "-m", "research: publish validated platform state"], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
        print("Published successfully to GitHub main branch. GitHub Actions will validate the pushed revision.")
    else:
        print("Review changes, then confirm publication or run: ota publish --push")

def start_web_server(port: int = 8000):
    from website.server import run_server
    run_server(port=port)

def main():
    p = argparse.ArgumentParser(prog="ota", description="Open TAEDA Research Platform CLI")
    sp = p.add_subparsers(dest="cmd")
    
    sp.add_parser("init")
    t = sp.add_parser("technology"); t.add_argument("action", choices=["list"])
    d = sp.add_parser("design"); d.add_argument("action", choices=["list"])
    
    sp.add_parser("discover")
    sp.add_parser("collect")
    
    pr = sp.add_parser("publish-run")
    pr.add_argument("run_dir", help="Path to raw OpenLane run directory")
    pr.add_argument("--push", action="store_true", help="Push commit to GitHub remote")

    e = sp.add_parser("experiment")
    e.add_argument("action", choices=["validate"])
    e.add_argument("path")
    
    b = sp.add_parser("database")
    b.add_argument("action", choices=["init", "sync"])
    
    pub = sp.add_parser("publish")
    pub.add_argument("--push", action="store_true")

    w = sp.add_parser("web")
    w.add_argument("--port", type=int, default=8000, help="Port to run website server on (default 8000)")

    a = p.parse_args()
    
    if a.cmd in (None, "init"):
        print("Open TAEDA v0.1 initialized at", ROOT)
        db_init()
    elif a.cmd == "technology": list_registry("technology")
    elif a.cmd == "design": list_registry("design")
    elif a.cmd == "discover": discover_runs()
    elif a.cmd == "collect": collect_runs()
    elif a.cmd == "publish-run": publish_run(a.run_dir, a.push)
    elif a.cmd == "experiment": validate_manifest(a.path)
    elif a.cmd == "database": db_init()
    elif a.cmd == "publish": publish(a.push)
    elif a.cmd == "web": start_web_server(a.port)

if __name__ == "__main__":
    main()
