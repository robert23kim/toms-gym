"""SAM 2.1 video propagation of the ball across a cut, with far-end crop re-prompts.

All frame indices here are CUT-LOCAL (k); run.py adds cut_start.
"""
import os, time
import cv2, numpy as np

SAM_WEIGHTS = '/Users/toka/code/bowling-app/pov-engine/models/sam2.1_t.pt'


def _write_clip(path, frames):
    H, W = frames[0].shape[:2]
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 30, (W, H))
    for f in frames:
        vw.write(f)
    vw.release()


def _mask_stats(md):
    area = int(md.sum())
    if area == 0:
        return None
    ys, xs = np.nonzero(md)
    return float(xs.mean()), float(ys.mean()), float(np.sqrt(area / np.pi)), area


def propagate(frames, k0, box, device='mps', work_dir='.', tag='full', imgsz=1024, log=print, k_end=None):
    """Prompt frame k0 with `box` (x0,y0,x1,y1 in the frames' pixels) and propagate to the end.
    Returns {k: (cx, cy, r, area)} for frames with a mask, raw (no death gating)."""
    from ultralytics.models.sam import SAM2VideoPredictor
    clip = os.path.join(work_dir, f'clip_{tag}_{k0}.mp4')
    k_end = len(frames) - 1 if k_end is None else min(k_end, len(frames) - 1)
    _write_clip(clip, frames[k0:k_end + 1])
    ov = dict(conf=0.25, task='segment', mode='predict', imgsz=imgsz, model=SAM_WEIGHTS, device=device,
              verbose=False, save=False)
    pred = SAM2VideoPredictor(overrides=ov)
    out = {}
    t0 = time.time()
    for i, r in enumerate(pred(source=clip, bboxes=[list(map(int, box))], stream=True)):
        k = k0 + i
        if r.masks is None or len(r.masks.data) == 0:
            continue
        st = _mask_stats(r.masks.data[0].cpu().numpy().astype(np.uint8))
        if st is not None:
            out[k] = st
    log(f'  [sam2] {tag} prompt k={k0} box={list(map(int, box))}: {len(out)}/{k_end + 1 - k0} masks in {time.time() - t0:.1f}s')
    try:
        os.remove(clip)
    except OSError:
        pass
    return out


def gate(raw, k0, log=print, area_jump=2.5, jump_px=40.0, k_end=None):
    """Walk the raw masks from k0; stop at the first death: a missing frame, an area jump > area_jump x
    the running median of the last 3, or a centroid jump > 4 r + jump_px. Returns (good {k: ...}, k_death or None)."""
    good = {}
    prev = None
    k = k0
    kmax = (max(raw) if raw else k0 - 1) if k_end is None else k_end
    while k <= kmax:
        st = raw.get(k)
        if st is None:
            log(f'  [gate] mask missing at k={k}')
            return good, k
        if prev is not None:
            areas = [good[j][3] for j in sorted(good)[-3:]]
            med = float(np.median(areas))
            d = float(np.hypot(st[0] - prev[0], st[1] - prev[1]))
            if st[3] > area_jump * med or d > 4 * prev[2] + jump_px:
                log(f'  [gate] death at k={k}: area {st[3]} vs median {med:.0f}, jump {d:.0f} px (r {prev[2]:.0f})')
                return good, k
        good[k] = st
        prev = st
        k += 1
    return good, None


def crop_window(frames, k_last, good, side):
    """Square crop (x0, y0, side) centred on the position extrapolated 2 frames ahead of the last good one."""
    H, W = frames[0].shape[:2]
    ks = sorted(good)[-4:]
    x, y = good[ks[-1]][0], good[ks[-1]][1]
    if len(ks) >= 2:
        vx = (good[ks[-1]][0] - good[ks[0]][0]) / (ks[-1] - ks[0])
        vy = (good[ks[-1]][1] - good[ks[0]][1]) / (ks[-1] - ks[0])
        x, y = x + 2 * vx, y + 2 * vy
    x0 = int(min(max(0, x - side / 2), W - side))
    y0 = int(min(max(0, y - side / 2), H - side))
    return x0, y0, side


def track(frames, k0, box, *, device='mps', work_dir='.', k_end=None, max_passes=3, crop_side=480, crop_scale=2,
          log=print):
    """Full-frame propagation, then up to max_passes far-end crop re-prompts from the last good frame.
    Returns ({k: (cx, cy, r)}, passes list)."""
    k_end = len(frames) - 1 if k_end is None else k_end
    passes = []
    raw = propagate(frames, k0, box, device=device, work_dir=work_dir, tag='full', log=log, k_end=k_end)
    good, kd = gate(raw, k0, log=log, k_end=k_end)
    passes.append({'tag': 'full', 'k0': k0, 'box': list(map(int, box)), 'good': len(good), 'death': kd})
    result = {k: (v[0], v[1], v[2]) for k, v in good.items()}
    n = 0
    while kd is not None and kd < k_end and n < max_passes and result:
        n += 1
        k_last = max(result)
        if k_last < k0 + 2:
            break
        x0, y0, side = crop_window(frames, k_last, good, crop_side)
        crops = [cv2.resize(f[y0:y0 + side, x0:x0 + side], (side * crop_scale, side * crop_scale),
                            interpolation=cv2.INTER_CUBIC) for f in frames]
        cx, cy, r = result[k_last]
        rr = max(r, 6.0) * 1.3
        cb = [(cx - rr - x0) * crop_scale, (cy - rr - y0) * crop_scale, (cx + rr - x0) * crop_scale, (cy + rr - y0) * crop_scale]
        cb = [max(0, min(side * crop_scale - 1, v)) for v in cb]
        raw_c = propagate(crops, k_last, cb, device=device, work_dir=work_dir, tag=f'crop{n}', log=log, k_end=k_end)
        good_c, kd = gate(raw_c, k_last, log=log, k_end=k_end)
        # back to full-frame pixels; drop points that touch the crop border (the ball left the window)
        added = 0
        for k, (ccx, ccy, cr, ca) in good_c.items():
            fx, fy, fr = x0 + ccx / crop_scale, y0 + ccy / crop_scale, cr / crop_scale
            edge = min(ccx, ccy, side * crop_scale - ccx, side * crop_scale - ccy)
            if edge < 2 * cr + 4:
                kd = k
                break
            if k not in result:
                added += 1
            result[k] = (fx, fy, fr)
            good[k] = (fx, fy, fr, ca / crop_scale ** 2)
        passes.append({'tag': f'crop{n}', 'k0': k_last, 'crop': [x0, y0, side], 'good': len(good_c), 'added': added, 'death': kd})
        log(f'  [sam2] crop pass {n}: window {x0},{y0} side {side}, {added} frames added, death {kd}')
        if added == 0:
            break
    return result, passes


def track_back(frames, k0, box, k_rel, *, device='mps', work_dir='.', log=print):
    """Propagate the same prompt BACKWARDS from k0 to k_rel (frames reversed), so the near-release frames where the
    colour blob fails (ball blurred, dark, half out of frame) still get a mask. Returns {k: (cx, cy, r)}."""
    if k0 - k_rel < 1:
        return {}
    rev = frames[k_rel:k0 + 1][::-1]
    raw = propagate(rev, 0, box, device=device, work_dir=work_dir, tag='back', log=log)
    good, kd = gate(raw, 0, log=log, area_jump=3.5, jump_px=80.0)
    out = {k0 - i: (v[0], v[1], v[2]) for i, v in good.items() if i > 0}
    log(f'  [sam2] backward pass: {len(out)} frames k {min(out) if out else None}..{k0 - 1}, death {kd}')
    return out
