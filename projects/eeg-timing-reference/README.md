# Acquisition-edge timing reference — PTP / TSN / SAM E70

**Status:** non-clinical research and measurement reference.

**It is not patient-connected firmware, an AFE driver, a feedback protocol, or a medical-device design.**

This project answers the current architecture question: *which IEEE timing bus, processor class, and I²C interface should be used to measure office-fibre latency?*

## Direct answer

| Concern | Decision | Why |
| --- | --- | --- |
| Network clock | **IEEE 1588-2019 PTP**, with hardware MAC timestamps, disciplined to an explicitly named clock domain. | PTP is the applicable IEEE timing standard for packet-based measurement/control clocks. It is not a guarantee by itself; it measures/synchronizes clocks so each latency boundary can be observed. |
| Fibre/TSN profile | Use **IEEE 802.1AS-2020 (gPTP)** only when every relevant LAN bridge/endpoint supports the selected profile. Add **802.1Qbv scheduled traffic** only if the entire path is engineered and proven to support it. | gPTP is the LAN/TSN profile of PTP. Qbv time-aware shaping needs synchronized endpoints and time-aware bridges; a single endpoint cannot create a deterministic path. |
| Acquisition AFE data path | **`DRDY` GPIO/timer capture + SPI + DMA**. | EEG AFEs commonly expose a data-ready pin and an SPI serial-data interface. For example, TI's ADS1299 data sheet specifies SPI and `DRDY`; I²C is not its streaming sample interface. |
| I²C/TWIHS | **Control-plane only**, at the MCU's supported mode, initially 400 kHz Fast-mode for EEPROM, temperature/health monitor, configuration expanders, etc. No sample stream, timestamp, safety interlock, or latency-critical command may depend on I²C completion. | I²C is a two-wire board-control bus (NXP UM10204), not an IEEE deterministic timing transport. Arbitration, clock stretching, pull-up/bus capacitance and peripheral state make its completion time unsuitable as the timing reference. |
| MCU candidate | **Microchip SAM E70/SAM V71 family** as a *candidate*, not a selected medical design. | Current Microchip documentation lists a Cortex-M7, GMAC with dedicated DMA, IEEE 1588 PTP/802.1AS timestamping and TWIHS I²C-compatible peripherals. “Atmel” is legacy branding; Atmel was acquired by Microchip in 2016. |
| “Vector processor” | **Do not add one for the timing loop.** Timestamping, DMA, bounded copying and a light local quality pipeline belong on the MCU. Benchmark a DSP/FPGA only after channel count, sample rate, algorithm and measured CPU budget are known. | A processor choice cannot compensate for unmeasured ADC, queue, network and display timing. The SAM E70's Cortex-M7/FPU/DMA is a sensible measurement-prototype starting point, but it does not make a device deterministic or clinically validated. |

If “IEEE interface” means **IEEE 1451**, do not use it as the sample-timing bus. IEEE 1451 is a smart-transducer interoperability/metadata family (including TEDS), which can be useful for controlled inventory/calibration metadata later. It is not a replacement for the AFE's documented `DRDY`/SPI data path or IEEE 1588/802.1AS clock service.

## Important limitation: timing is not a treatment loop

The fibre/observer path must never determine or delay an output at the acquisition edge. The edge records its timing locally. Any browser, webxdc app or remote display is an **observer only**; it can be stale, disconnected or reordered without changing local operation.

For a product with patient connections or a clinical intended use, do not build from this reference alone. FDA recognizes IEC 60601-1 Edition 3.2 as covering basic safety and essential performance of medical electrical equipment/systems, and its standards listing also includes IEC 60601-1-10 for physiologic closed-loop controllers. The safety classification, isolation architecture, AFE, accessories, intended use, clinical evidence, risk management, cybersecurity, software lifecycle and regulatory pathway require a qualified team.

## Recommended timing topology

```text
approved / isolated analogue & acquisition subsystem
              │  (one sample-frame boundary)
      DRDY ──► timer capture on local PTP-disciplined clock
              │
        SPI RX + DMA  ──► DMA-complete timestamp
              │
  bounded local quality/processing  ──► processing-complete timestamp
              │
  local, independently safety-controlled output boundary
              │
  optional read-only telemetry frame  ──► Ethernet TX hardware timestamp
              │
   PTP-aware / gPTP-aware managed fibre switching
              │
       observer recorder/dashboard (never a feedback authority)
```

`DRDY` should be stamped at the timer capture/interrupt boundary, **not** when an Ethernet packet is later assembled. That makes the latency budget explicit:

```text
DRDY → SPI/DMA complete → local processing complete → local output request
```

The observer path is separately measured:

```text
local processing complete → TX timestamp → network arrival → observer render
```

Do not sum timestamps from separate devices unless their clock domain and uncertainty have been validated. The clock-health bit must accompany every trace; a disconnected/unsynchronized clock is a measurement failure, not a zero-latency result.

