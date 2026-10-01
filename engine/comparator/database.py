import sqlite3
import yaml
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "ota.db"
SCHEMA_PATH = ROOT / "database" / "schema" / "schema.sql"
SEED_PATH = ROOT / "database" / "seed" / "seed.sql"
MANIFESTS_DIR = ROOT / "experiments" / "manifests"

class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)

    def init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.executescript(SCHEMA_PATH.read_text())
        if SEED_PATH.exists():
            cur.executescript(SEED_PATH.read_text())
        con.commit()
        con.close()

    def sync_manifests(self):
        self.init_db()
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()

        manifest_files = sorted(MANIFESTS_DIR.glob("*.yaml"))
        for mfile in manifest_files:
            with open(mfile, "r") as f:
                data = yaml.safe_load(f)
            if not data or not isinstance(data, dict):
                continue
            
            exp = data.get("experiment", {})
            exp_id = exp.get("id")
            if not exp_id:
                continue

            des = data.get("design", {})
            tech = data.get("technology", {})
            flow = data.get("flow", {})
            status = data.get("status", "UNKNOWN")
            cfg = data.get("configuration", {})

            # Upsert experiment record including parent_experiment_id
            cur.execute("""
                INSERT OR REPLACE INTO experiments 
                (experiment_id, campaign_id, name, design_id, technology_id, flow_id, parent_experiment_id, experiment_type, status, configuration_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp_id,
                exp.get("campaign", "TAEDA-CROSS-PDK"),
                exp.get("name", exp_id),
                des.get("id", "DES-001"),
                tech.get("id", "sky130"),
                "FLOW-001",
                exp.get("parent_experiment"),
                exp.get("type", "baseline"),
                status,
                cfg.get("config_hash")
            ))

            # Delete old related records for clean sync
            cur.execute("DELETE FROM stages WHERE experiment_id = ?", (exp_id,))
            cur.execute("DELETE FROM metrics WHERE experiment_id = ?", (exp_id,))
            cur.execute("DELETE FROM failures WHERE experiment_id = ?", (exp_id,))
            cur.execute("DELETE FROM evidence WHERE experiment_id = ?", (exp_id,))

            # Sync stages
            stages = data.get("stages", {})
            seq = 1
            for stage_name, stage_info in stages.items():
                st_stat = stage_info.get("status", "NOT_RUN") if isinstance(stage_info, dict) else str(stage_info)
                cur.execute("""
                    INSERT INTO stages (experiment_id, stage_name, sequence, status)
                    VALUES (?, ?, ?, ?)
                """, (exp_id, stage_name, seq, st_stat))
                seq += 1

            # Sync metrics
            metrics = data.get("metrics", {})
            for m_name, m_val in metrics.items():
                if isinstance(m_val, (int, float)):
                    cur.execute("""
                        INSERT INTO metrics (experiment_id, name, value, source)
                        VALUES (?, ?, ?, ?)
                    """, (exp_id, m_name, float(m_val), "manifest"))

            # Sync failure if present
            fail = data.get("failure")
            if fail and isinstance(fail, dict):
                fail_id = f"FAIL-{exp_id}"
                cur.execute("""
                    INSERT OR REPLACE INTO failures (failure_id, experiment_id, origin, mechanism, root_cause_class)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    fail_id,
                    exp_id,
                    fail.get("origin", "UNKNOWN"),
                    fail.get("mechanism", "UNKNOWN"),
                    fail.get("root_cause_class", "UNKNOWN")
                ))

            # Sync evidence
            ev = data.get("evidence", {})
            for ev_k, ev_v in ev.items():
                if ev_v:
                    ev_id = f"EV-{exp_id}-{ev_k}"
                    cur.execute("""
                        INSERT OR REPLACE INTO evidence (evidence_id, experiment_id, type, location)
                        VALUES (?, ?, ?, ?)
                    """, (ev_id, exp_id, ev_k, str(ev_v)))

        con.commit()
        con.close()
