# Unified AF stack-in-the-loop simulator v0.1

This package closes the software-architecture gap between the **real Dual-Pixel focal-stack benchmark** (Herrmann / Choi / Zhu) and the **continuous CPSAF control simulator**.

## Closed loop

```text
scene/target truth
    -> defocus-equivalent DP focal-stack replay
    -> measured A/B images
    -> calibrated gradient-NCC disparity estimator
    -> controller
    -> readout + compute delay
    -> continuous second-order lens plant
    -> next A/B observation
```

The critical change is that the dynamic controller no longer receives a synthetic signed focus error directly. It receives an estimate derived from replayed **left/right DP image observations**.

## What v0.1 makes scientifically possible

1. Use one API with either a deterministic synthetic stack or a real LearnAF/Herrmann focal sweep.
2. Query a measured 49-slice stack at a **continuous lens state** by image interpolation.
3. Approximate a moving target by preserving lens-target **diopter defocus**, rather than shifting raw focus indices.
4. Calibrate an empirical A/B disparity-to-defocus curve from one or more **training stacks** and apply it to held-out stacks; no global linear PDAF assumption is required.
5. Put DP sensing, readout delay, compute delay, controller, and continuous actuator dynamics in one closed loop.
6. Report both static Zhu-style sensor metrics and dynamic tracking/settling metrics.
7. Replace the baseline phase servo later with a fixed HCM/crossbar controller without changing the environment.
8. Replace the generic second-order plant later with an identified Canon EF lens plant without changing the sensor/controller API.

## Important limits

This is a **bridge environment**, not yet a full camera simulator.

- LearnAF official-data reproduction remains a separate validation gate.
- A single static focal sweep cannot recreate all scene-dependent changes caused by a genuinely moving 3-D target. Dynamic target motion therefore uses a **defocus-equivalent replay approximation**.
- The bridge estimator uses image-domain gradient NCC as a transparent bridge baseline. It is not claimed to equal Canon's internal PDAF pipeline.
- The actuator is still a generic second-order model until real EF lens system identification is available.
- Shot/read noise parameters are proxies because normalized public DP images do not expose photon-count calibration.

## Smoke validation

```bash
python run_smoke_validation.py
python test_unified_env.py
```

The smoke test checks:

- exact recovery of original stack images at integer static lens positions;
- calibrated DP sensor usefulness over all 49 positions;
- closed-loop 8 -> 40 step convergence through the continuous plant;
- 10-Hz target tracking;
- oracle actuator/timing lower bound.

Output is written to `results/smoke_report.json` and a compressed step trace.

## Real LearnAF use

```python
from unified_af_env import *

sample = HerrmannDiskStack(
    "/data/learnaf/train",
    capture_name="<capture>"
).load(
    gt_index=<nearest-focus-label>,
    roi_xywh=(x, y, 128, 128),
    out_hw=(128,128),
)

replay = FocusStackReplay(sample, ReplayConfig(defocus_space="diopter"))
estimator = DPDisparityEstimator(calibration_training_samples)  # do not calibrate on the test stack
controller = PhaseServoController()
plant = SecondOrderLensPlant(PlantConfig(natural_frequency_hz=80.0, damping_ratio=0.8))
sim = UnifiedAFSimulator(replay, estimator, controller, plant, TimingConfig())
```

For Zhu numerical reproduction, use the existing `zhu_herrmann/validation_v0_5` gate first. Do **not** tune the bridge environment to hide the unresolved official-data filtering/provenance discrepancy.

## Next validation gates

1. Mount official LearnAF and pass the existing v0.5 manifest/count/baseline gate.
2. Run this environment on representative real LearnAF patches and quantify DP-estimator calibration residuals vs defocus, texture, illumination and ROI.
3. Add an HCM controller adapter that consumes the intended raw-tap history rather than decoded error.
4. Identify a real Canon EF lens command-to-position plant and replace `SecondOrderLensPlant`.
5. Replace stack replay with measured live Canon PDAF/DP observations for the final sim-to-real bridge.

## Anti-leakage rule

A stack used for reported evaluation must **not** also be used to calibrate the disparity-to-defocus LUT.  The synthetic smoke test therefore calibrates on several independent textures/GT positions and evaluates on a held-out stack.  With official LearnAF data, calibration must be fitted on the training split only and frozen for test.
