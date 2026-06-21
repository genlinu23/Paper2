# D3 Build Sheet - R2

## Layers
| order | component | material | thickness | active area |
|---:|---|---|---|---|
| 1 | cathode | Cu | not specified | not specified |
| 2 | electrolyte/interlayer | liquid electrolyte, solid electrolyte | not specified | not specified |
| 3 | separator | porous PTFE, PTFE, diaphragm, separator, AEM, membrane | not specified | not specified |
| 4 | anode | Pt, anode | not specified | not specified |

Use KOH spray: False

## Gas Params
- cathode_flow: 10-50 sccm, feed from generated recommendation: CO2
- anode_flow: 10-50 sccm, feed from generated recommendation: not specified
- pressure: near ambient, balanced across compartments

## Cathode Feed
- CO2

## Anode Feed
- not specified

## Prewetting
- prewetting described in recommendation

## Gasket And Clamping
- not specified by recommendation

## Test Plan
- Use the Proton-exchange membrane porous solid electrolyte (PSE) reactor backbone evidenced in the KG, keeping catalyst and anode unchanged.
- Introduce a porous PTFE diaphragm/hydrophobic PTFE gas-path layer at the cathode-facing side to replace the continuous liquid-film contact with gas-aerosol-solid contacting.
- Feed CO2 gas as in the PSE reactor and operate with the minimum liquid delivery needed to wet the porous solid-electrolyte path rather than maintain a continuous catholyte film.
- Collect EIS/HFR, cathode pressure drop or fluctuation, and steady partial current/FE over time.

## Teardown Photo Points
- not specified by recommendation

## Safety Checks
- standard electrochemical cell safety checks

## Notes
A gradual convergence from the prior porous solid-electrolyte reactor toward a cathode-side gas-aerosol-solid contacting PSE architecture: Nafion-117/porous solid electrolyte remain the ion-transport backbone, while a hydrophobic porous PTFE diaphragm defines the gas-access side and suppresses a persistent flooded liquid layer.
