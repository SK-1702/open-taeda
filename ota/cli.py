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
        # Skip empty or uninformative runs if needed, or ingest all valid runs
        manifest = normalizer.build_manifest(r)
        out_path = normalizer.save_manifest(manifest)
        generated.append(out_path)
        print(f"Generated manifest: {out_path.name} for run {r.name} ({status})")
    print(f"Successfully generated {len(generated)} experiment manifests in {MANIFESTS_DIR}")

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

def main():
    p = argparse.ArgumentParser(prog="ota", description="Open TAEDA Research Platform CLI")
    sp = p.add_subparsers(dest="cmd")
    
    sp.add_parser("init")
    t = sp.add_parser("technology"); t.add_argument("action", choices=["list"])
    d = sp.add_parser("design"); d.add_argument("action", choices=["list"])
    
    sp.add_parser("discover")
    sp.add_parser("collect")
    
    e = sp.add_parser("experiment")
    e.add_argument("action", choices=["validate"])
    e.add_argument("path")
    
    b = sp.add_parser("database")
    b.add_argument("action", choices=["init", "sync"])
    
    pub = sp.add_parser("publish")
    pub.add_argument("--push", action="store_true")
    
    a = p.parse_args()
    
    if a.cmd in (None, "init"):
        print("Open TAEDA v0.1 initialized at", ROOT)
        db_init()
    elif a.cmd == "technology": list_registry("technology")
    elif a.cmd == "design": list_registry("design")
    elif a.cmd == "discover": discover_runs()
    elif a.cmd == "collect": collect_runs()
    elif a.cmd == "experiment": validate_manifest(a.path)
    elif a.cmd == "database": db_init()
    elif a.cmd == "publish": publish(a.push)

if __name__ == "__main__":
    main()
