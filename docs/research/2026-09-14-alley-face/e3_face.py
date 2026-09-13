"""E3: finding the face. From E2's candidate pool alone (no ball path, no student, no prompt):
regularly spaced chains of dark marks are read as arrow rows / dot rows (each chain tried as each
class and each contiguous board assignment), white rack blobs give the pin-7 / pin-10 bases, and a
homography is fitted per (chain, rack) pairing with the rule-book constellation as the model. Every
hypothesis is scored by the constellation points it explains (marks within 1.5 lane inches of the
projected arrows / dots, a rack blob at the projected rack, LSD segments along the projected gutters
and foul line). Hypotheses are clustered into lanes by their foul-line centre; the best per lane is
kept. Annotated videos: is the RIGHT lane among them (vs a neighbour), board MAE of that lane against
both truths, and whether the top score / the bowler's feet / the frame centre pick it. Feature-set
ablations: arrows | arrows+dots | arrows+dots+rack | +gutters (scoring).
Writes results/e3_face_<stem>.json (+ per-frame lanes in $AF_SCRATCH/pred/face_<stem>.json.gz),
overlays/e3_face_<stem>_f<f>.jpg. usage: e3_face.py [--sets a,b] [stems...]"""
import argparse
import gzip
import itertools
import json
import time

import cv2
import numpy as np

import af

LM = af.LM
CONST = af.constellation()
CLASS_PTS = {}
for _n, _p in CONST.items():
    CLASS_PTS.setdefault(af.classes_of(_n), []).append((_n, _p))
for _c in CLASS_PTS:
    CLASS_PTS[_c].sort(key=lambda t: t[1][0])   # image left -> right = lane x increasing (x is inches from the LEFT edge, board 39 side)
ROW_CLASSES = ("arrow", "dot", "fdot", "adot")
SETS = {"arrows": {"rows": ("arrow",), "rack": False, "gutters": False},
        "arrows+dots": {"rows": ("arrow", "dot", "fdot", "adot"), "rack": False, "gutters": False},
        "arrows+dots+rack": {"rows": ("arrow", "dot", "fdot", "adot"), "rack": True, "gutters": False},
        "arrows+dots+rack+gutters": {"rows": ("arrow", "dot", "fdot", "adot"), "rack": True, "gutters": True},
        "arrows+rack": {"rows": ("arrow",), "rack": True, "gutters": True}}


# ---------------------------------------------------------------- chains of regularly spaced marks

def chains(marks, dx_rng=(5.0, 95.0), min_len=5, max_len=11, ratio=(0.5, 2.0), dy_frac=0.28):
    """Maximal chains of marks left->right with near-constant spacing and direction. Greedy from
    every ordered pair (i, j): the next mark is the one nearest to the extrapolated position within
    tolerance. Returns lists of mark indices (deduplicated, subsets removed)."""
    if len(marks) < min_len:
        return []
    xs = np.array([m["x"] for m in marks]); ys = np.array([m["y"] for m in marks])
    order = np.argsort(xs); xs_o = xs[order]
    out = set()
    n = len(marks)
    for a_ in range(n):
        i = order[a_]
        # partners to the right within dx range
        b0 = np.searchsorted(xs_o, xs[i] + dx_rng[0]); b1 = np.searchsorted(xs_o, xs[i] + dx_rng[1], side="right")
        for b_ in range(b0, b1):
            j = order[b_]
            dx = xs[j] - xs[i]; dy = ys[j] - ys[i]
            if abs(dy) > max(3.0, dy_frac * dx):
                continue
            chain = [i, j]
            while len(chain) < max_len:
                p, q = chain[-2], chain[-1]
                gx = xs[q] - xs[p]
                # x extrapolated by the last gap; y held within a band of the last mark (the arrows form a V,
                # so the direction is allowed to turn at the apex)
                ex, ey = xs[q] + gx, ys[q]
                c0 = np.searchsorted(xs_o, xs[q] + ratio[0] * gx); c1 = np.searchsorted(xs_o, xs[q] + ratio[1] * gx, side="right")
                best = None
                for c_ in range(c0, c1):
                    k = order[c_]
                    if k in chain:
                        continue
                    d = np.hypot(xs[k] - ex, ys[k] - ey)
                    tol = max(4.0, 0.5 * gx)
                    if abs(ys[k] - ey) <= max(3.0, dy_frac * gx) and d <= tol and (best is None or d < best[0]):
                        best = (d, k)
                if best is None:
                    break
                chain.append(best[1])
            if len(chain) >= min_len:
                out.add(tuple(chain))
    # remove chains contained in longer ones
    res = sorted(out, key=len, reverse=True)
    keep = []
    for c in res:
        sc = set(c)
        if any(sc <= set(k) for k in keep):
            continue
        keep.append(c)
    return keep


