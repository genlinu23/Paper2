# Step2 Local Anode Re-extraction Report

- Step1 input: `C:\Users\logan\reactor_agent\outputs\step1_run_ready_v1_full`
- Base KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v5_corr_edges`
- Output KG: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges`
- Filtered core: `C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges_filtered_core.json`
- Selected HOR/Pt@PTL anode docs: 67
- Mode: `build`

## Selection Summary

- Flag counts: `{}`
- Docs with direct Pt@PTL/PTL-anode hits: None
- Docs with KOH aerosol/spray + H2 anode hits: None

## Extraction Summary

- Base nodes: 31913
- Base edges: 21274
- Raw anode nodes: 1244
- Raw anode edges: 665
- Merged raw nodes: 32620
- Merged raw edges: 21833
- Normalized nodes: 32619
- Normalized edges: 21833

## New Edge Analysis

- New edges total: 559
- New traceable edges: 559
- New Pt@PTL/HOR anode-ring edges: 136
- Canonical `Anode:Pt_PTL_anode` incident edges: 0

## Selected Doc Samples

### doc_0009 | 10.1002/adma.202002382

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'anodic']`
- feed `doc_0009_chunk_000782`: In the MEA-SSE system, H2 gas was used as a feedstock at the anode compartment to promote electrocatalytic hydrogenation of CO and to avoid O2 as a byproduct, motivated by the lower overpotential of hydrogen oxidation reaction compared to oxygen evolution reaction.
- performance `doc_0009_chunk_000778`: The Cu-HDD catalyst delivers a C2+ Faradaic efficiency of over 90% at a current density of 727 mA cm−2 in a flow cell system, reaching total current density up to 1 A cm−2 with C2+ Faradaic efficiency over 80%. The C2+ current normalized to electrochemical surface area of Cu-HDD is about seven times larger than Cu-LDD and more than 13 times larger than Cu-NC at −0.795 V versus RHE.
- performance `doc_0009_chunk_000781`: In a catholyte-free MEA electrolyzer, a stable cell voltage of 3.94 V with C2+ product selectivity over 90% was maintained during continuous operation for 20 h at 1.0 A cell current, delivering a gaseous product stream with 19.7 vol% ethylene and liquid streams with concentrations of 1.06 M ethanol and 0.45 M n-propanol at the cathode outlet.

### doc_0036 | 10.1016/j.chempr.2018.05.019

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anodic']`
- structure `doc_0036_chunk_002901`: For a face-centered cubic (fcc) noble-metal crystal structure, the surface facets can be classified as low-index facets, including the three basic (111), (100), and (110) facets, and high-index facets (hkl) (h ≥ k ≥ l > 0). Nanocrystals with low-index planes feature high coordination numbers and relatively low catalytic performance, while nanostructured exposed facets with high surface energies are beneficial for boosting catalytic performance. High-index facets have many terraces, steps, kinks, edges, vertexes, and corners that possess abundant defect sites and low-coordinate active sites, exhibiting attractive catalytic properties. Well-defined metal nanocrystals with exposed high-index fa
- structure `doc_0036_chunk_002906`: Electrocatalytic reactions occur on the surface of the catalyst, which is key to heterogeneous electrocatalytic reactions. There are mainly three interfaces: the inner boundary between components in a hybrid catalyst, the interface between the electrolyte and the catalyst, and the interface between the catalyst and the electrode or other substrate materials. Rationally designing and controlling the interface structures of electrocatalysts is key to enhancing catalytic performance by increasing active sites, facilitating synergistic reactions, and improving contact between electrolyte and catalyst.
- structure `doc_0036_chunk_002909`: Metal-metal interfaces produce synergistic effects at nanoscale interfaces, enhancing catalytic performance. Metal-metal hybrids with different structures, morphologies, dimensions, and compositions have been fabricated and proven to improve electrocatalytic activity due to synergistic effects. For example, Pt and Pt3Ni nanoparticles grown on Au nanowires showed better activity and durability in ORR than Pt/C catalysts. Precise interface engineering of metal-metal heterostructures can achieve more efficient electrocatalysts by exposing more active sites.

