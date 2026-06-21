# Reactor Agent Version Lock: v13 Paper-Level Reaction-System Run

Locked version: `v13-paper-reaction-system`

## What Is Locked

This version locks the corrected paper-level reaction-system labeling pipeline and the corresponding Step3 run.

## Key Artifacts

- Paper-level labeled KG:
  - `outputs/step2_causal_kg_v8_paper_reaction_system`
- Step3 run:
  - `outputs/step3_reasoning_v13_paper_reaction_system_full_diagnosis`
- KG paper-label report:
  - `outputs/step2_causal_kg_v8_paper_reaction_system/PAPER_REACTION_SYSTEM_REPORT.md`
- Step3 comparison report:
  - `outputs/step3_reasoning_v13_paper_reaction_system_full_diagnosis/V12_V13_PAPER_REACTION_SYSTEM_COMPARISON.md`

## Reaction-System Labeling Method

Reaction system is treated as a paper-level property.

1. Normalize edge `source_doc_id` to paper id.
2. Classify each paper with `gpt-5-mini` using title, abstract chunks, and conclusion/summary/outlook chunks.
3. Let edges inherit the paper-level label.
4. Override only non-reaction paper edges to `transferable` when the edge is pure transport / membrane / mechanism and has no reaction words.
5. Keep unrelated reaction papers as `other_reaction`, not `transferable`.

## v8 KG Distribution

Paper labels:

- `CO2RR`: 1092
- `CORR`: 104
- `both`: 43
- `other_reaction`: 899
- `non_reaction`: 156
- `unknown`: 203

Edge labels:

- `CO2RR`: 9590
- `CORR`: 872
- `transferable`: 597
- `other_reaction`: 7892
- `unknown`: 2882
- missing `reaction_system`: 0

## v13 Step3 Result

Inputs:

- KG: `outputs/step2_causal_kg_v8_paper_reaction_system`
- Diagnosis mode: `full`
- Model role/name recorded in run configs: `reasoning` / `gpt-5.4`

Key outputs:

- R5 cathode feed: `CO`
- R7 cathode feed: `CO`
- R7 selected reaction-system counts:
  - `CO2RR`: 24
  - `CORR`: 32
  - `transferable`: 6
  - `other_reaction`: 15
  - `unknown`: 3
  - `MISSING`: 0

## Verification

Before locking:

- `python -m pytest C:\Users\logan\reactor_agent\tests -q`
  - `32 passed`
- `py_compile` passed for changed Python files.
- Static forced-answer check had no matches for:
  - `ROUND_STRUCTURE_CONSTRAINTS`
  - `corr_bonus`
  - `co2_penalty`
  - `r7_bad_cathode_co2`
  - `must feed CO`
  - `must contain CORR`

## Notes

The previous v12 edge-level reaction-system labels are superseded by v13 because v12 treated reaction system as an edge-text property. v13 treats it as a paper property and is the locked version.
