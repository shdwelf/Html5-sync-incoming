# EEG Pathways / Neuropathways research and reconstruction brief

**Prepared:** 2026-09-26 (UTC)

**Scope:** historical-source review, a functional reconstruction plan, and the safety/transport boundary for the companion `webxdc/eeg-feedback-lab/` demonstrator.

> **Important boundary.** This is an archival and software-design investigation, **not** a medical-device reconstruction, clinical protocol, diagnosis tool, or treatment recommendation. The accompanying app processes generated data by default, has no device-control capability, does not send EEG samples through webxdc, and labels its visual threshold indicator as unvalidated. A licensed clinician and a qualified regulatory/quality team must own any clinical use.

## Executive finding

The query appears to combine two different names:

- The archived historical site is **Neuropathways EEG Imaging** at `neuropathways.com`, not a site captured as `eegpathways.com` or `eegpathways.org`.
- The sources spell the inventor's name **Margaret E. Ayers** (not “Ayres”).
- The book title is **_Whispers From The Brain_**, not “Whispers from the Mind.”

Internet Archive's CDX index has no successful captures for `eegpathways.com` or `eegpathways.org` as checked on the preparation date. It does preserve a substantial `neuropathways.com` site beginning in 1998. The original pages state both a 1997 copyright notice and a registered trademark claim. This project therefore does **not** copy its artwork, logo, layout, claims, or wording. It makes an independently designed, clearly non-clinical implementation of the *functional ideas evidenced in the patents*: acquisition → digital processing → selected-band display → threshold/event → visual feedback → session log.

## Claim check: what the accessible sources do and do not support

