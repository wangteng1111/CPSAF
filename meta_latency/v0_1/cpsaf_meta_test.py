from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import csv
import math
import numpy as np

FOCUS_DISTANCES_MM = np.array([
    3910.92, 2289.27, 1508.71, 1185.83, 935.91, 801.09, 700.37,
    605.39, 546.23, 486.87, 447.99, 407.40, 379.91, 350.41, 329.95,
    307.54, 291.72, 274.13, 261.53, 247.35, 237.08, 225.41, 216.88,
    207.10, 198.18, 191.60, 183.96, 178.29, 171.69, 165.57, 160.99,
    155.61, 150.59, 146.81, 142.35, 138.98, 134.99, 131.23, 127.69,
    124.99, 121.77, 118.73, 116.40, 113.63, 110.99, 108.47, 106.54,
    104.23, 102.01
], dtype=np.float64)
FOCUS_DIOPTERS = 1000.0 / FOCUS_DISTANCES_MM

@dataclass(frozen=True)
class PathConfig:
    name: str
    sample_period_s: float
    compute_delay_s: float

@dataclass(frozen=True)
class PlantConfig:
    natural_frequency_hz: float = 80.0
    damping_ratio: float = 0.8

@dataclass
class SimResult:
    t: np.ndarray
    target_index: np.ndarray
    lens_index: np.ndarray
    command_index: np.ndarray

def index_to_diopter(x: np.ndarray) -> np.ndarray:
    return np.interp(x, np.arange(49, dtype=np.float64), FOCUS_DIOPTERS)

def make_target(t: np.ndarray, kind: str, *, freq_hz: float = 10.0, center: float = 24.0, amplitude: float = 10.0, step_from: float = 8.0, step_to: float = 40.0, step_time_s: float = 0.05) -> np.ndarray:
    if kind == "sine": return center + amplitude * np.sin(2 * np.pi * freq_hz * t)
    if kind == "step": return np.where(t < step_time_s, step_from, step_to).astype(np.float64)
    if kind == "static": return np.full_like(t, center, dtype=np.float64)
    raise ValueError(kind)

def simulate(*, duration_s: float, dt_s: float, path: PathConfig, plant: PlantConfig, target_kind: str = "sine", target_freq_hz: float = 10.0, step_time_s: float = 0.05, phase_gain: float = 1.0, phase_noise_sigma_index: float = 0.0, seed: int = 0) -> SimResult:
    n = int(round(duration_s / dt_s)) + 1
    t = np.arange(n, dtype=np.float64) * dt_s
    target = make_target(t, target_kind, freq_hz=target_freq_hz, step_time_s=step_time_s)
    x = float(target[0]); v = 0.0; u = x
    wn = 2.0 * np.pi * plant.natural_frequency_hz; zeta = plant.damping_ratio
    rng = np.random.default_rng(seed); next_sample_s = 0.0; pending: List[Tuple[float, float]] = []
    lens = np.empty(n, dtype=np.float64); cmd = np.empty(n, dtype=np.float64)
    for i, ti in enumerate(t):
        while pending and pending[0][0] <= ti + 0.5 * dt_s:
            _, u = pending.pop(0)
        if ti + 0.5 * dt_s >= next_sample_s:
            err = phase_gain * (target[i] - x)
            if phase_noise_sigma_index > 0: err += float(rng.normal(0.0, phase_noise_sigma_index))
            target_est = float(np.clip(x + err, 0.0, 48.0))
            pending.append((ti + path.compute_delay_s, target_est)); next_sample_s += path.sample_period_s
        a = wn * wn * (u - x) - 2.0 * zeta * wn * v
        v += a * dt_s; x += v * dt_s; x = float(np.clip(x, 0.0, 48.0))
        lens[i] = x; cmd[i] = u
    return SimResult(t=t, target_index=target, lens_index=lens, command_index=cmd)

def tracking_metrics(result: SimResult, warmup_s: float = 0.2) -> Dict[str, float]:
    m = result.t >= warmup_s; e_idx = result.lens_index[m] - result.target_index[m]
    e_d = index_to_diopter(result.lens_index[m]) - index_to_diopter(result.target_index[m])
    return {"rmse_index": float(np.sqrt(np.mean(e_idx ** 2))), "mae_index": float(np.mean(np.abs(e_idx))), "maxae_index": float(np.max(np.abs(e_idx))), "rmse_diopter": float(np.sqrt(np.mean(e_d ** 2)))}

