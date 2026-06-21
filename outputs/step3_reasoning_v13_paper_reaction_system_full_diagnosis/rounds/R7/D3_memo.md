# D3 Recommendation Memo - R7

Primary bottleneck: Misallocation of transport functions: conventional membrane-centered layouts blur gas access, water supply, and cation supply, whereas the diagnosis indicates that PTFE should not be tasked with ion transport and that H2O/K+ must instead be delivered through the cathode gas-aerosol-solid path; if this is not enforced, flooding or ohmic loss dominates.
Hypothesis: A gradual R7 convergence is that CORR performance is limited less by catalyst identity than by misallocated transport functions. If PTFE is used only as a porous diaphragm/separator for physical phase isolation and hydrophobic gas-path preservation, while H2O and K+ are supplied through the gas-aerosol-solid cathode feed, then the reactor can retain high gas accessibility and lower flooding tendency without relying on the separator for ion transport. Pairing this with a supported polycrystalline Cu powder cathode on PTFE-treated carbon fiber paper should leverage a known CO-reduction-active cathode while isolating the transport-path redesign as the main variable.

## New Architecture
A CO-reduction flow reactor using a gas-aerosol-solid contacting cathode, with a supported polycrystalline Cu powder gas diffusion electrode on PTFE-treated carbon fiber paper and a porous PTFE diaphragm/separator used only for physical phase isolation/cost reduction, while H2O and K+ are delivered through the cathode aerosol stream rather than through the separator.

## Design Changes
- Replace the ion-exchange membrane element with a porous PTFE diaphragm/separator, while allocating H2O and K+ supply to the gas-aerosol-solid cathode feed path rather than to the separator.
- Use a supported polycrystalline Cu powder cathode on PTFE-treated carbon fiber paper as the CO-reduction gas diffusion electrode.

## Rationale
The recommendation follows the diagnosis and stays within the same CORR direction. KG evidence supports a PTFE separator role in gas management, not ion conduction: porous PTFE diaphragm improves CO2 delivery and diffusion and preserves hydrophobicity, but also causes severe ohmic losses at larger sizes. This directly supports using PTFE only as a porous physical separator and avoiding any assumption that it transports K+ or other ions. For water management, CORR flooding is repeatedly linked in the KG to gas-fed GDE operation, KOH electrolyte, high current density, and certain membrane properties; therefore moving H2O delivery into a controlled aerosol path is consistent with the diagnosis and avoids assigning bulk water-management duty to a high-water-uptake membrane, which is linked to flooding risk. For gas access, PTFE-backed porous structures are evidence-backed for improved gas delivery/diffusion and persistent hydrophobicity, so a porous PTFE diaphragm/separator should help preserve open gas pathways. For cation availability, there is no KG edge showing PTFE provides K+ transport, so the only evidence-consistent statement is that cation supply must come from the aerosolized cathode feed, not the separator. For ion transport, replacing an ion-exchange membrane with PTFE is a benefit for cost/phase isolation but a risk for ionic conduction because PTFE is effectively nonconductive; this is why the experiment must directly measure resistance and keep spacing small. For the cathode, supported polycrystalline copper powder electrocatalysts on PTFE-treated carbon fiber paper are linked to CO electroreduction current density above 100 mA cm^-2, giving an evidence-backed CO-reduction-active baseline without introducing a new catalyst direction. Across the six transport functions: ion transport—risk, because PTFE separator is not ion-conducting and can raise resistance; water management—potential benefit if aerosolized H2O is metered, but risk of flooding remains if overfed; gas access—benefit from hydrophobic porous PTFE pathways and improved diffusion/delivery evidence; cation availability—benefit only if aerosol carries K+, otherwise risk of cation starvation; ohmic loss—clear risk from PTFE separator scale-up evidence; mechanical stability—potential benefit from persistent hydrophobicity and stable operation evidence in PTFE-based porous separators, but durability still requires validation in CORR operation. This is therefore a single-step transport-path reallocation, not a one-step final stack invention.

## Expected Improvement
This should improve gas access and reduce separator cost while making the transport-function allocation explicit: the porous PTFE diaphragm/separator provides gas-liquid-solid isolation and preserves hydrophobic gas pathways, and the aerosol feed supplies H2O and K+ to the cathode. Expected net result is a more stable operating window against flooding with maintained or improved CO reduction current density relative to a conventional gas-fed GDE layout, provided the diaphragm area/thickness does not create prohibitive ohmic loss.

