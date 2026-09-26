# Net and interface intent

This file is a review aid for [`eagle/eeg_ip67_onewire.sch`](eagle/eeg_ip67_onewire.sch), not an electrical release netlist. The schematic’s labels are the source of connection intent.

## Interface partition

| Partition | Elements | Intent | Explicitly excluded |
| --- | --- | --- | --- |
| Controller-side management | `J2`, `U1` I²C/SLPZ pins | Internal SAM E70-class TWIHS management interface | EEG sample transport, PTP time distribution, patient isolation control |
| 1-Wire host bridge | `U1`, `R1`, `R5` | Enumerate and read/write a controlled non-patient accessory metadata device | Clinical/safety authorization, real-time control |
| Exposed accessory interface | `J1`, `D1`, `F1`, `C2` | Connector-domain protection and optional low-power accessory supply | Electrode input, ADS1299 lead, patient cable |
| Accessory-side metadata | `U2` | DS28E07 serial number plus a defined calibration/asset record | Cryptographic authentication or an authority source |
| Shield/chassis review boundary | J1 shell, `TP1` | Preserve a separately reviewed shield/chassis node | Automatic connection to logic, auxiliary or patient-related ground |

## Named nets

| Net | Pins/elements | Intent / review condition |
| --- | --- | --- |
| `3V3_LOGIC` | J2.3V3_LOGIC, U1.VCC, R2.2, R3.2, R4.2, R5.2, C1.1, F1.1 | Host logic supply. Exact source, voltage tolerance, transient behavior and isolation are outside this file. |
| `3V3_AUX` | F1.2, J1.P1, C2.1 | Current-limited auxiliary supply at the external connector. Select F1 only after accessory/cable fault analysis. |
| `GND_AUX` | J1.P3, D1.K, U1.GND, C1.2, C2.2, J2.GND, U2.GND | Accessory return shown for reference. The ultimate grounding and any isolation architecture require system analysis. |
| `1WIRE_EXT` | J1.P2, D1.A, R1.1, U2.IO | External conductor after the connector. D1 is a candidate clamp location; placement/return strategy must be proven by test. |
| `1WIRE_IO` | R1.2, U1.IO, R5.1 | DS2484 port-side conductor. R1/R5 values are explicitly provisional. |
| `MCU_TWIHS_SDA` | J2.SDA, U1.SDA, R2.1 | Internal I²C data. Pullup value needs capacitance and timing measurement. |
| `MCU_TWIHS_SCL` | J2.SCL, U1.SCL, R3.1 | Internal I²C clock. Pullup value needs capacitance and timing measurement. |
| `MCU_1WIRE_ENABLE` | J2.OW_EN, U1.SLPZ, R4.1 | Optional controller enable/state-control node. Failure/reset behavior must be reviewed; it is not a safety control. |
| `SHIELD_CHASSIS` | J1.SHELL, TP1 | A deliberate unresolved shield/chassis boundary, not a logic-ground connection. |
| `RESERVED_NO_CONNECT` | J1.P4 intent | Pin 4 is reserved and must remain electrically unused unless a controlled requirement and revised design are approved. |

## J1 pin assignment review

The symbol labels its contacts by functional name to prevent a generic “pin 1/2/3/4” ambiguity. Before any physical build, an independent reviewer must compare the above assignment against **all** of the following for the actual chosen product variant: panel-side mating-face view, cable-side mating-face view, vendor pin numbering, wire color convention, cable assembly drawing and firmware/accessory documentation. M8 contact views are easy to reverse.

| J1 contact name | Required net | Build status |
| --- | --- | --- |
| `P1_3V3_AUX` | `3V3_AUX` | Candidate only |
| `P2_1WIRE` | `1WIRE_EXT` | Candidate only |
| `P3_GND_AUX` | `GND_AUX` | Candidate only |
| `P4_RESERVED` | no connection | Reserved |
| `SHELL` | `SHIELD_CHASSIS` | Boundary unresolved |

## Metadata contract to define before firmware

A DS28E07 can identify a cable/accessory and hold a small record, but this reference does not prescribe or authorize a record format. A controlled implementation needs at least:

1. a ROM-ID enrollment process and an immutable asset record external to the device;
2. a versioned EEPROM page map with byte order, CRC/integrity protection and a safe default for malformed data;
3. calibration provenance, units, validity range, expiry/revision and an audit path;
4. write authorization and service tooling rules; and
5. a defined response to absent, duplicated, malformed or unexpected identifiers.

None of those outcomes may enable a clinical mode, substitute for an operator check, alter ADS1299 acquisition settings automatically, or establish device authenticity. EEPROM content is untrusted input until it is validated against the controlled host-side record.
