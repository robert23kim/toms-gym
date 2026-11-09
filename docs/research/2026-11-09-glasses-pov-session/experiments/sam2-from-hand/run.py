"""run.py <stem> [--device mps|cpu] [--no-refine]

Session experiment 'sam2-from-hand' (stage: ball). SAM 2 prompted from the ball just out of the hand, whatever its
colour, then propagated through the roll:
  prompt : the loop-1 fine-tuned YOLO11n (colour-agnostic) at imgsz 320 on release+2..release+10, first box with
           conf >= PROMPT_CONF, side PROMPT_SIDE px, centre below the top (1 - PROMPT_Y_FRAC) of the frame (the head-down release of 104946 puts the ball at 38 % from the top); fallback: the
           largest round dark/saturated contour in the lower half at release+3..+8.
  sam    : loop-1 sam2-video track() (full-frame propagation + up to 3 far-end 2x crop re-prompts) from the prompt
           frame to the END of the cut, and track_back() from the prompt frame to release.
  gate   : loop-2 lane gate on every mask centroid using the per-frame edge lane (lane-first mask + RANSAC edges with
           the centroid as the component hint): board outside [GATE_LO, GATE_HI] is dropped unless the previous kept
           point was already at board <= 2.5 or >= 37.5; from release+8 a lateral step > LAT_BOARDS x min(2, frames skipped)
           from the last kept point is dropped (113911: SAM wandered 10 boards right through a head whip for 15 frames). The gate runs through cut pin_hit+2 only (deck points are read on the extended
           edge lines by the lane stage, as in loop 2).
  refine : far end (r_geo <= R_FAR px): disc-minus-annulus matched filter at the geometric radius on a per-clip
           ballness map learned at the prompt frame (Lab k-means of the box's central disc), the loop-2 purple filter
           with the colour learned instead of fixed. Accepted when resp >= 0.40, annulus <= 0.35, lateral <= 3 boards.
  lane / pin row / events / drawing: loop-2 track_v2 functions by import (CM.run edge+smooth3 with the ball stage
           injected, clean_series, pin_row_estimate, pin_motion, deck_decoy, add_depth, compute_events, draw_overlay_v2).
Reads S/work/cuts/cuts.json (session cuts). Writes tracks/<stem>.json (loop-2 tracks format), overlays/final__<stem>.jpg
and overlays/check__<stem>.jpg (crops at ~20/40/55 ft with that frame's own circle). Never opens truth.
"""
import argparse
import importlib.util
import json
import math
import os
import statistics
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np

S = '/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session'
L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
E = '/Users/toka/code/bowling-app/pov-engine'
X = os.path.join(S, 'experiments', 'sam2-from-hand')
sys.path.insert(0, os.path.join(L1, 'experiments', 'sam2-video'))
from sam_track import track as sam_track_fwd, track_back as sam_track_back  # noqa: E402

PROMPT_SCAN = (2, 10)
PROMPT_CONF = 0.3
PROMPT_SIDE = (60, 450)
PROMPT_Y_FRAC = 0.9
GATE_LO, GATE_HI = -0.5, 40.5
LAT_BOARDS = 3.0
LAT_GAP_CAP = 2
LAT_FROM = 8
EDGE_B = 2.5
GATE_TAIL = 2
R_FAR = 16.0
REFINE_MIN_RESP, REFINE_MAX_ANN, DIST_PEN = 0.40, 0.35, 0.015
BALL_UNITS = 7.78


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TV2 = load('track_v2', os.path.join(L2, 'track_v2.py'))
CM, LGB, LG, LN = TV2.CM, TV2.LGB, TV2.CM.LG, TV2.CM.LN
CUTS = {c['stem']: c for c in json.load(open(os.path.join(S, 'work', 'cuts', 'cuts.json')))}
CM.load_cut = lambda stem: CUTS[stem]
LGB.load_cut = lambda stem: CUTS[stem]


