# Paper-Level Reaction-System KG Report

- Base KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges`
- Output KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v8_paper_reaction_system`
- Papers classified: 2497
- Nodes: 32619
- Edges: 21833
- Missing edge `reaction_system`: 0

## Paper Distribution

| label | papers |
|---|---:|
| CO2RR | 1092 |
| CORR | 104 |
| both | 43 |
| non_reaction | 156 |
| other_reaction | 899 |
| unknown | 203 |

## Edge Distribution

| label | edges |
|---|---:|
| CO2RR | 9590 |
| CORR | 872 |
| other_reaction | 7892 |
| transferable | 597 |
| unknown | 2882 |

## Inheritance Distribution

| paper label -> edge label | edges |
|---|---:|
| CO2RR->CO2RR | 9590 |
| CORR->CORR | 872 |
| both->transferable | 394 |
| non_reaction->transferable | 203 |
| non_reaction->unknown | 1160 |
| other_reaction->other_reaction | 7892 |
| unknown->unknown | 1722 |
