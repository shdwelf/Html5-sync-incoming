# IP67 1-Wire accessory-identification reference

**Status: pre-production engineering reference, revision A.** This directory is a bounded, non-clinical interface concept for a controlled research prototype. It is **not** a fabrication release, a medical-device design, an IP67 certification, a safety assessment, or a patient-connected circuit.

The reference isolates a narrow purpose: allow an external, removable **non-patient** accessory or cable to expose a Dallas/Maxim/Analog Devices 1-Wire identifier and small calibration/asset metadata record. It expressly does **not** carry ADS1299 electrode signals, sample data, timing-reference traffic, therapy control, or safety interlocks.

## Files

| File | Purpose |
| --- | --- |
| [`eagle/eeg_ip67_onewire.sch`](eagle/eeg_ip67_onewire.sch) | Autodesk EAGLE 9 XML source, including a deliberately schematic-only embedded symbol library. |
| [`BOM.csv`](BOM.csv) | Engineering BOM with candidates, placeholders, and release blockers. It is not an approved procurement BOM. |
| [`NETLIST.md`](NETLIST.md) | Connector/pin and net intent. |
| [`VERIFICATION_PLAN.md`](VERIFICATION_PLAN.md) | Design, ingress, electrical, EMC, firmware, and safety-boundary verification matrix. |
| [`tools/validate_eagle_schematic.py`](tools/validate_eagle_schematic.py) | Reproducible XML and reference-structure check; it is not Autodesk EAGLE ERC/DRC. |

## Intended topology

```text
SAM E70-class controller TWIHS (internal only)
      SDA / SCL / enable
              |
          DS2484R+T
       I²C-to-1-Wire master
              |
  exposed 1-Wire conductor — ESD candidate — current-limit candidate
              |
 M8 A-coded, four-contact panel connector (candidate IP67 assembly)
              |
 optional cable/accessory DS28E07 identity/calibration EEPROM
```

The host-side `DS2484R+T` is an I²C-controlled 1-Wire master. The optional `DS28E07` belongs in the removable accessory/cable, not the host enclosure. Its immutable 64-bit ROM identifier and EEPROM support **identification and controlled metadata only**. They do not authenticate an accessory and must not authorize a safety-relevant action. If authenticity is actually required, define a threat model, a separately selected cryptographic authenticator, key provisioning, field recovery, and test evidence.

## External port candidate and fixed pin intent

`J1` is a researched candidate: Binder **86-6319-1120-00004**, an M8 A-coded 4-contact shieldable panel-mount connector. The vendor rating applies only under its stated mating and installation conditions. The finished product’s enclosure, panel hole, gasket, mating cable or cap, torque, strain relief, materials, corrosion environment and test configuration must be selected and verified as a system.

| J1 contact | Schematic net | Fixed purpose | Boundary |
| --- | --- | --- | --- |
| Pin 1 | `3V3_AUX` | Optional, current-limited accessory supply | Non-patient only |
| Pin 2 | `1WIRE_EXT` | 1-Wire data | Non-patient identity/calibration only |
| Pin 3 | `GND_AUX` | Accessory return | Non-patient only |
| Pin 4 | `RESERVED` | Leave unconnected pending controlled requirement | Must not be repurposed informally |
| Shell | `SHIELD_CHASSIS` | Enclosure/shield boundary | Bonding strategy is intentionally unresolved |

There is no electrode connector, ADS1299 input, patient-applied part, or medical power barrier in this schematic.

## Why this does not establish IP67

IEC 60529 IP67 means both dust-tight protection (`IP6X`) and temporary immersion protection (`IPX7`) for a defined, tested finished assembly. A connector datasheet marking and a TVS do not establish either result. In particular, this source does not define or verify:

- enclosure/panel material, geometry, wall thickness, hole tolerance, O-ring/gasket selection or compression;
- mating connector, cable overmold, cap, torque, strain relief, aging, corrosion, cleaning agents, altitude or temperature;
- PCB creepage/clearance, coating, venting, drainage, pressure equalization, condensation or service access;
- production assembly controls or complete-assembly IP6X/IPX7 testing.

