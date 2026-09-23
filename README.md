# CPSAF / Neuro-AF

**Continuous phase-sensing autofocus with hardware-compatible neural control.**

This repository contains the autofocus research line of Neuro-AF: simulation environments, academic benchmark reconstruction, dynamic closed-loop control models, hardware-compatible HCM/crossbar controller prototypes, validation tooling, and the current path toward real-camera experiments.

The central research question is not whether neural inference can be made extremely fast in isolation, but whether a complete autofocus loop can benefit from a high-bandwidth learned controller when the full chain is considered:

```text
optical scene / target motion
        ↓
PDAF / Dual-Pixel observation
        ↓
sensor readout + signal representation
        ↓
hardware-compatible neural controller
        ↓
command/interface latency
        ↓
lens actuator dynamics
        ↓
new optical observation
```

Accordingly, the project now treats autofocus as a **closed-loop sensing–decision–actuation problem** rather than a compute-latency benchmark.

---

## Current project status

The project is organized into three validation stages.

### Stage 1 — Validate the academic AF environment

Canonical validation layer: `zhu_herrmann/validation_v0_5/`.

Current status:

> **Protocol validated + provenance audited; official-data numerical validation pending.**

Already reconstructed/frozen:

- 49 LearnAF focal states and the official focus-distance table;
- 128×128 patches and Zhu stride-96 extraction;
- all-49-start expansion;
- relative action `GT-current`, range `[-48,+48]`, 97 classes;
- Choi AFPE `[L,R,f,x,y]` conventions;
- RoI-PE / Lens-PE conventions;
- squared-distance SORD with `T=1`;
- MobileNetV2 5-channel / 97-class parameter count and training plumbing;
- strict provenance and validation gates.

Open data-level gate:

- mount and audit the official LearnAF release;
- resolve or freeze the confidence-filtering rule;
- reproduce Zhu's reported 68,187 / 7,805 spatial-stack counts;
- run the 10k relative-label MobileNetV2 baseline;
- reproduce the published single-step metrics within the frozen tolerance policy.

A first-class provenance discrepancy is tracked explicitly: Herrmann reports 460/50 train/test stacks, while the current public LearnAF archive documents 351/47 focal sweeps. This difference must not be silently normalized away.

### Stage 2 — Unified DP-image + dynamic closed-loop simulation

Canonical bridge environment: `unified_af/v0_1/`.

This closes the previous software gap between:

```text
Herrmann / Zhu:
real DP focal-stack observations + discrete/static lens states
```

and

```text
CPSAF dynamic simulator:
continuous lens plant + synthetic signed focus error
```

The new unified loop is:

```text
target truth
  → defocus-equivalent DP focal-stack replay
  → left/right A/B image observation
  → calibrated disparity/defocus bridge or raw-DP controller
  → readout + compute delay
  → continuous lens plant
  → next A/B observation
```

Important properties of `unified_af/v0_1`:

- real LearnAF/Herrmann stacks and deterministic synthetic smoke stacks share one API;
- measured 49-slice DP stacks can be queried at continuous lens positions by interpolation;
- moving targets preserve **optical defocus in diopter space**, not raw focus-index displacement;
- the transparent bridge baseline uses horizontal gradient NCC plus a cross-stack empirical monotone disparity→defocus LUT;
- calibration and held-out evaluation stacks are separated to prevent leakage;
- sensor sampling, readout delay, compute delay, command scheduling and continuous plant integration are explicit;
- the controller receives both decoded defocus/confidence and raw A/B images, allowing a future HCM controller to bypass the bridge decoder;
- the generic second-order lens plant can later be replaced by an identified Canon EF plant without changing the simulator API.

### Stage 3 — Sim-to-real / camera hardware

The target deployment architecture remains a **fixed feed-forward hardware-compatible controller** driven by phase/Dual-Pixel information plus short lens-state history.

The real-camera path is:

1. validate the unified environment on held-out real LearnAF stacks;
2. adapt the HCM/raw-tap controller to the unified simulator;
3. identify a real Canon EF lens command→position plant;
4. measure camera PDAF/DP readout timing;
5. replace stack replay with live measured Canon observations;
6. compare conventional and CPSAF control under the same real optical/actuator test cases.

Older Canon digital bodies such as the 40D/50D remain candidate research platforms because they provide a digital image ground truth while the feasibility of direct PDAF access and lens-control interception is investigated separately.

---

## Unified AF simulator v0.1

Location: `unified_af/v0_1/`

### Quick start

```bash
cd unified_af/v0_1
pip install -r requirements.txt
python test_unified_env.py
python run_smoke_validation.py
```

Expected smoke-test behavior:

- unit/smoke tests pass;
- `results/smoke_report.json` is regenerated;
- `results/phase_servo_step_trace.npz` is regenerated locally.

The compressed trace is a reproducible generated artifact; the repository's scientific evidence is the source code, deterministic test configuration, and machine-readable JSON metrics.

### Current synthetic smoke result

These numbers verify software closure and synthetic observability only. They are **not** LearnAF benchmark results and **not** Canon hardware results.

