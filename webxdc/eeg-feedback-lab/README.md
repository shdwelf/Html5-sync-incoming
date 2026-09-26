# EEG Feedback Lab — webxdc package

A self-contained **research/simulation** companion to [`docs/EEG_PATHWAYS_RESEARCH_AND_RECONSTRUCTION.md`](../../docs/EEG_PATHWAYS_RESEARCH_AND_RECONSTRUCTION.md).

## What it does

- generates a bounded, single-channel synthetic signal at 256 Hz;
- draws an in-memory 10-second trace;
- calculates an intentionally labelled **illustrative** 8–12 Hz projection;
- exposes a visual-only threshold state, event log, sequence-gap counter, and display timing;
- allows an opt-in `wss://` **browser-mode** development observer stream that follows the documented `eeg-feedback-lab/v1` frame schema;
- in webxdc only, shares deliberately initiated **non-sensitive marker events** through the normal messenger API.

## What it does not do

It does **not** acquire electrodes, control a device, assess signal quality/impedance/artifact, identify or diagnose any condition, select a treatment, create audio/tactile stimulation, store participant records, or transport raw samples through webxdc. It is not a medical device or latency guarantee.

Webxdc apps are network-isolated. The normal `sendUpdate()` API is a collaboration/state mechanism with host-controlled throttling, not an EEG transport. Any future clinical feedback loop needs to stay at an approved acquisition edge; remote displays are observer-only.

## Build and validate

From the repository root:

```bash
python3 webxdc/webxdc_tool.py pack webxdc/eeg-feedback-lab webxdc/eeg-feedback-lab/dist/eeg-feedback-lab.xdc
python3 webxdc/webxdc_tool.py validate webxdc/eeg-feedback-lab/dist/eeg-feedback-lab.xdc
```

Or use `webxdc/build-all.sh` to rebuild all standalone packages.

## Development frame schema

The browser-only WebSocket control is deliberately opt-in, requires `wss://`, and rejects unbounded or identifying frame shapes. A development sender must send JSON like:

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

This contract is **not** a device integration specification. The app accepts one short non-identifying channel label, 32–2048 Hz, 1–1024 finite samples and an increasing sequence. The source timestamp only becomes a possible arrival-age estimate after a separate clock-sync validation; it cannot establish end-to-end latency.

No application code initiates a gateway connection automatically. Inside webxdc, the controls are disabled and no raw sample is included in a `sendUpdate()` payload.
