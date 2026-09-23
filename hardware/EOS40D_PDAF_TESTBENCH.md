# Canon EOS 40D PDAF Test Bench Plan

**Status:** hardware research plan, 2026-09-24  
**Project:** CPSAF / Neuro-AF

## 1. Objective

The hardware goal is to replace the autofocus estimator / autofocus-compute block while preserving the rest of the camera ecosystem as far as practical:

```text
real scene
  → Canon phase-detection optics + AF sensor
  → raw / low-level paired phase information
  → CPSAF / HCM
  → Canon EF focus command
  → real EF lens actuator
  → optical feedback
  → digital image ground truth
```

The target is **not** to redesign the lens motor, image sensor, or photographic optics. The experiment should isolate the scientific question:

> Can a hardware-compatible CPSAF/HCM controller infer the required focus correction from real phase-detection measurements and close the loop on a real camera/lens system?

For this purpose, the desired input is as close as possible to the AF sensor's paired pupil-separated line data (A_i[n], B_i[n]), rather than Canon's final defocus/error estimate. The desired output is a direct EF focus command, with the imaging CMOS used only to establish independent focus ground truth.

---

## 2. Why EOS 40D is the current primary donor platform

### 2.1 Architecture

Canon's EOS 40D service documentation describes a dedicated **TTL-CT-SIR AF CMOS sensor** with nine cross-type AF points and a 14.4 µm sensor pitch. The AF sensor is physically separate from the main imaging CMOS and is connected through a distinct **AF-FPC**. This creates a hardware boundary that does not exist as cleanly in modern on-sensor PDAF cameras.

Conceptually:

```text
EF lens
  ↓
main mirror / sub-mirror
  ↓
secondary-image AF optics
  ↓
dedicated AF CMOS
  ↓
AF-FPC / AF front end
  ↓
Canon AF processing
  ↓
EF lens command
```

The research insertion point is between the AF sensor/front end and the Canon AF estimator.

### 2.2 Ground truth

Unlike older film EOS bodies with very accessible discrete AF modules, the 40D is digital. After an autofocus command is applied, the main imaging sensor can capture the final image and provide an independent focus-quality measurement.

For a static target, ground truth should be defined by a local lens-position sweep and a sharpness/MTF maximum, not merely by whether the camera reports AF lock:

```text
controlled lens sweep
  → RAW captures
  → MTF50 / edge response / target contrast
  → q* = best-focus lens position
```

The CPSAF result (hat q) can then be evaluated against (q^*).

### 2.3 Why not use R10 as the primary bench

The Qin et al. spatially-varying autofocus work demonstrates that Canon Dual-Pixel views can be recovered from EOS R10 RAW files, but this route is a file/host acquisition path rather than a low-latency AF-sensor interface. Their prototype reported a severe DP-RAW access bottleneck and later used a machine-vision sensor for real-time work.

R10 therefore remains useful as evidence that Canon DP data can be recovered, but is not the preferred platform for the first direct sensor-to-HCM hardware bench.

### 2.4 Why not start from Sony A7-series

Sony A7-series bodies provide modern focal-plane PDAF, but the phase pixels are integrated into the main imaging sensor and the low-level path is tightly coupled to sensor readout and the BIONZ processing chain. RAW files may preserve PDAF-row artifacts on some models, but this is not equivalent to a real-time calibrated A/B phase stream.

The 40D is less modern optically, but more suitable for hardware interception because the AF sensor, AF optics, AF-FPC, image sensor, and EF actuator remain distinct subsystems.

---

## 3. Primary acquisition route: Canon service / AF Sensor Output path

The most important current lead is that Canon DSLR service software and third-party SPT tooling expose an **AF Sensor Output** diagnostic path.

For the EOS 40D specifically, SPT documents that its 40D autofocus plugin can:

- check the camera's AF sensor output;
- calibrate body AF sensors;
- adjust individual sensors.

SPT's later generic Canon DSLR documentation describes the Sensor Output view as displaying live/raw data from each AF sensor.

This is highly relevant because it suggests that the camera already contains a service path of approximately:

```text
AF CMOS
  → Canon AF front end
  → AF line data / sensor output
  → private service command
  → USB
  → PC diagnostic software
```

### Important limitation

The exact processing level of the service waveform is **not yet established**. “Raw sensor output” may mean:

1. ADC-level line samples;
2. samples after dark/gain/shading correction;
3. another low-level internal representation.

For CPSAF, (1) or (2) are both useful. The project must not claim direct photodiode/ADC access until the service stream is characterized.

The old 40D SPT package is also listed as obsolete / unsupported, so software availability is a practical risk.

---

## 4. USB service-command reverse engineering

If the AF Sensor Output diagnostic can be run, the first engineering target is to reproduce its data stream without depending on the GUI.

### 4.1 Capture procedure

Use a Windows environment compatible with the available 40D service software and record USB traffic while performing controlled UI actions:

```text
EOS 40D
  ↕ USB
USBPcap / equivalent capture
  ↕
Canon/SPT service software
```

Record separate traces for:

