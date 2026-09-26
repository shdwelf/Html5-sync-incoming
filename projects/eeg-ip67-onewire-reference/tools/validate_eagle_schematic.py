#!/usr/bin/env python3
"""Project-local checks for the IP67 / 1-Wire EAGLE XML reference.

This script intentionally does NOT claim to be an Autodesk EAGLE ERC/DRC,
mechanical/IP test, electrical analysis, or manufacturing validation. It only
checks that the checked-in XML is well formed and retains this project's
minimum safety-boundary and topology markers.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / "eagle" / "eeg_ip67_onewire.sch"
BOM = ROOT / "BOM.csv"

REQUIRED_PARTS = {
    "J1", "J2", "U1", "U2", "F1", "D1", "R1", "R2", "R3", "R4", "R5", "C1", "C2", "TP1"
}
REQUIRED_NETS = {
    "3V3_LOGIC",
    "3V3_AUX",
    "GND_AUX",
    "1WIRE_EXT",
    "1WIRE_IO",
    "MCU_TWIHS_SDA",
    "MCU_TWIHS_SCL",
    "MCU_1WIRE_ENABLE",
    "SHIELD_CHASSIS",
}
EXPECTED_PINREFS = {
    "1WIRE_EXT": {("J1", "P2_1WIRE"), ("U2", "IO"), ("D1", "A"), ("R1", "1")},
    "1WIRE_IO": {("U1", "IO"), ("R1", "2"), ("R5", "1")},
    "SHIELD_CHASSIS": {("J1", "SHELL"), ("TP1", "TP")},
    "MCU_TWIHS_SDA": {("J2", "SDA"), ("U1", "SDA"), ("R2", "1")},
    "MCU_TWIHS_SCL": {("J2", "SCL"), ("U1", "SCL"), ("R3", "1")},
    "MCU_1WIRE_ENABLE": {("J2", "OW_EN"), ("U1", "SLPZ"), ("R4", "1")},
}
FORBIDDEN_TERMS = ("PATIENT_SAFE", "THERAPY_CONTROL", "ELECTRODE_INPUT", "ADS1299_INPUT")


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not SCHEMATIC.is_file():
        fail(f"schematic missing: {SCHEMATIC}")

    try:
        tree = ET.parse(SCHEMATIC)
    except ET.ParseError as exc:
        fail(f"XML is not well formed: {exc}")

    root = tree.getroot()
    if root.tag != "eagle":
        fail(f"expected <eagle> root, found <{root.tag}>")
    if root.attrib.get("version", "").split(".")[0] != "9":
        fail("schematic is not marked as EAGLE 9 XML")

    parts = {part.attrib["name"] for part in root.findall(".//parts/part")}
    missing_parts = REQUIRED_PARTS - parts
    if missing_parts:
        fail(f"missing required reference part(s): {', '.join(sorted(missing_parts))}")

    if not BOM.is_file():
        fail(f"engineering BOM missing: {BOM}")
    with BOM.open(newline="", encoding="utf-8") as bom_file:
        bom_rows = list(csv.DictReader(bom_file))
    if not bom_rows or set(bom_rows[0]) != {
        "Item", "RefDes", "Qty", "Function", "Manufacturer", "Manufacturer part number",
        "Package or interface", "Proposed value or configuration", "Engineering status",
        "Selection basis and required verification",
    }:
        fail("BOM header does not match the controlled engineering-BOM columns")
    bom_refs = {row["RefDes"] for row in bom_rows}
    if bom_refs != REQUIRED_PARTS:
        fail(f"BOM/schematic reference mismatch: {sorted(bom_refs ^ REQUIRED_PARTS)}")

    nets = {net.attrib["name"]: net for net in root.findall(".//nets/net")}
    missing_nets = REQUIRED_NETS - nets.keys()
    if missing_nets:
        fail(f"missing required net(s): {', '.join(sorted(missing_nets))}")

    # Pin 4 is deliberately unused, preventing this port from silently gaining
    # an undocumented function in the reference.
    reserved_pinrefs = root.findall(".//pinref[@part='J1'][@pin='P4_RESERVED']")
    if reserved_pinrefs:
        fail("J1.P4_RESERVED must remain unconnected in this reference")

    for net_name, expected in EXPECTED_PINREFS.items():
        actual = {
            (pinref.attrib.get("part"), pinref.attrib.get("pin"))
            for pinref in nets[net_name].findall(".//pinref")
        }
        absent = expected - actual
        if absent:
            fail(f"{net_name} missing pin reference(s): {sorted(absent)}")

    joined = "\n".join(element.text or "" for element in root.iter())
    forbidden = [term for term in FORBIDDEN_TERMS if term in joined]
    if forbidden:
        fail(f"forbidden patient/control claim marker(s) in schematic: {', '.join(forbidden)}")

    library = root.find(".//libraries/library[@name='IP67_ONEWIRE_REF']")
    if library is None:
        fail("embedded reference library missing")

    # This is intentional: package-less devices and no .brd force controlled
    # footprint/layout work before a manufacturing release.
    board = ROOT / "eagle" / "eeg_ip67_onewire.brd"
    if board.exists():
        fail("unexpected board file: this reference must remain schematic-only")

    print("PASS: XML well formed; required non-patient 1-Wire reference topology is present.")
    print("INFO: Run Autodesk EAGLE 9 ERC and all electrical/mechanical/safety verification separately.")


if __name__ == "__main__":
    main()
