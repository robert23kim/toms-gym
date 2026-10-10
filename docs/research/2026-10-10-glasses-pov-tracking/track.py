"""track.py <stem> [--device mps|cpu]: the loop's chosen method (sam2-video) as one entry point.

Glue over experiments/sam2-video (prompt.py, sam_track.py, run.py) + the engine SAM lane pass.
Writes results/tracks/<stem>.json (tracks format, SOURCE frames, plus lane_top_down) and overlays/final__<stem>.jpg.
Inputs: work/cuts/cuts.json, the cut, the engine worktree, and results/tracks_baseline/ for the fallback.
"""
import argparse, json, os, sys, time

L = os.path.dirname(os.path.abspath(__file__))
X = os.path.join(L, 'experiments', 'sam2-video')
sys.path.insert(0, L)
sys.path.insert(0, X)
import run as S  # noqa: E402  (experiments/sam2-video/run.py; puts the engine on sys.path)
from sam_track import track, track_back  # noqa: E402
from lane_geom import lane_point, depth_ratio, fit_ft_model, image_point  # noqa: E402

METHOD = 'sam2-video'
FALLBACK_CONFIG = 'yolo_chain_sam'
MIN_POINTS = 15


def pin_rows(calib, ks):
    from src.bowling.lane_tracking.frame_alignment import warp_point
    (la, lb), (ra, rb) = calib.left, calib.right
    y = calib.pin_row
    p_ref = (0.5 * ((la * y + lb) + (ra * y + rb)), y)
    return {k: warp_point(calib.aligner.transform(calib.ref_frame, k), p_ref)[1] for k in ks}


def run_method(stem, device, log):
    t_start = time.time()
    cut = S.load_cut(stem)
    empty = {'stem': stem, 'method': METHOD, 'frames': [], 'lane': {}, 'boards': {}, 'final_board': None,
             'release_frame': None, 'pin_hit_frame': None, 'meta': {'note': 'no cut: no throw in the clip',
                                                                   'passes': [], 'device': device}}
    if not cut.get('cut_path'):
        empty['meta']['wall_s'] = round(time.time() - t_start, 1)
        return empty, None, cut
    off = cut['cut_start']
    frames = S.read_frames(cut['cut_path'])
    k_rel, k_pin = cut['release_frame'] - off, cut['pin_hit_frame'] - off
    work = os.path.join(L, 'work', 'final', stem)
    os.makedirs(work, exist_ok=True)
    k0, box, src = S.find_prompt(frames, k_rel, log)
    meta = {'device': device, 'prompt_k0': None if k0 is None else k0 + off, 'prompt_src': src, 'passes': [],
            'release_source': 'cuts.json', 'pin_hit_source': 'cuts.json', 'cut_start': off}
    pts = {}
    if k0 is not None:
        t0 = time.time()
        sam_pts, passes = track(frames, k0, box, device=device, work_dir=work,
                                k_end=min(len(frames) - 1, k_pin + S.PIN_TAIL), log=log)
        meta['passes'], meta['sam_s'] = passes, round(time.time() - t0, 1)
        pts.update(sam_pts)
        if k0 in sam_pts:
            back = track_back(frames, k0, box, k_rel, device=device, work_dir=work, log=log)
            pts.update(S.near_release(frames, k_rel, k0, sam_pts[k0], log))
            pts.update(back)
    positions = [(k, pts[k][0], pts[k][1], pts[k][2], 1.0) for k in sorted(pts)]
    lane, boards, final_board, pin_y = {}, {}, None, {}
    if positions:
        t0 = time.time()
        seg = [p for p in positions if k_rel + S.LANE_SEG_START <= p[0] <= k_pin]
        calib, fields, per, bmap = S.lane_pass(cut, [p for p in positions if p[0] <= k_pin], seg, k_pin, log)
        meta['lane_s'], meta['lane_method'] = round(time.time() - t0, 1), fields.get('lane_method')
        meta['lane_error'] = fields.get('lane_calibration_error')
        if calib is not None:
            final_board = fields.get('final_board')
            meta['final_board_raw'] = fields.get('final_board_raw')
            meta['pin_row_ref'] = calib.pin_row
            meta['pins_rack_accepted'] = calib.pins_row is not None
            meta['last_lane_frame'] = None if fields.get('last_lane_frame') is None else fields['last_lane_frame'] + off
            pin_y = pin_rows(calib, list(per))
            for k, c in per.items():
                q = S.quad(c)
                q['pin_y'] = round(float(pin_y[k]), 1)
                lane[str(k + off)] = q
            boards = {str(k + off): round(float(b), 2) for k, b in bmap.items() if b is not None}
    meta['wall_s'] = round(time.time() - t_start, 1)
    tr = {'stem': stem, 'method': METHOD,
          'frames': [{'f': k + off, 'x': round(pts[k][0], 1), 'y': round(pts[k][1], 1), 'r': round(pts[k][2], 1),
                      'conf': None} for k in sorted(pts)],
          'lane': lane, 'boards': boards, 'final_board': None if final_board is None else float(final_board),
          'release_frame': cut['release_frame'], 'pin_hit_frame': cut['pin_hit_frame'], 'meta': meta}
    return tr, frames, cut


def baseline_track(stem):
    p = os.path.join(L, 'results', 'tracks_baseline', f'{FALLBACK_CONFIG}__{stem}.json')
    return json.load(open(p)) if os.path.exists(p) else None