# ---------------------------------------------------------------- prompt
def yolo_prompt(frames, k_rel, log):
    from ultralytics import YOLO
    model = YOLO(os.path.join(E, 'models', 'yolo11n_bowling.pt'))
    H = frames[0].shape[0]
    tried = []
    for k in range(k_rel + PROMPT_SCAN[0], min(len(frames), k_rel + PROMPT_SCAN[1] + 1)):
        r = model.predict(frames[k], conf=0.1, verbose=False, imgsz=320)[0]
        if r.boxes is None or len(r.boxes) == 0:
            tried.append((k, None))
            continue
        b = r.boxes.xyxy.cpu().numpy()
        c = r.boxes.conf.cpu().numpy()
        best = None
        for (x0, y0, x1, y1), cf in zip(b, c):
            side = max(x1 - x0, y1 - y0)
            cy = 0.5 * (y0 + y1)
            if cf >= PROMPT_CONF and PROMPT_SIDE[0] <= side <= PROMPT_SIDE[1] and cy >= (1 - PROMPT_Y_FRAC) * H:
                if best is None or cf > best[1]:
                    best = ([float(v) for v in (x0, y0, x1, y1)], float(cf))
        tried.append((k, None if best is None else round(best[1], 2)))
        if best is not None:
            log(f'  [prompt] YOLO@320 box at k={k}: {[int(v) for v in best[0]]} conf {best[1]:.2f}')
            return k, best[0], f'yolo320 conf {best[1]:.2f}', tried
    return None, None, None, tried