- connection / idle;
- opening AF Sensor Output;
- selecting the center AF point;
- selecting other AF points/orientations;
- start / stop sensor-output acquisition;
- changing focus from front-focus → in-focus → back-focus;
- changing scene texture while lens position is fixed.

The working hypothesis is that a Canon vendor-specific PTP/service command returns a repeated fixed-structure payload. This must be demonstrated from traffic; it should not be assumed in advance.

### 4.2 Desired software endpoint

The first useful research API is:

```text
read_40d_af_sensor(...)
    → timestamp
    → sensor / AF-point ID
    → orientation / line ID
    → A[0:N-1]
    → B[0:N-1]
    → optional exposure/gain metadata
```

The immediate objective is **not** high speed. The USB route is a discovery and data-characterization path.

---

## 5. Identifying the actual phase pair

A service waveform should not automatically be labeled “PDAF A/B.” It must be experimentally identified.

### 5.1 Controlled target

Use a high-contrast target with strong content in the appropriate sensor orientation, for example a vertical edge or Siemens-star sector.

Acquire at several known lens offsets:

```text
large front focus
small front focus
best focus
small back focus
large back focus
```

### 5.2 Pair test

For candidate line pair (A[n], B[n]), evaluate horizontal/line displacement, for example with normalized cross-correlation:

```math
d = \arg\max_\tau \sum_n \tilde A[n] \tilde B[n+\tau]
```

A valid phase pair should show:

- disparity approaching zero near best focus;
- opposite disparity sign on opposite sides of focus;
- approximately monotonic magnitude over a local defocus range;
- repeatability under repeated captures.

The test should be repeated across AF points, target orientations, illumination levels, and lenses.

---

## 6. Fallback software route: 40D firmware / Magic Lantern

EOS 40D is a VxWorks-generation body and experimental/unmaintained Magic Lantern ports exist. This provides a second software route if the service USB protocol is inaccessible.

Possible strategy:

```text
AF front end
  → internal RAM / Canon task
  → firmware hook
  → custom buffer dump
```

The current evidence only establishes that user code / experimental Magic Lantern work exists on the 40D. It does **not** establish that an AF sensor dump hook already exists. Therefore this is a reverse-engineering fallback, not a ready-made solution.

---

## 7. Final acquisition route: AF-FPC hardware tap

The long-term real-time bench should bypass the slow service/USB path.

The 40D service manual explicitly shows a separate AF-FPC with IC3301 and associated passive components. The final task is to determine the electrical interface between the AF module/front end and the main camera electronics.

### 7.1 Do not probe blind

Use the service-output waveform as a known reference:

```text
                     ┌→ USB service output → known waveform
AF CMOS → AF-FPC ────┤
                     └→ oscilloscope / logic analyzer
```

While moving a known edge or sweeping defocus, look for AF-FPC nodes whose electrical waveform changes synchronously with the service waveform.

### 7.2 Characterization targets

Determine:

- analog versus digital output;
- supply and I/O voltage domains;
- sensor integration / reset control;
- clock(s);
- frame / line synchronization;
- sample width and ordering;
- mapping from electrical stream to AF point / orientation;
- gain/exposure control;
- update period and timing jitter.

Only after this mapping is known should an FPGA/ADC interface be designed.

### 7.3 Preferred final input boundary

The preferred CPSAF boundary is:

```text
AF CMOS
  → necessary sensor AFE / correction
  → A_i[n], B_i[n]
  → CPSAF / HCM
```

There is no scientific requirement to replace Canon's sensor biasing, integration control, ADC, or fixed-pattern correction if those functions are not part of the AF estimator being studied.

---

## 8. Lens-output interface

The output side is substantially more accessible than the sensor side.

Public EF reverse engineering documents a synchronous body↔lens protocol and, on tested lenses, a relative focus command of the form:

```text
0x44 HH LL    relative signed focus movement
0x05          focus toward one limit
0x06          focus toward the other limit
```

The exact behavior must be calibrated per lens; protocol notes from a tested lens must not be assumed universal without measurement.

Two actuator phases are proposed:

### Phase A — body-mediated actuation

Use the Canon body or a host command path to move the lens while sensor acquisition is being established. This is acceptable for functional validation.

### Phase B — direct EF controller

Use MCU/FPGA hardware to communicate directly with the EF lens:

```text
CPSAF / HCM
  → focus correction
  → MCU / FPGA EF interface
  → EF lens MCU
  → USM / STM actuator
```

This removes Canon's autofocus estimator while preserving the real Canon lens actuator.

---

## 9. Ground-truth protocol

Ground truth must be independent of the PDAF estimator under test.

Recommended static protocol:

1. fix camera, target, illumination, aperture, and focal length;
2. command a dense local focus sweep around the expected optimum;
3. capture main-sensor RAW frames;
4. compute an image-domain sharpness metric at the target ROI;
5. optionally compute slanted-edge MTF50 or equivalent target-based resolution;
6. fit/interpolate the peak to obtain (q^*);
7. reset the lens to controlled starting positions;
8. run Canon AF and CPSAF/HCM separately;
9. compare final lens position/image quality to (q^*).

