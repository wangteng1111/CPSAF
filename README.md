# CPSAF / Neuro-AF

**Continuous phase-sensing autofocus with hardware-compatible neural control.**

CPSAF studies whether the inner autofocus loop can be replaced by a fast learned hardware controller while keeping the real optical sensor and lens ecosystem. The target is not “fast neural inference” in isolation, but a complete closed-loop system:

~~~text
scene / target motion
  → PDAF / Dual-Pixel observation
  → sensor readout
  → CPSAF / HCM controller
  → lens command
  → real lens actuator
  → new optical observation
~~~

The project therefore treats autofocus as a **closed-loop sensing–decision–actuation problem**. Subject selection / identity tracking are separate outer-loop problems; CPSAF currently targets the phase-to-lens inner loop.

---

## Current research status

| Area | Current state |
|---|---|
| Academic AF reconstruction | **Protocol reconstructed; official-data numerical validation still open** |
| Unified DP/phase simulation | **v0.1 software loop closed and smoke-tested** |
| HCM-compatible controller | fixed feed-forward / crossbar prototypes exist; scaling is intentionally secondary to validation |
| Real-camera hardware | **Canon EOS 40D selected as the primary first-generation test bench** |

### 1. Zhu / Herrmann validation

Canonical work: [zhu_herrmann/validation_v0_5/](zhu_herrmann/validation_v0_5/)

Frozen/reconstructed elements include the 49 LearnAF focal states, 97 relative actions, 128×128 patches, Zhu stride-96 extraction, all-49-start evaluation, Choi AFPE [L,R,f,x,y], RoI/Lens positional encodings, squared-distance SORD, and the 5-channel / 97-class MobileNetV2 plumbing.

The remaining gate is **official-data numerical reproduction**: mount/audit the authoritative LearnAF release, freeze the confidence-filter rule, reproduce the published sample counts, and reproduce the single-step benchmark. A provenance discrepancy is tracked explicitly: Herrmann reports 460/50 train/test stacks whereas the currently documented public archive reports 351/47 focal sweeps.

### 2. Unified AF simulator

Canonical environment: [unified_af/v0_1/](unified_af/v0_1/)

The simulator bridges real Dual-Pixel focal-stack observations to a continuous closed-loop lens plant:

~~~text
target truth
  → defocus-equivalent A/B focal-stack replay
  → raw DP observation
  → calibrated phase/defocus bridge or learned raw-DP controller
  → readout + compute delay
  → continuous lens plant
  → next A/B observation
~~~

Key design choices:

- continuous interpolation of measured 49-slice DP stacks;
- motion represented in **diopter space**, not raw focus-index displacement;
- transparent reference estimator: horizontal-gradient NCC + empirical monotone disparity→defocus LUT;
- separate calibration and held-out stacks;
- explicit sensor sampling, readout, compute delay, command scheduling and actuator dynamics;
- raw A/B images remain available so HCM can bypass the reference decoder.

Current deterministic smoke results are software/observability checks only:

| Test | v0.1 smoke result |
|---|---:|
| held-out sensor MAE | 0.0303 focus index |
| held-out sensor RMSE | 0.0384 focus index |
| 8→40 step settling | 7.28 ms |
| oracle step settling | 7.14 ms |
| 10 Hz tracking RMSE | 0.262 D |

These are **not** LearnAF reproduction results and **not** Canon hardware results.

### 3. HCM / crossbar controller work

Existing work under [hcm_controllers/](hcm_controllers/) and [meta_latency/](meta_latency/) includes:

- Acquire–Track–Hold teacher experiments;
- fixed feed-forward crossbar MLP prototypes;
- raw-tap inputs using short error/lens histories;
- 5 kHz static, step, sinusoidal, mixed-motion and confidence-dropout tests;
- latency/actuator meta-tests.

The retained conclusion is:

~~~text
AF performance ≠ compute latency alone
~~~

Useful hardware latency must survive sensor-readout, command, actuator and optical-settling limits. Large HCM scaling therefore remains downstream of simulator and camera validation.

---

## Real-camera direction: Canon EOS 40D

The current hardware plan is documented in:

**[hardware/EOS40D_PDAF_TESTBENCH.md](hardware/EOS40D_PDAF_TESTBENCH.md)**

The 40D is preferred over the R10 and Sony A7-series for the first hardware bench because it combines:

- a **dedicated phase-detection AF CMOS** and separate AF-FPC;
- a digital imaging sensor for independent focus ground truth;
- the Canon EF lens ecosystem;
- a substantially more accessible separation between AF sensing, AF computation and lens actuation.

The present acquisition strategy is:

~~~text
Phase 1:
40D AF sensor
  → Canon/SPT service AF Sensor Output
  → USB capture / service-command reverse engineering
  → identify A_i[n], B_i[n]

Phase 2:
AF-FPC hardware tap
  → native-rate phase data
  → CPSAF / HCM
  → direct EF controller
  → EF lens
  → main-sensor image ground truth
~~~

The service/USB path is a **discovery and labeling path**, not the final latency benchmark. The final timing experiment must use the AF-FPC/native sensor boundary and report estimator latency, sensor-to-command latency, and full optical settling separately.

---

## Validation roadmap

1. **Gate A — academic reproduction:** reproduce Zhu/Herrmann on authoritative LearnAF data.
2. **Gate B — real-stack sensing:** validate the DP disparity/defocus bridge on held-out real focal stacks.
3. **Gate C — 40D sensor access:** recover AF Sensor Output, reverse the service USB stream, and identify paired phase line data.
4. **Gate D — real actuator model:** characterize EF command→lens-position dynamics, deadband, reversal and repeatability.
5. **Gate E — direct hardware loop:** AF-FPC → HCM → EF lens.
6. **Gate F — comparative camera test:** run Canon AF and CPSAF from matched starting conditions and evaluate final focus, settling, hunting and failure probability against independent image-plane ground truth.

Strong camera-level claims require the later gates; synthetic or service-USB results must not be relabeled as real-time hardware validation.

---

## Repository layout

~~~text
CPSAF/
├── README.md
├── hardware/
│   └── EOS40D_PDAF_TESTBENCH.md       # current real-camera plan
├── zhu_herrmann/
│   ├── v0_4/
│   └── validation_v0_5/               # frozen academic validation gates
├── unified_af/
│   └── v0_1/                          # DP observation + continuous plant
├── hcm_controllers/
│   └── v0_3_crossbar/
├── meta_latency/
│   └── v0_1/
├── benchmarks/
├── artifacts/
└── archive/
~~~

### Unified simulator quick start

~~~bash
cd unified_af/v0_1
pip install -r requirements.txt
python test_unified_env.py
python run_smoke_validation.py
~~~

---

## Project principle

The intended contribution is a **hardware-compatible learned fast inner autofocus loop** whose benefit remains measurable after real sensing, readout, lens dynamics and optical feedback are included.

The project currently has a closed software loop and a defined Canon 40D hardware path. The next decisive milestones are official LearnAF reproduction and direct characterization of the 40D AF Sensor Output / AF-FPC interface.
