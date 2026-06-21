# D3 Build Sheet - R3

## Layers
| order | component | material | thickness | active area |
|---:|---|---|---|---|
| 1 | cathode | Cu, carbon paper | not specified | not specified |
| 2 | electrolyte/interlayer | described in recommendation | not specified | not specified |
| 3 | separator | porous PTFE, PTFE, diaphragm, separator, AEM, membrane | not specified | not specified |

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
- Prepare a single cathode architecture change only: same catalyst and catalyst loading, but move from carbon paper GDL support to porous PTFE diaphragm/separator support with conductive catalyst layer.
- Operate with the same CO2 feed and same K+-containing catholyte conditions used in the current reactor.
- Run a stepped-current stability test long enough to expose dry-out/flooding transitions, while measuring product FE, cell voltage/HFR, and cathode pressure drop.
- Post-test inspect cathode wetting pattern and any carbonate deposition location.

## Teardown Photo Points
- not specified by recommendation

## Safety Checks
- standard electrochemical cell safety checks

## Notes
AEM-based flow cathode with the catalyst/conductive layer deposited on a porous PTFE diaphragm/separator instead of carbon paper GDL, targeting a controlled gas-liquid-solid contacting zone adjacent to the cathode where gas passes through open pores while a thin electrolyte film maintains water and K+ near the active surface.
