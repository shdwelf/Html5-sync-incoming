<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<!--
  EEG IP67 / 1-Wire reference schematic
  Revision A — RESEARCH / PRE-PRODUCTION ONLY

  This is an Autodesk EAGLE 9 XML schematic source with an embedded generic
  symbol library. It intentionally has no board layout, no controlled
  footprint/library release, and no patient/electrode circuit. It must NOT be
  fabricated, populated, or connected to a person.
-->
<eagle version="9.6.2">
  <drawing>
    <settings alwaysvectorfont="no" verticaltext="up"/>
    <grid distance="1.27" unitdist="mm" unit="mm" style="lines" multiple="1" display="yes" altdistance="0.254" altunitdist="mm" altunit="mm"/>
    <layers>
      <layer number="1" name="Top" color="4" fill="1" visible="yes" active="yes"/>
      <layer number="16" name="Bottom" color="1" fill="1" visible="yes" active="yes"/>
      <layer number="17" name="Pads" color="2" fill="1" visible="yes" active="yes"/>
      <layer number="18" name="Vias" color="2" fill="1" visible="yes" active="yes"/>
      <layer number="19" name="Unrouted" color="6" fill="1" visible="yes" active="yes"/>
      <layer number="20" name="Dimension" color="15" fill="1" visible="yes" active="yes"/>
      <layer number="21" name="tPlace" color="7" fill="1" visible="yes" active="yes"/>
      <layer number="22" name="bPlace" color="7" fill="1" visible="yes" active="yes"/>
      <layer number="25" name="tNames" color="7" fill="1" visible="yes" active="yes"/>
      <layer number="27" name="tValues" color="7" fill="1" visible="yes" active="yes"/>
      <layer number="51" name="tDocu" color="7" fill="1" visible="yes" active="yes"/>
      <layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes"/>
      <layer number="92" name="Busses" color="1" fill="1" visible="yes" active="yes"/>
      <layer number="93" name="Pins" color="2" fill="1" visible="yes" active="yes"/>
      <layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes"/>
      <layer number="95" name="Names" color="7" fill="1" visible="yes" active="yes"/>
      <layer number="96" name="Values" color="8" fill="1" visible="yes" active="yes"/>
      <layer number="97" name="Info" color="7" fill="1" visible="yes" active="yes"/>
    </layers>
    <schematic>
      <description>RESEARCH REFERENCE ONLY. No board, routing, patient circuit, electrical safety classification, leakage analysis, IEC 60601 evaluation, enclosure validation or IP67 certification is supplied by this file.</description>
      <libraries>
        <library name="IP67_ONEWIRE_REF">
          <description>Generic schematic-only symbols for an IP67 accessory-identification reference. Packages are deliberately omitted.</description>
          <packages/>
          <symbols>
            <symbol name="M8_4P_IP67">
              <wire x1="-7.62" y1="12.7" x2="7.62" y2="12.7" width="0.254" layer="94"/>
              <wire x1="7.62" y1="12.7" x2="7.62" y2="-12.7" width="0.254" layer="94"/>
              <wire x1="7.62" y1="-12.7" x2="-7.62" y2="-12.7" width="0.254" layer="94"/>
              <wire x1="-7.62" y1="-12.7" x2="-7.62" y2="12.7" width="0.254" layer="94"/>
              <text x="-7.62" y="15.24" size="1.27" layer="95">&gt;NAME</text>
              <text x="-7.62" y="-15.24" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="P1_3V3_AUX" x="-10.16" y="7.62" visible="both" length="middle" direction="pas"/>
              <pin name="P2_1WIRE" x="-10.16" y="2.54" visible="both" length="middle" direction="pas"/>
              <pin name="P3_GND_AUX" x="-10.16" y="-2.54" visible="both" length="middle" direction="pas"/>
              <pin name="P4_RESERVED" x="-10.16" y="-7.62" visible="both" length="middle" direction="pas"/>
              <pin name="SHELL" x="10.16" y="0" visible="both" length="middle" direction="pas" rot="R180"/>
            </symbol>
            <symbol name="DS2484">
              <wire x1="-7.62" y1="10.16" x2="7.62" y2="10.16" width="0.254" layer="94"/>
              <wire x1="7.62" y1="10.16" x2="7.62" y2="-10.16" width="0.254" layer="94"/>
              <wire x1="7.62" y1="-10.16" x2="-7.62" y2="-10.16" width="0.254" layer="94"/>
              <wire x1="-7.62" y1="-10.16" x2="-7.62" y2="10.16" width="0.254" layer="94"/>
              <text x="-7.62" y="12.7" size="1.27" layer="95">&gt;NAME</text>
              <text x="-7.62" y="-12.7" size="1.016" layer="96">&gt;VALUE</text>
              <text x="-5.08" y="2.54" size="1.27" layer="94">I2C to</text>
              <text x="-5.08" y="0" size="1.27" layer="94">1-Wire</text>
              <pin name="VCC" x="-10.16" y="5.08" visible="both" length="middle" direction="pwr"/>
              <pin name="SDA" x="-10.16" y="0" visible="both" length="middle" direction="io"/>
              <pin name="SCL" x="-10.16" y="-5.08" visible="both" length="middle" direction="in"/>
              <pin name="IO" x="10.16" y="5.08" visible="both" length="middle" direction="io" rot="R180"/>
              <pin name="SLPZ" x="10.16" y="0" visible="both" length="middle" direction="in" rot="R180"/>
              <pin name="GND" x="10.16" y="-5.08" visible="both" length="middle" direction="pwr" rot="R180"/>
            </symbol>
            <symbol name="DS28E07_ACCESSORY">
              <wire x1="-7.62" y1="7.62" x2="7.62" y2="7.62" width="0.254" layer="94"/>
              <wire x1="7.62" y1="7.62" x2="7.62" y2="-7.62" width="0.254" layer="94"/>
              <wire x1="7.62" y1="-7.62" x2="-7.62" y2="-7.62" width="0.254" layer="94"/>
              <wire x1="-7.62" y1="-7.62" x2="-7.62" y2="7.62" width="0.254" layer="94"/>
              <text x="-7.62" y="10.16" size="1.27" layer="95">&gt;NAME</text>
              <text x="-7.62" y="-10.16" size="1.016" layer="96">&gt;VALUE</text>
              <text x="-5.08" y="0" size="1.016" layer="94">ACCESSORY</text>
              <pin name="IO" x="-10.16" y="2.54" visible="both" length="middle" direction="io"/>
              <pin name="GND" x="10.16" y="-2.54" visible="both" length="middle" direction="pwr" rot="R180"/>
            </symbol>
            <symbol name="HEADER_5">
              <wire x1="-7.62" y1="12.7" x2="7.62" y2="12.7" width="0.254" layer="94"/>
              <wire x1="7.62" y1="12.7" x2="7.62" y2="-12.7" width="0.254" layer="94"/>
              <wire x1="7.62" y1="-12.7" x2="-7.62" y2="-12.7" width="0.254" layer="94"/>
              <wire x1="-7.62" y1="-12.7" x2="-7.62" y2="12.7" width="0.254" layer="94"/>
              <text x="-7.62" y="15.24" size="1.27" layer="95">&gt;NAME</text>
              <text x="-7.62" y="-15.24" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="SDA" x="-10.16" y="10.16" visible="both" length="middle" direction="io"/>
              <pin name="SCL" x="-10.16" y="5.08" visible="both" length="middle" direction="in"/>
              <pin name="OW_EN" x="-10.16" y="0" visible="both" length="middle" direction="in"/>
              <pin name="3V3_LOGIC" x="-10.16" y="-5.08" visible="both" length="middle" direction="pwr"/>
              <pin name="GND" x="-10.16" y="-10.16" visible="both" length="middle" direction="pwr"/>
            </symbol>
            <symbol name="R">
              <wire x1="-2.54" y1="1.27" x2="2.54" y2="1.27" width="0.254" layer="94"/>
              <wire x1="2.54" y1="1.27" x2="2.54" y2="-1.27" width="0.254" layer="94"/>
              <wire x1="2.54" y1="-1.27" x2="-2.54" y2="-1.27" width="0.254" layer="94"/>
              <wire x1="-2.54" y1="-1.27" x2="-2.54" y2="1.27" width="0.254" layer="94"/>
              <text x="-2.54" y="2.54" size="1.016" layer="95">&gt;NAME</text>
              <text x="-2.54" y="-3.81" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="1" x="-5.08" y="0" visible="both" length="middle" direction="pas"/>
              <pin name="2" x="5.08" y="0" visible="both" length="middle" direction="pas" rot="R180"/>
            </symbol>
            <symbol name="C">
              <wire x1="-1.27" y1="2.54" x2="-1.27" y2="-2.54" width="0.254" layer="94"/>
              <wire x1="1.27" y1="2.54" x2="1.27" y2="-2.54" width="0.254" layer="94"/>
              <text x="-2.54" y="3.81" size="1.016" layer="95">&gt;NAME</text>
              <text x="-2.54" y="-5.08" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="1" x="-5.08" y="0" visible="both" length="middle" direction="pas"/>
              <pin name="2" x="5.08" y="0" visible="both" length="middle" direction="pas" rot="R180"/>
            </symbol>
            <symbol name="FUSE">
              <wire x1="-2.54" y1="1.27" x2="2.54" y2="1.27" width="0.254" layer="94"/>
              <wire x1="2.54" y1="1.27" x2="2.54" y2="-1.27" width="0.254" layer="94"/>
              <wire x1="2.54" y1="-1.27" x2="-2.54" y2="-1.27" width="0.254" layer="94"/>
              <wire x1="-2.54" y1="-1.27" x2="-2.54" y2="1.27" width="0.254" layer="94"/>
              <text x="-2.54" y="2.54" size="1.016" layer="95">&gt;NAME</text>
              <text x="-2.54" y="-3.81" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="1" x="-5.08" y="0" visible="both" length="middle" direction="pas"/>
              <pin name="2" x="5.08" y="0" visible="both" length="middle" direction="pas" rot="R180"/>
            </symbol>
            <symbol name="TVS_2P">
              <wire x1="-2.54" y1="2.54" x2="2.54" y2="-2.54" width="0.254" layer="94"/>
              <wire x1="-2.54" y1="-2.54" x2="2.54" y2="2.54" width="0.254" layer="94"/>
              <text x="-2.54" y="3.81" size="1.016" layer="95">&gt;NAME</text>
              <text x="-2.54" y="-5.08" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="A" x="-5.08" y="0" visible="both" length="middle" direction="pas"/>
              <pin name="K" x="5.08" y="0" visible="both" length="middle" direction="pas" rot="R180"/>
            </symbol>
            <symbol name="TP">
              <circle x="0" y="0" radius="2.54" width="0.254" layer="94"/>
              <text x="-2.54" y="3.81" size="1.016" layer="95">&gt;NAME</text>
              <text x="-2.54" y="-5.08" size="1.016" layer="96">&gt;VALUE</text>
              <pin name="TP" x="-5.08" y="0" visible="both" length="middle" direction="pas"/>
            </symbol>
          </symbols>
          <devicesets>
            <deviceset name="M8_4P_IP67" prefix="J"><gates><gate name="G$1" symbol="M8_4P_IP67" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="DS2484" prefix="U"><gates><gate name="G$1" symbol="DS2484" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="DS28E07_ACCESSORY" prefix="U"><gates><gate name="G$1" symbol="DS28E07_ACCESSORY" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="HEADER_5" prefix="J"><gates><gate name="G$1" symbol="HEADER_5" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="R" prefix="R"><gates><gate name="G$1" symbol="R" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="C" prefix="C"><gates><gate name="G$1" symbol="C" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="FUSE" prefix="F"><gates><gate name="G$1" symbol="FUSE" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="TVS_2P" prefix="D"><gates><gate name="G$1" symbol="TVS_2P" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
            <deviceset name="TP" prefix="TP"><gates><gate name="G$1" symbol="TP" x="0" y="0"/></gates><devices><device name="" package=""><technologies><technology name=""/></technologies></device></devices></deviceset>
          </devicesets>
        </library>
      </libraries>
      <attributes/>
      <variantdefs/>
      <classes><class number="0" name="default" width="0" drill="0"/></classes>
      <parts>
        <part name="J1" library="IP67_ONEWIRE_REF" deviceset="M8_4P_IP67" device="" value="Binder 86-6319-1120-00004 candidate"/>
        <part name="F1" library="IP67_ONEWIRE_REF" deviceset="FUSE" device="" value="AUX 3V3 current limiter TBD"/>
        <part name="D1" library="IP67_ONEWIRE_REF" deviceset="TVS_2P" device="" value="1-Wire ESD protection TBD"/>
        <part name="R1" library="IP67_ONEWIRE_REF" deviceset="R" device="" value="100R provisional"/>
        <part name="U1" library="IP67_ONEWIRE_REF" deviceset="DS2484" device="" value="DS2484R+T"/>
        <part name="R2" library="IP67_ONEWIRE_REF" deviceset="R" device="" value="I2C SDA pullup TBD"/>
        <part name="R3" library="IP67_ONEWIRE_REF" deviceset="R" device="" value="I2C SCL pullup TBD"/>
        <part name="R4" library="IP67_ONEWIRE_REF" deviceset="R" device="" value="SLPZ pullup TBD"/>
        <part name="R5" library="IP67_ONEWIRE_REF" deviceset="R" device="" value="4.7k 1-Wire pullup provisional"/>
        <part name="C1" library="IP67_ONEWIRE_REF" deviceset="C" device="" value="100nF X7R candidate"/>
        <part name="C2" library="IP67_ONEWIRE_REF" deviceset="C" device="" value="1uF X7R candidate"/>
        <part name="J2" library="IP67_ONEWIRE_REF" deviceset="HEADER_5" device="" value="MCU TWIHS internal-only"/>
        <part name="U2" library="IP67_ONEWIRE_REF" deviceset="DS28E07_ACCESSORY" device="" value="DS28E07 accessory/cable side"/>
        <part name="TP1" library="IP67_ONEWIRE_REF" deviceset="TP" device="" value="CHASSIS test point"/>
      </parts>
      <sheets>
        <sheet>
          <description>IP67 accessory / Dallas-heritage 1-Wire identification reference. Separate from patient electrode and AFE circuits.</description>
          <plain>
            <text x="12.7" y="139.7" size="2.54" layer="97">EEG RESEARCH PROTOTYPE — IP67 ACCESSORY / 1-WIRE REFERENCE</text>
            <text x="12.7" y="134.62" size="1.778" layer="97">SHT-001 Rev A • EAGLE 9 XML • NOT FOR FABRICATION OR HUMAN CONNECTION</text>
            <text x="12.7" y="129.54" size="1.27" layer="97">IP67 is an enclosure/cable/connector test claim. This schematic does not establish ingress protection, patient isolation, EMC, leakage, or clinical compliance.</text>
            <text x="12.7" y="124.46" size="1.27" layer="97">J1 is a candidate 4-contact IP67 panel interface for non-patient accessory ID only: 3V3_AUX, 1WIRE, GND_AUX, RESERVED; shell to chassis.</text>
            <text x="12.7" y="119.38" size="1.27" layer="97">Do not route electrode or ADS1299 patient inputs through this reference. A controlled IEC 80601-2-26 / IEC 60601 design is required.</text>
            <wire x1="10.16" y1="116.84" x2="193.04" y2="116.84" width="0.508" layer="97"/>
            <text x="12.7" y="65" size="1.27" layer="97">U1: I2C-to-1-Wire protocol master. U2 exists in the removable accessory/cable, not the host enclosure. Verify electrical/mechanical polarity before build.</text>
            <text x="12.7" y="59.92" size="1.27" layer="97">Keep accessory identity metadata out of sample frames. Use an immutable serial and controlled calibration record; no clinical decision may rely on 1-Wire availability.</text>
          </plain>
          <instances>
            <instance part="J1" gate="G$1" x="25.4" y="100" smashed="yes"/>
            <instance part="F1" gate="G$1" x="55" y="107.62" smashed="yes"/>
            <instance part="D1" gate="G$1" x="50" y="102.54" smashed="yes"/>
            <instance part="R1" gate="G$1" x="65" y="102.54" smashed="yes"/>
            <instance part="U1" gate="G$1" x="95" y="95" smashed="yes"/>
            <instance part="R2" gate="G$1" x="75" y="85" smashed="yes"/>
            <instance part="R3" gate="G$1" x="75" y="80" smashed="yes"/>
            <instance part="R4" gate="G$1" x="115" y="95" smashed="yes"/>
            <instance part="R5" gate="G$1" x="115" y="80" smashed="yes"/>
            <instance part="C1" gate="G$1" x="95" y="75" smashed="yes"/>
            <instance part="C2" gate="G$1" x="45" y="85" smashed="yes"/>
            <instance part="J2" gate="G$1" x="145" y="95" smashed="yes"/>
            <instance part="U2" gate="G$1" x="165" y="102" smashed="yes"/>
            <instance part="TP1" gate="G$1" x="45" y="95" smashed="yes"/>
          </instances>
          <busses/>
          <nets>
            <net name="3V3_LOGIC" class="0"><segment>
              <pinref part="F1" gate="G$1" pin="1"/><wire x1="49.92" y1="107.62" x2="52.46" y2="107.62" width="0.1524" layer="91"/><label x="52.46" y="107.62" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="U1" gate="G$1" pin="VCC"/><wire x1="84.84" y1="100.08" x2="82.3" y2="100.08" width="0.1524" layer="91"/><label x="80.01" y="100.08" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R2" gate="G$1" pin="2"/><wire x1="80.08" y1="85" x2="82.62" y2="85" width="0.1524" layer="91"/><label x="82.62" y="85" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R3" gate="G$1" pin="2"/><wire x1="80.08" y1="80" x2="82.62" y2="80" width="0.1524" layer="91"/><label x="82.62" y="80" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R4" gate="G$1" pin="2"/><wire x1="120.08" y1="95" x2="122.62" y2="95" width="0.1524" layer="91"/><label x="122.62" y="95" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R5" gate="G$1" pin="2"/><wire x1="120.08" y1="80" x2="122.62" y2="80" width="0.1524" layer="91"/><label x="122.62" y="80" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="C1" gate="G$1" pin="1"/><wire x1="89.92" y1="75" x2="87.38" y2="75" width="0.1524" layer="91"/><label x="84.84" y="75" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="J2" gate="G$1" pin="3V3_LOGIC"/><wire x1="134.84" y1="89.92" x2="132.3" y2="89.92" width="0.1524" layer="91"/><label x="129.76" y="89.92" size="1.27" layer="95"/>
            </segment></net>
            <net name="3V3_AUX" class="0"><segment>
              <pinref part="F1" gate="G$1" pin="2"/><wire x1="60.08" y1="107.62" x2="62.62" y2="107.62" width="0.1524" layer="91"/><label x="62.62" y="107.62" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="J1" gate="G$1" pin="P1_3V3_AUX"/><wire x1="15.24" y1="107.62" x2="17.78" y2="107.62" width="0.1524" layer="91"/><label x="17.78" y="107.62" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="C2" gate="G$1" pin="1"/><wire x1="39.92" y1="85" x2="37.38" y2="85" width="0.1524" layer="91"/><label x="34.84" y="85" size="1.27" layer="95"/>
            </segment></net>
            <net name="1WIRE_EXT" class="0"><segment>
              <pinref part="J1" gate="G$1" pin="P2_1WIRE"/><wire x1="15.24" y1="102.54" x2="17.78" y2="102.54" width="0.1524" layer="91"/><label x="17.78" y="102.54" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="D1" gate="G$1" pin="A"/><wire x1="44.92" y1="102.54" x2="42.38" y2="102.54" width="0.1524" layer="91"/><label x="39.84" y="102.54" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R1" gate="G$1" pin="1"/><wire x1="59.92" y1="102.54" x2="57.38" y2="102.54" width="0.1524" layer="91"/><label x="54.84" y="102.54" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="U2" gate="G$1" pin="IO"/><wire x1="154.84" y1="104.54" x2="152.3" y2="104.54" width="0.1524" layer="91"/><label x="149.76" y="104.54" size="1.27" layer="95"/>
            </segment></net>
            <net name="1WIRE_IO" class="0"><segment>
              <pinref part="R1" gate="G$1" pin="2"/><wire x1="70.08" y1="102.54" x2="72.62" y2="102.54" width="0.1524" layer="91"/><label x="72.62" y="102.54" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="U1" gate="G$1" pin="IO"/><wire x1="105.16" y1="100.08" x2="107.7" y2="100.08" width="0.1524" layer="91"/><label x="107.7" y="100.08" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R5" gate="G$1" pin="1"/><wire x1="109.92" y1="80" x2="107.38" y2="80" width="0.1524" layer="91"/><label x="104.84" y="80" size="1.27" layer="95"/>
            </segment></net>
            <net name="GND_AUX" class="0"><segment>
              <pinref part="J1" gate="G$1" pin="P3_GND_AUX"/><wire x1="15.24" y1="97.46" x2="17.78" y2="97.46" width="0.1524" layer="91"/><label x="17.78" y="97.46" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="D1" gate="G$1" pin="K"/><wire x1="55.08" y1="102.54" x2="57.62" y2="102.54" width="0.1524" layer="91"/><label x="57.62" y="102.54" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="U1" gate="G$1" pin="GND"/><wire x1="105.16" y1="89.92" x2="107.7" y2="89.92" width="0.1524" layer="91"/><label x="107.7" y="89.92" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="C1" gate="G$1" pin="2"/><wire x1="100.08" y1="75" x2="102.62" y2="75" width="0.1524" layer="91"/><label x="102.62" y="75" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="C2" gate="G$1" pin="2"/><wire x1="50.08" y1="85" x2="52.62" y2="85" width="0.1524" layer="91"/><label x="52.62" y="85" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="J2" gate="G$1" pin="GND"/><wire x1="134.84" y1="84.84" x2="132.3" y2="84.84" width="0.1524" layer="91"/><label x="129.76" y="84.84" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="U2" gate="G$1" pin="GND"/><wire x1="175.16" y1="99.46" x2="177.7" y2="99.46" width="0.1524" layer="91"/><label x="177.7" y="99.46" size="1.27" layer="95"/>
            </segment></net>
            <net name="MCU_TWIHS_SDA" class="0"><segment>
              <pinref part="U1" gate="G$1" pin="SDA"/><wire x1="84.84" y1="95" x2="82.3" y2="95" width="0.1524" layer="91"/><label x="79.76" y="95" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R2" gate="G$1" pin="1"/><wire x1="69.92" y1="85" x2="67.38" y2="85" width="0.1524" layer="91"/><label x="64.84" y="85" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="J2" gate="G$1" pin="SDA"/><wire x1="134.84" y1="105.16" x2="132.3" y2="105.16" width="0.1524" layer="91"/><label x="129.76" y="105.16" size="1.27" layer="95"/>
            </segment></net>
            <net name="MCU_TWIHS_SCL" class="0"><segment>
              <pinref part="U1" gate="G$1" pin="SCL"/><wire x1="84.84" y1="89.92" x2="82.3" y2="89.92" width="0.1524" layer="91"/><label x="79.76" y="89.92" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R3" gate="G$1" pin="1"/><wire x1="69.92" y1="80" x2="67.38" y2="80" width="0.1524" layer="91"/><label x="64.84" y="80" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="J2" gate="G$1" pin="SCL"/><wire x1="134.84" y1="100.08" x2="132.3" y2="100.08" width="0.1524" layer="91"/><label x="129.76" y="100.08" size="1.27" layer="95"/>
            </segment></net>
            <net name="MCU_1WIRE_ENABLE" class="0"><segment>
              <pinref part="U1" gate="G$1" pin="SLPZ"/><wire x1="105.16" y1="95" x2="107.7" y2="95" width="0.1524" layer="91"/><label x="107.7" y="95" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="J2" gate="G$1" pin="OW_EN"/><wire x1="134.84" y1="95" x2="132.3" y2="95" width="0.1524" layer="91"/><label x="129.76" y="95" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="R4" gate="G$1" pin="1"/><wire x1="109.92" y1="95" x2="107.38" y2="95" width="0.1524" layer="91"/><label x="104.84" y="95" size="1.27" layer="95"/>
            </segment></net>
            <net name="SHIELD_CHASSIS" class="0"><segment>
              <pinref part="J1" gate="G$1" pin="SHELL"/><wire x1="35.56" y1="100" x2="38.1" y2="100" width="0.1524" layer="91"/><label x="38.1" y="100" size="1.27" layer="95"/>
            </segment><segment>
              <pinref part="TP1" gate="G$1" pin="TP"/><wire x1="39.92" y1="95" x2="37.38" y2="95" width="0.1524" layer="91"/><label x="34.84" y="95" size="1.27" layer="95"/>
            </segment></net>
          </nets>
        </sheet>
      </sheets>
    </schematic>
  </drawing>
</eagle>
