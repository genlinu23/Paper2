# D3 Build Sheet - R6

## Layers
| order | component | material | thickness | active area |
|---:|---|---|---|---|
| 1 | cathode | Cu | not specified | not specified |
| 2 | electrolyte/interlayer | described in recommendation | not specified | not specified |
| 3 | separator | porous PTFE, PTFE, separator, AEM, membrane | not specified | not specified |
| 4 | anode | Pt, HOR | not specified | not specified |

Use KOH spray: False

## Gas Params
- cathode_flow: 10-50 sccm, feed from generated recommendation: not specified
- anode_flow: 10-50 sccm, feed from generated recommendation: H2
- pressure: near ambient, balanced across compartments

## Cathode Feed
- not specified

## Anode Feed
- H2

## Prewetting
- prewetting described in recommendation

## Gasket And Clamping
- not specified by recommendation

## Test Plan
- Build one cathode variant only: Cu on porous PTFE GDL with sub-10 μm PCRL, keeping catalyst identity/loading, electrolyte, membrane, and flow hardware unchanged.
- Test in the existing CO-reduction/flow-cell configuration under the same KOH electrolyte used in the baseline.
- Run short steady-state holds across relevant current densities and record FE, partial currents, cell voltage, and time-to-flooding or dry-out.

## Teardown Photo Points
- not specified by recommendation

## Safety Checks
- standard electrochemical cell safety checks
- H2 leak check

## Notes
A gradual R7 convergence to a gas-fed flow-cell/MEA-like cathode architecture in which a Cu catalyst is supported on a porous PTFE transport layer and coupled to a thin PCRL, so the cathode transport path is intentionally split into gas access through PTFE pores and a short liquid/ion path at the catalyst for gas-aerosol-solid contacting.