See [`VERIFICATION_PLAN.md`](VERIFICATION_PLAN.md) for the test matrix and the evidence that is still needed before a finished assembly could make an ingress claim.

## Electrical design boundaries

- Use a **certified external medical PSU only after its exact model, output, isolation ratings, cabling and end-equipment integration are reviewed**. No PSU model or isolation barrier has been supplied here.
- I²C/TWIHS is management traffic only. It is not the acquisition timing path. Keep ADS1299 acquisition on the separately defined `DRDY`/SPI/DMA path and use PTP hardware timestamps only at defined observer boundaries; see [`../eeg-timing-reference/`](../eeg-timing-reference/).
- Values marked `TBD`, `provisional`, or `DNP option` in the BOM are deliberately unresolved. The starting values are not a release authorization.
- The connector-side protection components are candidates whose location, return path and component selection require measured 1-Wire signal integrity and system-level ESD/EMC testing.
- `SHIELD_CHASSIS` is not silently tied to `GND_AUX` or any patient-related ground. The finished product must define that strategy from enclosure, EMC and safety analysis.
- This 1-Wire bus is unavailable/invalid tolerant: loss, corruption, an unknown ROM ID, or EEPROM read/write failure must only disable optional metadata features and record a diagnostic. It must not control sampling, stimulation, therapy, safety state, or a clinical interpretation.

## EAGLE use and validation

The schematic is EAGLE v6+ XML and was written for Autodesk EAGLE 9. It embeds generic symbols only and intentionally has **no packages and no board file**. A controlled library with approved manufacturer footprints, a board stack-up, panel/enclosure drawings, and formal review are prerequisites for a PCB release.

Run the repository-side structural check:

```sh
python3 projects/eeg-ip67-onewire-reference/tools/validate_eagle_schematic.py
```

Then, in the approved EAGLE 9 environment:

1. Open `eagle/eeg_ip67_onewire.sch` and retain the original XML in configuration control.
2. Replace the generic/schematic-only symbols with reviewed library devices and footprints; re-check every manufacturer pin mapping against current datasheets.
3. Run EAGLE ERC and resolve/document all warnings. Create a board only after the enclosure, outline, stack-up, cable and safety requirements are controlled.
4. Perform independent peer review of net names, J1 pin assignment, grounding/shield strategy, supply fault protection and state behavior.
5. Execute the verification plan before any product, ingress, safety, EMC, medical, or production claim.

The included script verifies XML well-formedness, schematic/BOM reference matching, and a short list of project-specific reference rules. It cannot prove that EAGLE opens the file, prove no electrical-rule violations, or substitute for DRC/ERC, testing, certification, or risk management.

## Sources used for candidate selection

- Analog Devices, [DS2484 product page](https://www.analog.com/en/products/ds2484.html) and [DS2484 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/DS2484.pdf): I²C-to-1-Wire master, timing/active-pullup behavior and package constraints.
- Analog Devices, [DS28E07 product page](https://www.analog.com/en/products/ds28e07.html) and [DS28E07 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds28e07.pdf): 1 Kbit 1-Wire EEPROM and immutable ROM identifier characteristics.
- Analog Devices, [1-Wire attachment methods article](https://www.analog.com/en/resources/technical-articles/attachment-methods-for-the-electromechanical-1wire-contact-package.html): identity/calibration use cases and the distinction between EEPROM identification and cryptographic authentication.
- Binder, [86-6319-1120-00004](https://www.binder-usa.com/us-en/products/automation-technology/m8/86-6319-1120-00004-m8-male-panel-mount-connector-4-shieldable-tht-ip67-front-fastened): candidate M8 connector; verify current vendor documentation at release.
- IEC, [IEC 60529:1989+A1:1999+A2:2013](https://webstore.iec.ch/en/publication/2452) (edition availability/access varies): ingress-protection test framework, not a component-level guarantee.
- ISO, [IEC 80601-2-26:2019](https://www.iso.org/standard/77773.html): EEG-system basic safety and essential-performance particular requirements. This reference does not claim conformity.

All supplier status, lifecycle and technical data must be rechecked against current controlled documents at the time of design release.