## IEEE layer selection

### 1. PTP first: IEEE 1588-2019

Use PTP for the clock service. It has to be backed by **hardware ingress/egress timestamps** in the endpoint MAC/PHY and PTP-aware boundary/transparent clocks where required by the topology. The chosen PTP profile, domain number, grandmaster policy, Sync interval, delay mechanism, maximum clock uncertainty, holdover policy and loss-of-sync behavior must be version-controlled and verified in the office network.

Do not write “sub-microsecond” into a requirement merely because a standard supports it. IEEE describes PTP as capable of sub-microsecond synchronization in correctly designed systems; the delivered system has to produce its own measured offset/jitter/error evidence at the relevant reference plane.

### 2. gPTP only for an all-TSN LAN: IEEE 802.1AS-2020

If the office fibre segment uses a TSN-capable switch and endpoints, select a defined 802.1AS/gPTP profile. This specifies LAN timing transport, time-source selection and timing-impairment indication. It does not create application scheduling by itself.

### 3. Scheduled traffic requires real Qbv support

IEEE 802.1Qbv adds scheduled-traffic forwarding/time-aware gates. Treat it as an end-to-end feature requiring compatible switch(es), NIC/MAC/driver support and a validated gate-control schedule. The Microchip SAM E70/V71 family data sheet advertises 802.1AS timestamping and 802.1Qav **credit-based** shaping; it must not be represented as a Qbv time-aware shaper.

For a first measurement prototype, use an isolated VLAN and PTP-aware managed switch with timestamped telemetry. Only move to Qbv after the deterministic requirement is quantified and the endpoint/switch vendor explicitly documents the needed feature.

## SAM E70/V71 interface map

This is a conceptual map, **not a board schematic or a clearance/safety design**.

| Plane | Peripheral / signal | Purpose | Timing rule |
| --- | --- | --- | --- |
| AFE stream | GPIO/timer capture of `DRDY` | Captures frame-ready edge against local PTP-disciplined counter. | This is the sample time anchor. ISR does bounded bookkeeping only. |
| AFE stream | SPI controller + DMA | Reads a fixed-size conversion frame after `DRDY`. | DMA completion is a separate timestamp. No dynamic allocation/log printing in ISR/callback. |
| Network time | GMAC + external Ethernet PHY | PTP packet hardware timestamping and observer telemetry. | Capture hardware ingress/egress timestamp, not task wake-up time. |
| Fibre | Copper PHY → certified media/managed PTP or TSN fibre switch | Physical transport. | Fibre is a medium; it does not synchronize clocks or bound queues on its own. |
| Board management | TWIHS0/1/2 (I²C-compatible) | EEPROM/FRU, temperature, power/health monitor, noncritical configuration. | 400 kHz Fast-mode is a conservative initial limit. Each transaction gets a timeout/recovery/error counter but contributes no critical-path timing. |
| Diagnostics | UART/USB/offline storage | Development trace extraction. | Drain asynchronously and rate-limit; never allow trace I/O to block `DRDY`/DMA. |

The SAM E70 family has three TWIHS interfaces and supports I²C Fast Mode (400 kHz). The exact pull-up resistance, voltage level, bus capacitance, address map, reset/recovery topology and whether a peripheral permits clock stretching come from the selected board/device data sheets—not from this document.

## I²C control message shape

Use a small versioned control record; never make I²C a disguised data-acquisition bus:

```text
byte 0       protocol version
byte 1       message type
bytes 2..3   transaction sequence, big-endian
bytes 4..5   payload length, big-endian (bounded)
bytes ...    payload
bytes ...    CRC or device-integrity field if the selected peripheral protocol requires it
```

Rules for a prototype:

1. one owner/task per TWIHS controller; no interrupt handler starts I²C;
2. strict transaction deadline and bus-recovery procedure defined by the actual peripheral data sheet;
3. monotonic transaction/error counters; no retry loop that can run forever;
4. I²C errors surface as health telemetry and never rewrite/alter the AFE stream path;
5. a control setting has an effective-at-frame sequence number in the *local* acquisition domain, rather than relying on I²C completion time;
6. do not put identifiers or raw physiological samples in I²C debug traffic or PTP/observer packets.

## Code in this directory

`latency_trace.[ch]` is a portable C11, allocation-free timestamp ledger. It provides:

- ordered timing points from `DRDY` to optional observer transmit;
- one non-rewriteable value per stage;
- monotonicity and predecessor validation;
- a caller-provided PTP/gPTP clock-health check; and
- no platform registers, packets, sample payloads or feedback policy.

It is intentionally hardware-abstraction-layer agnostic. Wire it to a SAM E70/V71 only after an owner has selected the exact MCU package, Ethernet PHY/switch, analogue-front-end, clock source, isolation boundary, operating system/driver and test plan.

### Minimal integration outline (pseudocode)