def contour_prompt(frames, k_rel, log):
    """Largest round blob (circularity >= 0.6) of 'not lane wood' in the lower half: grey darkness + saturation blend."""
    H, W = frames[0].shape[:2]
    for k in range(k_rel + 3, min(len(frames), k_rel + 9)):
        im = frames[k]
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        wood = cv2.inRange(hsv, (LN.H_LO, LN.S_MIN, LN.V_MIN), (LN.H_HI, 255, 255))
        dark = (hsv[..., 2] < 90).astype(np.uint8) * 255
        sat = ((hsv[..., 1] > 90) & ~((hsv[..., 0] >= LN.H_LO) & (hsv[..., 0] <= LN.H_HI))).astype(np.uint8) * 255
        m = cv2.bitwise_and(cv2.bitwise_or(dark, sat), cv2.bitwise_not(wood))
        m[: H // 3] = 0
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        for c in cs:
            a = cv2.contourArea(c)
            if a < 2000:
                continue
            p = cv2.arcLength(c, True)
            circ = 4 * math.pi * a / max(p * p, 1e-6)
            (cx, cy), r = cv2.minEnclosingCircle(c)
            if circ >= 0.6 and 30 <= r <= 220 and (best is None or a > best[0]):
                best = (a, cx, cy, r, circ)
        if best is not None:
            a, cx, cy, r, circ = best
            log(f'  [prompt] contour at k={k}: centre ({cx:.0f},{cy:.0f}) r {r:.0f} circ {circ:.2f}')
            return k, [cx - r, cy - r, cx + r, cy + r], f'contour circ {circ:.2f}'
    return None, None, None


# ---------------------------------------------------------------- per-clip ball colour
class Ballness:
    """Lab k-means (k=2) of the prompt box's central disc; ballness = max over centres of a Gaussian in the Mahalanobis-
    like distance (per-centre spread, floor 6, cap 22 Lab units), thresholded at 0.5 -> float mask like LGB.purple."""

    def __init__(self, im, box):
        x0, y0, x1, y1 = box
        cx, cy, r = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.35 * max(x1 - x0, y1 - y0)
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
        Y, Xg = np.mgrid[0:im.shape[0], 0:im.shape[1]]
        d = (Xg - cx) ** 2 + (Y - cy) ** 2 <= r * r
        px = lab[d].reshape(-1, 3)
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
        _, lbl, cen = cv2.kmeans(px, 2, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        self.centres, self.sig = [], []
        for i in range(2):
            q = px[lbl.ravel() == i]
            if len(q) < 0.1 * len(px):
                continue
            s = float(np.sqrt(((q - cen[i]) ** 2).sum(axis=1).mean()))
            self.centres.append(cen[i])
            self.sig.append(min(22.0, max(6.0, s)))
        ring = ((Xg - cx) ** 2 + (Y - cy) ** 2 <= (2.2 * r) ** 2) & ~((Xg - cx) ** 2 + (Y - cy) ** 2 <= (1.4 * r) ** 2)
        self.bg_frac = float(self(im[ring].reshape(1, -1, 3)).mean()) if ring.any() else None

    def __call__(self, bgr):
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        best = np.zeros(lab.shape[:2], np.float32)
        for c, s in zip(self.centres, self.sig):
            d2 = ((lab - c) ** 2).sum(axis=2)
            best = np.maximum(best, np.exp(-0.5 * d2 / (s * s)))
        return (best >= 0.5).astype(np.float32)

    def describe(self):
        return {'centres_lab': [[round(float(v), 1) for v in c] for c in self.centres],
                'sigma': [round(s, 1) for s in self.sig], 'bg_frac_at_prompt': None if self.bg_frac is None else round(self.bg_frac, 3)}


def refine(im, ballness, x, y, r, win):
    """LGB.refine with the learned ballness map in place of the purple window."""
    H, W = im.shape[:2]
    ri, ro = max(3, int(round(r))), int(round(1.7 * r)) + 1
    pad = int(win + ro + 2)
    x0, y0, x1, y1 = int(max(0, x - pad)), int(max(0, y - pad)), int(min(W, x + pad + 1)), int(min(H, y + pad + 1))
    if x1 - x0 < 2 * ro + 3 or y1 - y0 < 2 * ro + 3:
        return None
    pm = ballness(im[y0:y1, x0:x1])
    inner = cv2.filter2D(pm, -1, LGB.disc_kernel(ri))
    outer = cv2.filter2D(pm, -1, LGB.disc_kernel(ro))
    ai, ao = math.pi * ri * ri, math.pi * ro * ro
    ann = (outer * ao - inner * ai) / max(1.0, ao - ai)
    Y, Xg = np.mgrid[y0:y1, x0:x1]
    dist = np.hypot(Xg - x, Y - y)
    resp = inner - ann - DIST_PEN * dist
    resp[(np.abs(Xg - x) > win) | (np.abs(Y - y) > win)] = -9
    yy, xx = np.unravel_index(np.argmax(resp), resp.shape)
    if resp[yy, xx] <= -9:
        return None
    d = (Xg - (xx + x0)) ** 2 + (Y - (yy + y0)) ** 2 <= ri * ri
    w = pm * d
    if w.sum() > 0:
        cx, cy = float((w * Xg).sum() / w.sum()), float((w * Y).sum() / w.sum())
    else:
        cx, cy = float(xx + x0), float(yy + y0)
    return cx, cy, float(inner[yy, xx] - ann[yy, xx]), float(inner[yy, xx]), float(ann[yy, xx])


# ---------------------------------------------------------------- lane gate
def gate_points(frames, pts, off, k_rel, k_pin, ballness, do_refine, log):
    """pts {k: (x, y, r)} -> (kept [{f,x,y,r,conf,src}], info). Per-frame edge quad with the centroid as hint."""
    kept, prev_mask, info = [], None, {'gated': [], 'quad_missing': 0, 'refined': 0, 'refine_rejected': 0, 'boards_pre': {}}
    last_b, last_k = None, None
    for k in sorted(pts):
        x, y, r = pts[k]
        q, prev_mask, qi = CM.edge_quad(frames[k], prev_mask, {'x': x, 'y': y}, False)
        b = None if q is None else LG.lane_point(q, x, y)[0]
        if b is not None and math.isfinite(b):
            info['boards_pre'][str(k + off)] = round(b, 2)
        src = 'sam'
        if k <= k_pin + GATE_TAIL and b is not None and math.isfinite(b):
            if not (GATE_LO <= b <= GATE_HI) and not (last_b is not None and (last_b <= EDGE_B or last_b >= 40.0 - EDGE_B)):
                info['gated'].append({'f': k + off, 'why': 'lane', 'board': round(b, 2)})
                continue
            if k >= k_rel + LAT_FROM and last_b is not None and abs(b - last_b) > LAT_BOARDS * min(LAT_GAP_CAP, max(1, k - last_k)):
                info['gated'].append({'f': k + off, 'why': 'lateral', 'board': round(b, 2), 'ref': round(last_b, 2)})
                continue
        elif b is None:
            info['quad_missing'] += 1
        if q is not None and do_refine and ballness is not None:
            rg = LGB.r_geo(q, y)
            if rg <= R_FAR:
                rf = refine(frames[k], ballness, x, y, rg, max(2.0 * rg, 12.0))
                ok = rf is not None and rf[2] >= REFINE_MIN_RESP and rf[4] <= REFINE_MAX_ANN
                if ok:
                    rb = LG.lane_point(q, rf[0], rf[1])[0]
                    ok = rb is not None and (b is None or abs(rb - b) <= LAT_BOARDS)
                if ok:
                    x, y, r, src = rf[0], rf[1], rg, 'sam+refine'
                    b = rb
                    info['refined'] += 1
                else:
                    info['refine_rejected'] += 1
        if b is not None and math.isfinite(b):
            last_b, last_k = b, k
        kept.append({'f': k + off, 'x': round(float(x), 1), 'y': round(float(y), 1), 'r': round(float(r), 1),
                     'conf': 1.0 if src == 'sam+refine' else 0.8, 'src': src})
    return kept, info


# ---------------------------------------------------------------- check image
def draw_check(frames, off, tr, pr, rel, out_path):
    td = {p['f']: p for p in tr.get('lane_top_down') or []}
    pts = {p['f']: p for p in tr['frames'] if p.get('src') != 'coast'}
    tiles = []
    for tgt in (20.0, 40.0, 55.0):
        cands = [f for f in pts if f in td and td[f].get('ft_cv') is not None]
        if not cands:
            continue
        f = min(cands, key=lambda g: abs(td[g]['ft_cv'] - tgt))
        p = pts[f]
        k = f - off
        if not 0 <= k < len(frames):
            continue
        im = frames[k]
        H, W = im.shape[:2]
        side = int(max(120, 8 * (p['r'] or 10)))
        x0, y0 = int(min(max(0, p['x'] - side / 2), W - side)), int(min(max(0, p['y'] - side / 2), H - side))
        crop = im[y0:y0 + side, x0:x0 + side].copy()
        sc = 240.0 / side
        crop = cv2.resize(crop, (240, 240), interpolation=cv2.INTER_CUBIC)
        cx, cy = int((p['x'] - x0) * sc), int((p['y'] - y0) * sc)
        cv2.circle(crop, (cx, cy), max(2, int((p['r'] or 3) * sc)), (0, 140, 255), 1)
        cv2.drawMarker(crop, (cx, cy), (0, 140, 255), cv2.MARKER_CROSS, 8, 1)
        t = f"{tgt:.0f}ft f{f} ({td[f]['ft_cv']:.0f}ft) b{td[f]['board']:.1f} {p['src']}"
        cv2.putText(crop, t, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 3)
        cv2.putText(crop, t, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
        tiles.append(crop)
    if tiles:
        cv2.imwrite(out_path, np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return len(tiles)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--no-refine', action='store_true')
    a = ap.parse_args()
    log = lambda *x, **k: print(*x, **k, flush=True)  # noqa: E731
    t0 = time.time()
    stem = a.stem
    cut = CUTS[stem]
    rel, pin, off = cut['release_frame'], cut['pin_hit_frame'], cut['cut_start']
    for d in ('tracks', 'overlays', 'work'):
        os.makedirs(os.path.join(X, d), exist_ok=True)
    work = os.path.join(X, 'work', stem)
    os.makedirs(work, exist_ok=True)
    frames = CM.read_frames(cut['cut_path'])
    k_rel, k_pin, k_end = rel - off, pin - off, len(frames) - 1
    log(f'{stem}: {len(frames)} cut frames {frames[0].shape[1]}x{frames[0].shape[0]}, release k={k_rel} (src {rel}), pin k={k_pin}')

    # ---- prompt
    t = time.time()
    k0, box, psrc, tried = yolo_prompt(frames, k_rel, log)
    if k0 is None:
        k0, box, psrc = contour_prompt(frames, k_rel, log)
    prompt_s = round(time.time() - t, 1)
    meta = {'device': a.device, 'cut_start': off, 'prompt_k0': None if k0 is None else k0 + off, 'prompt_src': psrc,
            'prompt_box': None if box is None else [round(v, 1) for v in box], 'prompt_tried': tried, 'prompt_s': prompt_s}
    pts = {}
    if k0 is not None:
        ballness = Ballness(frames[k0], box) if not a.no_refine else None
        meta['ballness'] = None if ballness is None else ballness.describe()
        t = time.time()
        fwd, passes = sam_track_fwd(frames, k0, box, device=a.device, work_dir=work, k_end=k_end, log=log)
        pts.update(fwd)
        if k0 in fwd:
            back = sam_track_back(frames, k0, box, k_rel, device=a.device, work_dir=work, log=log)
            pts.update(back)
            meta['back_frames'] = len(back)
        meta['passes'] = passes
        meta['sam_s'] = round(time.time() - t, 1)
    else:
        ballness = None
        log('  [prompt] nothing found; empty track')
    t = time.time()
    balls, ginfo = gate_points(frames, pts, off, k_rel, k_pin, ballness, not a.no_refine, log)
    meta['gate'] = {k: v for k, v in ginfo.items() if k != 'boards_pre'}
    meta['gate_s'] = round(time.time() - t, 1)
    meta['sam_points'] = len(pts)
    log(f'  [gate] {len(pts)} sam points -> {len(balls)} kept; gated {len(ginfo["gated"])}, refined {ginfo["refined"]}, '
        f'refine rejected {ginfo["refine_rejected"]}, quad missing {ginfo["quad_missing"]}')

    # ---- lane stage (loop-2 composition edge+smooth3 with the ball stage injected)
    CM.ball_stage = lambda s, c, how, lg: ([dict(p) for p in balls], 'sam2-from-hand (injected)')
    t = time.time()
    lane_tr = CM.run(stem, SimpleNamespace(device=a.device, lane='edge', refine=False, smooth=3, ball='file',
                                            out_dir=os.path.join(X, 'work', 'comp')), log)
    lane_s = round(time.time() - t, 1)
    tr = {k: lane_tr.get(k) for k in ('frames', 'lane', 'boards', 'boards_raw', 'boards_contact', 'final_board',
                                      'lane_top_down', 'lane_top_down_model')}
    tr['final_board_pre_fixpass'] = tr.get('final_board')
    rejected, pf_clean = TV2.clean_series(tr, rel, pin)
    lane_meta = {k: lane_tr['meta'].get(k) for k in ('lane_variant', 'lane_sources', 'edge_fit_failures',
                                                       'edge_fail_reasons', 'fallback_used', 'smooth', 'lane_s', 'board_row')}
    # ---- pin row, events (track_v2 post-lane sequence)
    t = time.time()
    pr_info = TV2.pin_row_estimate(tr, {}, rel, pin, frames, off)
    geo = pr_info['pin_row_source'].startswith('detected')
    pr_info['pin_row_frame_geometric'] = pr_info['pin_row_frame_est'] if geo else None
    mo = LGB.Motion(frames)
    pm, pm_info = TV2.pin_motion(tr, frames, off, pin, mo)
    tr['pin_motion'] = pm_info
    pr_info['pin_motion_frame'] = pm
    if pm is not None:
        pr_info['pin_row_frame_est'] = pm - TV2.PM_LEAD
        pr_info['pin_row_source'] = f'pin motion: first camera-compensated rack motion f{pm} - {TV2.PM_LEAD}'
    elif geo:
        pr_info['pin_row_source'] = 'geometric: ' + pr_info['pin_row_source']
    pr_info['pin_row_minus_cut'] = pr_info['pin_row_frame_est'] - pin
    pr = pr_info['pin_row_frame_est']
    tr['deck_decoy_from'], tr['deck_motion_px'] = TV2.deck_decoy(tr, frames, off, pr, mo)
    tr['cut_last_frame'] = off + len(frames) - 1
    TV2.add_depth(tr, rel, pin, pr)
    events = TV2.compute_events(tr, rel, pr)
    events.update({k: v for k, v in pr_info.items() if k != 'pin_row_frame_est'})
    events_s = round(time.time() - t, 1)
    log(f'[pin row] {pr_info["pin_row_source"]} f{pr} (cut {pin})')
    log(f'[events] entry {events["entry_board"]} exit f{events["exit_frame"]} {events["exit_board"]} deck {events["deck_frames"]} '
        f'break {events["breakpoint_board"]} @ {events["breakpoint_ft"]} ft')
    wall = round(time.time() - t0, 1)
    out = {'stem': stem, 'method': 'sam2-from-hand', 'stage': 'both',
           'stages': {'ball': 'sam2-from-hand', 'lane': 'composition/edge+smooth3', 'path': 'none'},
           **tr,
           'release_frame': rel, 'pin_hit_frame': pin, 'pin_row_frame_est': pr,
           'events': events,
           'final_board_rule': 'Theil-Sen over boards in pin_hit-10..pin_hit evaluated at pin_hit (composition fit_path), on the series after clean_series',
           'path_fit_diag': pf_clean, 'fallback': [], 'fallback_reasons': {},
           'meta': {**meta, **lane_meta, 'lane_stage_s': lane_s, 'events_s': events_s, 'wall_s': wall,
                    'stages': {'ball': 'sam2-from-hand', 'lane': 'composition/edge+smooth3', 'path': 'none'},
                    'boards_pre_gate': ginfo['boards_pre'],
                    'wall_note': 'whole process: prompt + SAM 2 + gate/refine + edge lane + pin row/events + drawing'}}
    tp = os.path.join(X, 'tracks', f'{stem}.json')
    json.dump(out, open(tp, 'w'), indent=1)
    quads = {int(k): v for k, v in (out.get('lane') or {}).items()}
    hdr = [f"ball sam2-from-hand ({psrc}) | lane composition/edge+smooth3 | path none | gated {len(ginfo['gated'])} refined {ginfo['refined']}",
           f"series rejected {sorted(int(k) for k in out.get('series_rejected') or {}) or '-'} | pin row {pr_info['pin_row_source'][:40]}"]
    op = os.path.join(X, 'overlays', f'final__{stem}.jpg')
    out['meta']['overlay'] = TV2.draw_overlay_v2(frames, dict(cut, pin_hit_frame=pr), dict(out, final_board=events['entry_board']),
                                                 op, quads, hdr)
    out['meta']['check_tiles'] = draw_check(frames, off, out, pr, rel, os.path.join(X, 'overlays', f'check__{stem}.jpg'))
    json.dump(out, open(tp, 'w'), indent=1)
    log(f'SAM2_FROM_HAND {stem}: points={len(out["frames"])} boards={len(out.get("boards") or {})} entry={events["entry_board"]} '
        f'pin_row={pr} (cut {pin}) wall={wall}s (prompt {prompt_s} sam {meta.get("sam_s")} gate {meta["gate_s"]} lane {lane_s} events {events_s}) -> {tp}')


if __name__ == '__main__':
    main()
