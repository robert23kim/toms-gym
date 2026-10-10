"""Appearance-prior ball tracker for the glasses POV cuts.

Appearance models (all produce a per-pixel ball-likelihood mask 0..255):
  fixed    : purple hue window set by hand (H 110-175, S >= 20, V >= 40 in OpenCV HSV).
  learned  : H-S histogram learned from the ball on its first on-lane frames (release..release+3, r 90-130 px,
             inner 0.5 r), histogram back-projection.
  adaptive : learned, then the histogram is blended with each accepted blob (so the model follows the ball as it
             washes out towards the pins: S 157 -> 50, V 90 -> 150 on the dev truth).
Candidates = connected components of the mask with a perspective size prior r(k) = A / (k - k0) (A fitted from the
first detections, k0 = start - 2), linked by motion continuity with the ORB camera shift (engine yolo_chain.reliable_shift).
YOLO boxes (cached, conf 0.1) can be added as candidates ('+yolo') or used alone ('yolo').
All frames here are CUT-LOCAL; run.py adds cut_start.
"""
import math
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

sys.path.insert(0, '/Users/toka/code/bowling-app/pov-engine')
from src.bowling.trajectory.yolo_chain import ChainConfig, apply_shift, reliable_shift  # noqa: E402

Cand = Tuple[float, float, float, float, str]  # x, y, r, score, source


@dataclass
class TrackConfig:
    model: str = 'adaptive'          # fixed | learned | adaptive | yolo
    use_yolo: bool = True            # add YOLO boxes as candidates
    start_lo: int = 6                # search the start in cut frames [start_lo, start_hi]
    start_hi: int = 18
    start_min_r: float = 50.0
    hist_bins: Tuple[int, int] = (30, 32)
    bp_thresh: int = 40              # back-projection threshold (0..255)
    adapt: float = 0.15              # histogram blend per accepted blob (adaptive only)
    gate_k: float = 3.0
    gate_min: float = 40.0
    miss_grow: float = 0.5           # gate grows by this fraction per consecutive miss
    max_miss: int = 6
    size_lo: float = 0.35            # candidate r / r_pred window
    size_hi: float = 2.2
    big_blob_factor: float = 12.0    # components larger than this x predicted area are scenery (backdrop) and removed
    min_area: int = 6
    yolo_min_conf: float = 0.2
    vel_blend: float = 0.5
    first_gate: float = 700.0
    motion: bool = True              # weight far-end candidates by camera-compensated frame difference
    motion_r: float = 30.0           # apply the motion weight when r_pred is below this
    motion_full: float = 12.0        # mean |diff| inside the blob that counts as fully moving
    motion_peak: bool = True         # far end: add the peak of blackhat x motion x hue-window as a candidate
    peak_min: float = 0.25           # accept a peak if its motion value >= peak_min x the median of accepted peaks
    reacquire: bool = True           # after misses, search the whole frame for a round blob of the predicted size
    reacq_after: int = 2


def hsv_fixed_mask(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (h >= 110) & (h <= 175) & (s >= 20) & (v >= 40)
    return (m.astype(np.uint8) * 255)


class Appearance:
    def __init__(self, cfg: TrackConfig):
        self.cfg = cfg
        self.hist: Optional[np.ndarray] = None

    def learn(self, hsv: np.ndarray, x: float, y: float, r: float, weight: float = 1.0):
        H, W = hsv.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        inner = (((xx - x) ** 2 + (yy - y) ** 2) <= (0.5 * r) ** 2).astype(np.uint8)
        if inner.sum() < 10:
            return
        h = cv2.calcHist([hsv], [0, 1], inner, list(self.cfg.hist_bins), [0, 180, 0, 256])
        h = h / max(h.sum(), 1e-6)
        if self.hist is None or weight >= 1.0:
            self.hist = h
        else:
            self.hist = (1 - weight) * self.hist + weight * h

    def mask(self, hsv: np.ndarray) -> np.ndarray:
        if self.cfg.model == 'fixed' or self.hist is None:
            return hsv_fixed_mask(hsv)
        h = self.hist / max(self.hist.max(), 1e-9) * 255.0
        bp = cv2.calcBackProject([hsv], [0, 1], h.astype(np.float32), [0, 180, 0, 256], 1)
        return ((bp >= self.cfg.bp_thresh).astype(np.uint8) * 255)


def blobs(mask: np.ndarray, r_pred: float, cfg: TrackConfig) -> List[Cand]:
    k = max(1, int(round(r_pred / 6)))
    if k > 1:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask, 8)
    a_pred = math.pi * r_pred ** 2
    out: List[Cand] = []
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if a < cfg.min_area or a > cfg.big_blob_factor * a_pred:
            continue
        r = math.sqrt(a / math.pi)
        if not (cfg.size_lo * r_pred <= r <= cfg.size_hi * r_pred * 1.0):
            continue
        w, hgt = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        fill = a / max(w * hgt, 1)
        if not (0.5 <= w / max(hgt, 1) <= 2.0):
            continue
        out.append((float(cen[i][0]), float(cen[i][1]), float(r), float(min(1.0, fill / 0.6)), 'blob', float(fill), float(w / max(hgt, 1))))
    return out


