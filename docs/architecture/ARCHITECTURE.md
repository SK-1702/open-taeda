# Open TAEDA v0.1 Architecture

Open TAEDA is organized around reproducible experiments linking technology, design, EDA flow, physical outcomes, failures, interventions, evidence, models and eventually an evidence-grounded agent.

## Four truths

1. Design Truth — what the RTL/design contains.
2. Technology Truth — what the technology and library collateral actually provide.
3. Tool Truth — what the EDA software actually executed and reported.
4. Physical/Experimental Truth — what implementation and verification actually produced.

## Initial matrix

6 technologies × 3 designs = 18 baseline slots.

Technologies: SKY130, ICsprout55, Nangate45, ASAP7, GT3, GT2N.
Designs: PicoRV32, SERV, Ibex.

## One-click publication

`ota publish` validates experiment manifests, initializes/rebuilds the local research database, shows Git status, and prepares the repository for publication. The CI workflow performs validation after push.

Large artifacts should not be committed directly to Git. Use an artifact/versioning layer such as DVC/object storage, with only manifests, hashes and selected small artifacts in Git.