def assignments(chain_len, class_pts):
    """Contiguous placements of a chain of chain_len marks onto the class's points (left->right)."""
    m = len(class_pts)
    if chain_len > m:
        return []
    return [list(range(o, o + chain_len)) for o in range(0, m - chain_len + 1)]


# ---------------------------------------------------------------- hypotheses

def fit_h(points, weights=None):
    return LM.fit_homography(points, (), weights, None)


def lane_sane(H, img_shape):
    """Projected lane must be a forward-facing trapezoid of plausible size inside the frame."""
    h, w = img_shape[:2]
    if H is None or not np.all(np.isfinite(H)) or abs(np.linalg.det(H)) < 1e-12 or np.linalg.cond(H) > 1e12:
        return False
    try:
        p = af.to_image(H, [(0, 0), (af.W_IN, 0), (0, LM.HEAD_IN), (af.W_IN, LM.HEAD_IN), (af.W_IN / 2, 0), (af.W_IN / 2, LM.HEAD_IN)])
    except np.linalg.LinAlgError:
        return False
    if not np.all(np.isfinite(p)):
        return False
    near_w = p[1][0] - p[0][0]; far_w = p[3][0] - p[2][0]
    # camera-placement priors (a phone behind the foul line, roughly at chest height): the near end is
    # wider than the far end by 2-20x, the pin deck sits at least 0.6 near-widths above the foul line,
    # the foul line is inside or just below the frame, the lane is not wider than the frame
    if not (near_w > 25 and 4 < far_w and 2.0 <= near_w / far_w <= 20.0 and near_w <= 1.2 * w):
        return False
    if not (p[4][1] - p[5][1] >= 0.6 * near_w):
        return False
    if not (-0.5 * w <= p[4][0] <= 1.5 * w and 0.1 * h <= p[4][1] <= 1.3 * h and 0 <= p[5][0] <= w and 0 <= p[5][1] <= h):
        return False
    # the arrows (15 ft) must be in the frame: a lane view from the approach always shows them
    a = af.to_image(H, [(af.W_IN / 2, CONST["arrow_20"][1]), (CONST["arrow_35"][0], CONST["arrow_35"][1]), (CONST["arrow_5"][0], CONST["arrow_5"][1])])
    if not np.all((a[:, 0] >= 0) & (a[:, 0] < w) & (a[:, 1] >= 0) & (a[:, 1] < h)):
        return False
    return True


def local_ppi(H, x_in, y_in):
    p = af.to_image(H, [(x_in, y_in), (x_in + 1.0, y_in)])
    return float(np.hypot(*(p[1] - p[0])))


