# reactor_agent

Locked Reactor workflow implementation and artifacts for Paper2.

Current locked version: `v13-paper-reaction-system`.

See `VERSION_LOCK_V13.md` for the exact locked KG, Step3 run, reaction-system distributions, and verification checks.

Key locked artifacts:

- `outputs/step2_causal_kg_v8_paper_reaction_system`
- `outputs/step3_reasoning_v13_paper_reaction_system_full_diagnosis`

Step 1 implementation for the Reactor workflow.

Project rule: no substitute paths are allowed. Missing inputs, metadata, or LLM integration must fail explicitly.

## Step 1 anchors

Validate the 8 anchor papers without calling the LLM:

```powershell
python -m reactor_agent.steps.literature --step1-anchors --join-only --out-dir C:\Users\logan\reactor_agent\outputs\step1_anchor_join_only
```

Run real fact extraction after setting `VECTORENGINE_API_KEY`:

```powershell
$env:VECTORENGINE_API_KEY = "<key>"
python -m reactor_agent.steps.literature --step1-anchors --out-dir C:\Users\logan\reactor_agent\outputs\step1_anchor_llm
```

Main outputs:

- `chunk_join_manifest.json`
- `core_papers.json`
- `paper_facts.json` when LLM extraction succeeds
- `D1_summary.md` when LLM extraction succeeds

## Step 2 KG

Run Step 2 KG extraction from Step 1 facts:

```powershell
python -m reactor_agent.steps.kg --step1-dir C:\Users\logan\reactor_agent\outputs\step1_batch_lib1_5_ab_full --filtered-core <filtered_core.json> --out-dir C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2
```

By default, Step 2 now writes both the KG data files and the interactive visualization bundle:

- `kg_nodes.json`
- `kg_edges.json`
- `kg_summary.json`
- `kg_causal_view.html`
- `kg_causal_snapshot.svg`
- `viz\index.html`
- `viz\overview.html`

Optional flags:

```powershell
--skip-viz          # do not generate viz\index.html
--viz-max-full 400 # maximum nodes in viz\overview.html
```

Regenerate visualization only from an existing KG:

```powershell
python -m reactor_agent.steps.kg_visualize --kg_dir C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2 --out C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2\viz --max_full 400
```
