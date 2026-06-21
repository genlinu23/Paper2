# D3 Build Sheet - R4

## Layers
| order | component | material | thickness | active area |
|---:|---|---|---|---|
| 1 | cathode | Cu, GDE, gas-diffusion electrode | not specified | not specified |
| 2 | electrolyte/interlayer | described in recommendation | not specified | not specified |
| 3 | separator | porous PTFE, PTFE, diaphragm, separator, AEM, membrane | not specified | not specified |
| 4 | anode | Pt, HOR, anode | not specified | not specified |

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
- Build a zero-gap cell with porous PTFE-supported CO2 gas feed at the cathode, an AEM separator, and continuous cathode-side recirculation of K-containing alkaline electrolyte at fixed low flow.
- Use the same cathode, same membrane, same compression, and same CO2 feed while switching only between static local reservoir vs flowing cathode-side replenishment.
- Run galvanostatic durability tests long enough to expose depletion behavior, while measuring CO product rate/FE, cell voltage, high-frequency resistance, cathode pressure drop, and post-test salt deposition in the gas-diffusion layer.
- Add a second step using the same flowing architecture under isothermal versus cooler-cathode/warmer-anode conditions to test precipitation suppression.

## Teardown Photo Points
- not specified by recommendation

## Safety Checks
- standard electrochemical cell safety checks

## Notes
A gradual R4 convergence to a zero-gap AEM-based CO2 electrolyzer in which the cathode is a gas-diffusion electrode fed by CO2 through a porous PTFE separator/diaphragm path, while a continuously recirculated K-containing alkaline liquid stream runs adjacent to the cathode to replenish water and cation availability; the anode is separated by an AEM, and optional cooler-cathode/warmer-anode non-isothermal control is used to reduce salt precipitation.
