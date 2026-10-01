# Experiment Lifecycle

CREATE → VALIDATE → RESOLVE INPUTS → FREEZE ENVIRONMENT → EXECUTE → COLLECT → PARSE → NORMALIZE → VALIDATE RESULTS → CLASSIFY FAILURES → REGISTER INTERVENTIONS → GENERATE EVIDENCE → COMMIT METADATA → PUBLISH.

Experiments are immutable. A changed configuration creates a new experiment with a parent reference where appropriate.