```c
/* These routines are board/HAL specific and are intentionally not supplied. */
void on_afe_drdy_irq(void) {
    lt_trace_init(&pending_trace, ++sequence, "PTP-1");
    if (!lt_clock_is_usable(&ptp_health, configured_uncertainty_ns)) {
        record_clock_fault();       /* do not claim a valid latency measurement */
        return;
    }
    (void)lt_trace_mark(&pending_trace, LT_STAGE_DRDY, capture_ptp_timer_ns());
    start_spi_rx_dma();             /* fixed frame length, bounded callback */
}

void on_spi_dma_done_irq(void) {
    (void)lt_trace_mark(&pending_trace, LT_STAGE_SPI_DMA_DONE, capture_ptp_timer_ns());
    queue_fixed_frame_for_local_processing();
}

void local_processing_task(void) {
    /* Versioned, reviewed algorithm goes here; not supplied by this reference. */
    (void)lt_trace_mark(&pending_trace, LT_STAGE_PROCESS_DONE, capture_ptp_timer_ns());
    queue_read_only_observer_telemetry(&pending_trace);
}
```

A production implementation must define overflow behavior, DMA/cache coherency, interrupt priorities, watchdog handling, sequence gaps, fault latching, test hooks, trace integrity, boot-time clock state and formal verification/validation requirements. No code may assume that an ISR timestamp or a PTP lock alone makes a patient-facing action safe.

## Build the host-only timing test

```bash
make -C projects/eeg-timing-reference test
```

The test builds a temporary host executable in `/tmp`, verifies allowed/missing/out-of-order timing transitions and clock-health gating, then leaves no firmware artifact in the repository.

## Evidence ledger

Accessed 2026-09-26. These sources support component/standard capability claims, not a clinical claim or a validated latency budget.

1. **PTP:** [IEEE 1588-2019](https://standards.ieee.org/standard/1588-2019.html) defines precise synchronization for networked measurement/control systems and discusses profile-based use.
2. **gPTP / timing impairments:** [IEEE 802.1AS-2020 record](https://standards.ieee.org/ieee/8802-1AS_2021_Cor_1/11158/) defines LAN timing transport, time-source selection and timing-impairment indication.
3. **Scheduled traffic:** [IEEE 802.1Qbv record](https://standards.ieee.org/ieee/802.1Qbv/6068/) covers enhancements for scheduled traffic; the [IEEE TSN overview](https://standards.ieee.org/wp-content/uploads/2025/10/D1_08_Janos-Farkas-Time-Sensitive-Networking-Standardization.pdf) distinguishes Qbv from the rest of TSN.
4. **MCU candidate:** [Microchip SAM E70/S70/V70/V71 data sheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU32/ProductDocuments/DataSheets/SAM-E70-S70-V70-V71-Family-Data-Sheet-DS60001527.pdf) lists GMAC/DMA, IEEE 1588 PTP frames, 802.1AS timestamping, 802.1Qav shaping and TWIHS; [Microchip’s Atmel acquisition page](https://www.microchip.com/en-us/about/corporate-overview/acquisitions/atmel) establishes the current supplier name.
5. **I²C:** [NXP UM10204](https://www.nxp.com/docs/en/user-guide/UM10204.pdf) is the I²C-bus specification/user manual; [Microchip’s compatibility note](https://onlinedocs.microchip.com/oxy/GUID-89A2670A-012B-4B42-867E-FA7E7D6FFC4A-en-US-1/GUID-BB070CBC-D272-42A3-802A-0D33131999CC.html) documents SAM E70 TWI Fast Mode (400 kHz).
6. **AFE example:** [TI ADS1299 data sheet](https://www.ti.com/lit/ds/symlink/ads1299.pdf) documents the `DRDY` signal and SPI-compatible serial interface for an EEG/biopotential AFE family.
7. **Smart-transducer metadata (not selected for timing):** [NIST’s IEEE 1451 overview](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=822097) describes the family’s transducer-to-microprocessor/network interfaces and TEDS self-description role.
8. **Medical boundary:** [FDA recognized-standard record for IEC 60601-1](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfstandards/detail.cfm?standard__identification_no=44029) describes scope for basic safety and essential performance; the FDA recognized-standards list also identifies IEC 60601-1-10 for physiologic closed-loop controllers.

## Information needed before actual board work

1. Exact AFE part number, channel count, maximum frame size and samples-per-second.
2. Exact SAM E70/V71 part/package (or a different MCU), PHY, oscillator, media converter/SFP module and managed switch model/firmware.
3. Whether the office switch supports PTP transparent/boundary clock, 802.1AS and Qbv; documentation alone is not enough—provide configuration and timestamp reference plane.
4. Whether the intended system is research-only visualization or has a clinical/patient-connected intended use.
5. The approved clock uncertainty limit, maximum permissible local stage timings, overflow behavior and fault response—set by a test/risk plan, not coded as guesses.