### doc_0299 | 10.1038/ncomms3466

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'hydrogen feed']`
- reaction `doc_0299_chunk_028347`: Hydrogen oxidation reaction (HOR) at the anode is severely deactivated by ppm-level CO impurities in reformate hydrogen.
- reaction `doc_0299_chunk_028347`: Ru cores promote CO tolerance of Pt surface by preferential CO oxidation in hydrogen feeds on Ru@Pt nanoparticles compared with Ru-Pt alloys or Pt shells with other metal cores.
- feed `doc_0299_chunk_028374`: Hydrogen feed containing ppm-level CO impurities deactivates Pt catalysts; reformate hydrogen with about 10 ppm CO and air bleeding is targeted to reduce CO poisoning in PEM fuel cells.

### doc_0316 | 10.1038/nmat1040

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['hydrogen oxidation']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_0316_chunk_029659`: Cu-YSZ cermets prepared by calcining mixtures of CuO and YSZ are unstable in reducing atmospheres above 650 °C due to Cu mobility. The Cu/CeO system achieves improved thermal stability by first obtaining a porous skeleton by ceramic methods, then adding Cu and ceria in subsequent low-temperature steps, resulting in stable operation up to 800 °C.
- structure `doc_0316_chunk_029660`: The Cu forms an intimate near-continuous thin network within the retaining skeleton, with some carbon deposition enhancing conduction by bridging links between the Cu network. The anode electrolyte microstructure is the dominant feature governing fuel electrode activity, emphasizing the importance of controlled interfacial and microstructural engineering.
- reaction `doc_0316_chunk_029611`: In the commonly used Ni/YSZ cermet anode, nickel acts as catalyst for hydrogen oxidation and electrical current conductor. Nickel is also highly active for steam-reforming of methane, enabling internal reforming SOFCs operating on methane and water mixtures. However, nickel catalyzes carbon filament formation from hydrocarbons under reducing conditions, which can destroy the anode unless sufficient steam is present to remove carbon faster than it forms.

### doc_0365 | 10.1038/s41467-019-12744-y

- Flags: `{"direct_hor_anode": false, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": true, "cross_fact_hor_h2_anode": false}`
- HOR hits: `[]`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'anodic', 'paired electrolysis']`
- structure `doc_0365_chunk_033494`: There are four types of electrochemical coproduction: parallel, convergent, divergent, and linear paired electrolysis. Parallel paired electrolysis features simultaneous occurrence of two unrelated half-reactions in a divided cell. Convergent paired electrolysis produces a single product from intermediates formed at cathode and anode in an undivided cell. Divergent paired electrolysis uses a common starting substrate at both electrodes to produce different products. Linear paired electrolysis produces the same product from the same substrate via different electrochemical reactions.
- reaction `doc_0365_chunk_033497`: The study selected 16 cathodic reactions including CO2RR and hydrogen evolution reaction (HER), and 18 anodic reactions including OOR and oxygen evolution reaction (OER), categorized based on feedstock source and reaction characteristics. A commercial electrolyzer with parallel paired electrolysis was considered for process modeling.
- reaction `doc_0365_chunk_033510`: Global sensitivity analysis (GSA) was performed to quantify effects of current density, Faraday efficiency (FE), and overpotential on levelized cost of chemicals (LCC). The analysis revealed that LCC sensitivity varies by product and process combination, with FE generally a key factor due to its impact on operating expenditures.

### doc_0394 | 10.1038/s41467-020-17403-1

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_0394_chunk_035919`: The cathode and anode were separated by a porous solid electrolyte (PSE) layer, where electrochemically generated formate and proton were recombined to form molecular formic acid. Gas diffusion layer (GDL) electrodes coated with CO2RR and HOR catalysts were used as cathode and anode to improve mass transfer of CO2 and H2. Both catalysts were in close contact with anion and cation exchange membranes (AEM and CEM) respectively for efficient ion transportation.
- reaction `doc_0394_chunk_035919`: Electrochemical CO2 reduction reaction (CO2RR) to formate occurs on the cathode where CO2 is selectively reduced to formate ions on a selective CO2RR catalyst. On the anode side, hydrogen oxidation reaction (HOR) is performed by feeding H2 gas stream to release protons. Electrochemically generated HCOO− and H+ are driven by electric field to move across AEM or CEM into the PSE layer and recombine to form HCOOH molecule.
- reaction `doc_0394_chunk_035920`: Using an inert N2 gas flow instead of DI water flow to carry away formic acid vapors avoids accumulation of products within the solid electrolyte layer, maintaining high Faradaic efficiency and selectivity. The gas flow can be kept high to prevent product buildup, and high concentration formic acid can be obtained by simple cold-condensation downstream.

