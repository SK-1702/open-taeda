import argparse, json, os, sqlite3, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "ota.db"

SCHEMA = ROOT / "database" / "schema" / "schema.sql"

def db_init():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text())
    seed = ROOT / "database" / "seed" / "seed.sql"
    if seed.exists():
        con.executescript(seed.read_text())
    con.commit(); con.close()
    print(f"Initialized {DB}")

def list_registry(kind):
    path = ROOT / ("technologies" if kind == "technology" else "designs")
    print(f"{kind.title()}s:")
    for p in sorted(path.iterdir()):
        if p.is_dir():
            print(f"  - {p.name}")

def validate(path):
    try:
        import yaml
    except ImportError:
        print("PyYAML is not installed; basic validation only.")
        txt = Path(path).read_text()
        for required in ("schema_version:", "experiment:", "design:", "technology:", "flow:", "stages:"):
            if required not in txt:
                raise SystemExit(f"Validation failed: missing {required}")
        print("PASS: required experiment sections found")
        return
    data = yaml.safe_load(Path(path).read_text())
    required = ["schema_version", "experiment", "design", "technology", "flow", "stages"]
    missing = [k for k in required if k not in data]
    if missing: raise SystemExit("Validation failed: " + ", ".join(missing))
    print("PASS: experiment manifest structure is valid")

def publish(push=False):
    print("Open TAEDA Publisher v0.1")
    print("[1/4] Validate experiment manifests")
    manifests = sorted((ROOT/"experiments"/"manifests").glob("*.yaml"))
    for m in manifests: validate(m)
    print("[2/4] Build research database")
    db_init()
    print("[3/4] Git status")
    subprocess.run(["git", "status", "--short"], cwd=ROOT, check=False)
    print("[4/4] Publication ready")
    if push:
        if not (ROOT / ".git").exists():
            raise SystemExit("Not a Git repository. Run git init and configure a GitHub remote first.")
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if status.returncode != 0:
            subprocess.run(["git", "commit", "-m", "research: publish validated platform state"], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
        print("Published to configured Git remote. GitHub Actions will validate the pushed revision.")
    else:
        print("Review changes, then run: ota publish --push")

def main():
    p=argparse.ArgumentParser(prog="ota")
    sp=p.add_subparsers(dest="cmd")
    sp.add_parser("init")
    t=sp.add_parser("technology"); t.add_argument("action", choices=["list"])
    d=sp.add_parser("design"); d.add_argument("action", choices=["list"])
    e=sp.add_parser("experiment"); e.add_argument("action", choices=["validate"]); e.add_argument("path")
    b=sp.add_parser("database"); b.add_argument("action", choices=["init"])
    pub=sp.add_parser("publish"); pub.add_argument("--push", action="store_true")
    a=p.parse_args()
    if a.cmd in (None, "init"):
        print("Open TAEDA v0.1 initialized at", ROOT); db_init()
    elif a.cmd=="technology": list_registry("technology")
    elif a.cmd=="design": list_registry("design")
    elif a.cmd=="experiment": validate(a.path)
    elif a.cmd=="database": db_init()
    elif a.cmd=="publish": publish(a.push)

if __name__ == "__main__": main()
