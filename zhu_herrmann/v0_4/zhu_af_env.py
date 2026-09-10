from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
import json
import math

import cv2
import numpy as np

# Official LearnAF focus distances, from the dataset README (mm), slice_00 ... slice_48.
FOCUS_DISTANCES_MM = np.array([
    3910.92, 2289.27, 1508.71, 1185.83, 935.91, 801.09, 700.37,
    605.39, 546.23, 486.87, 447.99, 407.40, 379.91, 350.41, 329.95,
    307.54, 291.72, 274.13, 261.53, 247.35, 237.08, 225.41, 216.88,
    207.10, 198.18, 191.60, 183.96, 178.29, 171.69, 165.57, 160.99,
    155.61, 150.59, 146.81, 142.35, 138.98, 134.99, 131.23, 127.69,
    124.99, 121.77, 118.73, 116.40, 113.63, 110.99, 108.47, 106.54,
    104.23, 102.01
], dtype=np.float32)


def _normalize_u16_like(img: np.ndarray, white_level: float = 1023.0) -> np.ndarray:
    x = img.astype(np.float32)
    denom = 65535.0 if x.max(initial=0.0) > white_level * 1.5 else white_level
    return np.clip(x / denom, 0.0, 1.0)


def crop_patch(img: np.ndarray, roi_xywh: Tuple[int, int, int, int], out_hw=(128, 128)) -> np.ndarray:
    x, y, w, h = map(int, roi_xywh)
    if w <= 0 or h <= 0:
        raise ValueError("ROI width/height must be positive")
    y2, x2 = min(img.shape[0], y + h), min(img.shape[1], x + w)
    x, y = max(0, x), max(0, y)
    patch = img[y:y2, x:x2]
    if patch.size == 0:
        raise ValueError(f"ROI {roi_xywh} is outside image shape {img.shape}")
    if patch.shape[:2] != tuple(out_hw):
        patch = cv2.resize(patch, (out_hw[1], out_hw[0]), interpolation=cv2.INTER_AREA)
    return patch.astype(np.float32)


@dataclass
class StackSample:
    left: np.ndarray
    right: np.ndarray
    gt_index: int
    roi_xywh: Tuple[int, int, int, int]
    source_id: str = ""
    source_hw: Optional[Tuple[int, int]] = None

    def __post_init__(self):
        if self.left.shape != self.right.shape:
            raise ValueError("left/right stack shapes must match")
        if self.left.ndim != 3 or self.left.shape[0] != 49:
            raise ValueError(f"expected [49,H,W], got {self.left.shape}")
        if not (0 <= int(self.gt_index) <= 48):
            raise ValueError("gt_index must be in [0,48]")
        self.left = self.left.astype(np.float32, copy=False)
        self.right = self.right.astype(np.float32, copy=False)
        self.gt_index = int(self.gt_index)
        if self.source_hw is None:
            self.source_hw = tuple(map(int, self.left.shape[1:]))


class HerrmannDiskStack:
    def __init__(self, root: str | Path, capture_name: str, use_upsampled: bool = False):
        self.root = Path(root)
        self.capture_name = capture_name
        self.left_dir = self.root / ("raw_up_left_pd" if use_upsampled else "raw_left_pd") / capture_name
        self.right_dir = self.root / ("raw_up_right_pd" if use_upsampled else "raw_right_pd") / capture_name

    @staticmethod
    def _first_png(slice_dir: Path, side: str) -> Path:
        if not slice_dir.exists():
            raise FileNotFoundError(slice_dir)
        candidates = sorted(slice_dir.glob("*.png"))
        if not candidates:
            raise FileNotFoundError(f"No PNG under {slice_dir}")
        preferred = [p for p in candidates if side in p.name.lower()]
        return preferred[0] if preferred else candidates[0]

    def load(self, gt_index: int, roi_xywh: Tuple[int,int,int,int], out_hw=(128,128)) -> StackSample:
        L, R = [], []
        for k in range(49):
            s = f"slice_{k:02d}"
            lp = self._first_png(self.left_dir / s, "left")
            rp = self._first_png(self.right_dir / s, "right")
            li = cv2.imread(str(lp), cv2.IMREAD_UNCHANGED)
            ri = cv2.imread(str(rp), cv2.IMREAD_UNCHANGED)
            if li is None or ri is None:
                raise IOError(f"Could not read {lp} or {rp}")
            if k == 0:
                source_hw = tuple(map(int, li.shape[:2]))
            li = crop_patch(_normalize_u16_like(li), roi_xywh, out_hw)
            ri = crop_patch(_normalize_u16_like(ri), roi_xywh, out_hw)
            L.append(li); R.append(ri)
        return StackSample(np.stack(L), np.stack(R), gt_index, roi_xywh, self.capture_name, source_hw)


