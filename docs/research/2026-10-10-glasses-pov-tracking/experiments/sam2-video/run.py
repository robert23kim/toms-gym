"""run.py <stem> [--device mps|cpu]: SAM 2 video-propagation tracker for the glasses-POV cuts.

Reads L/work/cuts/cuts.json + the cut, writes tracks/<stem>.json (SOURCE frames) and overlays/<stem>.jpg.
"""
import argparse, json, os, sys, time
import cv2, numpy as np

L = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
X = os.path.join(L, 'experiments', 'sam2-video')
E = '/Users/toka/code/bowling-app/pov-engine'
sys.path.insert(0, X)
sys.path.insert(0, E)
from prompt import compact_blobs, blob_at, chained_blob  # noqa: E402
from sam_track import track, track_back  # noqa: E402

PROMPT_OFFSET = 3          # first prompt frame = release + 3 (ball clear of the hand on the dev stems)
PROMPT_SCAN = 20           # scan release+3 .. release+23 for the first chained compact purple blob (185121 re-enters at release+16)
NEAR_MAX_DIST = 200.0
LANE_SEG_START = 8         # lane pass segment = release+8 .. pin hit: the aligner's warp through the release frames is broken
PIN_TAIL = 4               # SAM passes stop at pin hit + 4 (cut-local); the cut runs 20 past pin hit


def load_cut(stem):
    cuts = {c['stem']: c for c in json.load(open(os.path.join(L, 'work', 'cuts', 'cuts.json')))}
    return cuts[stem]


def read_frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        out.append(im)
    return out


def yolo_box(frames, k, conf=0.15):
    from ultralytics import YOLO
    model = YOLO(os.path.join(E, 'models', 'yolo11n_bowling.pt'))
    r = model.predict(frames[k], conf=conf, verbose=False, imgsz=1280)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None
    b = r.boxes.xyxy.cpu().numpy()
    c = r.boxes.conf.cpu().numpy()
    i = int(np.argmax(c))
    return [float(v) for v in b[i]], float(c[i])


def find_prompt(frames, k_rel, log):
    """First compact purple blob at release+3.., else the best YOLO box in the same window."""
    for k in range(k_rel + PROMPT_OFFSET, min(len(frames), k_rel + PROMPT_OFFSET + PROMPT_SCAN + 1)):
        b = chained_blob(frames, k)
        if b is not None:
            log(f'  [prompt] chained compact blob at k={k}: {b[:4]} area {b[4]}')
            return k, list(b[:4]), 'blob-chain'
    for k in range(k_rel + PROMPT_OFFSET, min(len(frames), k_rel + PROMPT_OFFSET + PROMPT_SCAN + 1)):
        yb = yolo_box(frames, k)
        if yb is not None:
            log(f'  [prompt] YOLO box at k={k}: {yb}')
            return k, yb[0], 'yolo'
    return None, None, None


def near_release(frames, k_rel, k0, first_pt, log):
    """Cheap points for release..k0-1: the compact blob chained backwards from the prompt."""
    pts = {}
    nxt = first_pt
    for k in range(k0 - 1, k_rel - 1, -1):
        b = blob_at(frames[k], near=nxt, max_dist=NEAR_MAX_DIST + 2 * nxt[2])
        if b is None:
            break
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        r = float(np.sqrt(b[4] / np.pi))
        pts[k] = (cx, cy, r)
        nxt = (cx, cy, r)
    log(f'  [near] {len(pts)} near-release blob points for k {k_rel}..{k0 - 1}')
    return pts


def lane_pass(cut, positions, seg, pin_hit_k, log):
    """Engine SAM lane calibration on the cut with the SAM track as the rolling segment."""
    from scripts.sam_lane_pass import run_sam_lane_pass
    cwd = os.getcwd()
    os.chdir(E)
    try:
        calib, fields = run_sam_lane_pass(cut['cut_path'], positions, pin_hit=pin_hit_k, weights='sam2.1_t.pt',
                                          weights_dir=os.path.join(E, 'models'), json_path=None, overlay_path=None,
                                          verbose=False, segment=seg)
    finally:
        os.chdir(cwd)
    if calib is None:
        log(f"  [lane] no calibration: {fields.get('lane_calibration_error')}")
        return None, fields, {}, {}
    from scripts.sam_lane_pass import calibrated_boards
    boards = {int(p['frame']): p.get('board') for p in calibrated_boards(calib, positions)}
    doc = calib.to_dict()
    per = {int(k): v for k, v in (doc.get('per_frame') or {}).items()}
    log(f"  [lane] {calib.method}: final board {fields.get('final_board')} (raw {fields.get('final_board_raw')}), "
        f"last_lane_frame {fields.get('last_lane_frame')}, {fields.get('lane_calibration_s')}s")
    return calib, fields, per, boards


CORNER_MAP = {'top_left': 'pd_l', 'top_right': 'pd_r', 'bottom_left': 'fl_l', 'bottom_right': 'fl_r'}


def quad(c):
    q = {CORNER_MAP[k]: [round(float(c[k][0]), 1), round(float(c[k][1]), 1)] for k in CORNER_MAP}
    q['fl_is_foul_line'] = False
    return q


