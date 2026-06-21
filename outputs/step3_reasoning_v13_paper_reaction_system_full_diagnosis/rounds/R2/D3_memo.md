# D3 Recommendation Memo - R2

Primary bottleneck: A persistent cathode-side liquid film that couples flooding, pressure imbalance, unstable gas transport, and added effective resistance.
Hypothesis: The remaining bottleneck is not bulk ionic conduction alone but the continuous cathode liquid film. Replacing that film with a hydrophobically confined gas-aerosol-solid contacting layer using a porous PTFE diaphragm should interrupt persistent flooding pathways, maintain gas access, and keep ion transport localized through the porous solid-electrolyte path, thereby reducing extra resistance and pressure imbalance.

## New Architecture
A gradual convergence from the prior porous solid-electrolyte reactor toward a cathode-side gas-aerosol-solid contacting PSE architecture: Nafion-117/porous solid electrolyte remain the ion-transport backbone, while a hydrophobic porous PTFE diaphragm defines the gas-access side and suppresses a persistent flooded liquid layer.

## Design Changes
- Replace the persistent cathode-side liquid electrolyte film with a gas-aerosol-solid contacting interface built around a hydrophobic porous PTFE diaphragm/gas path layer coupled to the existing porous solid-electrolyte transport path.

## Rationale
This recommendation stays within the existing PSE reactor direction supported by the KG rather than introducing a new chemistry. The PSE reactor already combines a proton-exchange membrane, an AEM, and a porous solid electrolyte under CO2 gas feed, demonstrating that ion transport can be maintained without relying on a bulk flooded cathode layer (doc_2040). The diagnosed issue is specifically the continuous liquid layer, so the next structural change should alter the transport path at the cathode interface. The KG shows a porous PTFE diaphragm is highly hydrophobic, functions as a gas phase isolation interface, and has robust non-blocking pores; a related hydrophobic PTFE membrane with gas paths is linked as a replacement in the separator family. This supports using PTFE not as an ion conductor, but as a porous diaphragm/separator to confine liquid water and preserve gas pathways. The transport-path logic is: (1) ion transport benefit—ions still move through the existing porous solid-electrolyte/PSE path, so the PTFE layer does not need to conduct ions; risk—if the hydrophobic layer separates the catalyst too far from the wetted PSE, ionic continuity can worsen. (2) water management benefit—the hydrophobic PTFE barrier should discourage formation of a continuous flooding-prone liquid film; risk—over-correction can create dry-out. (3) gas access benefit—gas pathways are preserved at the cathode side, which directly addresses unstable mass transport; this is consistent with local-environment sensitivity in CO2RR and with forced-flow benefits seen in the literature (doc_0241, doc_1782). (4) cation availability risk—the KG does not support PTFE supplying cations, and if an AEM is retained it transports anions rather than K+, so local alkali-cation availability may not improve and must be monitored. (5) ohmic loss benefit/risk—removing excess liquid film can reduce extra transport resistance, but only if the remaining wetted ionic path through the PSE stays continuous; otherwise HFR can rise. (6) mechanical stability benefit—PTFE separators are chemically robust and the KG reports no pore blocking/biofouling for the hydrophobic PTFE diaphragm; risk—interfacial compression/contact must be controlled because PTFE is nonconductive. This is therefore a single-variable architecture refinement: shift the cathode contact mode from persistent gas-liquid-solid flooding toward controlled gas-aerosol-solid contacting while preserving the proven PSE backbone.

## Expected Improvement
More stable gas access and water distribution at the cathode, reduced pressure-driven flooding behavior, and lower effective transport resistance relative to a continuous liquid layer, while preserving an ion-conducting path through the porous solid electrolyte.

## Risks
- PTFE is electrically insulating, so excessive thickness or poor interfacial contact could increase effective ionic path length and raise resistance.
- Too little retained water at the PTFE-mediated interface could dry the reaction zone and destabilize ion transport through the porous solid-electrolyte path.
- If an AEM-containing architecture is retained upstream, note that the AEM transmits anions rather than K+; cation supply near the cathode may therefore remain limited unless provided by the local electrolyte environment.
- AEM use also carries a reported risk of increased reverse reaction rate in a solid electrolyte layer context.

## Minimum Experiment
- Use the Proton-exchange membrane porous solid electrolyte (PSE) reactor backbone evidenced in the KG, keeping catalyst and anode unchanged.
- Introduce a porous PTFE diaphragm/hydrophobic PTFE gas-path layer at the cathode-facing side to replace the continuous liquid-film contact with gas-aerosol-solid contacting.
- Feed CO2 gas as in the PSE reactor and operate with the minimum liquid delivery needed to wet the porous solid-electrolyte path rather than maintain a continuous catholyte film.
- Collect EIS/HFR, cathode pressure drop or fluctuation, and steady partial current/FE over time.

## Discriminating Test
- Build two otherwise identical cathode assemblies: baseline flooded liquid-film contact vs PTFE-diaphragm-mediated gas-aerosol-solid contact on the same porous solid-electrolyte reactor backbone.
- Measure HFR/impedance, pressure stability, and product current over stepped CO2 flow and humidification conditions.
- Track whether the PTFE-mediated interface lowers resistance and suppresses transport oscillations without causing dry-out.

## Diagnostic Trigger
- Continuous liquid layer is diagnosed as causing pressure imbalance, unstable mass transport, and extra resistance.
- Previous round already moved in the right direction on solid-electrolyte resistance, so the next single-variable step should target liquid-film persistence rather than changing catalyst chemistry or bulk reactor concept.
- KG evidence shows hydrophobic PTFE diaphragms provide gas-phase isolation and resist pore blocking, while forced flow improves CO2RR mass transport.

Go/No-Go: Go if the PTFE-mediated interface gives lower or unchanged HFR together with visibly reduced flooding/pressure oscillation and improved steady partial current at matched catalyst loading and CO2 feed. No-go if dry-out raises resistance or product current becomes less stable than the flooded baseline.

## Literature
- doc_2040 | 10.1038/s41467-025-63722-6 | Interface engineering of single-molecular heterojunction catalysts for CO2 electroreduction in strong acid medium
- doc_0241 | 10.1021/jacs.8b04058 | Direct Observation of the Local Reaction Environment during the Electrochemical Reduction of CO<sub>2</sub>
- doc_2142 | 10.1039/d5cs00969c | Efficient green synthesis of ammonia: from mechanistic understanding to reactor design for potential production
- doc_1782 | 10.1021/acsenergylett.6b00557 | Synergistic Electrochemical CO<sub>2</sub> Reduction and Water Oxidation with a Bipolar Membrane

Score: 0.81

Referenced nodes: 100
Referenced edges: 80