def score_h(H, pool, img_shape, use_gutters=True, tol_in=0.6, tol_px=(3.0, 8.0)):
    """Constellation points explained by H, chance-corrected: each projected arrow / dot in the frame
    scores 1 (0.5 for a weak mark) when a dark mark lies within tol = clip(tol_in * local px/in,
    3, 8) px, minus the expected number of chance matches at that tolerance (mark density x pi tol^2).
    A rack blob at the projected rack scores 3; each LSD segment along a projected gutter 0.5 (up to
    3 per side), along the foul line 0.5 (up to 2). Returns (score, detail)."""
    marks = pool["marks"]; racks = pool["racks"]; segs = pool["segs"]
    mx = pool["_mx"]; my = pool["_my"]; mw = pool["_mw"]
    det = {"arrow": 0, "dot": 0, "fdot": 0, "adot": 0, "rack": 0, "gutter": 0, "foul_line": 0, "chance": 0.0}
    score = 0.0
    names = list(CONST); pts_in = np.array([CONST[n] for n in names], np.float32)
    proj = af.to_image(H, pts_in)
    used = set()
    dens = len(marks) / float(img_shape[0] * img_shape[1])
    for n, (x, y), (x_in, y_in) in zip(names, proj, pts_in):
        cls = af.classes_of(n)
        if cls not in ROW_CLASSES or len(mx) == 0:
            continue
        if not (0 <= x < img_shape[1] and 0 <= y < img_shape[0]):
            continue
        tol = float(np.clip(tol_in * local_ppi(H, x_in, y_in), tol_px[0], tol_px[1]))
        chance = dens * np.pi * tol * tol
        det["chance"] += chance; score -= chance
        d = np.hypot(mx - x, my - y)
        k = int(np.argmin(d))
        if d[k] <= tol and k not in used:
            used.add(k); w = 0.5 if mw[k] else 1.0
            det[cls] += w; score += w
    # rack: the projected rack centre (between pins 7 and 10 at the base row) and width
    r7 = af.to_image(H, [CONST["pin_7_base"], CONST["pin_10_base"], (af.W_IN / 2, LM.HEAD_IN)])
    rc = 0.5 * (r7[0] + r7[1]); ppi = local_ppi(H, af.W_IN / 2, LM.HEAD_IN)
    for r in racks:
        if abs(r["cx"] - rc[0]) <= 3.0 * ppi and abs(r["base_y"] - rc[1]) <= 5.0 * ppi and 0.7 <= r["w"] / (40.8 * ppi) <= 1.35:
            det["rack"] = 3; score += 3; break
    if use_gutters and segs:
        # sampled segment points in lane coordinates
        S = pool["_seg_pts"]   # (n_segs, 5, 2)
        lane = cv2.perspectiveTransform(S.reshape(-1, 1, 2), H).reshape(S.shape[0], S.shape[1], 2)
        for x0 in (0.0, af.W_IN):
            ok = np.all(np.abs(lane[:, :, 0] - x0) <= tol_in, axis=1) & np.all((lane[:, :, 1] > -40) & (lane[:, :, 1] < 780), axis=1)
            k = min(3, int(ok.sum())); det["gutter"] += k; score += 0.5 * k
        ok = np.all(np.abs(lane[:, :, 1]) <= tol_in, axis=1) & np.all((lane[:, :, 0] > -6) & (lane[:, :, 0] < af.W_IN + 6), axis=1)
        k = min(2, int(ok.sum())); det["foul_line"] += k; score += 0.5 * k
    return score, det


def prep_pool(c):
    pool = dict(c)
    pool["_mx"] = np.array([m["x"] for m in c["marks"]], np.float32); pool["_my"] = np.array([m["y"] for m in c["marks"]], np.float32)
    pool["_mw"] = np.array([m.get("weak", 0) for m in c["marks"]], bool)
    S = []
    for s in c["segs"]:
        S.append([(s["x1"] + t * (s["x2"] - s["x1"]), s["y1"] + t * (s["y2"] - s["y1"])) for t in np.linspace(0, 1, 5)])
    pool["_seg_pts"] = np.array(S, np.float32) if S else np.zeros((0, 5, 2), np.float32)
    return pool


