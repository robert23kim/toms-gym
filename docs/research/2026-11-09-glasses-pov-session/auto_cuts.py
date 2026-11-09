#!/usr/bin/env python3
"""Raw Meta-glasses bowling clip -> one cuts.json entry with no hand labels.

usage: auto_cuts.py <source.mp4> [--out-dir DIR] [--no-cut] [--release N]

Rules. v1 (first up-frame dy jerk, frozen on 3 dev stems) scored 3/7 on the September holdout; v2 (purple-ball blip)
was fitted after reading those failures; v3 (this rule) replaces the purple mask with a colour-free one for house balls
of any colour and was frozen on the 11 September clips before any 2026-11-08 clip was run (see auto_cuts_notes.md).
  release  : region = rows 65-100 %, columns 10-90 % of the 1/8-scale frame. Ball mask = pixels darker than
             LUMA_FRAC x the region's median Lab L, or further than CHROMA_DIST from the region's median (a, b): the
             median is the lane, so this is "not lane wood" for a black, blue, red, green or purple ball, and the arm
             (skin is close to wood in chroma and luma) mostly drops out. Fractions per row band: bot = rows 80-100 %,
             mid = rows 65-80 %. The released ball crosses the frame bottom in about one frame:
             blip T[k] = min(max(bot[k-1], bot[k]) - max(bot[k-3], bot[k+1], bot[k+2]), mid[k] - max(mid[k+1], mid[k+2])).
             Candidates: T >= BLIP_MIN and mean(bot + mid) over k+1..k+3 < POST_MAX (the ball has left the bottom 35 %;
             a ball held in front of the face fails this), and k <= last frame - MIN_ROLL (v3.1, added post hoc after the
             2026-11-08 batch: 5/25 throws picked a walk-back blob 7-27 frames from the clip end; September's smallest
             release-to-end margin is 110). release = the EARLIEST candidate (post-pin camera whips
             make later blips; a held ball before release fails the post gate).
             No candidate -> no cut (cut_path null, reason); the first dy-jerk run (v1) is attached as an advisory
             field jerk_release_candidate and is never used to cut.
  thud     : a low-band (40-300 Hz) onset within release+1..+10 is recorded as a confidence tag only.
  pin hit  : strongest mid-band (300-2000 Hz) onset (rise > ONSET_DB over the median of the previous 2-12 frames)
             within release+50..+130, minus CRASH_LAG; none -> release + TRAVEL. Rough by design.
  cut      : cut_start = release - 10, cut_end = max(pin_hit + 20, release + MIN_TAIL), clamped, inclusive.
             MIN_TAIL is a floor so a slow ball or a wrong crash onset never ends the cut before the pin row.
Frame numbers are SOURCE frames at the true rate (nb_frames / duration, ~30 fps; ffprobe r_frame_rate says 120).
Frames are always decoded sequentially (cv2 seeks one frame late on some clips).
"""
import argparse, json, os, subprocess, sys, time
import numpy as np, cv2

FF = '/opt/homebrew/bin/'
JERK_DY = -12.0
REL_OFFSET = 1
BLIP_MIN = 0.04
POST_MAX = 0.04
LUMA_FRAC = 0.6
CHROMA_DIST = 30.0
THUD_WIN = (1, 10)
ONSET_DB = 9.0
CRASH_WIN = (50, 130)
CRASH_LAG = 17
TRAVEL = 60
MIN_TAIL = 95
PRE = 10
POST = 20
MIN_SECONDS = 4.0
MIN_ROLL = 45
SCALE = 8
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work', 'auto_cuts')