### doc_0432 | 10.1038/s41467-021-24578-8

- Flags: `{"direct_hor_anode": false, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- reaction `doc_0432_chunk_039046`: Ir-based catalysts exhibit multifunctional catalytic activity for oxygen evolution reaction (OER), hydrogen evolution reaction (HER), and hydrogen oxidation reaction (HOR); amorphous IrOx surfaces are highly active for OER, while metallic Ir surfaces are active for HER and HOR.
- reaction `doc_0432_chunk_039048`: Under OER operation, crystalline IrNi/C-HT nanoparticles generate an atomically-thin IrNiOx layer that reversibly transforms into metallic IrNi at cathodic potentials, restoring high activity for HER and HOR; in contrast, IrNi/C-LT forms a thick amorphous IrNiOx layer that irreversibly converts and loses HER/HOR activity.
- feed `doc_0432_chunk_039073`: Fuel starvation experiments in a single PEM fuel cell were conducted by switching the anode gas from H2 to Ar at a current density of 100 mA cm-2 to induce voltage reversal conditions.

### doc_0587 | 10.1038/s41467-024-45787-x

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'anodic']`
- structure `doc_0587_chunk_054003`: The cell contains a Ni(OH)2/NiOOH mediator sandwiched by a CO2RR gas diffusion electrode (GDE) and a HOR GDE, to decouple CO2RR and HOR while eliminating sluggish oxygen catalysis. The cell operates in two alternating steps: Step 1 reduces CO2 to CO or formate at the CO2RR GDE while oxidizing Ni(OH)2 to NiOOH; Step 2 uses Ni electrode and HOR GDE to harvest energy by reducing NiOOH back to Ni(OH)2 and oxidizing H2.
- structure `doc_0587_chunk_054059`: The Ni(OH)2/NiOOH mediator is supported on Ni foam (2×2 cm2). The CO2RR GDE is 1×1 cm2, and the HOR GDE is Pt/C with 0.1 mg cm−2 Pt loading. A 1.5 cm thick PEEK frame separates the CO2RR GDE and the mediator, with a Hg/HgO reference electrode placed there. The mediator and HOR GDE are separated by a 130-μm-thick porous separator soaked in 1 M KOH.
- reaction `doc_0587_chunk_054003`: Step 1: CO2 is electrochemically reduced to CO or formate at the cathode, while Ni(OH)2 is oxidized to NiOOH at the anode. Step 2: NiOOH is reduced back to Ni(OH)2 at the cathode, while H2 is oxidized to water at the anode, generating electricity. This alternating operation enables continuous CO2 reduction coupled with hydrogen oxidation.