def depth_png_to_focus_index(depth_png: np.ndarray, roi_xywh: Tuple[int,int,int,int], min_m: float = 0.2, max_m: float = 100.0) -> int:
    x, y, w, h = map(int, roi_xywh)
    d = depth_png[y:y+h, x:x+w].astype(np.float32) / 255.0
    z = (max_m * min_m) / (max_m - (max_m - min_m) * d)
    z = z[np.isfinite(z) & (z > 0)]
    if z.size == 0:
        raise ValueError("ROI contains no valid depth")
    med_m = float(np.median(z))
    inv_gt = 1.0 / med_m
    inv_focus = 1.0 / (FOCUS_DISTANCES_MM.astype(np.float64) / 1000.0)
    return int(np.argmin(np.abs(inv_focus - inv_gt)))


class ZhuAFEnv:
    def __init__(self, sample: StackSample, max_steps: int = 4, fh_penalty: float = -2.0, terminate_on_exact: bool = False):
        self.sample = sample
        self.k_max = 48
        self.max_steps = int(max_steps)
        self.fh_penalty = float(fh_penalty)
        self.terminate_on_exact = bool(terminate_on_exact)
        self.k = 0
        self.t = 0
        self.prev_effective_move = 0
        self.trajectory: List[int] = []
        self.hunting_events = 0

    def _roi_pe(self) -> np.ndarray:
        x, y, w, h = self.sample.roi_xywh
        cx = (x + 0.5*w) / 2016.0
        cy = (y + 0.5*h) / 756.0
        return np.array([2*cx-1, 2*cy-1], dtype=np.float32)

    def _lens_pe(self) -> np.ndarray:
        return np.array([(self.k + 1.0) / (self.k_max + 1.0)], dtype=np.float32)

    def _state(self) -> Dict[str, Any]:
        left = self.sample.left[self.k]
        right = self.sample.right[self.k]
        state = {"left": left, "right": right, "roi_pe": self._roi_pe(), "lens_pe": self._lens_pe(), "lens_index": int(self.k)}
        try:
            from afpe import encode_afpe_np
            state["afpe"] = encode_afpe_np(left, right, self.k, self.sample.roi_xywh, self.sample.source_hw)
        except Exception:
            pass
        return state

    def reset(self, start_index: Optional[int] = None, rng: Optional[np.random.Generator] = None):
        if start_index is None:
            rng = rng or np.random.default_rng()
            start_index = int(rng.integers(0, 49))
        if not 0 <= int(start_index) <= 48:
            raise ValueError("start_index must be in [0,48]")
        self.k = int(start_index); self.t = 0; self.prev_effective_move = 0
        self.trajectory = [self.k]; self.hunting_events = 0
        return self._state(), self._info(False, 0, 0)

    def _info(self, hunting: bool, requested_action: int, effective_move: int) -> Dict[str, Any]:
        err = abs(self.k - self.sample.gt_index)
        return {"t": int(self.t), "lens_index": int(self.k), "gt_index": int(self.sample.gt_index), "abs_error": int(err), "requested_action": int(requested_action), "effective_move": int(effective_move), "focus_hunting": bool(hunting), "hunting_events": int(self.hunting_events), "trajectory": tuple(self.trajectory), "source_id": self.sample.source_id}

    def step(self, action: int):
        action = int(np.rint(action)); old_k = self.k
        self.k = int(np.clip(old_k + action, 0, self.k_max)); effective = self.k - old_k
        hunting = (self.prev_effective_move != 0 and effective != 0 and np.sign(self.prev_effective_move) != np.sign(effective))
        if hunting: self.hunting_events += 1
        reward = -float(abs(self.k - self.sample.gt_index)) + (self.fh_penalty if hunting else 0.0)
        if effective != 0: self.prev_effective_move = effective
        self.t += 1; self.trajectory.append(self.k)
        terminated = self.terminate_on_exact and (self.k == self.sample.gt_index)
        truncated = self.t >= self.max_steps
        return self._state(), reward, terminated, truncated, self._info(hunting, action, effective)