def hypotheses(pool, img_shape, cfg, max_chains=600, max_racks=12):
    """All (chain-as-class-with-assignment [+ rack]) homographies for one feature set."""
    marks = pool["marks"]
    sub = marks
    ch = chains(sub)
    # rank chains by spacing regularity (std / mean of the gaps), strong marks first, then length:
    # on a 1080p six-lane frame the ceiling yields hundreds of long loose chains that would crowd out
    # the seven-arrow rows if length ranked first
    def key(c):
        g = np.diff([sub[i]["x"] for i in c]); reg = float(np.std(g) / (np.mean(g) + 1e-6))
        weak = float(np.mean([sub[i].get("weak", 0) for i in c]))
        return (reg + 0.5 * weak - 0.02 * min(len(c), 7),)
    ch = sorted(ch, key=key)[:max_chains]
    racks = pool["racks"] if cfg["rack"] else []
    hyps = []
    # single-row (+ rack) hypotheses
    for c in ch:
        pts_img = [(sub[i]["x"], sub[i]["y"]) for i in c]
        cy = float(np.mean([p[1] for p in pts_img])); cx = float(np.mean([p[0] for p in pts_img])); span = pts_img[-1][0] - pts_img[0][0]
        for cls in cfg["rows"]:
            cp = CLASS_PTS[cls]
            for asg in assignments(len(c), cp):
                corr = [(pts_img[k], cp[a][1]) for k, a in enumerate(asg)]
                cand_racks = [None] if not cfg["rack"] else []
                if cfg["rack"]:
                    # px/in at this row from its spacing (arrows 5 boards, guide dots 3, foul / approach dots 5)
                    pitch_in = {"arrow": 5 * af.BOARD_IN, "dot": 3 * af.BOARD_IN, "fdot": 5 * af.BOARD_IN, "adot": 5 * af.BOARD_IN}[cls]
                    ppi_row = (span / max(1, len(c) - 1)) / pitch_in
                    for r in racks:
                        if r["base_y"] < cy - 0.3 * span and abs(r["cx"] - cx) <= 1.5 * span + 40 and 0.12 * ppi_row <= r["ppi"] <= 0.9 * ppi_row:
                            cand_racks.append(r)
                    cand_racks = sorted(cand_racks, key=lambda r: abs(r["cx"] - cx))[:max_racks] or [None]
                for r in cand_racks:
                    pts = list(corr); w = [1.0] * len(corr)
                    if r is not None:
                        ppi = r["ppi"]
                        pts += [((r["cx"] - 18.0 * ppi, r["base_y"]), CONST["pin_7_base"]), ((r["cx"] + 18.0 * ppi, r["base_y"]), CONST["pin_10_base"])]
                        w += [1.5, 1.5]
                    if len(pts) < 4:
                        continue
                    H = fit_h(pts, w)
                    if H is None or not np.all(np.isfinite(H)) or not lane_sane(H, img_shape):
                        continue
                    hyps.append({"H": H, "chain": list(c), "cls": cls, "asg": asg, "rack": r, "n_pts": len(pts)})
    # two-row hypotheses (no rack): arrows + a dot row
    if len(cfg["rows"]) > 1:
        rows_by_cls = {}
        for c in ch:
            pts_img = [(sub[i]["x"], sub[i]["y"]) for i in c]
            for cls in cfg["rows"]:
                for asg in assignments(len(c), CLASS_PTS[cls]):
                    rows_by_cls.setdefault(cls, []).append((c, asg, pts_img))
        for (ca, aa, pa) in rows_by_cls.get("arrow", [])[:40]:
            ya = np.mean([p[1] for p in pa]); xa = np.mean([p[0] for p in pa])
            for cls in ("dot", "fdot", "adot"):
                for (cb, ab, pb) in rows_by_cls.get(cls, [])[:40]:
                    if set(ca) & set(cb):
                        continue
                    yb = np.mean([p[1] for p in pb]); xb = np.mean([p[0] for p in pb])
                    if not (yb > ya + 5 and abs(xb - xa) < 3.0 * (pa[-1][0] - pa[0][0]) + 60):
                        continue
                    pts = [(pa[k], CLASS_PTS["arrow"][a][1]) for k, a in enumerate(aa)] + [(pb[k], CLASS_PTS[cls][a][1]) for k, a in enumerate(ab)]
                    H = fit_h(pts)
                    if H is None or not np.all(np.isfinite(H)) or not lane_sane(H, img_shape):
                        continue
                    hyps.append({"H": H, "chain": list(ca) + list(cb), "cls": f"arrow+{cls}", "asg": aa + ab, "rack": None, "n_pts": len(pts)})
    return hyps, ch


def lanes_from(hyps, pool, img_shape, use_gutters):
    """Score every hypothesis, cluster by foul-line centre, keep the best per lane."""
    scored = []
    for h in hyps:
        s, det = score_h(h["H"], pool, img_shape, use_gutters=use_gutters)
        if det["arrow"] < 3:      # a face needs its eyes: no hypothesis without at least three arrows explained
            continue
        p = af.to_image(h["H"], [(af.W_IN / 2, 0), (0, 0), (af.W_IN, 0), (af.W_IN / 2, LM.HEAD_IN), (0, LM.HEAD_IN), (af.W_IN, LM.HEAD_IN)])
        h.update({"score": s, "det": det, "foul_c": (float(p[0][0]), float(p[0][1])), "near_w": float(p[2][0] - p[1][0]), "far_c": (float(p[3][0]), float(p[3][1])), "far_w": float(p[5][0] - p[4][0])})
        scored.append(h)
    scored.sort(key=lambda h: -h["score"])
    lanes = []
    for h in scored:
        dup = False
        for l in lanes:
            nw = max(h["near_w"], l["near_w"]); fw = max(h["far_w"], l["far_w"])
            if abs(h["foul_c"][0] - l["foul_c"][0]) < 0.5 * nw and abs(h["foul_c"][1] - l["foul_c"][1]) < 0.5 * nw and abs(h["far_c"][0] - l["far_c"][0]) < 2.0 * fw and abs(h["far_c"][1] - l["far_c"][1]) < 2.0 * fw:
                dup = True; break
        if not dup:
            lanes.append(h)
    return lanes


