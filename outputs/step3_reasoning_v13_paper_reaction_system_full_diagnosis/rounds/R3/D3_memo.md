# D3 Recommendation Memo - R3

Primary bottleneck: Cathode-side dry-out coupled to insufficient local alkali-cation availability at the reaction interface.
Hypothesis: The remaining bottleneck is not bulk catalyst activity but an interfacial transport mismatch: after suppressing continuous-liquid flooding, the carbon-paper-based cathode now under-supplies water and nearby alkali cations. Replacing that support with a porous PTFE diaphragm/separator should create a more controlled gas-liquid-solid contact zone that retains enough electrolyte near the catalyst for hydration and K+ presence, while preserving gas access better than a flooded carbon paper GDL.

## New Architecture
AEM-based flow cathode with the catalyst/conductive layer deposited on a porous PTFE diaphragm/separator instead of carbon paper GDL, targeting a controlled gas-liquid-solid contacting zone adjacent to the cathode where gas passes through open pores while a thin electrolyte film maintains water and K+ near the active surface.

## Design Changes
- Replace the carbon paper GDL cathode with a cathode built on a porous PTFE diaphragm/separator that supports gas-liquid-solid contacting while retaining a thin cathode-side liquid film supplied with K+-containing electrolyte.

## Rationale
The KG supports three linked points. First, carbon paper GDL cathodes carry a flooding risk because hydrophobicity degrades, and flooding through the gas diffusion layer is explicitly connected to carbon paper GDL behavior; this makes simply adding more liquid an unsafe fix. Second, hydrophobic porous PTFE diaphragms/membranes are evidenced as gas-phase isolation interfaces with persistent gas paths and high water contact angle, so they are plausible supports for preserving gas access while limiting bulk liquid invasion. Third, alkali cations, especially larger cations such as K+, are connected to improved CO production and lower interfacial barriers, so maintaining a thin local liquid environment that keeps K+ near the catalyst is directionally supported. This is therefore a gradual convergence step: shift the cathode support from a degradation-prone carbon paper GDL toward a porous PTFE diaphragm/separator to reshape transport paths, not to change catalyst chemistry. Transport-path consequences are: ion transport benefit/risk—thin retained electrolyte near the catalyst can sustain local ionic conduction, but PTFE itself is insulating so excess separation from the ion-conducting phase would increase resistance; water management benefit—a limited liquid film can relieve dry-out without requiring a continuous liquid layer, but over-retention would reverse into flooding; gas access benefit—PTFE diaphragm evidence shows persistent gas paths, supporting CO2 delivery to the contact zone; cation availability benefit—the retained thin electrolyte film is the route for K+ presence because the AEM transmits anions, not K+, so this design specifically uses local liquid retention rather than membrane cation transport; ohmic-loss risk/benefit—avoiding a thick flooded layer should limit added transport resistance, but insufficient ionic contact or an overthick liquid film would increase HFR; mechanical stability benefit—PTFE diaphragm/gasket evidence supports robust hydrophobic structure and stable pore function, while avoiding carbon-paper hydrophobicity-degradation-linked flooding risk. The precipitation risk remains real because cations and alkaline conditions can drive carbonate blockage, so the design should be tested conservatively.

## Expected Improvement
A porous PTFE-diaphragm-supported cathode should better balance transport by preserving gas paths while holding only a limited cathode-side liquid inventory. Expected result is less dry-out, improved local K+ availability at the reaction interface, maintained CO2 access, and more stable performance than carbon paper GDL, provided the liquid layer remains thin enough to avoid renewed mass-transfer loss and excessive resistance.

## Risks
- Too little wetting on the highly hydrophobic PTFE diaphragm may fail to solve dry-out if the thin liquid film cannot be sustained.
- Excess cathode-side electrolyte retention could recreate gas-access limitations or flooding-like behavior.
- Any increase in local alkalinity together with cation presence can raise carbonate precipitation risk that blocks CO2 diffusion.
- PTFE itself is electrically insulating, so the electronic pathway must remain through the catalyst/conductive additive layer; otherwise effective resistance can rise.
- If operation remains near strongly alkaline local conditions, catalyst restructuring/leaching risk can persist.

## Minimum Experiment
- Prepare a single cathode architecture change only: same catalyst and catalyst loading, but move from carbon paper GDL support to porous PTFE diaphragm/separator support with conductive catalyst layer.
- Operate with the same CO2 feed and same K+-containing catholyte conditions used in the current reactor.
- Run a stepped-current stability test long enough to expose dry-out/flooding transitions, while measuring product FE, cell voltage/HFR, and cathode pressure drop.
- Post-test inspect cathode wetting pattern and any carbonate deposition location.

## Discriminating Test
- Build two otherwise identical cathodes: baseline carbon paper GDL versus porous PTFE-diaphragm-supported cathode, both operated with the same K+-containing catholyte feed and gas feed.
- Map current density/selectivity stability together with cathode-side high-frequency resistance and outlet humidity/water balance over time; improvement with lower drift would support better local hydration without major ohmic penalty.
- Track salt accumulation and pressure-drop change across the cathode; improvement should occur without renewed flooding or carbonate blockage.

## Diagnostic Trigger
- Cathode-side dry-out persists after reducing continuous-liquid-layer problems.
- Local lack of K+ / cation environment remains the active limitation.
- Previous carbon paper GDL has evidence-backed flooding risk from hydrophobicity degradation, so added water supply must avoid returning to a thick unstable liquid layer.

Go/No-Go: Go if the PTFE-diaphragm cathode shows sustained higher CO2RR performance or stability than the carbon paper GDL baseline together with lower resistance drift and no clear resurgence of flooding/salt blockage. No-go if performance gains require a visibly thicker liquid layer, if ohmic loss rises substantially, or if carbonate precipitation / gas-transport loss appears earlier than baseline.

## Literature
- doc_0678 | 10.1038/s41467-025-59604-6 | Non-isothermal CO2 electrolysis enables simultaneous enhanced electrochemical and anti-precipitation performance
- doc_2065 | 10.1038/s41560-021-00973-9 | Gas diffusion electrodes, reactor designs and key metrics of low-temperature CO2 electrolysers
- doc_0756 | 10.1038/s41560-021-00973-9 | Gas diffusion electrodes, reactor designs and key metrics of low-temperature CO2 electrolysers
- doc_2546 | 10.1038/s41929-022-00816-0 | Correlating hydration free energy and specific adsorption of alkali metal cations during CO2 electroreduction on Au

Score: 0.82

Referenced nodes: 98
Referenced edges: 80