| Test | v0.1 smoke result |
|---|---:|
| held-out sensor MAE | 0.0303 focus index |
| held-out sensor RMSE | 0.0384 focus index |
| held-out within ±1 | 100% |
| 8→40 step settling | 7.28 ms |
| step overshoot | 0.495 index |
| oracle step settling | 7.14 ms |
| 10 Hz tracking RMSE | 1.308 index |
| 10 Hz tracking RMSE | 0.262 D |
| exact integer-stack replay error | 0 |

The ~0.14 ms gap between the phase-servo bridge and the truth-using oracle in the synthetic step test indicates that, under this smoke-test observability, the generic actuator plant rather than the software bridge dominates the step-settling bound. This is a simulator result only and must not be projected onto real Canon hardware before plant and sensor identification.

### Why the bridge estimator is intentionally simple

An initial unconstrained 2-D phase-correlation bridge was unstable in large-defocus regions. v0.1 therefore uses a constrained **horizontal gradient-domain normalized cross-correlation** search with subpixel refinement, followed by an empirical monotone LUT learned only from calibration stacks.

This estimator is a transparent reference path, not the proposed final CPSAF/HCM algorithm and not a claim about Canon's proprietary PDAF decoder. Its role is to make the sensor→controller→plant loop observable and testable while preserving the raw A/B images for learned-controller experiments.

---

## Dynamic-control findings retained from earlier CPSAF meta-tests

The early latency and actuator studies remain useful as architecture studies, but their interpretation has been narrowed.

The important conclusion is:

```text
AF performance ≠ compute latency alone
```

A more defensible formulation is:

```text
T_AF = f(T_sensor, T_readout, T_compute, controller, actuator, target dynamics, noise)
```

High-rate sensing can make very low controller latency useful, while an actuator- or sensor-limited system cannot be transformed simply by reducing neural inference latency. The repository therefore preserves the latency sweeps as meta-tests rather than presenting them as camera-level validation.

Existing controller work includes:

- Acquire–Track–Hold software teacher experiments;
- fixed feed-forward crossbar MLP prototypes;
- raw-tap controller inputs using short error/lens histories rather than explicit runtime mode switching;
- 5 kHz dynamic tests with static, step, sinusoidal, mixed-motion and confidence-dropout cases.

Large controller scaling is intentionally subordinate to simulator validation: a more powerful HCM should not be trained against an unvalidated sensing/plant model.

---

## Repository layout

```text
CPSAF/
├── README.md
├── zhu_herrmann/
│   ├── v0_4/                         # focal-stack AF environment
│   └── validation_v0_5/              # frozen academic validation gates
├── unified_af/
│   └── v0_1/                         # DP-image + continuous-plant bridge
├── hcm_controllers/
│   └── v0_3_crossbar/                # hardware-compatible controller prototypes
├── meta_latency/
│   └── v0_1/                         # early latency/actuator meta-tests
├── benchmarks/                       # published/static vs CPSAF dynamic comparisons
├── artifacts/                        # checkpoint/result metadata
└── archive/                          # historical notes and reconstruction context
```

---

## Evaluation philosophy

Two benchmark families are kept distinct.

### Static academic AF metrics

Used for Herrmann / Choi / Zhu comparison:

- exact focus state;
- within ±1 / ±2 / ±4 states;
- MAE;
- RMSE;
- focus-hunting rate.

### Dynamic closed-loop metrics

Used for CPSAF control evaluation:

- tracking RMSE / MAE;
- diopter-domain error;
- settling time;
- overshoot;
- command jitter;
- lens-direction reversals / hunting;
- confidence-dropout behavior;
- eventual P95/P99 settling and failure probability in real-hardware tests.

Published static benchmark values and current dynamic simulator values must not be numerically ranked against one another until both policies are run through the same bridge benchmark.

---

## Validation gates before strong scientific claims

### Gate A — Official LearnAF / Zhu reproduction

Required before claiming an academically validated baseline comparison.

### Gate B — Held-out real-stack sensor bridge

Fit any disparity/defocus calibration on the LearnAF training split only, freeze it, and evaluate held-out stacks versus defocus magnitude, texture, illumination/SNR, ROI position and mixed-depth content.

### Gate C — Real lens plant identification

Replace the generic second-order model with measured Canon EF dynamics across start position, displacement, direction, reversal, update rate, velocity/acceleration saturation, dead zone, hysteresis and backlash where observable.

### Gate D — Live Canon sensor bridge

Replace focal-stack replay with measured camera PDAF/DP observations and measured timing while preserving the controller and plant interfaces.

Only after these gates should the project make camera-level performance claims.

---

## Reproducibility and non-claims

This repository deliberately distinguishes four evidence levels:

1. **protocol reconstruction** — code/protocol matches published descriptions;
2. **synthetic smoke validation** — software architecture executes and invariants hold;
3. **official-data numerical validation** — benchmark numbers reproduce on the authoritative dataset;
4. **real-hardware validation** — measured camera/lens behavior supports the same conclusion.

Results from a lower level must not be relabeled as evidence from a higher level.

The current strongest completed result is the software closure of a DP-image-observation + continuous-actuator autofocus loop. Official LearnAF numerical reproduction and real Canon validation remain open gates.

---

## Key project principle

The intended CPSAF contribution is not merely “a neural network that runs in nanoseconds.” The research target is a **hardware-compatible learned fast inner autofocus loop** whose benefit survives realistic sensing, timing and actuator constraints.

That is the standard against which the simulator, controller and eventual hardware experiments are being built.
