"""run.py <stem> [--model fixed|learned|adaptive|yolo] [--no-yolo] [--no-sam] [--out-dir DIR] [--tag TAG]
Reads L/work/cuts/cuts.json and the cut, tracks the ball with apptrack, calibrates the lane with the engine's SAM
pass (segment = the track), writes tracks/<stem>.json (SOURCE frame numbers) and overlays/<stem>.jpg."""
import argparse, json, subprocess, sys, time
from pathlib import Path

import cv2
import numpy as np

X = Path(__file__).resolve().parent
L = X.parent.parent
E = Path('/Users/toka/code/bowling-app/pov-engine')
sys.path.insert(0, str(E))
sys.path.insert(0, str(X))
from apptrack import TrackConfig, track  # noqa: E402

PY = sys.executable


def load_frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    return out


def ensure_cache(stem):
    p = X / 'cache' / f'{stem}.json'
    if not p.exists():
        subprocess.run([PY, str(X / 'cache_scan.py'), stem], check=True, cwd=str(X))
    c = json.load(open(p))
    dets = {int(k): v for k, v in c['dets'].items()}
    shifts = {int(k): v for k, v in c['shifts'].items()}
    return dets, shifts, c['meta']


def sam_lane(cut_path, pos, log, pin_hit=None, verbose=False, back=4):
    """Engine SAM lane calibration prompted from the track (cut-local). Returns (lane per frame, final_board, last_lane_frame, info)."""
    from scripts.sam_lane_pass import run_sam_lane_pass
    positions = [(p['k'], p['x'], p['y'], p['r']) for p in pos]
    import os
    cwd = os.getcwd()
    os.chdir(str(E))   # weights resolve relative to the engine root
    try:
        calib, fields = run_sam_lane_pass(cut_path, positions, pin_hit=pin_hit, verbose=verbose, segment=positions, back=back)
    finally:
        os.chdir(cwd)
    if calib is None:
        return {}, None, None, {'lane_method': 'none', 'error': fields.get('lane_calibration_error'), 'sam_s': fields.get('lane_calibration_s')}
    d = calib.to_dict()
    lane = {}
    for f, q in d['per_frame'].items():
        lane[int(f)] = {'pd_l': q['top_left'], 'pd_r': q['top_right'], 'fl_l': q['bottom_left'], 'fl_r': q['bottom_right'],
                        'fl_is_foul_line': False}
    info = {'lane_method': fields.get('lane_method'), 'final_board_raw': fields.get('final_board_raw'),
            'entry_board': fields.get('entry_board'), 'on_lane_positions': fields.get('on_lane_positions'),
            'sam_s': fields.get('lane_calibration_s'), 'quality': d.get('quality')}
    return lane, fields.get('final_board'), fields.get('last_lane_frame'), info