def step_settling_ms(result: SimResult, step_time_s: float, tol_index: float = 1.0, hold_s: float = 0.005) -> float:
    e = np.abs(result.lens_index - result.target_index); start = int(np.searchsorted(result.t, step_time_s)); dt = result.t[1] - result.t[0]
    hold_n = max(1, int(round(hold_s / dt)))
    for i in range(start, len(result.t) - hold_n):
        if np.all(e[i:i + hold_n] <= tol_index): return float((result.t[i] - step_time_s) * 1000.0)
    return float("nan")

def write_csv(path: Path, rows: List[Dict[str, float | str]]) -> None:
    if not rows: return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True); dt = 1e-5
    latency_rows=[]
    for fn in (20.0,40.0,80.0,160.0):
        for delay_ms in (0.01,0.1,0.5,1.0,2.0,5.0,10.0):
            path=PathConfig(f"Ts1ms_Tc{delay_ms:g}ms",1e-3,delay_ms*1e-3)
            r=simulate(duration_s=1.0,dt_s=dt,path=path,plant=PlantConfig(fn,0.8),target_freq_hz=10.0)
            latency_rows.append({"plant_fn_hz":fn,"target_hz":10.0,"sample_ms":1.0,"compute_delay_ms":delay_ms,**tracking_metrics(r)})
    write_csv(output_dir/"latency_sweep.csv",latency_rows)
    paths=[PathConfig("frame_4ms_compute_2ms",4e-3,2e-3),PathConfig("frame_4ms_compute_10us",4e-3,10e-6),PathConfig("cpsaf_1ms_compute_10us",1e-3,10e-6),PathConfig("cpsaf_0p1ms_compute_10us",0.1e-3,10e-6)]
    arch_rows=[]
    for target_hz in (5.0,10.0,20.0):
        for path in paths:
            r=simulate(duration_s=1.0,dt_s=dt,path=path,plant=PlantConfig(80.0,0.8),target_freq_hz=target_hz)
            arch_rows.append({"path":path.name,"target_hz":target_hz,"sample_ms":path.sample_period_s*1e3,"compute_delay_ms":path.compute_delay_s*1e3,**tracking_metrics(r)})
    write_csv(output_dir/"architecture_sweep.csv",arch_rows)
    actuator_rows=[]
    for fn in (20.0,40.0,80.0,160.0):
        for target_hz in (5.0,10.0,20.0):
            slow=simulate(duration_s=1.0,dt_s=dt,path=PathConfig("2ms",1e-3,2e-3),plant=PlantConfig(fn,0.8),target_freq_hz=target_hz)
            fast=simulate(duration_s=1.0,dt_s=dt,path=PathConfig("10us",1e-3,10e-6),plant=PlantConfig(fn,0.8),target_freq_hz=target_hz)
            ms,mf=tracking_metrics(slow),tracking_metrics(fast)
            actuator_rows.append({"plant_fn_hz":fn,"target_hz":target_hz,"rmse_2ms_index":ms["rmse_index"],"rmse_10us_index":mf["rmse_index"],"rmse_reduction_pct":100.0*(1.0-mf["rmse_index"]/ms["rmse_index"])})
    write_csv(output_dir/"actuator_sweep.csv",actuator_rows)
    step_rows=[]
    for path in paths:
        vals=[]
        for phase in np.linspace(0.0,path.sample_period_s,20,endpoint=False):
            st=0.05+float(phase); r=simulate(duration_s=0.25,dt_s=dt,path=path,plant=PlantConfig(80.0,0.8),target_kind="step",step_time_s=st)
            vals.append(step_settling_ms(r,st,tol_index=1.0,hold_s=0.005))
        a=np.asarray(vals); step_rows.append({"path":path.name,"mean_settle_ms":float(np.nanmean(a)),"p05_settle_ms":float(np.nanpercentile(a,5)),"median_settle_ms":float(np.nanmedian(a)),"p95_settle_ms":float(np.nanpercentile(a,95))})
    write_csv(output_dir/"step_response.csv",step_rows)
    robust_rows=[]
    for path in paths:
        vals=[]
        for seed in range(8):
            r=simulate(duration_s=0.7,dt_s=dt,path=path,plant=PlantConfig(80.0,0.8),target_freq_hz=10.0,phase_gain=0.85,phase_noise_sigma_index=0.25,seed=seed)
            vals.append(tracking_metrics(r)["rmse_index"])
        a=np.asarray(vals); robust_rows.append({"path":path.name,"phase_gain":0.85,"phase_noise_sigma_index":0.25,"rmse_index_mean":float(a.mean()),"rmse_index_std":float(a.std(ddof=1))})
    write_csv(output_dir/"robustness.csv",robust_rows)

if __name__ == "__main__": run(Path(__file__).resolve().parent/"results")