# ---------------------------------------------------------------- per video

def truth_geom(stem, f):
    H = af.truth_h(stem, f, "all")
    p = af.to_image(H, [(af.W_IN / 2, 0), (0, 0), (af.W_IN, 0), (af.W_IN / 2, LM.HEAD_IN), (0, LM.HEAD_IN), (af.W_IN, LM.HEAD_IN)])
    return {"foul_c": p[0], "near_w": float(p[2][0] - p[1][0]), "far_c": p[3], "far_w": float(p[5][0] - p[4][0])}


def is_right_lane(l, tg):
    """The hypothesis is the truth's lane (not a neighbour): far-end centre within one far width of the
    truth's, foul-line centre within half a near width. E3 is a coarse find - arrows at one depth plus a
    rack blob leave the near end loosely constrained (the alignment step E4 fixes it) - so the near test
    is deliberately loose; the board MAE columns carry the accuracy."""
    return abs(l["foul_c"][0] - tg["foul_c"][0]) <= 0.5 * tg["near_w"] and abs(l["foul_c"][1] - tg["foul_c"][1]) <= 0.5 * tg["near_w"] and abs(l["far_c"][0] - tg["far_c"][0]) <= 1.0 * tg["far_w"] and abs(l["far_c"][1] - tg["far_c"][1]) <= 1.0 * tg["far_w"]


def person_feet(img):
    m = af.person_mask(img)
    ys, xs = np.where(m)
    if len(ys) < 50:
        return None
    yb = np.percentile(ys, 99); sel = ys >= yb - 5
    return (float(np.median(xs[sel])), float(yb))


