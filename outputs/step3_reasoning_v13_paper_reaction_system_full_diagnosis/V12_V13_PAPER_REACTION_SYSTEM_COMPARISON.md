# Step3 v12 vs v13 Reaction-System Label Comparison

## Conclusion

v13 uses the corrected paper-level reaction-system labels. It is not a repeat of v12.

- v8 KG labels papers first with `gpt-5-mini`, then lets edges inherit the paper label.
- v13 Step3 uses v8 KG and records `reaction_system_counts` in every `D3_context.json` and `run_config.json`.
- R5 and R7 now explicitly produce CO/CORR-side outputs: R5 cathode feed is `CO`; R7 cathode feed is `CO`.
- Compared with v12 edge-level heuristic labels, v13 is stricter and more article-faithful. It selects fewer CORR-labeled edges in some rounds because paper-level CORR papers are much fewer than edge-level keyword hits.

## KG Labeling Method

v12 used edge-text rules. v13 does not.

For v13:

1. Normalize KG source ids to paper ids.
   - Raw distinct `source_doc_id` values in v6 KG: 2537.
   - 49 of those are chunk-like ids such as `doc_0368_chunk_...`.
   - Normalized distinct paper ids: 2497.
2. For each paper, feed `gpt-5-mini`:
   - title
   - abstract chunks
   - conclusion / summary / outlook chunks
3. Assign one paper-level label:
   - `CO2RR`
   - `CORR`
   - `both`
   - `other_reaction`
   - `non_reaction`
   - `unknown`
4. Edges inherit the label via `source_doc_id` -> normalized `paper_doc_id`.
5. Edge override is only used for non-reaction papers:
   - pure transport / membrane / mechanism edge with no reaction words -> `transferable`
   - unrelated reaction papers stay `other_reaction`, not `transferable`

## v8 KG Distribution

| paper label | papers |
|---|---:|
| CO2RR | 1092 |
| CORR | 104 |
| both | 43 |
| non_reaction | 156 |
| other_reaction | 899 |
| unknown | 203 |

| edge label | edges |
|---|---:|
| CO2RR | 9590 |
| CORR | 872 |
| transferable | 597 |
| other_reaction | 7892 |
| unknown | 2882 |

Total edges: 21833. Missing `reaction_system`: 0.

## Step3 Inputs

| item | v12 | v13 |
|---|---|---|
| KG | `step2_causal_kg_v7_reaction_system` | `step2_causal_kg_v8_paper_reaction_system` |
| Label source | edge-text rules | paper-level `gpt-5-mini` labels |
| Diagnosis mode | full | full |
| Output | `step3_reasoning_v12_reaction_system_full_diagnosis` | `step3_reasoning_v13_paper_reaction_system_full_diagnosis` |

## Round-Level Step3 Comparison

| round | v12 CORR/CO2 terms | v13 CORR/CO2 terms | v12 selected systems | v13 selected systems | v12 feeds | v13 feeds |
|---|---:|---:|---|---|---|---|
| R1 | 3/21 | 6/63 | CO2RR=7, CORR=1, transferable=66, other=0, unknown=6 | CO2RR=24, CORR=1, transferable=31, other=16, unknown=8 | cathode=`CO2`, anode=`H2` | cathode=`CO2`, anode=`H2` |
| R2 | 7/13 | 2/61 | CO2RR=4, CORR=7, transferable=65, other=0, unknown=4 | CO2RR=24, CORR=0, transferable=45, other=10, unknown=1 | cathode=`CO2`, anode=`H2` | cathode=`CO2`, anode=`not specified` |
| R3 | 6/26 | 8/45 | CO2RR=6, CORR=6, transferable=56, other=0, unknown=12 | CO2RR=16, CORR=3, transferable=37, other=19, unknown=5 | cathode=`CO`, anode=`H2` | cathode=`CO2`, anode=`not specified` |
| R4 | 6/25 | 4/53 | CO2RR=10, CORR=6, transferable=53, other=0, unknown=11 | CO2RR=19, CORR=1, transferable=38, other=17, unknown=5 | cathode=`CO2`, anode=`not specified` | cathode=`CO2`, anode=`not specified` |
| R5 | 33/12 | 37/47 | CO2RR=3, CORR=24, transferable=49, other=0, unknown=4 | CO2RR=19, CORR=15, transferable=27, other=11, unknown=8 | cathode=`CO`, anode=`H2` | cathode=`CO`, anode=`H2` |
| R6 | 33/11 | 33/39 | CO2RR=3, CORR=26, transferable=47, other=0, unknown=4 | CO2RR=14, CORR=14, transferable=24, other=10, unknown=18 | cathode=`CO`, anode=`H2` | cathode=`not specified`, anode=`H2` |
| R7 | 41/16 | 66/67 | CO2RR=6, CORR=37, transferable=35, other=0, unknown=2 | CO2RR=24, CORR=32, transferable=6, other=15, unknown=3 | cathode=`not specified`, anode=`H2` | cathode=`CO`, anode=`not specified` |

## Interpretation

v13 is more methodologically correct because reaction system is a paper property. It also changes the scientific interpretation:

- The paper-level corpus is CO2RR-heavy: 1092 CO2RR papers vs 104 CORR papers.
- Some v12 CORR enrichment came from edge-level keyword matching and transferable edge inflation.
- Even under stricter paper-level labels, R5 and R7 still recover CO/CORR outputs. That is stronger evidence that the CORR direction is not merely a keyword artifact.
- R6 remains incomplete in feed specificity, so the remaining weakness is not solved by paper-level tags alone.

## Verification

- v13 is a formal agent rerun, not `quality-only`.
- v13 `run_config.kg_dir` points to `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v8_paper_reaction_system`.
- Every v13 round has `D3_memo`, `D3_build_sheet`, `D3_context`, and `run_config`.
- Every selected context records non-missing `reaction_system_counts`.