def probe(src):
    pts = subprocess.run([FF + 'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time',
                          '-of', 'csv=p=0', src], capture_output=True, text=True, check=True).stdout.split()
    pts = np.sort(np.array([float(x) for x in pts if x not in ('', 'N/A')]))
    dur = float(subprocess.run([FF + 'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src],
                               capture_output=True, text=True, check=True).stdout.strip())
    return pts, dur


def frame_shifts(src):
    cap = cv2.VideoCapture(src)
    prev, win, dys, bands = None, None, [], []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        sm = cv2.resize(fr, (fr.shape[1] // SCALE, fr.shape[0] // SCALE), interpolation=cv2.INTER_AREA)
        H, W = sm.shape[:2]
        lab = cv2.cvtColor(sm[int(H * 0.65):, int(W * 0.1):int(W * 0.9)], cv2.COLOR_BGR2LAB).astype(np.float32)
        med = np.median(lab.reshape(-1, 3), axis=0)
        bm = (lab[..., 0] < LUMA_FRAC * med[0]) | (np.sqrt(((lab[..., 1:] - med[1:]) ** 2).sum(-1)) > CHROMA_DIST)
        cut = int(round(bm.shape[0] * 0.15 / 0.35))
        bands.append([bm[:cut].mean(), bm[cut:].mean()])
        g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is None:
            win = cv2.createHanningWindow((g.shape[1], g.shape[0]), cv2.CV_32F)
            dys.append(0.0)
        else:
            (_, dy), _ = cv2.phaseCorrelate(prev, g, win)
            dys.append(float(dy))
        prev = g
    cap.release()
    return np.array(dys), np.array(bands)


def audio_rises(src, pts, n):
    raw = subprocess.run([FF + 'ffmpeg', '-v', 'error', '-i', src, '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    out = {}
    if len(a) < 4096:
        return {k: np.zeros(n) for k in ('low', 'mid')}
    sr, hop, w = 48000, 400, 1024
    nf = (len(a) - w) // hop
    fr = np.lib.stride_tricks.as_strided(a, (nf, w), (a.strides[0] * hop, a.strides[0])) * np.hanning(w)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(w, 1 / sr)
    fi = np.interp((np.arange(nf) * hop + w / 2) / sr, pts, np.arange(len(pts)))
    for name, (lo, hi) in {'low': (40, 300), 'mid': (300, 2000)}.items():
        e = 10 * np.log10(S[:, (f >= lo) & (f < hi)].sum(1) + 1e-9)
        per = np.full(n, np.nan)
        for i in range(n):
            m = (fi >= i - 0.5) & (fi < i + 0.5)
            if m.any():
                per[i] = e[m].max()
        base = np.array([np.nanmedian(per[max(0, i - 12):max(1, i - 2)]) for i in range(n)])
        out[name] = np.nan_to_num(per - base, nan=0.0)
    return out


def onsets(rise, lo, hi):
    lo, hi = max(1, lo), min(len(rise) - 1, hi)
    return [i for i in range(lo, hi + 1) if rise[i] > ONSET_DB and rise[i] >= rise[max(0, i - 3):i + 4].max()]


def blip_scores(mid, bot):
    n = len(bot)
    g = lambda a, i: float(a[i]) if 0 <= i < n else 0.0
    T, post = np.full(n, -1.0), np.ones(n)
    for k in range(3, n - 3):
        T[k] = min(max(g(bot, k - 1), g(bot, k)) - max(g(bot, k - 3), g(bot, k + 1), g(bot, k + 2)),
                   g(mid, k) - max(g(mid, k + 1), g(mid, k + 2)))
        post[k] = float((mid[k + 1:k + 4] + bot[k + 1:k + 4]).mean())
    return T, post


def jerk_candidate(dy):
    runs, i, n = [], 0, len(dy)
    while i < n:
        if dy[i] < JERK_DY:
            j = i
            while j + 1 < n and dy[j + 1] < JERK_DY:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    if not runs:
        return None, []
    a, b = runs[0]
    k = a + int(np.argmin(dy[a:b + 1]))
    return k - REL_OFFSET, [[int(x), int(y), round(float(dy[x:y + 1].min()), 1)] for x, y in runs]


def detect(dy, pur, rises, n):
    """Pure rule on per-frame signals -> dict (release_frame None = no throw / not found)."""
    T, post = blip_scores(pur[:, 0], pur[:, 1])
    cand = [k for k in range(n) if T[k] >= BLIP_MIN and post[k] < POST_MAX and n - 1 - k >= MIN_ROLL]
    jrel, runs = jerk_candidate(dy)
    top = [[int(k), round(float(T[k]), 3), round(float(post[k]), 3)] for k in np.argsort(-T)[:3]]
    diag = {'blip_top3': top, 'blip_candidates': len(cand), 'jerk_release_candidate': None if jrel is None else int(jrel),
            'jerk_runs': runs}
    if not cand:
        return dict(diag, release_frame=None,
                    reason=f'no release found: no bottom-of-frame ball blip with T >= {BLIP_MIN} and the ball gone '
                           f'from the bottom 35 % within 3 frames (post < {POST_MAX}) at least {MIN_ROLL} frames before the clip end; a clip with no throw, a ball the '
                           f'colour and brightness of the lane, or a release out of frame all land here')
    k = cand[0]
    det = from_release(k, rises, diag)
    det.update(blip_T=round(float(T[k]), 3), blip_post=round(float(post[k]), 3))
    det['release_source'] = ('blip+thud' if det['thud_frame'] is not None else 'blip, no thud') + \
        f' (earliest bottom-of-frame ball blip at f{k}, {len(cand)} candidates)'
    return det


def from_release(rel, rises, diag):
    thud = onsets(rises['low'], rel + THUD_WIN[0], rel + THUD_WIN[1])
    crash = onsets(rises['mid'], rel + CRASH_WIN[0], rel + CRASH_WIN[1])
    if crash:
        c = max(crash, key=lambda x: rises['mid'][x])
        pin, psrc = c - CRASH_LAG, f'audio mid-band crash onset f{c} - {CRASH_LAG}'
    else:
        c, pin, psrc = None, rel + TRAVEL, f'release + {TRAVEL} (no mid-band onset in release+{CRASH_WIN[0]}..+{CRASH_WIN[1]})'
    return dict(diag, release_frame=int(rel), blip_T=None, blip_post=None, release_source='eye',
                thud_frame=int(thud[0]) if thud else None, crash_frame=None if c is None else int(c),
                pin_hit_frame=int(pin), pin_hit_source=psrc)


def cut_and_verify(src, pts, cut_start, cut_end, out_path):
    nexp = cut_end - cut_start + 1
    step = float(np.median(np.diff(pts)))
    t = max(0.0, pts[cut_start] - 0.5 * step)
    subprocess.run([FF + 'ffmpeg', '-y', '-v', 'error', '-i', src, '-ss', f'{t:.6f}', '-frames:v', str(nexp),
                    '-t', f'{(nexp + 1) * step:.6f}', '-fps_mode', 'passthrough', '-c:v', 'libx264', '-crf', '18',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', out_path], check=True)
    cap = cv2.VideoCapture(out_path)
    cut_frames = 0
    ok, f0 = cap.read()
    if not ok:
        f0 = None
    while ok:
        cut_frames += 1
        ok, _ = cap.read()
    cap.release()
    cap = cv2.VideoCapture(src)
    mad, i = {}, 0
    while i <= cut_start + 2:
        ok, fr = cap.read()
        if not ok:
            break
        if i >= cut_start - 2 and f0 is not None:
            mad[str(i - cut_start)] = round(float(np.abs(fr.astype(np.float32) - f0.astype(np.float32)).mean()), 2)
        i += 1
    cap.release()
    best = min(mad, key=mad.get) if mad else None
    return cut_frames, nexp, mad, best


def run(src, out_dir=DEFAULT_OUT, write_cut=True, release=None):
    stem = os.path.splitext(os.path.basename(src))[0]
    pts, dur = probe(src)
    n = len(pts)
    entry = {'stem': stem, 'source': os.path.abspath(src), 'nb_frames_source': n, 'duration_s': round(dur, 3),
             'fps_true': round(n / dur, 3) if dur else None, 'release_frame': None, 'release_source': None,
             'pin_hit_frame': None, 'cut_start': None, 'cut_end': None, 'cut_path': None, 'nb_frames': None,
             'verified': False, 'frame0_mad_by_offset': None, 'notes': ''}
    if dur < MIN_SECONDS:
        entry['notes'] = f'too short: {dur:.2f} s < {MIN_SECONDS} s'
        return entry
    diag = ('blip_top3', 'blip_candidates', 'jerk_release_candidate', 'jerk_runs')
    if release is None:
        dy, pur = frame_shifts(src)
        n = min(n, len(dy))
        rises = audio_rises(src, pts, n)
        det = detect(dy[:n], pur[:n], {k: v[:n] for k, v in rises.items()}, n)
    else:
        cap, nd = cv2.VideoCapture(src), 0
        while cap.grab():
            nd += 1
        cap.release()
        n = min(n, nd)
        rises = audio_rises(src, pts, n)
        det = from_release(int(release), rises, {k: None for k in diag})
    entry.update({k: det[k] for k in diag})
    if det['release_frame'] is None:
        entry['notes'] = det['reason']
        return entry
    rel, pin = det['release_frame'], det['pin_hit_frame']
    cs = max(0, rel - PRE)
    ce = min(n - 1, max(pin + POST, rel + MIN_TAIL))
    entry.update({k: det[k] for k in ('release_frame', 'release_source', 'pin_hit_frame', 'pin_hit_source', 'blip_T',
                                      'blip_post', 'thud_frame', 'crash_frame')})
    entry.update({'cut_start': cs, 'cut_end': ce, 'expected_frames': ce - cs + 1,
                  'cut_end_rule': f'max(pin_hit + {POST}, release + {MIN_TAIL}), clamped to the clip',
                  'cut_method': 'ffmpeg -i src -ss <pts[cut_start] - half a frame> -frames:v N (output seek), '
                                'libx264 crf 18 yuv420p, fps_mode passthrough'})
    notes = []
    if ce < pin + POST or ce < rel + MIN_TAIL:
        notes.append(f'cut_end clamped to the clip end f{n - 1}')
    if det['jerk_release_candidate'] is not None and abs(det['jerk_release_candidate'] - rel) > 3:
        notes.append(f"advisory dy-jerk candidate f{det['jerk_release_candidate']} disagrees with the blip")
    if rel + 45 > n - 1:
        notes.append('release is within 45 frames of the clip end; the roll may be cut off')
    if write_cut:
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, stem + '.mp4')
        if os.path.abspath(out) == os.path.abspath(src):
            out = os.path.join(out_dir, stem + '_cut.mp4')
        got, nexp, mad, best = cut_and_verify(src, pts, cs, ce, out)
        entry.update({'cut_path': out, 'nb_frames': got, 'frame0_mad_by_offset': mad,
                      'verified': bool(got == nexp and best == '0' and mad.get('0', 99) < 3.0)})
        if not entry['verified']:
            notes.append(f'cut check failed: frames {got}/{nexp}, best offset {best}')
    entry['notes'] = '; '.join(notes)
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--out-dir', default=DEFAULT_OUT)
    ap.add_argument('--no-cut', action='store_true', help='detect only, write no cut')
    ap.add_argument('--release', type=int, default=None,
                    help='skip detection and cut from this release frame (release_source "eye")')
    a = ap.parse_args()
    t0 = time.time()
    e = run(a.source, a.out_dir, not a.no_cut, a.release)
    e['runtime_s'] = round(time.time() - t0, 1)
    print(json.dumps(e, indent=1))


if __name__ == '__main__':
    main()