### doc_0594 | 10.1038/s41467-024-46803-w

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_0594_chunk_054667`: The continuous-flow reactor configuration includes a proton shuttle that participates in reactions forming lithium nitride and ammonia, with protons generated through HOR on PtAu anode catalysts and transferred via protonated shuttle species.
- structure `doc_0594_chunk_054667`: The proton shuttle should contain functional groups capable of donating/accepting protons, have proper pKa in the electrolyte to balance protonation ability and minimize side reactions, form a functional SEI layer on the cathode, have stable deprotonated form, optimal diffusion rate, and compatibility with the Li-NRR system.
- structure `doc_0594_chunk_054710`: The PtAu/SSC anode electrode is prepared by electrodeposition using a 5 μm pore size stainless steel cloth as working electrode and Pt mesh as counter electrode, with a current density of -0.2 A/cm2 applied for 2 min to deposit high surface area PtAu structures.

### doc_0708 | 10.1038/s41467-025-66140-w

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_0708_chunk_067775`: Phenylacetylene (R-Ph) based ligands coordinate with Cu(I) ions forming metal-organic polymers (MOPs) with stable Cu^δ+ sites via strong σ-π dative bonding, enhancing structural stability and tunable electronic structure of copper sites.
- reaction `doc_0708_chunk_067801`: Methoxyl substitution reduces energy difference in potential-determining step (CO2 to *COOH) by 0.23 eV, increasing reactivity toward CO2 reduction; stronger *CO adsorption on OMe-PhCu compared to F-PhCu which weakens *CO adsorption.
- membrane `doc_0708_chunk_067792`: A proton exchange membrane (PEM) electrolyzer with hydrogen oxidation reaction (HOR) as anode was constructed, demonstrating lower cell voltage and good stability at 200 mA cm−2 while maintaining considerable methane Faradaic efficiency.

### doc_0718 | 10.1038/s41467-025-67949-1

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'anodic']`
- structure `doc_0718_chunk_069041`: Catalyst inks were prepared by dispersing catalyst powder with PTFE emulsion, ethanol, and Nafion solution followed by ultrasonication, then sprayed onto gas diffusion layers with specific mass loadings (0.5 mg cm⁻²) to form electrodes (doc_0718_chunk_069041, Results and Discussion).
- reaction `doc_0718_chunk_068981`: Interstitial carbon infusion modulates Pd soft acid strength, weakens Pd-O bond energy, promotes formation and desorption of HCOOH, suppresses CO poisoning and hydrogen evolution reaction (HER), enhancing selectivity and stability for acidic CO2 reduction to formic acid (doc_0718_chunk_068981, Results and Discussion).
- membrane `doc_0718_chunk_068981`: Proton exchange membrane (PEM) electrolyzer used for acidic CO2 electroreduction with PdCx catalyst, operating at high current density (1000 mA cm-2) and low cell voltage (1.8 V), demonstrating long-term stability (500 hours) and high Faradaic efficiency for HCOOH (doc_0718_chunk_068981, doc_0718_chunk_069012, doc_0718_chunk_069013, Results and Discussion).

### doc_0800 | 10.1038/s41586-023-06917-5

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- reaction `doc_0800_chunk_076576`: The proton-exchange membrane (PEM) system reduces CO2 to formic acid at the r-Pb catalyst, coupling CO2 reduction with hydrogen oxidation reaction (HOR) at the anode, achieving over 93% Faradaic efficiency and nearly 91% single-pass CO2 conversion efficiency at 600 mA cm-2 and 2.2 V cell voltage.
- membrane `doc_0800_chunk_076582`: The PEM system uses a proton-exchange membrane (Nafion 212) and achieves durable operation for more than 5,200 hours at 2.2 V and 600 mA cm-2, with membrane stability attributed to the use of HOR at the anode to avoid harmful hydrogen peroxide generation that could degrade the membrane.
- feed `doc_0800_chunk_076623`: The cathode is fed with high-purity CO2 gas at controlled flow rates (optimized at 3 sccm for high single-pass conversion efficiency), and the anode is fed with humid hydrogen gas at 20 sccm for the hydrogen oxidation reaction.

### doc_0938 | 10.1039/d0ee03756g

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['hydrogen oxidation']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_0938_chunk_089863`: GDLs require high conductivity for electron transfer, high porosity for gas diffusion, a smooth surface to accommodate the CL, and high water-repellence to prevent flooding; flooding blocks active catalytic sites and gas pathways, triggering severe hydrogen evolution reaction (HER) and resulting in GDE performance failure.
- structure `doc_0938_chunk_089866`: Single-layer GDLs are macroporous substrates usually made of carbon material, with hydrophobic agent content (e.g., PTFE) determining surface hydrophobicity, gas permeability, and electrical conductivity; excessive PTFE can reduce hydrophobicity and increase electrical resistance.
- structure `doc_0938_chunk_089870`: Dual-layer GDLs include a microporous layer (MPL) between the macroporous layer and catalyst layer, improving hydrophobicity, water management, reducing ohmic resistance, and enhancing structural integrity; MPL is typically made of carbon black powder and hydrophobic agents like PTFE or PVDF.

