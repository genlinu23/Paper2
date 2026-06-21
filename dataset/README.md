# Reactor Agent Corpus DOI Dataset

This directory is a public, metadata-only manifest for the corpus used by the locked
Paper2 Reactor Agent run.

It contains DOI lists, corpus partition labels, chunk counts, and the paper-level
reaction-system labels used by the locked `v13-paper-reaction-system` run. It does
not contain PDFs, parsed full text, abstracts, conclusions, or chunk text.

## Files

| File | Rows | Description |
|---|---:|---|
| `doi_list_all_3611.csv` | 3,611 | DOI manifest for the full local corpus after Step1 metadata alignment. |
| `doi_list_kg_used_2497_with_reaction_system.csv` | 2,497 | DOI manifest for papers that contributed to the locked v8 KG paper-level reaction-system labeling. |
| `dataset_summary.json` | 1 | Machine-readable summary of counts, source paths, library distribution, class distribution, and reaction-system distribution. |

## Columns

`doi_list_all_3611.csv`

- `doc_id`: internal document id used by the local pipeline.
- `doi`: normalized DOI.
- `title`: title field available in the Step1 metadata. In this run many entries use the DOI as the title placeholder because the public manifest is DOI-centered.
- `lib`: source-library partition (`lib1` to `lib5`).
- `class_name`: source class (`classA` or `classB`).
- `chunk_count`: number of body chunks linked to the document.

`doi_list_kg_used_2497_with_reaction_system.csv`

- All columns above.
- `reaction_system`: normalized paper-level label used by v13 Step3 retrieval.
- `raw_reaction_system`: raw model label before normalization.
- `confidence`: paper-level classifier confidence.
- `status`: classifier status.

The public CSV intentionally excludes the model rationale and evidence snippets. The
full per-document classification cache is not published because it can contain
abstract/conclusion-derived text.

## Corpus Counts

Full Step1 corpus:

- Papers: 3,611
- Papers with DOI: 3,611
- Body chunks: 299,284
- Local parsed JSON files: 3,611
- Local PDF files in the source library: 4,262

Source-library partitions:

- `lib1`: 1,388
- `lib2`: 894
- `lib3`: 441
- `lib4`: 400
- `lib5`: 488

Source classes:

- `classA`: 3,469
- `classB`: 142

v8 paper-level reaction-system labels for KG-used papers:

- `CO2RR`: 1,092
- `CORR`: 104
- `both`: 43
- `other_reaction`: 899
- `non_reaction`: 156
- `unknown`: 203

## How The Local Corpus Was Built

The corpus was assembled locally before this public repository export.

Local source paths recorded for this run:

- PDF library:
  `C:\Users\logan\Desktop\project2_strict\strict_clean_v2\final_rule_based_ab_v1\library`
- Parsed JSON library:
  `C:\Users\logan\Desktop\project2_strict\strict_clean_v2\final_rule_based_ab_v1\membership_aligned_dataset_v1\source_json_flat`
- Chunk library:
  `C:\Users\logan\Desktop\project2_strict\strict_clean_v2\final_rule_based_ab_v1\membership_aligned_dataset_v1\chunk_run_v3\03_text_chunks`

The public repo keeps only the metadata manifest. To fully reproduce the raw corpus,
a user must provide equivalent PDF, parsed JSON, and chunk files, then update the
local paths or environment variables used by the pipeline.

## Library Selection And Keyword Signals

The Step1 batch configuration in `reactor_agent/steps/literature.py` uses:

- Libraries: `lib1`, `lib2`, `lib3`, `lib4`, `lib5`
- Classes: `classA`, `classB`

Topic signal keywords used by the Step1 literature code:

- Structure: `cell`, `electrode`, `membrane`, `separator`, `porous`, `flow field`, `GDE`, `PTL`, `AEM`
- Reaction: `reaction`, `cathode`, `anode`, `electrolysis`, `CO2`, `H2`, `OER`, `HER`
- Membrane: `membrane`, `separator`, `diaphragm`, `AEM`, `PEM`, `ion exchange`
- Feed: `feed`, `electrolyte`, `KOH`, `solution`, `gas`, `liquid`, `aerosol`
- Performance: `performance`, `Faradaic`, `selectivity`, `yield`, `current density`, `voltage`, `stability`
- Failure: `failure`, `flooding`, `dry`, `degradation`, `salt`, `block`, `short`, `crack`

Reactor relevance keep signals:

`reactor`, `electrolyzer`, `electrolysis`, `GDE`, `gas diffusion`,
`gas-diffusion`, `flow cell`, `flow-cell`, `membrane`, `bipolar membrane`,
`anion exchange membrane`, `AEM`, `PTL`, `PTFE`, `spray`, `flood`, `dry-out`,
`carbonation`, `crossover`, `diagnos`, `stability`, `durability`,
`selectivity`, `current density`, `Faradaic`

Drop signals used to reduce unrelated literature:

`photocatal`, `photocatalysis`, `photochemical`, `bio-inspired`, `wettability`,
`fog collection`, `crystallization`, `protein`, `enzyme`, `hydrogenase`,
`proton memory`, `superhydrophobic`, `corrosion`

These keyword lists are screening and topic signals, not final scientific labels.
The locked v13 reaction-system labels were assigned at paper level.

## Reaction-System Labeling Used By v13

The locked v13 run treats reaction system as a paper-level property:

1. Normalize each KG edge `source_doc_id` to its paper id.
2. Classify each paper with `gpt-5-mini` using title, abstract chunks, and conclusion/summary/outlook chunks.
3. Let KG edges inherit the paper-level label.
4. Override only reaction-independent pure transport, membrane, or mechanism edges to `transferable`.
5. Keep unrelated electrochemical reactions as `other_reaction`, not `transferable`.
6. Keep low-confidence cases as `unknown`.

The locked run is documented in `VERSION_LOCK_V13.md`.

## Reproducibility Boundary

This dataset lets readers audit the DOI set and the paper-level labels used in the
public v13 artifacts. It does not allow byte-for-byte reconstruction of the raw text
corpus because copyrighted PDFs, parsed full text, and chunk text are intentionally
not included.

For a full local rerun, provide equivalent raw libraries and use the commands and
locked artifact paths described in the repository root `README.md` and
`VERSION_LOCK_V13.md`.
