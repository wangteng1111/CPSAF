from __future__ import annotations
import json
from pathlib import Path
import numpy as np

from unified_af_env import (
    make_synthetic_dp_stack, FocusStackReplay, ReplayConfig,
    DPDisparityEstimator, SecondOrderLensPlant, PlantConfig,
    TimingConfig, PhaseServoController, OraclePositionController,
    UnifiedAFSimulator, make_step_target, make_sine_target,
    tracking_metrics, step_metrics, static_sensor_bridge_metrics,
)


def main() -> None:
    out = Path(__file__).resolve().parent / "results"
    out.mkdir(exist_ok=True)

    # Calibrate on independent focal stacks and test on a held-out texture/stack.
    calibration_stacks = [
        make_synthetic_dp_stack(gt_index=g, size=128, seed=s)
        for g, s in [(18,1), (24,2), (31,3), (37,4), (42,5)]
    ]
    sample = make_synthetic_dp_stack(gt_index=31, size=128, seed=19)
    estimator = DPDisparityEstimator(calibration_stacks)
    replay = FocusStackReplay(sample, ReplayConfig(defocus_space="diopter", seed=7))

    report = {
        "calibration": estimator.calibration_metrics(),
        "heldout_static_sensor_bridge": static_sensor_bridge_metrics(sample, estimator),
    }

    timing = TimingConfig(integration_dt_s=2e-5, sample_period_s=2e-4,
                          readout_delay_s=0.0, compute_delay_s=1e-5)

    # Sensor/controller/plant closed-loop step.
    ctl = PhaseServoController(gain=1.0, max_command_delta=14.0, confidence_floor=0.02)
    sim = UnifiedAFSimulator(
        replay, estimator, ctl,
        SecondOrderLensPlant(PlantConfig(80.0, 0.8)), timing)
    tr = sim.run(0.16, make_step_target(8.0, 40.0, 0.05), start_index=8.0)
    report["phase_servo_step"] = {**tracking_metrics(tr, warmup_s=0.05),
                                  **step_metrics(tr, 0.05)}

    # 10-Hz tracking.
    sim = UnifiedAFSimulator(
        replay, estimator,
        PhaseServoController(gain=0.9, max_command_delta=10.0, confidence_floor=0.02),
        SecondOrderLensPlant(PlantConfig(80.0, 0.8)), timing)
    tr2 = sim.run(0.35, make_sine_target(24.0, 8.0, 10.0), start_index=24.0)
    report["phase_servo_track_10Hz"] = tracking_metrics(tr2, warmup_s=0.08)

    # Oracle bounds the actuator/timing problem independent of the DP estimator.
    sim = UnifiedAFSimulator(
        replay, estimator, OraclePositionController(),
        SecondOrderLensPlant(PlantConfig(80.0, 0.8)), timing)
    tr3 = sim.run(0.16, make_step_target(8.0, 40.0, 0.05), start_index=8.0)
    report["oracle_step"] = {**tracking_metrics(tr3, warmup_s=0.05),
                             **step_metrics(tr3, 0.05)}

    # Exact-slice replay invariant at static stack GT.
    max_err = 0.0
    for k in range(49):
        l, r, meta = replay.observe(float(k), float(sample.gt_index))
        max_err = max(max_err, float(np.max(np.abs(l - sample.left[k]))),
                      float(np.max(np.abs(r - sample.right[k]))))
    report["invariants"] = {
        "integer_static_replay_max_abs_error": max_err,
        "finite_step_metrics": bool(np.isfinite(report["phase_servo_step"]["settle_ms"])),
        "command_updates_step": int(np.sum(tr.command_updates)),
    }

    (out / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.savez_compressed(out / "phase_servo_step_trace.npz",
                        t=tr.t, target=tr.target_index, lens=tr.lens_index,
                        command=tr.command_index, confidence=tr.confidence,
                        disparity=tr.disparity_px, source_index=tr.sensor_source_index)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