def add_top_down(tr):
    lanes = tr.get('lane') or {}
    rel, pin = tr.get('release_frame'), tr.get('pin_hit_frame')
    samples = []
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if q and rel is not None and pin is not None and rel <= p['f'] <= pin:
            s = depth_ratio(q, p['y'])
            board = lane_point(q, p['x'], p['y'])[0]
            if s is not None and s <= 1.05 and board is not None and 0.5 <= board <= 39.5:
                samples.append((p['f'], s))
    model = fit_ft_model(samples, rel)
    out = []
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if not q:
            continue
        board, ft = lane_point(q, p['x'], p['y'], model['a'], model['b'])
        if board is None or ft is None:
            continue
        on = bool(0.5 <= board <= 39.5 and 0.0 <= ft <= 60.5)
        zone = ('behind_foul' if ft < 0 else 'past_pins' if ft > 60.5 else 'gutter_r' if board < 0.5
                else 'gutter_l' if board > 39.5 else 'lane')
        out.append({'f': p['f'], 'board': round(board, 2), 'ft': round(ft, 2), 'on_lane': on, 'zone': zone,
                    'board_engine': tr.get('boards', {}).get(str(p['f']))})
    tr['lane_top_down'] = out
    tr['lane_top_down_model'] = model


def final_overlay(frames, cut, tr, out_path):
    """run.overlay (raw per-frame track, cyan quad) + the track re-projected into the shown frame through lane_top_down
    (green: camera motion removed) + a top-down strip (board 39 left, foul line bottom)."""
    import cv2, numpy as np
    S.overlay(frames, cut, tr, out_path)
    im = cv2.imread(out_path)
    off = cut['cut_start']
    f = off + max(0, min(len(frames) - 1, cut['pin_hit_frame'] - 4 - off))
    q = (tr.get('lane') or {}).get(str(f))
    m = tr.get('lane_top_down_model') or {'a': 60.0, 'b': 0.0}
    td = [p for p in tr.get('lane_top_down') or [] if p['zone'] in ('lane', 'gutter_r', 'gutter_l')]
    if q and td:
        pts = [image_point(q, p['board'], p['ft'], m['a'], m['b']) for p in td]
        pl = [(int(x / 2), int(y / 2)) for x, y in (p for p in pts if p is not None)]
        if len(pl) > 1:
            cv2.polylines(im, [np.array(pl, np.int32)], False, (60, 220, 60), 3)
    H = im.shape[0]
    W = 120
    strip = np.full((H, W, 3), (70, 160, 215), np.uint8)
    for bd in (5, 10, 15, 20, 25, 30, 35):
        x, y = int(W * (39 - (1 + (bd - 0.5) * 38 / 39)) / 38), int(H * (1 - 15 / 60))
        cv2.drawMarker(strip, (x, y), (40, 40, 40), cv2.MARKER_TRIANGLE_UP, 8, 2)
    cv2.circle(strip, (int(W * 19 / 38), 6), 4, (255, 255, 255), -1)
    tp = [(int(W * (39 - min(max(p['board'], -0.5), 40.5)) / 38), int(H * (1 - p['ft'] / 60))) for p in td]
    if len(tp) > 1:
        cv2.polylines(strip, [np.array(tp, np.int32)], False, (150, 40, 150), 3)
    if tr.get('final_board') is not None:
        cv2.putText(strip, f"b{tr['final_board']:g}", (6, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.imwrite(out_path, np.hstack([im, strip]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--top-down-only', action='store_true', help='recompute lane_top_down on the existing output')
    args = ap.parse_args()
    out = os.path.join(L, 'results', 'tracks', f'{args.stem}.json')
    if args.top_down_only:
        tr = json.load(open(out))
        add_top_down(tr)
        json.dump(tr, open(out, 'w'), indent=1)
        print(f'{args.stem}: {len(tr["lane_top_down"])} top-down points, model {tr["lane_top_down_model"]}')
        cut = S.load_cut(args.stem)
        if cut.get('cut_path'):
            final_overlay(S.read_frames(cut['cut_path']), cut, tr, os.path.join(L, 'overlays', f'final__{args.stem}.jpg'))
        return
    log = lambda *a, **k: print(*a, **k, flush=True)  # noqa: E731
    tr, frames, cut = run_method(args.stem, args.device, log)
    reasons = []
    if len(tr['frames']) < MIN_POINTS:
        reasons.append(f'{len(tr["frames"])} points < {MIN_POINTS}')
    if tr['final_board'] is None:
        reasons.append('no final_board')
    fb = {'triggered': bool(reasons), 'reasons': reasons, 'applied': False}
    if reasons:
        base = baseline_track(args.stem)
        if base is None:
            fb['not_applied_because'] = 'no baseline track for this stem'
        elif len(base.get('frames') or []) < MIN_POINTS or base.get('final_board') is None:
            fb['not_applied_because'] = (f'baseline {FALLBACK_CONFIG} has {len(base.get("frames") or [])} points, '
                                         f'final_board {base.get("final_board")}: it does not fix what triggered')
        else:
            meta = dict(base.get('meta') or {})
            meta.update({'passes': [], 'device': args.device, 'wall_s': tr['meta'].get('wall_s'),
                         'replaced_method_meta': tr['meta']})
            tr = dict(base, stem=args.stem, method=f'{METHOD}+fallback:{FALLBACK_CONFIG}', meta=meta)
            fb['applied'] = True
    tr['meta']['fallback'] = fb
    add_top_down(tr)
    os.makedirs(os.path.join(L, 'results', 'tracks'), exist_ok=True)
    json.dump(tr, open(out, 'w'), indent=1)
    if frames is not None and cut.get('cut_path'):
        final_overlay(frames, cut, tr, os.path.join(L, 'overlays', f'final__{args.stem}.jpg'))
    log(f'wrote {out}: method {tr["method"]}, {len(tr["frames"])} frames, final board {tr["final_board"]}, '
        f'top-down {len(tr["lane_top_down"])}, fallback {fb}, wall {tr["meta"].get("wall_s")}s')


if __name__ == '__main__':
    main()
