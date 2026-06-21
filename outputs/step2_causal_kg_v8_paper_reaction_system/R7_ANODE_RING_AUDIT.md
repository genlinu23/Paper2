# R7 Pt@PTL Anode Ring Audit

Conclusion: the local Step2 re-extraction found additional HOR/H2 anode evidence in the existing corpus, but it did not connect the specific `Pt@PTL anode -> HOR/H2/KOH aerosol -> performance` ring. This ring remains an evidence gap in the current corpus/KG, not a Step3 retrieval miss.

## Inputs

- Step1 corpus: `C:\Users\logan\reactor_agent\outputs\step1_run_ready_v1_full`
- Base KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v5_corr_edges`
- Re-extracted KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges`
- R7 validation output: `C:\Users\logan\reactor_agent\outputs\step3_reasoning_v9_anode_edges`

## Re-extraction Result

- Selected HOR/Pt@PTL-anode candidate docs: 67
- Base KG: 31913 nodes / 21274 edges
- Raw local anode extraction: 1244 nodes / 665 edges
- v6 normalized KG: 32619 nodes / 21833 edges
- New edges after merge: 559
- New traceable edges: 559 / 559
- New broad HOR/H2/anode-ring related edges: 136
- Failures: 0
- Discarded edges: 0

## Selector Findings

- Direct `HOR + anode` docs: 51
- Cross-fact `HOR + H2/anode` docs: 57
- Paired electrolysis/H2-anode docs: 10
- Direct `Pt@PTL` / `Pt porous transport layer` anode hits in Step1 facts: 0
- `KOH aerosol/spray + H2 anode` hits in Step1 facts: 0

## KG Chain Status After v6

The v6 KG still has only one Pt@PTL-like ring node:

- `Anode:Pt_RuO2_catalyst_on_titanium_felt_PTL`

Its incident edges remain:

- `Failure_Mode:Ru_ion_leaching_from_undoped_RuO2_catalyst -> Anode:Pt_RuO2_catalyst_on_titanium_felt_PTL`, `caused_by`, `doc_2030`, `doc_2030_chunk_186241`
- `Reactor:PEM_electrolyzer_with_4_cm2_active_area -> Anode:Pt_RuO2_catalyst_on_titanium_felt_PTL`, `has_component`, `doc_2030`, `doc_2030_chunk_186290`

No new edge connects this node to HOR, H2 feed, KOH aerosol/spray, CORR/CO reduction, or performance.

## R7 Step3 Validation Against v6 KG

- R7 KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges`
- R7 context edges: 80
- R7 context nodes: 101
- Evidence counts: `corr_terms=6`, `co2rr_terms=7`

Chain completion status:

| from | to | status | edge count |
|---|---|---|---:|
| CO feed | CORR/CO reduction | completed_from_kg | 1 |
| CORR/CO reduction | Cu@carbon-paper cathode | completed_from_kg | 1 |
| CORR/CO reduction | Pt@PTL anode | not_found_in_kg_within_3_hops | 0 |
| CORR/CO reduction | porous PTFE diaphragm | completed_from_kg | 2 |
| Cu@carbon-paper cathode | stability/performance | completed_from_kg | 1 |
| Pt@PTL anode | stability/performance | not_found_in_kg_within_3_hops | 0 |
| porous PTFE diaphragm | stability/performance | completed_from_kg | 1 |
| CO feed | stability/performance | completed_from_kg | 1 |

## Classification

Classification: **(b) true evidence gap for the specific Pt@PTL/HOR/KOH aerosol anode ring**.

Reason: re-extraction did recover additional HOR/H2 anode evidence from the existing corpus, including Pt/C HOR and H2-to-anode edges, but the existing corpus/KG still does not contain a traceable causal chain connecting `Pt@PTL anode` to HOR/H2/KOH aerosol and performance. The recovered evidence supports broader HOR/H2 anode chemistry, not the specific R7 `Pt@PTL` architecture.

## Verification

- `kg_summary.json`: 21833 / 21833 edges traceable
- `failures.json`: `[]`
- `discarded_edges.json`: `[]`
- Full test suite: `27 passed`
- Forced-answer static check: no matches for `ROUND_STRUCTURE_CONSTRAINTS`, `corr_bonus`, `co2_penalty`, `r7_bad_cathode_co2`, `must feed CO`, or `must contain CORR`
- Secret scan over v6 and Step3 v9 outputs: no provided API key string found
