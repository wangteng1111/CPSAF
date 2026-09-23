# Unified AF v0.1 — design rationale and implementation notes

## Why this environment exists

Before v0.1 the CPSAF project had two useful but disconnected simulation domains:

1. **Herrmann / Choi / Zhu focal-stack AF** — real Dual-Pixel A/B observations and academically comparable 49-state protocols, but a discrete/static lens-state model.
2. **CPSAF dynamic control** — explicit sample timing, compute delay and a continuous actuator plant, but the sensor side was represented by a synthetic signed focus error.

That separation prevented a clean answer to the central controller question: can a controller that operates on DP information still retain an advantage once sensing and actuator dynamics are put in the same loop?

v0.1 therefore implements a stack-in-the-loop bridge:

```text
target truth
  -> DP stack replay
  -> A/B image observation
  -> estimator or raw-DP controller
  -> controller command
  -> timing queues
  -> continuous lens plant
  -> new A/B observation
```

## Continuous replay from a 49-slice measured stack

LearnAF focal positions are non-uniform in distance and approximately uniform neither in millimetres nor in raw lens index. For moving-target replay, v0.1 therefore preserves defocus in **diopter space**.

For stack ground-truth diopter `D_gt`, simulated lens diopter `D_lens`, and simulated target diopter `D_target`, the focal-stack query is

```text
D_source = D_gt + (D_lens - D_target)
```

`D_source` is mapped back to the 49-state coordinate and adjacent measured A/B slices are linearly interpolated. This is still a replay approximation, but it preserves the optical meaning of lens-target defocus better than translating raw focus indices.

At integer static positions with the target held at the original stack ground truth, the replay is an exact identity. The smoke invariant checks a maximum absolute pixel error of zero.

## Sensor bridge development

### Rejected first attempt: unconstrained 2-D phase correlation

The first bridge used generic phase correlation between the A/B images. It behaved acceptably near focus but became non-monotonic / unstable at larger defocus, producing a static focus-index MAE of roughly seven states in early smoke testing.

This failure is informative: a generic phase-correlation primitive should not be equated with camera PDAF.

### v0.1 baseline: horizontal gradient NCC

Dual-Pixel disparity is predominantly horizontal in this simplified replay. v0.1 therefore uses:

1. horizontal Sobel gradients;
2. bounded horizontal normalized cross-correlation;
3. sub-pixel parabolic refinement around the best lag;
4. an empirical monotone disparity->optical-defocus LUT.

The LUT is a transparent bridge baseline. It is not the proposed final HCM inference path and is not claimed to reproduce Canon's proprietary PDAF decoder.

## Anti-leakage rule

A focal stack used for reported evaluation may not also be used to fit the disparity->defocus LUT.

The deterministic smoke test therefore:

- calibrates on five independently generated synthetic focal stacks;
- evaluates the static sensor bridge and dynamic closed loop on a held-out stack.

For real LearnAF work, the same rule becomes stricter: calibration must be fit only on the official training split and frozen before any test-split evaluation.

## Continuous plant and timing

The default actuator remains a replaceable second-order model:

```text
x'' + 2*zeta*wn*x' + wn^2*x = wn^2*u
```

with the default smoke configuration:

- natural frequency: 80 Hz;
- damping ratio: 0.8;
- sensor sample period: 200 us (5 kHz);
- integration step: 20 us;
- compute delay: 10 us.

The plant implementation also exposes position bounds and optional command quantization, deadband, velocity limit and acceleration limit.

Readout and compute delays are represented explicitly by sensor and command queues. The API is intended to survive replacement of the generic plant with an experimentally identified EF lens model.

## Controller interface

Each controller observation can contain:

- lens position;
- lens velocity;
- previous command;
- decoded optical defocus;
- confidence;
- measured disparity and correlation response;
- raw left/right DP images.

The current `PhaseServoController` is only a sanity baseline. A future HCM/crossbar controller can ignore the decoded error and operate directly on raw-DP-derived features/history without changing the environment.

An `OraclePositionController` uses target truth only to establish a simulator lower bound for the same timing and actuator plant.

## Reproduced synthetic smoke result

The committed deterministic smoke configuration reproduces:

| quantity | result |
|---|---:|
| held-out sensor MAE | 0.0303116 index |
| held-out sensor RMSE | 0.0383873 index |
| held-out within +/-1 | 1.0 |
| phase-servo 8->40 settling | 7.28 ms |
| phase-servo overshoot | 0.4946 index |
| oracle 8->40 settling | 7.14 ms |
| 10 Hz tracking RMSE | 1.30798 index |
| 10 Hz tracking RMSE | 0.26153 D |
| integer replay max pixel error | 0 |

These are software/synthetic validation results only.

## What v0.1 does and does not close

v0.1 closes the **software architecture gap** between image-domain DP observation and continuous closed-loop dynamics.

It does not yet close:

- the official LearnAF/Zhu numerical-reproduction gate;
- real scene-motion image formation;
- calibrated photon/read-noise statistics;
- Canon PDAF readout timing;
- Canon EF motor/driver dynamics;
- friction, backlash and hysteresis identified from hardware;
- real-camera sim-to-real validation.

Those remaining gaps are now isolated behind explicit sensor/plant interfaces and can be replaced one at a time rather than being mixed into the controller logic.