### doc_1022 | 10.1016/j.nanoen.2016.01.027

- Flags: `{"direct_hor_anode": false, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'anodic']`
- structure `doc_1022_chunk_097025`: Epitaxial rutile IrO2 and RuO2 films with (100) orientation have greater OER activity than (110) orientation, possibly due to enhanced active site density.
- structure `doc_1022_chunk_097025`: (110) orientation in Co3O4 nanocrystals contains more active Co3+ phase and features greater OER activity than (001) plane.
- structure `doc_1022_chunk_097025`: SrRuO3 single-crystal thin films show OER activity decreasing in order (111) > (110) > (001), with stability increasing in same order, indicating a stability-activity relation.

### doc_1050 | 10.1039/d0gc01412e

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- reaction `doc_1050_chunk_099403`: Direct CO reduction to formaldehyde (CORTF) is achieved under ambient conditions using MoP catalyst, combining electrochemical and thermal mechanisms. The reaction involves hydrogen underpotential deposition (HUPD) generating *H species that react with dissolved CO to form formaldehyde with nearly 100% Faradaic efficiency at low current density.
- feed `doc_1050_chunk_099475`: CO is fed to the cathode compartment where CORTF occurs, and H2 is fed to the anode compartment for hydrogen oxidation reaction in the full cell setup.
- performance `doc_1050_chunk_099455`: Formaldehyde production rate reaches over 30 mg/(g_cat h) with more than 50% Faradaic efficiency by tuning current density and temperature, which is one order of magnitude higher than previous thermal catalysis methods. Faradaic efficiency approaches 96.6% at low current density (-5 μA cm-2).

### doc_1118 | 10.1038/ncomms10141

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'anodic']`
- reaction `doc_1118_chunk_104715`: Hydrogen oxidation reaction (HOR) in alkaline electrolyte follows Tafel-Volmer or Heyrovsky-Volmer mechanisms with key intermediate adsorbed hydrogen (Had); elementary steps include H2 + 2* -> 2Had (Tafel), H2 + OH- + * -> Had + H2O + e- (Heyrovsky), Had + OH- -> H2O + e- + * (Volmer).
- reaction `doc_1118_chunk_104689`: Ni/N-CNT catalyst shows HOR activity similar to platinum-group metals in alkaline electrolyte; nitrogen-doped carbon nanotubes alone are poor HOR catalysts but as support increase Ni nanoparticle catalytic performance by factor of 33 (mass activity) and 21 (exchange current density) relative to unsupported Ni nanoparticles.
- membrane `doc_1118_chunk_104692`: Hydroxide exchange membrane fuel cells (HEMFCs) operate in alkaline environment enabling use of PGM-free catalysts such as Ni/N-CNT for HOR at anode.

### doc_1166 | 10.1038/ncomms3466

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode', 'hydrogen feed']`
- reaction `doc_1166_chunk_107934`: Hydrogen oxidation reaction (HOR) at the anode is challenged by CO impurities in reformate hydrogen, which deactivate Pt catalysts; Ru cores with Pt shells promote preferential CO oxidation and improve CO tolerance.
- reaction `doc_1166_chunk_107936`: Pt shell thickness affects CO binding energy and oxygen adsorption behavior, influencing CO tolerance and HOR activity; bilayer Pt shells provide an optimal balance.
- reaction `doc_1166_chunk_107935`: CO oxidation on Ru@Pt nanoparticles is preferential compared to Ru–Pt alloys and other Pt shell/core combinations, enhancing CO tolerance in hydrogen feeds.

