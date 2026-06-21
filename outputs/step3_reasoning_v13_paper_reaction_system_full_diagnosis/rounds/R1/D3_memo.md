# D3 Recommendation Memo - R1

Primary bottleneck: Excessive ohmic impedance caused by a thick solid-electrolyte/ionic transport path.
Hypothesis: Because the diagnosed bottleneck is excessive ohmic impedance from a thick solid-electrolyte path, the most evidence-grounded next step is to convert the reactor toward a zero-gap AEM membrane-electrode assembly so anions traverse a much shorter path. In this architecture, the AEM provides the ionic pathway, while the porous PTFE layer is limited to gas-side distribution and hydrophobic gas-liquid-solid interface control. KG evidence supports AEM-containing MEA reactors as a compact architecture and supports porous PTFE for improved CO2 delivery, improved CO2 diffusion, and persistent hydrophobicity, but also warns that porous PTFE/ePTFE can cause severe ohmic losses if it remains part of the main ionic transport thickness.

## New Architecture
Zero-gap AEM membrane-electrode assembly in which the cathode is membrane-adjacent for short anion transport, paired with a porous PTFE gas-side diffusion/separator layer that preserves hydrophobic gas access but is excluded from the main ionic conduction thickness.

## Design Changes
- Shift from a thick electrolyte-separated configuration to a zero-gap membrane-electrode assembly using an AEM with the cathode pressed directly against the membrane, while retaining a porous PTFE gas-diffusion/separator layer on the gas side for gas-aerosol-solid contacting.

## Rationale
This is a gradual convergence step, not a final-system claim. The diagnosis points directly to path-length-limited ionic resistance. The KG contains zero-gap membrane-electrode assembly and MEA/AEM reactor motifs, which are the closest evidence-backed route to shorten transport distance. For the six transport functions: (1) ion transport: benefit expected because the AEM becomes the short anion-conducting path in a zero-gap geometry, replacing a thick electrolyte path; risk is low only if PTFE is not left in the ionic path because PTFE itself is not the ion conductor. (2) water management: porous PTFE is evidence-backed for persistent hydrophobicity and can help resist water invasion, but flooding is still a documented risk and must be monitored. (3) gas access: porous PTFE is linked to improved CO2 delivery and improved CO2 diffusion, so keeping it on the gas side should preserve gas-liquid-solid contacting. (4) cation availability: no KG evidence supports AEM transport of K+; therefore the design should be interpreted as anion-transport-dominant, with any cathode cation environment arising from local electrolyte/contacting rather than membrane transport. (5) ohmic loss: strong expected benefit from shortening the AEM/electrolyte path; strong risk if ePTFE thickness remains electrically/ionically rate-limiting, since severe ohmic losses were reported for ePTFE electrodes at larger sizes. (6) mechanical stability: MEA/AEM assemblies with PTFE gaskets and porous transport layers provide a traceable compact structure, while porous PTFE shows persistent hydrophobicity and stable operation in cited contexts; however rapid decay and flooding have also been reported in related PTFE-containing systems, so durability is conditional rather than guaranteed.

## Expected Improvement
Primary expected gain is lower ohmic loss from a shorter anion-transport path through the AEM-based zero-gap geometry, with retained gas access from the porous PTFE layer. This should reduce cell resistance/overpotential and improve stable current density relative to the thick-path baseline, provided flooding remains controlled.

## Risks
- Porous PTFE diaphragm/ePTFE elements are linked to severe ohmic losses at larger sizes if they remain in the effective ionic path.
- Flooding risk remains associated with porous PTFE and carbon-paper-type gas diffusion structures.
- Porous PTFE diaphragm is linked to rapid decay of catalytic activity in some CO2RR contexts, so stability must be checked rather than assumed.
- If KOH-containing operation is used to lower overpotential, KG also flags electrolyte instability from KOH and CO2 reaction and alkaline salting risks.

## Minimum Experiment
- Assemble a single zero-gap AEM-MEA cell using the same catalysts as baseline, with AEM as the anion-conducting separator and a porous PTFE gas-side layer only for gas distribution/hydrophobic separation.
- Use the same CO2 feed and electrolyte as baseline to isolate architecture as the only variable.
- Collect EIS/HFR, polarization, and short stability data, plus flooding indicators and product/selectivity readouts.

## Discriminating Test
- Build matched cells that differ only in spacing architecture: current thick-path baseline versus zero-gap AEM-MEA with the same catalyst set and same gas feed.
- Measure high-frequency resistance / impedance and full cell voltage at fixed current density under identical CO2 flow and electrolyte conditions.
- Track flooding/wetting by gas-side pressure drop or visual breakthrough together with FE/current stability to verify that lower resistance is not offset by gas-access collapse.

## Diagnostic Trigger
- Baseline diagnosis identifies excessive ohmic impedance from a thick solid-electrolyte transport path.
- KG evidence links porous PTFE diaphragms/ePTFE electrodes to severe ohmic losses at larger sizes, so PTFE should be kept as a gas-side porous separator/path rather than the main ionic conduction path.
- The next step must shorten ion-transport distance while preserving gas access and mechanical stability.

Go/No-Go: Go if the zero-gap AEM-MEA reduces HFR/cell voltage materially versus baseline at the same current density while maintaining stable gas access and no rapid flooding. No-go if resistance does not drop, or if the PTFE gas-side layer introduces persistent flooding/rapid decay that erases the voltage benefit.

## Literature
- doc_2431 | 10.1038/s41467-024-53523-8 | Hierarchically conductive electrodes unlock stable and scalable CO2 electrolysis
- doc_1944 | 10.1038/s41467-023-38138-9 | Hierarchical triphase diffusion photoelectrodes for photoelectrochemical gas/liquid flow conversion
- doc_1754 | 10.1016/j.joule.2021.02.005 | Hydrophobicity of CO2 gas diffusion electrodes
- doc_2575 | 10.1016/j.joule.2021.02.005 | Hydrophobicity of CO2 gas diffusion electrodes

Score: 0.83

Referenced nodes: 100
Referenced edges: 80
