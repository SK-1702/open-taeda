# Open TAEDA v0.1 Data Model

## Core entities

Technology → PDK/Library → Flow → Design → Experiment → Stage → Metric

Experiment → Failure → Intervention → Outcome

Experiment → Artifact → Evidence → Claim → Publication

## Failure origin

DESIGN, TECHNOLOGY, PDK, LIBRARY, TOOL, FLOW, CONSTRAINT, ENVIRONMENT, UNKNOWN.

## Failure mechanism

SYNTHESIS, FLOORPLAN, POWER, PLACEMENT, CTS, ROUTING, RC, TIMING, POWER_ANALYSIS, DRC, LVS, ANTENNA, GDS, BUILD, MEMORY, PERFORMANCE.

## Intervention classification

A REAL_PHYSICAL_CORRECTION
B TOOL_OPTIMIZATION
C DESIGN_OR_FLOW_WORKAROUND
D CHECK_OR_REPAIR_DISABLED
E VERIFICATION_SCOPE_REDUCTION
F FAILURE_TERMINATION_RELAXATION
G PDK_DEFECT_CORRECTION
H TOOL_BUG_WORKAROUND
I ENVIRONMENT_CORRECTION

## Reproducibility levels

R0 undocumented; R1 metadata; R2 configuration; R3 environment; R4 artifacts; R5 independently reproduced.