def motion_map(gray_prev: np.ndarray, gray: np.ndarray, sh) -> np.ndarray:
    """|frame k - frame k-1 warped by the ORB camera shift|: static scenery (pins, masking, capping) cancels, the ball
    leaves a moving spot. sh = (a, b, tx, ty) maps k-1 -> k."""
    a, b, tx, ty = sh
    M = np.array([[a, b, tx], [-b, a, ty]], np.float32)
    warped = cv2.warpAffine(gray_prev, M, (gray.shape[1], gray.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    d = cv2.absdiff(gray, warped)
    return cv2.GaussianBlur(d, (5, 5), 0)


def far_peak(gray: np.ndarray, hsv: np.ndarray, mm: np.ndarray, px: float, py: float, gate: float, r_pred: float):
    """Strongest dark-disc x moving x purple-ish point within the gate: (x, y, motion value, product value) or None.
    Colour alone is dead here: the glossy pin deck reflects the purple backdrop (ring S 35 vs ball S 55 on 185331)."""
    H, W = gray.shape
    xa, xb = int(max(0, px - gate)), int(min(W, px + gate + 1))
    ya, yb = int(max(0, py - gate)), int(min(H, py + gate + 1))
    if xb - xa < 5 or yb - ya < 5:
        return None
    g = gray[ya:yb, xa:xb]
    ks = int(2 * r_pred) * 2 + 1
    sig = max(1.0, r_pred / 2)
    bh = cv2.GaussianBlur(cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks))).astype(np.float32), (0, 0), sig)
    m = cv2.GaussianBlur(mm[ya:yb, xa:xb].astype(np.float32), (0, 0), sig)
    h, s = hsv[ya:yb, xa:xb, 0], hsv[ya:yb, xa:xb, 1]
    hue = cv2.GaussianBlur(((h >= 125) & (h <= 175) & (s >= 25)).astype(np.float32), (0, 0), sig)
    prod = bh * m * hue
    iy, ix = np.unravel_index(int(np.argmax(prod)), prod.shape)
    if prod[iy, ix] <= 0:
        return None
    return (float(xa + ix), float(ya + iy), float(m[iy, ix]), float(prod[iy, ix]))


