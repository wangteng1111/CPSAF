from __future__ import annotations
import numpy as np
from unified_af_env import (
    make_synthetic_dp_stack, FocusStackReplay, ReplayConfig,
    DPDisparityEstimator, SecondOrderLensPlant, PlantConfig,
    TimingConfig, PhaseServoController, UnifiedAFSimulator,
    make_step_target, step_metrics, static_sensor_bridge_metrics,
)


def test_exact_integer_replay():
    s = make_synthetic_dp_stack(gt_index=30, size=64, seed=2)
    r = FocusStackReplay(s, ReplayConfig(defocus_space="diopter"))
    for k in range(49):
        l, rr, meta = r.observe(float(k), float(s.gt_index))
        assert np.max(np.abs(l - s.left[k])) < 1e-6
        assert np.max(np.abs(rr - s.right[k])) < 1e-6
        assert abs(meta["source_index"] - k) < 1e-6


def test_phase_calibration_is_useful():
    train = [make_synthetic_dp_stack(gt_index=g, size=96, seed=q)
             for g,q in [(18,1),(24,2),(31,3),(39,4)]]
    s = make_synthetic_dp_stack(gt_index=31, size=96, seed=17)
    e = DPDisparityEstimator(train)
    m = static_sensor_bridge_metrics(s, e)
    assert m["MAE"] < 2.5, m
    assert m["within4"] > 0.90, m


def test_closed_loop_step_converges():
    train = [make_synthetic_dp_stack(gt_index=g, size=96, seed=q)
             for g,q in [(18,1),(24,2),(31,3),(39,4)]]
    s = make_synthetic_dp_stack(gt_index=31, size=96, seed=17)
    rep = FocusStackReplay(s, ReplayConfig(defocus_space="diopter"))
    est = DPDisparityEstimator(train)
    sim = UnifiedAFSimulator(
        rep, est, PhaseServoController(gain=1.0, max_command_delta=14.0, confidence_floor=0.02),
        SecondOrderLensPlant(PlantConfig(80.0, 0.8)),
        TimingConfig(integration_dt_s=2e-5, sample_period_s=2e-4, compute_delay_s=1e-5))
    tr = sim.run(0.16, make_step_target(8, 40, 0.05), start_index=8)
    sm = step_metrics(tr, 0.05)
    assert np.isfinite(sm["settle_ms"]), sm
    assert sm["settle_ms"] < 40.0, sm


if __name__ == "__main__":
    test_exact_integer_replay()
    test_phase_calibration_is_useful()
    test_closed_loop_step_converges()
    print("all tests passed")
