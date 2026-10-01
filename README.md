# Open TAEDA — Open Technology-Aware EDA Research Platform

Open TAEDA is an experimental research infrastructure for studying how semiconductor technology, design architecture, EDA flows, physical implementation, failures, interventions, and evidence interact.

## Initial research matrix

- Technologies: SKY130, ICsprout55, Nangate45, ASAP7, GT3, GT2N
- Designs: PicoRV32, SERV, Ibex
- Initial baseline population: 6 × 3 = 18 controlled experiment slots

GT3 and GT2N are classified as **research technology platforms** in v0.1. Their status should be upgraded only when the available collateral and validation justify it.

## Core invariant

> Every research claim must be traceable to an experiment, every experiment to its inputs and environment, every intervention to its justification, and every conclusion to evidence.

## Quick start

```bash
python3 -m ota init
python3 -m ota technology list
python3 -m ota design list
python3 -m ota experiment validate experiments/manifests/EXP-000001.yaml
python3 -m ota database init
```

The CLI is intentionally lightweight in v0.1. The RTL-to-GDS execution adapters are extension points under `engine/runner/`.

## Publication

```bash
ota publish
```

The publication workflow validates schemas, rebuilds the SQLite research database, verifies provenance metadata, commits metadata, and pushes to GitHub. Large experiment artifacts should be handled through an artifact/versioning layer rather than committed directly to Git.

## Repository

See `docs/architecture/ARCHITECTURE.md` for the v0.1 architecture and `docs/architecture/DATA_MODEL.md` for the ontology and relational model.
