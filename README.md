# CPSAF

Continuous / phase-sensing autofocus research enabled by HCM crossbar neural control.

This repository archives the simulation environments, controller prototypes, evaluation reports, and validation tooling produced during the CPSAF study.

## Research path

The project is now organized around a strict three-stage workflow:

1. **Validate the autofocus simulation environment** against Herrmann / Choi / Zhu.
2. **Train hardware-compatible CPSAF MLP controllers** only inside the validated environment.
3. **Sim-to-real transfer to HCM hardware** after the simulator and controller are both validated.

## Repository layout

- `zhu_herrmann/` — Zhu 2025 / Herrmann 2020 reproduction and validation environment.
- `benchmarks/` — quantitative comparisons and published autofocus targets.
- `hcm_controllers/` — hardware-compatible controller prototypes.
- `meta_latency/` — early latency / actuator meta-tests.
- `archive/` — archive notes and reconstruction information.
- `artifacts/` — machine-readable metrics and checkpoint metadata.

## Zhu/Herrmann validation status

The current canonical validation layer is `zhu_herrmann/validation_v0_5/`.

**Current status: protocol-validated + provenance-audited; data-level validation pending.**

Already passed:

- 49-state focus formulation;
- 97-class relative action formulation;
- Choi AFPE conventions;
- squared-distance SORD;
- MobileNetV2 parameter count and 49-start evaluation plumbing;
- stride-96 / all-start protocol invariants;
- mounted-data and provenance audit tooling.

Still required before any large CPSAF training is accepted:

- mount and audit the official LearnAF data;
- resolve or empirically cross-check the confidence filtering rule without train/test-specific tuning;
- reproduce Zhu's 68,187 / 7,805 spatial-patch counts;
- run the 10k relative-label MobileNetV2 baseline;
- reproduce Zhu's published single-step metrics within frozen tolerances.

The repository explicitly tracks the discrepancy between Herrmann's paper split (460 train / 50 test stacks) and the smaller current public LearnAF release (351 train / 47 test sweeps). This discrepancy must not be silently ignored.

## Hardware-oriented direction

The deployment target remains a **fixed feed-forward crossbar MLP** driven by Dual-Pixel A/B information plus lens-state history. Runtime inference must not depend on explicit Acquire/Track/Hold state switching, argmin disparity decoding, or digital strategy selection.

However, HCM/controller scaling is intentionally paused until the Stage-1 simulator validation gate passes.

## Snapshot integrity

The current Stage-1 validation sandbox package has SHA-256:

```text
d6592a718db5cea6ad3c2e4880dfafc9f3feb7892d2ee1e264a9a99b3908ae12
```

See `zhu_herrmann/validation_v0_5/SNAPSHOT_SHA256.md` and `CURRENT_VALIDATION_STATUS.md` for details.
