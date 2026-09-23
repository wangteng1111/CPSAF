from __future__ import annotations

"""Unified stack-in-the-loop autofocus simulation environment.

The design intentionally bridges two previously separate CPSAF environments:
1) static Herrmann/LearnAF Dual-Pixel focal stacks; and
2) continuous-time dynamic lens/control simulation.

The core loop is:
    scene/target truth -> DP stack replay -> sensor/estimator -> controller
    -> command latency -> continuous lens plant -> next DP observation

No official LearnAF data are bundled here. The same code can use either a real
HerrmannDiskStack or the deterministic synthetic stack generator for smoke tests.
"""

from dataclasses import dataclass, field
from pathlib import Path
from collections import deque
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import math

import cv2
import numpy as np


# Official LearnAF focus distances, slice_00 ... slice_48 (mm).
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
LENS_INDICES = np.arange(49, dtype=np.float64)


def index_to_diopter(index: float | np.ndarray) -> float | np.ndarray:
    return np.interp(index, LENS_INDICES, FOCUS_DIOPTERS)


def diopter_to_index(diopter: float | np.ndarray) -> float | np.ndarray:
    return np.interp(diopter, FOCUS_DIOPTERS, LENS_INDICES)


def _normalize_u16_like(img: np.ndarray, white_level: float = 1023.0) -> np.ndarray:
    x = img.astype(np.float32)
    mx = float(np.max(x)) if x.size else 0.0
    denom = 65535.0 if mx > white_level * 1.5 else white_level
    return np.clip(x / denom, 0.0, 1.0)


def crop_patch(img: np.ndarray, roi_xywh: Tuple[int, int, int, int], out_hw=(128, 128)) -> np.ndarray:
    x, y, w, h = map(int, roi_xywh)
    if w <= 0 or h <= 0:
        raise ValueError("ROI width/height must be positive")
    x = max(0, x); y = max(0, y)
    x2 = min(img.shape[1], x + w); y2 = min(img.shape[0], y + h)
    patch = img[y:y2, x:x2]
    if patch.size == 0:
        raise ValueError(f"ROI {roi_xywh} outside image shape {img.shape}")
    if patch.shape[:2] != tuple(out_hw):
        patch = cv2.resize(patch, (out_hw[1], out_hw[0]), interpolation=cv2.INTER_AREA)
    return patch.astype(np.float32)


@dataclass
class StackSample:
    left: np.ndarray               # [49,H,W]
    right: np.ndarray              # [49,H,W]
    gt_index: int
    roi_xywh: Tuple[int, int, int, int]
    source_id: str = ""
    source_hw: Optional[Tuple[int, int]] = None

    def __post_init__(self) -> None:
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
    """Load one LearnAF/Herrmann focal sweep from disk.

    Expected directory layout matches the public LearnAF release:
      root/raw_left_pd/<capture>/slice_00/*.png ... slice_48/*.png
      root/raw_right_pd/<capture>/slice_00/*.png ... slice_48/*.png
    """

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

    def load(self, gt_index: int, roi_xywh: Tuple[int, int, int, int], out_hw=(128, 128)) -> StackSample:
        left, right = [], []
        source_hw = None
        for k in range(49):
            s = f"slice_{k:02d}"
            lp = self._first_png(self.left_dir / s, "left")
            rp = self._first_png(self.right_dir / s, "right")
            li = cv2.imread(str(lp), cv2.IMREAD_UNCHANGED)
            ri = cv2.imread(str(rp), cv2.IMREAD_UNCHANGED)
            if li is None or ri is None:
                raise IOError(f"Could not read {lp} or {rp}")
            if source_hw is None:
                source_hw = tuple(map(int, li.shape[:2]))
            left.append(crop_patch(_normalize_u16_like(li), roi_xywh, out_hw))
            right.append(crop_patch(_normalize_u16_like(ri), roi_xywh, out_hw))
        return StackSample(np.stack(left), np.stack(right), gt_index, roi_xywh, self.capture_name, source_hw)


@dataclass
class ReplayConfig:
    """Optical observation replay from a focal stack.

    defocus_space='diopter' preserves optical defocus more faithfully than
    translating raw focal-stack indices when the simulated target depth moves.
    """
    defocus_space: str = "diopter"  # 'diopter' or 'index'
    read_noise_sigma: float = 0.0
    shot_noise_scale: float = 0.0
    gain: float = 1.0
    black_level: float = 0.0
    seed: int = 0


class FocusStackReplay:
    """Continuous observation model derived from a 49-slice DP focal stack.

    For a moving target, we use a defocus-equivalent replay approximation.  If
    the target focus state moves from the stack's static GT, we query the source
    stack at the slice that has the same lens-target defocus.  In diopter mode:

        D_source = D_stack_gt + (D_lens - D_target)

    then linearly interpolate between adjacent measured DP slices.
    """

    def __init__(self, sample: StackSample, config: ReplayConfig = ReplayConfig()):
        self.sample = sample
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        if config.defocus_space not in ("diopter", "index"):
            raise ValueError("defocus_space must be 'diopter' or 'index'")

    def source_index(self, lens_index: float, target_index: float) -> float:
        if self.config.defocus_space == "index":
            src = self.sample.gt_index + (float(lens_index) - float(target_index))
        else:
            d_l = float(index_to_diopter(lens_index))
            d_t = float(index_to_diopter(target_index))
            d_gt = float(index_to_diopter(self.sample.gt_index))
            src = float(diopter_to_index(d_gt + (d_l - d_t)))
        return float(np.clip(src, 0.0, 48.0))

    def _interp_stack(self, stack: np.ndarray, src_index: float) -> np.ndarray:
        k0 = int(math.floor(src_index)); k1 = min(48, k0 + 1)
        a = float(src_index - k0)
        if k0 == k1:
            return stack[j⁄Óù∆≠yÿß∂ä%q©e~äÌ≠©Ïr∏©µ∫ﬁæ+r