# Verification plan and release blockers

**Applies to:** the future finished assembly derived from the reference schematic, not to the schematic alone.

**Current disposition:** every row is open. No result in this directory supports an IP67, EMC, medical-safety, clinical, production, or patient-use claim.

## Required design inputs before board/layout release

| ID | Missing controlled input | Why it blocks release |
| --- | --- | --- |
| IN-01 | Exact ADS1299 suffix/channel count and the complete acquisition schematic | Defines the actual host interface and separation from patient/electrode circuitry. |
| IN-02 | Medical PSU make/model, output range, isolation classification, cable, grounding method and integration instructions | A “medical PSU” category alone does not define system isolation, leakage, fault behavior or enclosure bonding. |
| IN-03 | Electrode cable, connector, pinout, applied-part classification and full protection/isolation architecture | Required to establish that the accessory connector remains non-patient and that no unsafe coupling exists. |
| IN-04 | Enclosure, panel thickness/cutout/tolerance, gasket/O-ring, mating cable/cap, strain relief, torque and environmental profile | Required to create a testable ingress assembly. |
| IN-05 | PCB outline, layer stack-up, controlled library/footprints, return paths, creepage/clearance and component placement | Required before DRC, routing, EMI/ESD analysis or manufacturing release. |
| IN-06 | Intended accessory types, cable lengths, power budget, maximum load, fault cases, metadata contract and firmware fail-safe behavior | Required to choose F1/D1/R1/R5 and define the software response. |
| IN-07 | Risk-management file and standards strategy | Required before any patient-connected or production claim. |

## Verification matrix

| ID | Area | Method and acceptance evidence | Status |
| --- | --- | --- | --- |
| SCH-01 | Schematic integrity | Open source in controlled Autodesk EAGLE 9 installation; run ERC; archive resolved warning log and independent pin-map review against latest datasheets. | Open |
| SCH-02 | Library control | Replace schematic-only symbols with released symbols/packages; review each package pin 1, package orientation, footprint, courtyard and assembly data. | Open |
| ELEC-01 | I²C electrical behavior | Measure SDA/SCL rise/fall time and levels over voltage, temperature, tolerance and bus capacitance with chosen TWIHS speed. Verify DS2484 and controller data-sheet limits. | Open |
| ELEC-02 | 1-Wire waveform | Characterize reset/presence/read/write timing at minimum/maximum cable lengths, capacitance, supply voltage and temperature. Evaluate DS2484 active/strong pullup settings and fitted R1/R5. | Open |
| ELEC-03 | Accessory power faults | Analyze and test shorts, overload, reverse/incorrect cable, brownout, hot-plug, repeated faults and recovery. Confirm F1 selection, upstream supply behavior and thermal derating. | Open |
| ELEC-04 | Metadata failure behavior | Inject no device, unknown ROM, duplicate/enrolled mismatch, malformed EEPROM, CRC failure, write interruption and bus fault. Demonstrate only optional metadata is unavailable and no sampling/safety/clinical action changes. | Open |
| ESD-01 | ESD/transient robustness | Write a system-level plan using applicable immunity levels and contact/air discharges at J1/cable. Validate D1 type, placement, shield/chassis return, leakage and waveform survival. | Open |
| EMC-01 | EMC emissions/immunity | Test the finished product and cable configuration, including longest intended cable and any cap. Preserve pre-compliance and accredited-lab reports as applicable. | Open |
| MECH-01 | Connector integration | Verify actual part number, mating half, panel drawing, mounting torque, shell/bonding plan, cable strain relief, service cap and assembly instructions. | Open |
| IP-01 | Dust ingress | Test representative production-intent complete assemblies to the agreed IEC 60529 IP6X method at worst-case interfaces; document sample configuration and result. | Open |
| IP-02 | Temporary immersion | Test representative production-intent complete assemblies to the agreed IEC 60529 IPX7 method; inspect for ingress and verify post-test operation. The actual standard edition/test conditions must be controlled. | Open |
| IP-03 | Environmental durability | Define and test thermal cycling, humidity, condensation, corrosion, cleaning chemicals, UV if relevant, vibration, drop and cable flex appropriate to the intended use. | Open |
| SAFE-01 | Electrical safety | A qualified safety process must evaluate the full device, supply, enclosure, electrode interfaces, applied-part classification, leakage, creepage/clearance, single-fault conditions and relevant standards. This schematic is not evidence. | Open |
| EEG-01 | EEG-system requirements | If the finished device is intended as an EEG system, assess the complete design against the applicable regulatory and standards strategy, including IEC 80601-2-26 where applicable. | Open |
| FW-01 | Firmware boundary | Review firmware so 1-Wire reads are asynchronous/timeout bounded, never interrupt acquisition timing, and cannot change acquisition/therapy/safety behavior from device metadata. | Open |
| MFG-01 | Production control | Establish approved vendors, lifecycle monitoring, incoming inspection, programming/enrollment control, traceability, cable test, torque control and end-of-line test. | Open |

## Minimum evidence for an ingress statement

Do not call the eventual device “IP67” based on J1’s datasheet. At a minimum, a controlled release would need a named finished-assembly configuration, controlled drawings/BOM/work instructions, test standard edition and method, calibrated equipment, sample size/rationale, pre/post functional criteria, test reports, nonconformance handling and change control. Any material, mating cable/cap, panel, gasket or process change may invalidate the evidence.

## Safety and clinical boundary

This work purposefully omits a patient/electrode protection circuit and no amount of later testing of the 1-Wire port fills that omission. A patient-connected EEG product needs a system-level risk-management and engineering process led by appropriately qualified personnel. No result here authorizes connection to a human, diagnosis, treatment, neurofeedback therapy, performance claim, or sale.
