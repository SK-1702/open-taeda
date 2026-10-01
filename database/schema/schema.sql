PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS technologies (
  technology_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  node_nm REAL,
  device_architecture TEXT,
  device_type TEXT,
  status TEXT NOT NULL,
  validation_level TEXT,
  revision TEXT
);
CREATE TABLE IF NOT EXISTS designs (
  design_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  top_module TEXT,
  repository TEXT,
  revision TEXT,
  license TEXT
);
CREATE TABLE IF NOT EXISTS flows (
  flow_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT,
  repository TEXT,
  revision TEXT,
  container_image TEXT
);
CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY,
  campaign_id TEXT,
  name TEXT NOT NULL,
  design_id TEXT NOT NULL REFERENCES designs(design_id),
  technology_id TEXT NOT NULL REFERENCES technologies(technology_id),
  flow_id TEXT REFERENCES flows(flow_id),
  parent_experiment_id TEXT REFERENCES experiments(experiment_id),
  experiment_type TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  configuration_hash TEXT
);
CREATE TABLE IF NOT EXISTS stages (
  stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
  experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
  stage_name TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  status TEXT NOT NULL,
  tool_id TEXT,
  command_hash TEXT,
  started_at TEXT,
  completed_at TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
  metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
  experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
  stage_id INTEGER REFERENCES stages(stage_id),
  name TEXT NOT NULL,
  value REAL,
  unit TEXT,
  source TEXT,
  confidence TEXT
);
CREATE TABLE IF NOT EXISTS failures (
  failure_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
  stage_id INTEGER REFERENCES stages(stage_id),
  origin TEXT NOT NULL,
  mechanism TEXT NOT NULL,
  signature TEXT,
  severity TEXT,
  root_cause_class TEXT,
  confidence TEXT
);
CREATE TABLE IF NOT EXISTS interventions (
  intervention_id TEXT PRIMARY KEY,
  failure_id TEXT REFERENCES failures(failure_id),
  type TEXT NOT NULL,
  description TEXT,
  classification TEXT NOT NULL,
  before_state TEXT,
  after_state TEXT,
  result TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
  type TEXT NOT NULL,
  artifact_path TEXT,
  artifact_sha256 TEXT,
  location TEXT,
  claim TEXT,
  confidence TEXT
);
CREATE TABLE IF NOT EXISTS publications (
  publication_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  venue TEXT,
  doi TEXT,
  date TEXT,
  status TEXT
);
CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  publication_id TEXT REFERENCES publications(publication_id),
  statement TEXT NOT NULL,
  claim_type TEXT,
  status TEXT,
  confidence TEXT
);
CREATE TABLE IF NOT EXISTS claim_evidence (
  claim_id TEXT NOT NULL REFERENCES claims(claim_id),
  evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
  PRIMARY KEY (claim_id, evidence_id)
);
