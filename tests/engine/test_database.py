import sqlite3
import pytest
from pathlib import Path
from engine.comparator import DatabaseManager

ROOT = Path(__file__).resolve().parents[2]

def test_database_init_and_sync(tmp_path):
    test_db = tmp_path / "test_ota.db"
    db_mgr = DatabaseManager(test_db)
    db_mgr.sync_manifests()
    
    assert test_db.exists()
    con = sqlite3.connect(test_db)
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM technologies")
    tech_count = cur.fetchone()[0]
    assert tech_count >= 6
    con.close()