Dynamic experiments can later use a motorized target/rail with known trajectory, but static repeatability should be established first.

---

## 10. Latency boundaries

USB service access is **not** the latency benchmark.

The total loop should be decomposed as:

```text
T_AF =
  T_sensor/integration
+ T_readout
+ T_frontend
+ T_CPSAF
+ T_command
+ T_actuator
+ optical settling
```

Three timings should be reported separately:

1. **estimator/HCM latency** — input-valid to output-valid;
2. **sensor-to-command latency** — useful AF sample available to EF command issued;
3. **closed-loop optical settling** — target/defocus change to image-plane focus within tolerance.

The final AF-FPC tap is required to measure the first two without the artificial delay of diagnostic USB transport.

---

## 11. Experimental phases and gates

| Phase | Task | Exit criterion |
|---|---|---|
| P0 | Acquire one working 40D and preferably one donor body | repeatable normal AF + RAW capture |
| P1 | Recover service AF Sensor Output | live AF waveforms visible |
| P2 | USB capture and command replay | custom host code returns repeatable sensor arrays |
| P3 | Identify phase-pair semantics | front/back sign + near-zero disparity at GT focus |
| P4 | Correlate USB data with AF-FPC nodes | electrical stream mapped to line data |
| P5 | Build direct AF-FPC acquisition | repeatable real-time (A_i,B_i) capture |
| P6 | Establish direct EF control | deterministic command→lens response |
| P7 | Insert CPSAF/HCM | sensor→HCM→EF closed loop works |
| P8 | Quantitative comparison | accuracy, settling, hunting, latency measured against GT |

Strong camera-level claims require completion of P5–P8.

---

## 12. Data format to freeze early

A hardware-neutral record format should be defined before reverse engineering diverges into several capture methods.

Suggested logical record:

```text
AFSample
  timestamp
  camera_body
  lens_id
  aperture
  AF_point
  AF_orientation
  sensor_exposure_or_gain_if_known
  A[N]
  B[N]
  electrical_source = service_usb | firmware_hook | af_fpc
  processing_level = unknown | corrected | adc_like | ...
  lens_command
  lens_state_if_available
  image_gt_id
```

This allows service-USB, firmware-hook, and AF-FPC data to be compared without changing the CPSAF training/evaluation interface.

---

## 13. Principal risks

- SPT 40D software is obsolete and may be difficult to obtain/run.
- “Raw AF Sensor Output” may be corrected/processed data rather than direct ADC samples.
- The service protocol may provide diagnostic snapshots at low rate rather than the native AF update stream.
- AF-FPC signals may use undocumented timing or an integrated front-end protocol.
- EF focus-step magnitude is lens-dependent and may show hysteresis/backlash.
- DSLR phase AF and modern on-sensor Dual-Pixel/PDAF have different observation statistics; 40D validates a general phase-sensing controller, not by itself a modern focal-plane-PDAF ASIC replacement.
- The main-sensor GT must be measured independently and should not use Canon AF-lock status as truth.

---

## 14. Immediate next actions

1. Obtain a working 40D and a donor body if possible.
2. Archive the EOS 40D service manual and AF-FPC diagrams locally for bench use.
3. Attempt to recover/run the 40D service/SPT AF Sensor Output path.
4. Capture controlled front-focus / best-focus / back-focus waveforms.
5. Record USB traffic and isolate the sensor-output request/response.
6. Freeze the (A/B) dataset format and build an offline decoder.
7. Only after the USB waveform is understood, begin AF-FPC probing.
8. In parallel, build a minimal EF protocol controller and characterize one chosen EF lens.

---

## 15. References / evidence

- Canon EOS 40D service documentation: dedicated AF CMOS, nine cross-type points, 14.4 µm pitch, separate AF-FPC:  
  https://www.manualslib.com/manual/3072741/Canon-Eos-40d.html
- SPT EOS 40D autofocus plugin: explicitly lists “Check the camera's AF Sensors output”:  
  https://www.spt.info/sptstore.php/canon-eos-40d/software-canon-eos-40d-upgrade
- SPT Canon DSLR Sensor Output documentation: describes live/raw AF-sensor diagnostic data:  
  https://www.spt.info/sptstore.php/news/2026/06/24/af-sensor-outputs-in-canon-dslrs
- Experimental Canon 40D Magic Lantern / VxWorks work:  
  https://www.magiclantern.fm/forum/index.php?topic=1452.375  
  https://github.com/jmheder/ml
- Public Canon EF protocol reverse engineering, including focus commands on tested lenses:  
  https://gist.github.com/marcan/858c242db2fc595da1e0bb70a05192fc

---

## 16. Current decision

The present hardware strategy is therefore:

```text
First:
40D service USB
  → understand / label real AF sensor line data
  → build dataset and functional CPSAF loop

Then:
AF-FPC tap
  → native-rate A/B acquisition
  → HCM
  → direct EF command
  → real lens
  → main-sensor image GT
```

This sequence reduces reverse-engineering risk while preserving the final scientific target: a direct real-PDAF-sensor → hardware controller → real-lens autofocus loop.