| Statement to check | Finding | Evidence and interpretation |
| --- | --- | --- |
| “Margaret Ayres EEG patent” | **Substantiated with corrected spelling.** | Google Patents identifies **Margaret E. Ayers** as inventor on [US 4,919,143](https://patents.google.com/patent/US4919143A/en) and **Margaret A. Ayers** on [US 5,024,235](https://patents.google.com/patent/US5024235A/en). Both describe bioelectrical/EEG feedback apparatuses. |
| The historical system was digital, used thresholds and visual/auditory feedback. | **Substantiated as an invention/site description.** | The two patents describe electrodes, amplifier, A/D conversion, selection/analysis, thresholding, visual/audio signalling and storage. The [archived equipment page](https://web.archive.org/web/20001018025627id_/http://www.neuropathways.com/equipment.html) describes a one-channel differential input and contemporaneous computer designs. This documents claims/design intent; it is not independent validation of efficacy. |
| It could use a visual sequence/game as feedback. | **Substantiated by US 5,571,057.** | [US 5,571,057](https://patents.google.com/patent/US5571057A/en) describes changing visual-image sequences according to a thresholded bioelectrical signal. The app's visual-only demo is inspired by that interaction pattern, not a reproduction of the patented apparatus or a clinical training claim. |
| Penny Montgomery was Ayers's collaborator. | **Substantiated.** | [New Hope for the Brain’s biography](https://newhopeforthebrain.com/about/) says Montgomery co-authored _Whispers From The Brain_ with Ayers in 2007. A 2011 [tribute](https://zekeunlimited.wordpress.com/2011/08/29/82/) calls Montgomery Ayers's “friend, companion and colleague.” |
| Penny Montgomery “lived with” Ayers. | **Not established by sources reviewed.** | The tribute supports “friend, companion and colleague,” but I found no reliable primary/official source that establishes a shared residence. This personal detail is excluded from the app and should not be published as fact without an appropriate source/permission. |
| Montgomery has a business called “Whispers from the Mind.” | **Not supported; title/name corrected.** | The current official site identifies the co-owned practice as **New Hope for the Brain** and the book as _Whispers From The Brain_. It does not identify a business named “Whispers from the Mind.” |
| The 1997–2000 site proves sub-millisecond end-to-end clinical feedback latency. | **Not established.** | The archived site *claims* “less than one thousandth of a second,” but it is marketing/first-party material. The archived hardware specification does not yield a complete, independently tested latency budget (ADC, filter/window, decision, graphics/audio, monitor/speaker). It must not be recast as a measured guarantee. |

## Primary historical materials

### Patent family / related patent

| Patent | Issued / status reported by Google Patents | What it documents | Design relevance |
| --- | --- | --- | --- |
| [US 4,919,143 — *Electroencephalic neurofeedback apparatus and method for bioelectrical frequency inhibition and facilitation*](https://patents.google.com/patent/US4919143A/en) | 1990-04-24; Google Patents reports “Expired – Lifetime” | Analog signal input, A/D conversion, numerical frequency analysis, thresholds, visual/auditory signalling, artifact suppression and recording. | The core acquisition → process → threshold → feedback → record loop. |
| [US 5,024,235 — same title](https://patents.google.com/patent/US5024235A/en) | 1991-06-18; Google Patents reports “Expired – Lifetime” | A closely related later application with the same broad feedback architecture and display/review discussion. | A historical implementation reference, not a licence, clearance determination, or instructions for use. |
| [US 5,571,057 — *Apparatus and method for changing a sequence of visual images*](https://patents.google.com/patent/US5571057A/en) | 1996-11-05; consult USPTO for authoritative legal status | A thresholded bioelectrical signal changes visual-image sequences; it describes visual, auditory or tactile signalling and artifact suppression. | The visual feedback **interaction**, represented here only with simulation and no therapeutic claim. |

**Legal note.** Google’s legal-status labels are explicitly non-authoritative. Patent expiry does not clear trademarks, copyrighted historical webpages/artwork, privacy/personality rights, device regulation, or other patents. Confirm status, ownership, and freedom to operate through counsel/USPTO records before a product decision.

### What the original site records

The [1998 homepage capture](https://web.archive.org/web/19980109021836id_/http://neuropathways.com/) and [2006 homepage capture](https://web.archive.org/web/20060515060841id_/http://www.neuropathways.com/) list the site sections and claims. The [2000 technology overview](https://web.archive.org/web/20001017215629id_/http://www.neuropathways.com/technology.overview.html) describes raw/filtered waveform presentation, a threshold concept, visual/auditory reinforcement, minute statistics, notes, storage and printout. The [2000 equipment page](https://web.archive.org/web/20001018025627id_/http://www.neuropathways.com/equipment.html) provides the following historical system specification:

- single-channel bipolar differential input;
- claimed common-mode rejection `>110 dB` wideband and `>120 dB @ 60 Hz`;
- 22 MΩ stated input impedance; `<0.50 µV` stated noise; `<10 µA` stated leakage current;
- stated 1–30 Hz frequency response;
- 12-bit A/D sign-extended to 16-bit and real-time digital filtering;
- period desktop/notebook designs based on Pentium 233 MMX systems, Windows 3.11/32-bit Windows, CRT/TFT displays and Sound Blaster-compatible audio.

Those are historical, first-party stated specifications, **not measurements verified by this project**. We intentionally do not replicate the original 1990s brand, logo, copied page text, images, clinical claims, or obsolete operating environment.

The archived [publication list](https://web.archive.org/web/20001006054158id_/http://neuropathways.com/publication.list.html) is useful as an index of authored/cited material. Titles alone do not establish study quality, outcomes, or clinical recommendations; each paper must be obtained and appraised independently before being used to substantiate a health claim.

## Books and attributable publications

| Work | Attribution / source check | Notes |
| --- | --- | --- |
| _Whispers From The Brain_ (2007) | New Hope for the Brain’s [about page](https://newhopeforthebrain.com/about/) says Penny Montgomery co-authored it with Margaret Ayers. | Official biography identifies it as a neurofeedback textbook illustrating raw brainwave patterns/clinical conditions. Do not reuse pages, figures or protocol material without copyright permission. |
| _Whispers From The Brain: An Illustrated Guide to the Morphology of Brainwaves_, 2nd ed. (2019) | The [same official biography](https://newhopeforthebrain.com/about/) names Penny Montgomery and Glenda Lippmann as co-authors. The [training page](https://newhopeforthebrain.com/services/educational-services/) says it was updated to cover 30 conditions. | This is a training text claim from its owners, not an independently verified diagnostic catalogue. The app does not map waveforms to conditions. |
| _Clinical Biofeedback: A Procedural Manual for Behavioral Medicine_, editions 1 and 2 (1979, 1982) | Listed in Montgomery’s [official biography](https://newhopeforthebrain.com/about/) as co-authored with Kenneth Gaarder. | Bibliographic lead; verify editions/ISBNs in a library catalogue before formal citation. |
| “Neurofeedback for Cerebral Palsy” (2004) | [ISNR-hosted Journal of Neurotherapy text](https://isnr-jnt.org/article/view/16960/10882) gives Margaret E. Ayers, *Journal of Neurotherapy* 8(2), pp. 93–94, DOI 10.1300/J184v08n02_07. | The article itself says controlled research did not exist for CP; it is not grounds to turn this app into a treatment tool. |
| “The legacy of Margaret Ayers” (2019) | [ScienceDirect chapter record](https://www.sciencedirect.com/science/article/abs/pii/B9780128176597000038) identifies Penny S. Montgomery as author, in _Neurofeedback: The First Fifty Years_. | A secondary historical source; acquire/read the chapter rather than inferring claims from the abstract. |

## Functional reconstruction — deliberately limited

The original patents and archived pages support the following **conceptual** system decomposition:

```text
isolated acquisition hardware
   → amplification / anti-aliasing / A-D conversion
   → acquisition-node quality checks + artifact policy
   → raw, append-only sample store
   → explicitly versioned signal-processing policy
   → non-diagnostic visual/auditory feedback policy
   → local display / session record
   → optional remote observer mirror
```

The repository’s new `EEG Feedback Lab` package implements only the shaded application-side ideas in a simulation:

1. bounded incoming-frame validation;
2. short in-memory trace rendering;
3. an **illustrative**, non-diagnostic 8–12 Hz window indicator;
4. a visual-only demo cue and a clear cue-state display;
5. sequence-gap, buffer and local render/processing timing telemetry;
6. an optional browser-mode WebSocket observer bridge with no automatic connection; and
7. explicit, non-sensitive session-marker sharing through `webxdc.sendUpdate()`.

It does **not** acquire from electrodes, enforce electrode placement, assess impedance, compensate artifacts, identify a condition, choose a protocol, make a treatment decision, send an audio/tactile stimulus, control hardware, persist participant data, or share raw EEG samples through a messenger.

## Fibre-office latency: architecture decision

A fibre link lowers transport delay but does not, by itself, establish a safe feedback latency. The important number is the end-to-end distribution:

```text
sample acquisition + ADC
+ packet/frame accumulation
+ edge quality/processing
+ queueing and network jitter
+ browser decode/render scheduling
+ display/audio device latency
= feedback event latency
```

### Recommended split

| Plane | Location | Responsibility | Latency role |
| --- | --- | --- | --- |
| Acquisition and feedback edge | In the office, physically adjacent to the approved acquisition hardware | Hardware isolation, signal-quality checks, timestamping, raw data custody, clinician-approved feedback decision, local feedback output and safety stop. | This is the only candidate location for any time-critical feedback loop. It avoids making fibre/WAN/browser/webxdc delivery part of that loop. |
| Observer/operations mirror | Office LAN or a specifically authorised remote endpoint | Read-only waveform/status mirror, session notes, QA and audit telemetry. | Remote display delay is measured and labelled; it never gates or creates feedback. |
| webxdc collaboration | Messenger chat | Explicit, non-identifying session markers and collaboration notes only. | **Not a sample transport.** It is eventual/offline-capable state sharing, not a medical realtime transport. |

### Why webxdc is not the fibre data plane

Webxdc documentation says apps run in an isolated web view with no internet access and share state through the host messenger. The normal [`sendUpdate`](https://webxdc.org/docs/spec/sendUpdate.html) channel has a host-provided rate interval; apps must assume 10 seconds if a host does not expose one. There is an [experimental `joinRealtimeChannel`](https://webxdc.org/docs/spec/joinRealtimeChannel.html), but it is private to chat participants, ephemeral, host-dependent, and supplies no safety or latency SLA. Neither is a sound basis for a clinical closed loop or office-fibre sampling stream.

The app therefore uses webxdc only for manually initiated, non-sensitive markers. When opened in an ordinary browser (not webxdc), a user can opt into a secure WebSocket **observer** gateway for synthetic/de-identified frame development. The UI rejects that connection inside webxdc and warns that it cannot form a clinical feedback loop.

### Measurement plan before any hardware integration

1. **Define the use case and acceptance criterion first.** Specify whether it is visualization, research observation, or a regulated feedback function; do not borrow an old “real time” claim.
2. **Instrument each boundary.** Have the acquisition edge attach a monotonic sequence and a calibrated source timestamp; record decision time, gateway send/receive time, browser decode, and display-present estimate. Use PTP/NTP discipline where cross-host comparisons are required, and record clock uncertainty.
3. **Test the whole distribution.** Measure p50/p95/p99 and maximum under sustained load, reconnects, packet loss, browser backgrounding, display sleep, and link failover. A fibre ping is insufficient.
4. **Make the edge fail safe.** On stale frame, sequence gap, bad signal quality, clock uncertainty, queue growth, gateway disconnect, or out-of-range latency, suppress the feedback event and surface an operator-visible fault. The remote screen must never conceal a local fault.
5. **Validate data integrity.** Authenticate mutually, encrypt in transit, place the gateway on a segmented network, authorize roles, keep immutable audit logs, minimize identifiers, and run a threat model. Clinical data introduce HIPAA/privacy/security obligations in the applicable jurisdiction.
6. **Run human-factors and clinical/regulatory review.** The FDA’s [software-functions guidance](https://www.fda.gov/media/80958/download) notes that intended diagnostic/treatment use and use as/accessory to a device matter, regardless of platform. FDA’s [device-regulation overview](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/overview-device-regulation) lists registration/listing, premarket pathways where applicable, quality-system, labeling and reporting obligations. The QMSR became effective on 2026-02-02. Obtain regulatory and legal advice; this is not one.

### Timing-bus follow-on

The portable, host-tested reference in [`projects/eeg-timing-reference/`](../projects/eeg-timing-reference/) now records the acquisition-edge timing path without becoming an AFE driver or feedback controller. Its design conclusion is: PTP (IEEE 1588) at hardware timestamp boundaries; gPTP/802.1AS only over a verified TSN-capable LAN; SPI + `DRDY` + DMA for an EEG AFE data stream; and I²C/TWIHS only for non-critical board management. It identifies the Microchip SAM E70/V71 family as a candidate because its GMAC advertises PTP/802.1AS timestamping, but explicitly notes that its documented 802.1Qav credit-based shaper is **not** 802.1Qbv time-aware scheduling. The actual MCU, AFE, PHY, fibre switch and acceptance limits still need owner selection and validation.

## Incoming frame contract for a future *read-only development gateway*

The package documents and enforces a narrow JSON development contract, intentionally not an equipment protocol:

```json
{
  "protocol": "eeg-feedback-lab/v1",
  "type": "frame",
  "seq": 42,
  "sample_rate_hz": 256,
  "channel": "SIM-CH1",
  "sent_at_unix_ms": 1760000000000,
  "samples_uv": [1.2, 2.1, 0.8]
}
```

Constraints enforced by the app: exactly one bounded channel label, sample rate 32–2048 Hz, up to 1024 finite samples per frame, monotonically increasing sequence (gaps reported), and no participant ID, name, diagnosis, or treatment parameter. `sent_at_unix_ms` can only provide an **arrival-age estimate** after an explicit clock-synchronization validation; it is not a latency guarantee. A production integration needs a separately versioned, authenticated, quality-controlled protocol and a device/software validation plan.

## Source ledger

All links were accessed 2026-09-26 UTC. Source types are intentionally visible so that historical owner claims are not mistaken for independent clinical evidence.

1. **Patent text (primary patent record):** [US 4,919,143](https://patents.google.com/patent/US4919143A/en), [US 5,024,235](https://patents.google.com/patent/US5024235A/en), [US 5,571,057](https://patents.google.com/patent/US5571057A/en).
2. **Internet Archive / Wayback Machine (primary archival capture):** [1998 homepage](https://web.archive.org/web/19980109021836id_/http://neuropathways.com/), [2000 technology page](https://web.archive.org/web/20001017215629id_/http://www.neuropathways.com/technology.overview.html), [2000 equipment page](https://web.archive.org/web/20001018025627id_/http://www.neuropathways.com/equipment.html), [2000 publication list](https://web.archive.org/web/20001006054158id_/http://neuropathways.com/publication.list.html), [2006 homepage](https://web.archive.org/web/20060515060841id_/http://www.neuropathways.com/).
3. **Current owner/practice site (first-party biography and book information):** [New Hope for the Brain — About](https://newhopeforthebrain.com/about/), [Educational Services](https://newhopeforthebrain.com/services/educational-services/).
4. **Journal text:** [Ayers (2004), “Neurofeedback for Cerebral Palsy”](https://isnr-jnt.org/article/view/16960/10882). This document expressly prohibits redistribution/derivative works; this memo provides only a bibliographic note and paraphrase.
5. **Secondary historical reference:** [Montgomery (2019), “The legacy of Margaret Ayers”](https://www.sciencedirect.com/science/article/abs/pii/B9780128176597000038).
6. **Webxdc platform constraints:** [Get Started](https://webxdc.org/docs/get_started.html), [`sendUpdate`](https://webxdc.org/docs/spec/sendUpdate.html), [`joinRealtimeChannel`](https://webxdc.org/docs/spec/joinRealtimeChannel.html).
7. **U.S. regulation:** [FDA software-functions guidance](https://www.fda.gov/media/80958/download), [FDA device-regulation overview](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/overview-device-regulation).

## Handoff questions requiring the requester/clinical owner

1. What **exact domain or Internet Archive snapshot URL** was intended by “eegpathways”? If it is not `neuropathways.com`, provide it so the historical record can be corrected.
2. Is the intended deployment research visualization, clinician-supervised wellness, or a regulated diagnostic/treatment workflow? This changes the product boundary and evidence work substantially.
3. Which acquisition hardware/vendor, signal format, channels, sampling rate, local safety controls, and office topology are in scope? The package intentionally contains no driver and assumes none.
4. Who is the clinical, regulatory, security/privacy, and data-governance owner? No live sampling should begin until those roles and validation acceptance criteria are named.
5. Is permission available to use any trademark, website artwork, book text/figures, historical device photos, or personal narrative? This implementation deliberately uses none.
