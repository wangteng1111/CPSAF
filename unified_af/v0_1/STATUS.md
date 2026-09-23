# Unified AF simulator v0.1 — implementation status

Integration review: 2026-09-24

Original deterministic smoke snapshot: 2026-09-15; rerun successfully before repository integration on 2026-09-24.

## Implemented and smoke-tested

- 49-state LearnAF focus-distance / diopter coordinate table.
- Herrmann/LearnAF on-disk DP focal-stack loader.
- Continuous lens state querying of a measured 49-slice A/B stack.
- Defocus-equivalent moving-target replay in **diopter space**.
- Cross-stack calibrated A/B horizontal-disparity estimator using gradient NCC + empirical monotone LUT.
- Anti-leakage split: calibration stacks and held-out evaluation stack are separate in smoke validation.
- Continuous second-order lens plant with position bounds, optional velocity/acceleration limits, command quantization and deadband.
- Explicit sensor sample period, readout delay, compute delay, command queue and continuous integration step.
- Controller interface that receives both decoded defocus/confidence and the raw A/B images, so a later raw-tap HCM controller can bypass the baseline decoder.
- Phase-servo sanity baseline and truth-using oracle actuator/timing bound.
- Static sensor metrics plus dynamic tracking, settling, overshoot, command jitter and velocity reversals.
- Deterministic synthetic DP stack used only for software smoke testing.

## Latest synthetic smoke result

See `results/smoke_report.json`.

Key checks:

- held-out static sensor bridge: MAE ~0.03 focus index; RMSE ~0.038;
- 8 -> 40 step, 5 kHz sensing, 80 Hz plant, 10 us compute: settling ~7.28 ms;
- oracle same plant/timing: settling ~7.14 ms;
- 10 Hz sine tracking: RMSE ~1.31 focus index;
- exact integer focal-stack replay invariant: max absolute pixel error = 0.

These are **software/synthetic validation numbers only**. They are not LearnAF reproduction results and not Canon hardware results.

## Scientific gates still open

### Gate A — official LearnAF / Zhu numerical validation

Must be completed on a machine with the official data:

1. audit mounted train/test release;
2. reproduce or authoritatively resolve Zhu's 68,187 / 7,805 spatial-stack counts;
3. recover/freeze the confidence-filtering rule;
4. reproduce Zhu relative-label MobileNetV2 metrics within the existing v0.5 tolerance policy.

Until Gate A passes, no large CPSAF training result should be called an academically validated baseline comparison.

### Gate B — held-out real-stack sensor bridge

Fit the disparity/defocus calibration on LearnAF **training stacks only**, freeze it, then evaluate on held-out test stacks. Report error versus:

- defocus magnitude;
- texture / local spatial frequency;
- intensity / SNR;
- ROI position;
- depth discontinuity / mixed-depth patch.

This will quantify whether the transparent NCC bridge is usable as a reference decoder and where a learned raw-DP encoder is required.

### Gate C — real actuator plant

Replace the generic 80 Hz second-order plant with measured Canon EF lens dynamics. Required identification dimensions include:

- start position;
- commanded displacement;
- direction;
- reversal;
- command/update rate;
- velocity/acceleration saturation;
- dead zone / hysteresis / backlash if observable.

### Gate D — live Canon sensor bridge

Replace focal-stack replay with measured camera PDAF/DP observations and measured timing. At this point the same controller/plant interfaces can be retained.

## Interpretation

v0.1 closes the **software architecture gap** that previously separated real DP focal-stack sensing from continuous CPSAF dynamics. It does not close the **data realism** or **hardware realism** gates. Those are now isolated and measurable rather than mixed together.