## Risks
- Porous PTFE diaphragm/separator has intrinsically negligible electrical conductivity, so ion transport across the separator may be poor and cause severe ohmic loss at larger size.
- Improved hydrophobic gas access can still be offset by flooding in CORR gas-fed GDE operation if aerosol water delivery is excessive or poorly distributed.
- Because PTFE does not transmit K+ or anions, insufficient aerosol-mediated cation delivery could leave the cathode transport-limited even if gas access improves.
- Rapid catalytic decay has been linked in the KG to porous PTFE diaphragm use in some CO2RR contexts, so durability must be checked rather than assumed.
- The supported Cu cathode on PTFE-treated carbon fiber paper may improve CO reduction current density, but any benefit can be masked by separator resistance if the electrode spacing/path length is not tightly controlled.

## Minimum Experiment
- Build a two-electrode CO reduction flow reactor with identical geometry except for separator choice: porous PTFE diaphragm/separator versus incumbent ion-exchange membrane.
- Use the same supported polycrystalline Cu powder on PTFE-treated carbon fiber paper cathode in both cells.
- Feed gaseous CO with a controlled aerosol containing H2O and K+ to the cathode so that cation and water delivery are assigned to the gas-aerosol-solid path.
- Record polarization, high-frequency resistance, product distribution/current efficiency, flooding onset, and stability over a fixed galvanostatic hold.

## Discriminating Test
- Compare otherwise identical CO-reduction flow cells using porous PTFE diaphragm/separator versus ion-exchange membrane, with the same aerosolized H2O/K+ cathode feed and the same Cu/PTFE-treated carbon-fiber-paper cathode.
- Measure six transport-linked readouts: area-specific resistance/ohmic drop, flooding onset time, gas-side pressure stability, cathode local wetting state, current density at fixed voltage, and CO reduction selectivity/current efficiency.
- Vary only aerosol H2O/K+ delivery rate at fixed separator to confirm whether cation availability and water management are governed by the gas-aerosol-solid feed path rather than by the separator.

## Diagnostic Trigger
- Current diagnosis explicitly requires that spray/aerosol delivery provide H2O and K+ / cation availability, while PTFE serves only as physical isolation and cost-reduction.
- Prior CORR evidence shows flooding risk in gas-fed GDE devices, especially with KOH electrolyte, high current density, and certain membrane choices.
- KG evidence shows porous PTFE diaphragms improve gas delivery and maintain hydrophobicity, but also carry ohmic-loss risk at larger sizes because PTFE is not ion-conducting.

Go/No-Go: Go if the PTFE-diaphragm cell with aerosolized H2O/K+ feed shows lower flooding frequency or delayed flooding, maintains CO-reduction current density near or above the supported Cu benchmark (>100 mA cm^-2 class), and does not incur an area-specific resistance increase large enough to negate the gas-access benefit. No-go if ohmic loss dominates or if aerosol delivery fails to sustain cathode wetting/cation availability without rapid selectivity decay.

## Literature
- doc_0239 | 10.1021/jacs.8b03986 | Electrochemical CO Reduction Builds Solvent Water into Oxygenate Products
- doc_0114 | 10.1021/acscatal.9b00099 | Effectively Increased Efficiency for Electroreduction of Carbon Monoxide Using Supported Polycrystalline Copper Powder Electrocatalysts
- doc_0069 | 10.1021/acscatal.0c01670 | Correlating Oxidation State and Surface Area to Activity from <i>Operando</i> Studies of Copper CO Electroreduction Catalysts in a Gas-Fed Device
- doc_2431 | 10.1038/s41467-024-53523-8 | Hierarchically conductive electrodes unlock stable and scalable CO2 electrolysis
- doc_0531 | 10.1038/s41467-023-38524-3 | Construction of 3D copper-chitosan-gas diffusion layer electrode for highly efficient CO2 electrolysis to C2+ alcohols
- doc_1854 | 10.1038/s41467-020-15597-y | Highly efficient electrosynthesis of hydrogen peroxide on a superhydrophobic three-phase interface by natural air diffusion

Score: 0.8

Referenced nodes: 105
Referenced edges: 80