def overlay(frames, cut, tr, out_path):
    off = cut['cut_start']
    k = max(0, min(len(frames) - 1, cut['pin_hit_frame'] - 4 - off))
    im = frames[k].copy()
    f = off + k
    q = tr['lane'].get(str(f))
    if q:
        pts = np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)
        cv2.polylines(im, [pts], True, (255, 255, 0), 3)
    pl = [(int(p['x']), int(p['y'])) for p in tr['frames']]
    if len(pl) > 1:
        cv2.polylines(im, [np.array(pl, np.int32)], False, (0, 140, 255), 3)
    for p in tr['frames']:
        cv2.circle(im, (int(p['x']), int(p['y'])), max(2, int(p['r'] or 4)), (0, 140, 255), 1)
    txt = [f"sam2-video {tr['stem']} f{f}", f"final board {tr['final_board']}  frames {len(tr['frames'])}  "
           f"{tr['frames'][0]['f'] if tr['frames'] else '-'}..{tr['frames'][-1]['f'] if tr['frames'] else '-'}",
           f"passes {len(tr['meta']['passes'])}  wall {tr['meta']['wall_s']}s {tr['meta']['device']}"]
    for i, t in enumerate(txt):
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 6)
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    cv2.imwrite(out_path, cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--no-lane', action='store_true')
    args = ap.parse_args()
    log = lambda *a, **k: print(*a, **k, flush=True)  # noqa: E731
    t_start = time.time()
    cut = load_cut(args.stem)
    os.makedirs(os.path.join(X, 'tracks'), exist_ok=True)
    os.makedirs(os.path.join(X, 'overlays'), exist_ok=True)
    work = os.path.join(X, 'work', args.stem)
    os.makedirs(work, exist_ok=True)
    out_path = os.path.join(X, 'tracks', f'{args.stem}.json')
    if not cut.get('cut_path'):
        tr = {'stem': args.stem, 'method': 'sam2-video', 'frames': [], 'lane': {}, 'boards': {}, 'final_board': None,
              'release_frame': None, 'pin_hit_frame': None, 'meta': {'note': 'no cut: no throw in the clip'}}
        json.dump(tr, open(out_path, 'w'), indent=1)
        log('no cut; empty track written')
        return
    off = cut['cut_start']
    frames = read_frames(cut['cut_path'])
    k_rel = cut['release_frame'] - off
    k_pin = cut['pin_hit_frame'] - off
    log(f'{args.stem}: {len(frames)} cut frames, release k={k_rel} (src {cut["release_frame"]}), pin k={k_pin}')
    k0, box, src = find_prompt(frames, k_rel, log)
    meta = {'device': args.device, 'prompt_k0': None if k0 is None else k0 + off, 'prompt_src': src, 'passes': [],
            'release_source': 'cuts.json', 'pin_hit_source': 'cuts.json (lane pass pin guess)', 'cut_start': off}
    pts = {}
    if k0 is not None:
        t0 = time.time()
        sam_pts, passes = track(frames, k0, box, device=args.device, work_dir=work, k_end=min(len(frames) - 1, k_pin + PIN_TAIL), log=log)
        meta['passes'] = passes
        meta['sam_s'] = round(time.time() - t0, 1)
        pts.update(sam_pts)
        if k0 in sam_pts:
            back = track_back(frames, k0, box, k_rel, device=args.device, work_dir=work, log=log)
            meta['back_frames'] = len(back)
            near = near_release(frames, k_rel, k0, sam_pts[k0], log)
            meta['near_blob_frames'] = len(near)
            pts.update(near)      # blob points first, SAM backward masks override where both exist
            pts.update(back)
    positions = [(k, pts[k][0], pts[k][1], pts[k][2], 1.0) for k in sorted(pts)]
    lane, boards, final_board = {}, {}, None
    if positions and not args.no_lane:
        t0 = time.time()
        seg = [p for p in positions if k_rel + LANE_SEG_START <= p[0] <= k_pin]
        log(f'  [lane] segment {len(seg)} positions k {seg[0][0] if seg else None}..{seg[-1][0] if seg else None}')
        to_pin = [p for p in positions if p[0] <= k_pin]   # the board is read from frames up to pin contact only
        calib, fields, per, bmap = lane_pass(cut, to_pin, seg, k_pin, log)
        meta['lane_s'] = round(time.time() - t0, 1)
        meta['lane_method'] = fields.get('lane_method')
        meta['lane_error'] = fields.get('lane_calibration_error')
        if calib is not None:
            final_board = fields.get('final_board')
            meta['final_board_raw'] = fields.get('final_board_raw')
            meta['last_lane_frame'] = None if fields.get('last_lane_frame') is None else fields['last_lane_frame'] + off
            lane = {str(k + off): quad(c) for k, c in per.items()}
            boards = {str(k + off): round(float(b), 2) for k, b in bmap.items() if b is not None}
    meta['wall_s'] = round(time.time() - t_start, 1)
    tr = {'stem': args.stem, 'method': 'sam2-video', 'frames': [{'f': k + off, 'x': round(pts[k][0], 1), 'y': round(pts[k][1], 1),
                                                                  'r': round(pts[k][2], 1), 'conf': None} for k in sorted(pts)],
          'lane': lane, 'boards': boards, 'final_board': None if final_board is None else float(final_board),
          'release_frame': cut['release_frame'], 'pin_hit_frame': cut['pin_hit_frame'], 'meta': meta}
    json.dump(tr, open(out_path, 'w'), indent=1)
    overlay(frames, cut, tr, os.path.join(X, 'overlays', f'{args.stem}.jpg'))
    log(f'wrote {out_path}: {len(tr["frames"])} frames, final board {final_board}, wall {meta["wall_s"]}s')


if __name__ == '__main__':
    main()
