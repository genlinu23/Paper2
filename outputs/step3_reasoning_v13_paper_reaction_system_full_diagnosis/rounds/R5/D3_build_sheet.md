# D3 Build Sheet - R5

## Layers
| order | component | material | thickness | active area |
|---:|---|---|---|---|
| 1 | cathode | Cu, carbon paper | not specified | not specified |
| 2 | electrolyte/interlayer | described in recommendation | not specified | not specified |
| 3 | separator | porous PTFE, PTFE, diaphragm, separator, membrane | not specified | not specified |
| 4 | anode | Pt, HOR | not specified | not specified |

Use KOH spray: False

## Gas Params
- cathode_flow: 10-50 sccm, feed from generated recommendation: CO
- anode_flow: 10-50 sccm, feed from generated recommendation: H2
- pressure: near ambient, balanced across compartments

## Cathode Feed
- CO

## Anode Feed
- H2

## Prewetting
- prewetting described in recommendation

## Gasket And Clamping
- not specified by recommendation

## Test Plan
- Use the existing CORR flow-cell format and KOH electrolyte already represented in the KG; change only the cathode porous transport layer from carbon paper to hydrophobic porous PTFE diaphragm.
- Keep catalyst, current collector, electrolyte composition, feed composition, geometric area, and compression constant.
- Measure CORR partial current stability, cell voltage/HFR, and evidence of flooding or liquid breakthrough during a short durability run.
- Post-run inspect the porous layer and catalyst interface for wetting pattern and mechanical integrity.

## Teardown Photo Points
- not specified by recommendation

## Safety Checks
- standard electrochemical cell safety checks
- CO ventilation
- H2 leak check

## Notes
A gradual R5-to-R6 convergence toward a CORR flow cell in which the cathode-side porous transport path is a hydrophobic porous PTFE diaphragm/membrane rather than carbon paper, to support gas-aerosol-solid contacting without yet redefining the catalyst stack or separator scheme.