### doc_1213 | 10.1038/nmat1040

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['hydrogen oxidation']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_1213_chunk_111319`: Microstructure optimization of nickel-cermet anodes has relied on empirical improvement of materials specifications to control cermet morphology. Modern submicrometre active ceramic powder allows sintering temperatures to be decreased to 1400 °C or lower, with lower metal contents. Nickel oxide grain size around 1 µm is used, with a bidispersed ceramic component containing coarse powder grains of 25 µm or larger to form the structural skeleton and inhibit nickel aggregation, mixed with fine powder to promote sintering. This is applied to electrolyte-supported configurations with stabilized zirconia substrates 150 µm or thicker, providing structural integrity. Recent developments extend the a
- structure `doc_1213_chunk_111324`: In the Cu/CeO system, a porous skeleton is first obtained by ceramic methods and then the Cu and ceria are added in subsequent, low temperature steps, resulting in very advantageous microstructure and improved thermal stability.
- reaction `doc_1213_chunk_111276`: In Ni/YSZ cermet anodes, nickel acts as catalyst for hydrogen oxidation and steam reforming of methane, producing a hydrogen-rich synthesis gas that undergoes electrochemical oxidation at the three-phase boundary. Internal reforming SOFCs generally operate above 900 °C due to thermodynamic limitations of steam reforming. Nickel also catalyzes carbon filament formation from hydrocarbons under reducing conditions, which can destroy the anode unless sufficient steam is present to remove carbon faster than it forms. High steam-to-carbon ratios are needed to suppress carbon deposition with methane, but this approach does not work for higher hydrocarbons, requiring pre-reforming with steam or oxyg

### doc_1216 | 10.1038/nmat2883

- Flags: `{"direct_hor_anode": true, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": false}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- reaction `doc_1216_chunk_111457`: Hydrogen oxidation reaction (HOR) on Pt(111) is extremely fast and requires only a small number of Pt sites; calix[4]arene modification preserves Pt-like HOR activity even at high coverage (doc_1216_chunk_111457)
- feed `doc_1216_chunk_111473`: Experiments conducted in 0.1 M HClO4 electrolyte with controlled gas purging (Ar, O2, H2) to study HOR and ORR on Pt and Pt-calix surfaces (doc_1216_chunk_111473, doc_1216_chunk_111474)
- performance `doc_1216_chunk_111466`: Pt(111)-calix surfaces show high selectivity for HOR over ORR, with only 2% of Pt sites available sufficient to reach diffusion limiting currents for HOR while strongly inhibiting ORR (doc_1216_chunk_111457, doc_1216_chunk_111459, doc_1216_chunk_111466)

### doc_1234 | 10.1038/s41467-017-01100-7

- Flags: `{"direct_hor_anode": false, "pt_ptl_anode": false, "spray_h2_anode": false, "paired_h2_anode": false, "cross_fact_hor_h2_anode": true}`
- HOR hits: `['\\bHOR\\b', 'hydrogen oxidation', 'hydrogen oxidation reaction']`
- Pt/PTL hits: `[]`
- Anode context hits: `['anode']`
- structure `doc_1234_chunk_112578`: DFT calculations show CoN4C12, CoN3C10,porp, and CoN2C5 moieties have Co(II) binding energies of −6.8 to −7.5 eV and O2 adsorption energies from −0.80 to −1.26 eV, indicating stable porphyrinic structures with relatively weak O2 binding compared to Fe moieties.
- reaction `doc_1234_chunk_112556`: Co-based moieties bind O2 too weakly for efficient oxygen reduction reaction (ORR) compared to Fe-based moieties, as supported by DFT and experimental redox potentials.
- reaction `doc_1234_chunk_112584`: Operando XANES shows Co moieties do not change oxidation state from 0.0 to 1.0 V vs. RHE during ORR, unlike Fe moieties which undergo structural and electronic changes.