def blob_motion(mm: np.ndarray, x: float, y: float, r: float) -> float:
    H, W = mm.shape
    rr = max(2, int(round(r)))
    x0, x1, y0, y1 = max(0, int(x) - rr), min(W, int(x) + rr + 1), max(0, int(y) - rr), min(H, int(y) + rr + 1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float(mm[y0:y1, x0:x1].mean())


def find_start(frames_hsv, app: Appearance, cfg: TrackConfig) -> Optional[Tuple[int, float, float, float]]:
    """First cut frame in [start_lo, start_hi] with a round purple blob (fill >= 0.6 of its bbox, aspect 0.75-1.35,
    r >= start_min_r) in the lower 70 % of the frame: the ball just released (r 100-135 px). Gutters and the dark
    ball-return cap pass the hue window but are elongated or sparse (fill 0.1-0.55)."""
    for k in range(cfg.start_lo, cfg.start_hi + 1):
        hsv = frames_hsv[k]
        m = hsv_fixed_mask(hsv)
        H = m.shape[0]
        m[: int(0.3 * H)] = 0
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
        best = None
        for i in range(1, n):
            a = st[i, cv2.CC_STAT_AREA]
            r = math.sqrt(a / math.pi)
            w, hgt = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
            fill, aspect = a / max(w * hgt, 1), w / max(hgt, 1)
            if r >= cfg.start_min_r and fill >= 0.6 and 0.75 <= aspect <= 1.35 and (best is None or a > best[2]):
                best = (cen[i][0], cen[i][1], a, r)
        if best is not None:
            return k, float(best[0]), float(best[1]), float(best[3])
    return None


def track(frames_bgr: List[np.ndarray], dets: Dict[int, List[List[float]]], shifts: Dict[int, dict], cfg: TrackConfig,
          log=None) -> Tuple[List[dict], dict]:
    """Returns cut-local positions [{k, x, y, r, conf, src}] and a report."""
    frames_hsv = [cv2.cvtColor(f, cv2.COLOR_BGR2HSV) for f in frames_bgr]
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames_bgr]
    app = Appearance(cfg)
    st = find_start(frames_hsv, app, cfg)
    rep: dict = {'model': cfg.model, 'use_yolo': cfg.use_yolo}
    if st is None:
        rep['error'] = 'no start blob'
        return [], rep
    k0, x, y, r = st
    rep['start'] = {'k': k0, 'x': round(x, 1), 'y': round(y, 1), 'r': round(r, 1)}
    if cfg.model in ('learned', 'adaptive'):
        app.learn(frames_hsv[k0], x, y, r, weight=1.0)   # the start frame only: the ball moves 150-400 px/frame here
    pos = [{'k': k0, 'x': x, 'y': y, 'r': r, 'conf': 1.0, 'src': 'start'}]
    # size prior r(k) = A / (k - kz), kz = k0 - 2, A from the start blob; refit from accepted blobs as they come
    kz = k0 - 2
    A_samples = [r * (k0 - kz)]
    vel = (0.0, 0.0)
    peak_vals: List[float] = []
    prev_shift = None
    misses = 0
    chain_cfg = ChainConfig()
    for k in range(k0 + 1, len(frames_hsv)):
        last = pos[-1]
        sh, ok = reliable_shift(shifts, k, chain_cfg, prev_shift)
        prev_shift = sh
        px, py = apply_shift(sh, last['x'], last['y'])
        px, py = px + vel[0] * (k - last['k']), py + vel[1] * (k - last['k'])
        A = float(np.median(A_samples[-6:]))
        r_pred = max(3.0, A / max(1, k - kz))
        gate = (cfg.gate_k * r_pred + cfg.gate_min) * (1 + cfg.miss_grow * misses)
        if len(pos) == 1:
            gate = max(gate, cfg.first_gate)   # no velocity yet and the ball leaves the hand at 300-450 px/frame
        gate = max(gate, 1.5 * math.hypot(*vel) * (k - last['k']))
        cands: List[Cand] = []
        if cfg.model != 'yolo':
            cands += blobs(app.mask(frames_hsv[k]), r_pred, cfg)
        if cfg.use_yolo or cfg.model == 'yolo':
            for b in dets.get(k, []):
                if b[3] >= cfg.yolo_min_conf and cfg.size_lo * r_pred <= b[2] <= cfg.size_hi * r_pred * 1.5:
                    cands.append((b[0], b[1], b[2], float(b[3]), 'yolo', 1.0, 1.0))
        mm = None
        if cfg.motion and r_pred < cfg.motion_r and ok:
            mm = motion_map(grays[k - 1], grays[k], sh)
        reacq = cfg.reacquire and misses >= cfg.reacq_after
        if mm is not None and cfg.motion_peak:
            pk = far_peak(grays[k], frames_hsv[k], mm, px, py, gate, r_pred)
            if pk is not None:
                ref = float(np.median(peak_vals[-8:])) if peak_vals else cfg.motion_full
                if pk[2] >= cfg.peak_min * ref:
                    cands.append((pk[0], pk[1], r_pred, min(1.0, pk[2] / cfg.motion_full), 'motion', 1.0, 1.0, pk[2]))
        best, best_s = None, 0.0
        for c in cands:
            d = math.hypot(c[0] - px, c[1] - py)
            round_blob = c[4] == 'blob' and c[5] >= 0.6 and 0.75 <= c[6] <= 1.35
            if d > gate and not (reacq and round_blob):
                continue
            size = math.exp(-((math.log(c[2] / r_pred)) ** 2) / (2 * 0.5 ** 2))
            s = c[3] * size * (math.exp(-(d / gate) ** 2) if d <= gate else 0.3)
            if mm is not None and c[4] == 'blob':
                s *= min(1.0, blob_motion(mm, c[0], c[1], c[2]) / cfg.motion_full)
            if s > best_s:
                best, best_s = c, s
        if best is None:
            misses += 1
            if misses > cfg.max_miss:
                rep['stop'] = {'k': k, 'reason': 'misses'}
                break
            continue
        nx, ny, nr = best[0], best[1], best[2]
        dt = k - last['k']
        vx, vy = (nx - px + vel[0] * dt) / dt, (ny - py + vel[1] * dt) / dt
        vel = ((1 - cfg.vel_blend) * vel[0] + cfg.vel_blend * vx, (1 - cfg.vel_blend) * vel[1] + cfg.vel_blend * vy)
        misses = 0
        if best[4] == 'blob':
            A_samples.append(nr * (k - kz))
        if best[4] == 'motion':
            peak_vals.append(best[7])
        if cfg.model == 'adaptive' and best[4] == 'blob':
            app.learn(frames_hsv[k], nx, ny, max(nr, 3.0), weight=cfg.adapt)
        pos.append({'k': k, 'x': nx, 'y': ny, 'r': nr, 'conf': round(best_s, 3), 'src': best[4],
                    'mv': round(best[7], 1) if best[4] == 'motion' else None, 'step': [round(nx - px, 1), round(ny - py, 1)]})
    rep['positions'] = len(pos)
    rep['frames'] = [pos[0]['k'], pos[-1]['k']]
    rep['sources'] = {s: sum(1 for p in pos if p['src'] == s) for s in ('start', 'blob', 'yolo', 'motion')}
    return pos, rep