def draw_overlay(frames, cut, pos, lane, final_board, out_path, label):
    pin = cut['pin_hit_frame']
    k = max(0, min(len(frames) - 1, pin - 4 - cut['cut_start']))
    im = frames[k].copy()
    pts = np.array([[int(round(p['x'])), int(round(p['y']))] for p in pos], np.int32)
    if len(pts) >= 2:
        cv2.polylines(im, [pts], False, (0, 165, 255), 3)
    for p in pos:
        col = (0, 165, 255) if p['src'] == 'blob' else (255, 0, 255) if p['src'] == 'yolo' else (255, 255, 255) if p['src'] == 'motion' else (0, 255, 0)
        cv2.circle(im, (int(round(p['x'])), int(round(p['y']))), max(2, int(round(p['r']))), col, 2)
    q = lane.get(k) or (lane.get(min(lane, key=lambda g: abs(g - k))) if lane else None)
    if q:
        poly = np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)
        cv2.polylines(im, [poly], True, (255, 255, 0), 3)
    y0 = 40
    for line in [label, f'frame {pin - 4} (pin_hit-4)  final board {final_board}  lane frames {len(lane)}',
                 'orange = colour blob, white = motion peak, magenta = yolo box, green = start, cyan = SAM lane']:
        cv2.putText(im, line, (16, y0), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(im, line, (16, y0), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        y0 += 36
    cv2.imwrite(str(out_path), im, [cv2.IMWRITE_JPEG_QUALITY, 80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--model', default='fixed', help='fixed (default, best) | learned | adaptive | yolo')
    ap.add_argument('--yolo', action='store_true', help='add cached YOLO boxes as candidates (off by default: no gain on dev)')
    ap.add_argument('--bp-thresh', type=int, default=40)
    ap.add_argument('--sam-back', type=int, default=4)
    ap.add_argument('--sam-retry-offset', type=int, default=0, help='on refusal retry once with the pin-hit prompt moved by this many frames (0 = no retry)')
    ap.add_argument('--sam-r-scale', type=float, default=1.0, help='inflate track radii for the SAM pass (YOLO boxes were 2-3x the ball)')
    ap.add_argument('--no-sam', action='store_true')
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    cuts = {c['stem']: c for c in json.load(open(L / 'work' / 'cuts' / 'cuts.json'))}
    cut = cuts[a.stem]
    out_dir = Path(a.out_dir) if a.out_dir else X
    (out_dir / 'tracks').mkdir(parents=True, exist_ok=True)
    (out_dir / 'overlays').mkdir(parents=True, exist_ok=True)
    method = f'appearance-prior/{a.model}' + ('+yolo' if a.yolo else '') + (' (no sam)' if a.no_sam else '')
    if a.tag:
        method += f' [{a.tag}]'
    doc = {'stem': a.stem, 'method': method, 'frames': [], 'lane': {}, 'boards': {}, 'final_board': None,
           'release_frame': None, 'pin_hit_frame': None, 'meta': {}}
    if not cut.get('cut_path'):
        doc['meta'] = {'error': 'no cut (no throw in the clip)'}
        json.dump(doc, open(out_dir / 'tracks' / f'{a.stem}.json', 'w'), indent=1)
        print(json.dumps({'stem': a.stem, 'error': 'no cut'}))
        return
    off = cut['cut_start']
    frames = load_frames(cut['cut_path'])
    dets, shifts, scan_meta = ensure_cache(a.stem)
    t1 = time.time()
    cfg = TrackConfig(model=a.model, use_yolo=a.yolo, bp_thresh=a.bp_thresh)
    pos, rep = track(frames, dets, shifts, cfg)
    t2 = time.time()
    lane, final_board, last_lane, sam_info = ({}, None, None, {'lane_method': 'skipped'})
    if pos and not a.no_sam:
        # pin-hit prompt for the lane pass = cuts.json pin_hit_frame (cut-local). This is the visual/truth frame from the
        # cut table, NOT estimated here: the ball's own motion gives no usable pin-hit cue (probe_pinhit.py), and without
        # it SAM calibrates at the cut end, after the ball has left the lane (4 of 5 dev refused).
        pin_k = cut['pin_hit_frame'] - off
        # the engine warps the segment into the calibration frame through the ORB camera model, which is garbage on the
        # release frames (5-17 inliers, scale 0.4): start the SAM segment where the shifts are reliable (3 frames in a row
        # with >= 30 inliers), as the YOLO chain implicitly did by starting 8-11 frames after release.
        good = sorted(k for k, s in shifts.items() if s.get('inliers', 0) >= 30 and k >= pos[0]['k'])
        k_ok = next((k for k in good if k + 1 in shifts and k + 2 in shifts and shifts[k + 1].get('inliers', 0) >= 30
                     and shifts[k + 2].get('inliers', 0) >= 30), pos[0]['k'] + 8)
        seg = [dict(p, r=p['r'] * a.sam_r_scale) for p in pos if k_ok <= p['k'] <= pin_k + 2]
        lane, final_board, last_lane, sam_info = sam_lane(cut['cut_path'], seg, print, pin_hit=pin_k, verbose=a.verbose, back=a.sam_back)
        sam_info['pin_hit_prompt'] = {'k': pin_k, 'source': 'cuts.json pin_hit_frame', 'segment_positions': len(seg), 'segment_from_k': k_ok}
        if final_board is None and a.sam_retry_offset:
            # refused (residual / far-end-too-wide gates on the frames right before the pin hit): retry once with the
            # candidate frames moved earlier, where the ball is still on the lane and the head is steadier
            pin2 = pin_k + a.sam_retry_offset
            seg2 = [dict(p, r=p['r'] * a.sam_r_scale) for p in pos if k_ok <= p['k'] <= pin2 + 2]
            lane, final_board, last_lane, info2 = sam_lane(cut['cut_path'], seg2, print, pin_hit=pin2, verbose=a.verbose, back=a.sam_back)
            info2['retry'] = {'pin_hit_k': pin2, 'first_attempt': sam_info}
            sam_info = info2
    t3 = time.time()
    n = len(frames)
    for p in pos:
        assert 0 <= p['k'] < n
    doc['frames'] = [{'f': p['k'] + off, 'x': round(p['x'], 1), 'y': round(p['y'], 1), 'r': round(p['r'], 1),
                      'conf': p['conf'], 'src': p['src']} for p in pos]
    doc['lane'] = {str(k + off): v for k, v in lane.items() if 0 <= k < n}
    doc['final_board'] = None if final_board is None else float(final_board)
    doc['release_frame'] = (pos[0]['k'] + off) if pos else None
    doc['pin_hit_frame'] = (last_lane + off) if last_lane is not None else (cut['pin_hit_frame'] if pos else None)
    doc['meta']['pin_hit_source'] = 'sam last_lane_frame' if last_lane is not None else 'cuts.json pin_hit_frame'
    doc['meta'] = {'track': rep, 'sam': sam_info, 'scan_s_cached': scan_meta.get('scan_s'),
                   'wall_s': {'load': round(t1 - t0, 1), 'track': round(t2 - t1, 1), 'sam': round(t3 - t2, 1),
                              'total_excl_scan': round(t3 - t0, 1), 'total_incl_scan': round(t3 - t0 + (scan_meta.get('scan_s') or 0), 1)}}
    for p in doc['frames']:
        assert off <= p['f'] <= cut['cut_end'], p
    json.dump(doc, open(out_dir / 'tracks' / f'{a.stem}.json', 'w'), indent=1)
    draw_overlay(frames, cut, pos, lane, doc['final_board'], out_dir / 'overlays' / f'{a.stem}.jpg', f'{a.stem}  {method}')
    print(json.dumps({'stem': a.stem, 'track': rep, 'final_board': doc['final_board'], 'sam': sam_info, 'wall': doc['meta']['wall_s']}))


if __name__ == '__main__':
    main()