class OraclePolicy:
    def __call__(self, state: Dict[str, Any], gt_index: int) -> int:
        return int(gt_index - state["lens_index"])


class FractionalExpertPolicy:
    def __init__(self, max_steps=4): self.max_steps = int(max_steps)
    def action(self, k: int, gt: int, t: int) -> int:
        e = gt - k
        if e == 0: return 0
        remaining = max(1, self.max_steps - t)
        mag = int(math.ceil(abs(e) / remaining))
        return int(np.sign(e) * mag)


def make_synthetic_dp_stack(gt_index: int = 31, size: int = 128, seed: int = 1) -> StackSample:
    rng = np.random.default_rng(seed); yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    base = (0.35*np.sin(xx/5.7) + 0.25*np.cos(yy/8.1) + 0.20*np.sin((xx+yy)/13.0) + 0.20*rng.normal(size=(size,size)))
    base = cv2.GaussianBlur(base, (0,0), 0.6); base = (base - base.min()) / max(1e-6, float(base.max()-base.min()))
    left, right = [], []
    for k in range(49):
        d = float(k - gt_index); sigma = 0.45 + 0.11*abs(d); img = cv2.GaussianBlur(base, (0,0), sigma); shift = 0.09*d
        M_l = np.float32([[1,0,-0.5*shift],[0,1,0]]); M_r = np.float32([[1,0,+0.5*shift],[0,1,0]])
        L = cv2.warpAffine(img, M_l, (size,size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        R = cv2.warpAffine(img, M_r, (size,size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        left.append(L); right.append(R)
    return StackSample(np.stack(left), np.stack(right), gt_index, (0,0,size,size), "synthetic-smoke", (size,size))


def evaluate_policy(env: ZhuAFEnv, policy, starts=range(49)) -> Dict[str, float]:
    final_errors, hunts, steps = [], [], []; exact = within1 = within2 = within4 = 0
    for k0 in starts:
        state, _ = env.reset(int(k0)); done = False
        while not done:
            a = policy.action(state["lens_index"], env.sample.gt_index, env.t) if hasattr(policy, "action") else policy(state, env.sample.gt_index)
            state, _, term, trunc, info = env.step(a); done = term or trunc
        e = info["abs_error"]; final_errors.append(e); hunts.append(info["hunting_events"]); steps.append(env.t)
        exact += e <= 0; within1 += e <= 1; within2 += e <= 2; within4 += e <= 4
    n = len(final_errors); arr = np.asarray(final_errors, np.float32)
    return {"N": float(n), "exact": exact/n, "within1": within1/n, "within2": within2/n, "within4": within4/n, "MAE": float(arr.mean()), "RMSE": float(np.sqrt(np.mean(arr**2))), "FH_rate": float(np.mean(np.asarray(hunts) > 0)), "mean_hunting_events": float(np.mean(hunts)), "mean_steps": float(np.mean(steps))}