def run(stem, sets, frames=None, overlay_frames=(), step=1, tag="", cand_path=None):
    tg_ = (tag + "__") if tag else ""
    annotated = stem in af.STEMS
    with gzip.open(cand_path or (af.PRED / f"cand_{stem}.json.gz"), "rt") as fh:
        cands = json.load(fh)
    fids = sorted(int(k) for k in cands)
    if frames is not None:
        fids = [f for f in fids if f in set(frames)]
    fids = fids[::step]
    ball_pts = None
    if stem == "bowling_video":
        t = af.load(af.LOOP3 / "results" / "teacher__bowling_video.json"); ball_pts = t["ball_path"]
    per = {s: [] for s in sets}
    face_out = {}
    for f in fids:
        img = af.read_frame(stem, f); shape = img.shape
        pool = prep_pool(cands[str(f)])
        tg = truth_geom(stem, f) if annotated else None
        feet = person_feet(img) if annotated else None
        face_out[str(f)] = {}
        for sname in sets:
            cfg = SETS[sname]
            t0 = time.perf_counter()
            hyps, ch = hypotheses(pool, shape, cfg)
            lanes = lanes_from(hyps, pool, shape, cfg["gutters"])
            dt = time.perf_counter() - t0
            row = {"frame": f, "n_chains": len(ch), "n_hyps": len(hyps), "n_lanes": len(lanes), "ms": round(1000 * dt, 0),
                   "lanes": [{"score": l["score"], "det": l["det"], "cls": l["cls"], "foul_c": [round(v, 1) for v in l["foul_c"]], "near_w": round(l["near_w"], 1), "far_c": [round(v, 1) for v in l["far_c"]], "rack": l["rack"] is not None} for l in lanes[:8]]}
            if annotated:
                right = [i for i, l in enumerate(lanes) if is_right_lane(l, tg)]
                row["right_found"] = bool(right); row["right_rank"] = (right[0] + 1) if right else None
                row["top_is_right"] = bool(right and right[0] == 0)
                # alternative selectors
                if lanes:
                    if feet:
                        k = int(np.argmin([np.hypot(l["foul_c"][0] - feet[0], l["foul_c"][1] - feet[1]) for l in lanes])); row["feet_pick_right"] = bool(k in right)
                    k = int(np.argmin([abs(l["foul_c"][0] - shape[1] / 2) for l in lanes])); row["centre_pick_right"] = bool(k in right)
                    k = int(np.argmax([l["near_w"] for l in lanes])); row["widest_pick_right"] = bool(k in right)
                if right:
                    l = lanes[right[0]]
                    y_top, y_bot = af.L.gt_y(stem, f)
                    corners = LM.corners_from_h(l["H"], y_top, y_bot)
                    sb = af.score_both(stem, f, corners)
                    row["mae"] = {t: sb[t]["board_mae"] for t in af.TRUTHS}; row["tail"] = {t: sb[t]["board_mae_last20"] for t in af.TRUTHS}
                    row["width_err_px_pins"] = sb["pins"]["top_width_err_px"]; row["centre_err_px_pins"] = sb["pins"]["top_centre_err_px"]
                    row["corners"] = {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in corners.items()}
                    row["H"] = [[float(v) for v in r] for r in l["H"]]
                    row["right_det"] = l["det"]; row["right_score"] = l["score"]; row["right_cls"] = l["cls"]
            else:
                if ball_pts is not None and lanes:
                    # which found lane holds the ball path (points inside the lane polygon 0..60 ft)
                    inside = []
                    for l in lanes:
                        lane = af.to_lane(l["H"], ball_pts)
                        inside.append(int(np.sum((lane[:, 0] > -2) & (lane[:, 0] < af.W_IN + 2) & (lane[:, 1] > -10) & (lane[:, 1] < 760))))
                    k = int(np.argmax(inside)); row["ball_lane_rank"] = (k + 1) if inside[k] >= 0.5 * len(ball_pts) else None
                    row["ball_lane_score"] = lanes[k]["score"] if inside[k] >= 0.5 * len(ball_pts) else None
                if lanes:
                    row["H_top"] = [[float(v) for v in r] for r in lanes[0]["H"]]
            face_out[str(f)][sname] = {"lanes": [{"H": [[float(v) for v in r] for r in l["H"]], "score": l["score"], "det": l["det"], "cls": l["cls"]} for l in lanes[:8]]}
            per[sname].append(row)
        if f in overlay_frames:
            sname = sets[-1]; lanes = None
            ov = img.copy()
            fo = face_out[str(f)][sname]["lanes"]
            for i, l in enumerate(fo[:6]):
                H = np.array(l["H"]); col = (0, 255, 255) if i == 0 else (255, 160, 0)
                q = af.to_image(H, [(0, 0), (af.W_IN, 0), (af.W_IN, LM.HEAD_IN), (0, LM.HEAD_IN)]).astype(np.int32)
                cv2.polylines(ov, [q.reshape(-1, 1, 2)], True, col, 2 if i == 0 else 1, cv2.LINE_AA)
                for n, p in CONST.items():
                    x, y = af.to_image(H, [p])[0]
                    if 0 <= x < shape[1] and 0 <= y < shape[0]:
                        cv2.circle(ov, (int(x), int(y)), 3, col, 1, cv2.LINE_AA)
                cv2.putText(ov, f"#{i + 1} score {l['score']:.1f} {l['cls']}", (int(q[0][0]), int(q[0][1]) + 18 + 16 * 0), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)
            if annotated:
                t = af.truth_corners(stem, f, "all"); q = np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32)
                cv2.polylines(ov, [q.reshape(-1, 1, 2)], True, (0, 220, 0), 1, cv2.LINE_AA)
            cv2.putText(ov, f"E3 {af.SHORT[stem]} f{f} [{sname}]: lanes found from the candidate pool (yellow = top score, orange = others, green = truth)", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imwrite(str(af.OVERLAYS / f"e3_face_{stem}_f{f}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if f == fids[0] or f % 25 == 0:
            r = per[sets[-1]][-1]
            print(f"  {af.SHORT[stem]} f{f}: chains {r['n_chains']} hyps {r['n_hyps']} lanes {r['n_lanes']} {r['ms']:.0f} ms" + (f" right {r.get('right_found')} rank {r.get('right_rank')} mae {r.get('mae')}" if annotated else f" ball lane rank {r.get('ball_lane_rank')}"), flush=True)
    with gzip.open(af.PRED / f"face_{tg_}{stem}.json.gz", "wt") as fh:
        json.dump(face_out, fh)
    # summaries
    summ = {}
    throw = set(af.throw_frames(stem)) if annotated else None
    for sname in sets:
        rows = per[sname]
        s = {"frames": len(rows), "lanes_per_frame_median": float(np.median([r["n_lanes"] for r in rows])), "ms_median": float(np.median([r["ms"] for r in rows]))}
        if annotated:
            rt = [r for r in rows if r["frame"] in throw]
            s["throw_frames"] = len(rt)
            s["right_found_frac"] = round(float(np.mean([r["right_found"] for r in rt])), 3) if rt else None
            s["top_is_right_frac"] = round(float(np.mean([r["top_is_right"] for r in rt])), 3) if rt else None
            for k in ("feet_pick_right", "centre_pick_right", "widest_pick_right"):
                v = [r[k] for r in rt if k in r]; s[k + "_frac"] = round(float(np.mean(v)), 3) if v else None
            ph = af.pin_hit(stem)
            for t in af.TRUTHS:
                v = [r["mae"][t] for r in rt if "mae" in r]; s[f"mae_median_{t}"] = round(float(np.median(v)), 2) if v else None
                v = [r["tail"][t] for r in rt if "tail" in r]; s[f"tail_median_{t}"] = round(float(np.median(v)), 2) if v else None
                r = next((r for r in rows if r["frame"] == ph - 2 and "mae" in r), None); s[f"prehit_{t}"] = r["mae"][t] if r else None
            v = [abs(r["width_err_px_pins"]) for r in rt if "width_err_px_pins" in r]; s["far_width_err_px_medabs_pins"] = round(float(np.median(v)), 2) if v else None
            v = [abs(r["centre_err_px_pins"]) for r in rt if "centre_err_px_pins" in r]; s["far_centre_err_px_medabs_pins"] = round(float(np.median(v)), 2) if v else None
            s["right_found_all_frames_frac"] = round(float(np.mean([r["right_found"] for r in rows])), 3)
        else:
            if any("ball_lane_rank" in r for r in rows):
                v = [r.get("ball_lane_rank") for r in rows]
                s["ball_lane_found_frac"] = round(float(np.mean([x is not None for x in v])), 3); s["ball_lane_is_top_frac"] = round(float(np.mean([x == 1 for x in v])), 3)
            s["lanes_per_frame_max"] = int(max(r["n_lanes"] for r in rows)); s["frames_with_ge1_lane"] = round(float(np.mean([r["n_lanes"] >= 1 for r in rows])), 3)
        summ[sname] = s
        print(f"E3 {af.SHORT[stem]:13s} {sname:26s} " + json.dumps(s), flush=True)
    af.dump(af.RESULTS / f"e3_face_{tg_}{stem}.json", {"stem": stem, "sets": sets, "step": step, "summary": summ, "per_frame": {s: [{k: v for k, v in r.items() if k not in ("H", "corners")} for r in per[s]] for s in sets}})
    af.dump(af.PRED / f"face_rows_{tg_}{stem}.json", {s: per[s] for s in sets})
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--sets", default=",".join(SETS)); ap.add_argument("--step", type=int, default=1); ap.add_argument("--frames", default=None); ap.add_argument("--tag", default=""); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    sets = a.sets.split(",")
    for stem in (a.stems or af.ALL_STEMS):
        if stem in af.STEMS:
            fp = af.frame_for(stem, "prehit"); occ = af.C4.occluded_frames(stem)
            frames = [int(x) for x in a.frames.split(",")] if a.frames else None
            run(stem, sets, frames=frames, overlay_frames=(fp, occ[len(occ) // 2], af.L.frame_indices(stem, "mid")[0]) if not a.tag else (), step=a.step, tag=a.tag)
        else:
            ids = sorted(int(k) for k in json.load(gzip.open(af.PRED / f"cand_{stem}.json.gz", "rt")))
            run(stem, sets, overlay_frames=(ids[len(ids) // 4], ids[len(ids) // 2]) if not a.tag else (), step=a.step, tag=a.tag)
