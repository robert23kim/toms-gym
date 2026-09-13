"""E6: learning the face the way face alignment does. A small U-Net predicts one heatmap per
constellation landmark (stride 4) - 7 arrows, 11 guide dots, 7 foul-line dots, 7 approach dots,
10 pin bases, 2 foul corners = 44 channels ("landmark" variant) or one heatmap per class (6
channels, "class" variant) - trained on native-resolution crops of the three annotated videos with
random homography augmentation applied to image and points together (the constellation's only
freedom is a homography, so a warped frame is exact supervision), leave-one-video-out, best.pt
chosen on the TRAINING videos' held-back frames. Landmarks hidden by the bowler / ball (E1 timeline)
and pins after the hit are ignored in the loss.
usage: e6_heatmap.py build | train <fold> <variant> [iters] | predict <fold> <variant> <stem> | eval"""
import json
import math
import os
import sys
import time

import cv2
import numpy as np

import af

DS = af.SCRATCH / "ds" / "heat"; RUNS = af.SCRATCH / "runs"
CONST = af.constellation()
NAMES = sorted(CONST, key=lambda n: (["foul", "fdot", "dot", "adot", "arrow", "pin"].index(af.classes_of(n)), CONST[n][0]))
CLASSES = ["foul", "fdot", "dot", "adot", "arrow", "pin"]
CROP = 640; STRIDE = 4; SIGMA = 1.6   # heatmap sigma in output cells (6.4 px at full res)


# ---------------------------------------------------------------- data

def build():
    """Per-frame landmark image positions + visibility for the three annotated videos."""
    DS.mkdir(parents=True, exist_ok=True)
    for stem in af.STEMS:
        tl = {r["frame"]: r["status"] for r in af.load(af.RESULTS / f"e1_timeline_{stem}.json")["per_frame"]}
        rows = {}
        for f in af.frame_ids(stem):
            tp = af.truth_points(stem, f, "all")
            rows[str(f)] = {n: [round(tp[n][0], 2), round(tp[n][1], 2), 1 if tl[f][n] == "clear" else 0] for n in NAMES}
        (DS / f"points_{stem}.json").write_text(json.dumps(rows))
        print(stem, len(rows), "frames", flush=True)


def rand_h(w, h, rng, strength=1.0):
    """Random homography about the image centre: rotation, anisotropic scale, shear, perspective, translation."""
    cx, cy = w / 2, h / 2
    ang = rng.uniform(-12, 12) * strength; sc = math.exp(rng.uniform(-0.45, 0.35) * strength); asp = math.exp(rng.uniform(-0.12, 0.12) * strength)
    sh = rng.uniform(-0.15, 0.15) * strength; px, py = rng.uniform(-2.5e-4, 2.5e-4) * strength, rng.uniform(-2.5e-4, 2.5e-4) * strength
    tx, ty = rng.uniform(-0.15, 0.15) * w * strength, rng.uniform(-0.15, 0.15) * h * strength
    T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], np.float64)
    R = np.array([[math.cos(math.radians(ang)), -math.sin(math.radians(ang)), 0], [math.sin(math.radians(ang)), math.cos(math.radians(ang)), 0], [0, 0, 1]])
    S = np.array([[sc * asp, sh, 0], [0, sc / asp, 0], [0, 0, 1]]); P = np.array([[1, 0, 0], [0, 1, 0], [px, py, 1]])
    T2 = np.array([[1, 0, cx + tx], [0, 1, cy + ty], [0, 0, 1]], np.float64)
    return T2 @ P @ S @ R @ T1


class Data:
    def __init__(self, stems, frames_by_stem, variant, aug=True, seed=0):
        self.items = [(s, f) for s in stems for f in frames_by_stem[s]]
        self.pts = {s: json.loads((DS / f"points_{s}.json").read_text()) for s in stems}
        self.variant = variant; self.aug = aug; self.rng = np.random.default_rng(seed)
        self.nch = len(NAMES) if variant == "landmark" else len(CLASSES)
        self.ph = {s: af.pin_hit(s) for s in stems}

    def __len__(self):
        return len(self.items)

    def channel(self, name):
        return NAMES.index(name) if self.variant == "landmark" else CLASSES.index(af.classes_of(name))

    def sample(self, idx=None):
        s, f = self.items[idx if idx is not None else self.rng.integers(len(self.items))]
        img = af.read_frame(s, f); h, w = img.shape[:2]
        pts = self.pts[s][str(f)]
        P = np.array([[pts[n][0], pts[n][1]] for n in NAMES], np.float32)
        vis = np.array([pts[n][2] for n in NAMES], bool)
        if f >= self.ph[s]:
            vis &= np.array([af.classes_of(n) != "pin" for n in NAMES])
        # crop centre: a visible landmark (80 %) or anywhere (20 %)
        if self.aug and self.rng.random() < 0.8 and vis.any():
            k = self.rng.choice(np.where(vis)[0]); cx, cy = P[k] + self.rng.uniform(-CROP * 0.4, CROP * 0.4, 2)
        elif self.aug:
            cx, cy = self.rng.uniform(0, w), self.rng.uniform(0, h)
        else:
            cx, cy = w / 2, h / 2
        H = rand_h(w, h, self.rng) if self.aug else np.eye(3)
        # move the (warped) crop centre to the crop's centre
        c = cv2.perspectiveTransform(np.float32([[[cx, cy]]]), H)[0, 0]
        T = np.array([[1, 0, CROP / 2 - c[0]], [0, 1, CROP / 2 - c[1]], [0, 0, 1]], np.float64)
        Hc = T @ H
        crop = cv2.warpPerspective(img, Hc, (CROP, CROP), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        if self.aug:
            a = self.rng.uniform(0.7, 1.3); b = self.rng.uniform(-30, 30)
            crop = np.clip(crop.astype(np.float32) * a + b, 0, 255).astype(np.uint8)
            if self.rng.random() < 0.3:
                crop = cv2.GaussianBlur(crop, (3, 3), 0)
            if self.rng.random() < 0.3:
                crop = np.clip(crop.astype(np.float32) + self.rng.normal(0, 4, crop.shape), 0, 255).astype(np.uint8)
        Pw = cv2.perspectiveTransform(P.reshape(-1, 1, 2), Hc).reshape(-1, 2)
        # in-frame after warp (a warped point that came from outside the source frame is not supervision)
        inside = (P[:, 0] >= 0) & (P[:, 0] < w) & (P[:, 1] >= 0) & (P[:, 1] < h)
        # targets
        oh = CROP // STRIDE
        hm = np.zeros((self.nch, oh, oh), np.float32); wmask = np.ones((self.nch, 1, 1), np.float32)
        yy, xx = np.mgrid[0:oh, 0:oh]
        ignore = np.zeros((self.nch, oh, oh), np.float32)
        for i, n in enumerate(NAMES):
            x, y = Pw[i] / STRIDE
            if not (-2 <= x < oh + 2 and -2 <= y < oh + 2) or not inside[i]:
                continue
            ch = self.channel(n)
            g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * SIGMA ** 2))
            if vis[i]:
                hm[ch] = np.maximum(hm[ch], g)
            else:
                ignore[ch] = np.maximum(ignore[ch], (g > 0.05).astype(np.float32))
        x = crop.astype(np.float32).transpose(2, 0, 1) / 255.0
        return x, hm, 1.0 - ignore


# ---------------------------------------------------------------- model

def make_model(nch):
    import torch.nn as nn

    def blk(i, o):
        return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True), nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True))

    class UNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.e1 = blk(3, 32); self.e2 = blk(32, 64); self.e3 = blk(64, 128); self.e4 = blk(128, 192); self.e5 = blk(192, 256)
            self.pool = nn.MaxPool2d(2)
            self.up = nn.Upsample(scale_factor=2, mode="nearest")
            self.u4 = nn.Conv2d(256, 192, 3, padding=1); self.d4 = blk(384, 192)
            self.u3 = nn.Conv2d(192, 128, 3, padding=1); self.d3 = blk(256, 128)
            self.head = nn.Conv2d(128, nch, 1)

        def forward(self, x):
            e1 = self.e1(x)                 # /1
            e2 = self.e2(self.pool(e1))     # /2
            e3 = self.e3(self.pool(e2))     # /4
            e4 = self.e4(self.pool(e3))     # /8
            e5 = self.e5(self.pool(e4))     # /16
            import torch
            d4 = self.d4(torch.cat([self.u4(self.up(e5)), e4], 1).contiguous())   # /8
            d3 = self.d3(torch.cat([self.u3(self.up(d4)), e3], 1).contiguous())   # /4
            return self.head(d3)            # stride 4
    return UNet()


def folds():
    fr = {s: af.frame_ids(s) for s in af.STEMS}
    out = {}
    for held in af.STEMS:
        tr = [s for s in af.STEMS if s != held]
        out[f"lovo_{held}"] = {"train": {s: [f for i, f in enumerate(fr[s]) if i % 10 != 5] for s in tr}, "val": {s: [f for i, f in enumerate(fr[s]) if i % 10 == 5] for s in tr}, "held": held}
    return out


def focal_mse(pred, target, mask):
    import torch
    # weighted MSE: positives (target > 0.1) weighted 20x so the tiny peaks matter against the empty background
    w = 1.0 + 19.0 * (target > 0.1).float()
    return (((torch.sigmoid(pred) - target) ** 2) * w * mask).mean()


def train(fold, variant, iters=3000, batch=6):
    import torch
    torch.manual_seed(0)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    fd = folds()[fold]
    tr = Data(list(fd["train"]), fd["train"], variant, aug=True, seed=1); va = Data(list(fd["val"]), fd["val"], variant, aug=False, seed=2)
    model = make_model(tr.nch).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=iters, pct_start=0.1)
    run_dir = RUNS / f"heat_{variant}_{fold}"; run_dir.mkdir(parents=True, exist_ok=True)
    log = open(run_dir / "train.log", "a"); t0 = time.time(); best = (1e9, -1)
    # fixed validation crops (centre crops around visible landmarks, no aug) - drawn once
    va.aug = True; va.rng = np.random.default_rng(123)
    vb = [va.sample() for _ in range(48)]
    va.aug = False
    for it in range(1, iters + 1):
        model.train()
        xs, hs, ms = zip(*[tr.sample() for _ in range(batch)])
        x = torch.from_numpy(np.ascontiguousarray(np.stack(xs))).to(dev); hm = torch.from_numpy(np.ascontiguousarray(np.stack(hs))).to(dev); mk = torch.from_numpy(np.ascontiguousarray(np.stack(ms))).to(dev)
        loss = focal_mse(model(x), hm, mk)
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        if it % 100 == 0 or it == iters:
            model.eval(); vl = []
            with torch.no_grad():
                for k in range(0, len(vb), batch):
                    xs, hs, ms = zip(*vb[k:k + batch])
                    x = torch.from_numpy(np.stack(xs)).to(dev); hm = torch.from_numpy(np.stack(hs)).to(dev); mk = torch.from_numpy(np.stack(ms)).to(dev)
                    vl.append(float(focal_mse(model(x), hm, mk)))
            v = float(np.mean(vl))
            msg = f"{fold} {variant} it {it} train {float(loss):.5f} val {v:.5f} {(time.time() - t0) / 60:.1f} min"
            print(msg, flush=True); log.write(msg + "\n"); log.flush()
            if v < best[0]:
                best = (v, it); torch.save(model.state_dict(), run_dir / "best.pt")
            torch.save(model.state_dict(), run_dir / "last.pt")
    (run_dir / "done.json").write_text(json.dumps({"best_val": best[0], "best_it": best[1], "iters": iters, "minutes": round((time.time() - t0) / 60, 1)}))
    print("DONE", fold, variant, best, flush=True)


# ---------------------------------------------------------------- inference

def peaks(hm, thr=0.25, nms=3):
    """Local maxima per channel above thr with quadratic sub-cell refinement. Returns [(ch, x, y, conf)] in heatmap cells."""
    import torch
    t = torch.from_numpy(hm)[None]
    mx = torch.nn.functional.max_pool2d(t, nms, stride=1, padding=nms // 2)[0].numpy()
    out = []
    C, H, W = hm.shape
    for c in range(C):
        ys, xs = np.where((hm[c] >= mx[c]) & (hm[c] > thr))
        for y, x in zip(ys, xs):
            dx = dy = 0.0
            if 0 < x < W - 1:
                l, m, r = hm[c, y, x - 1], hm[c, y, x], hm[c, y, x + 1]; dx = 0.5 * (l - r) / (l - 2 * m + r + 1e-9) if (l - 2 * m + r) != 0 else 0.0
            if 0 < y < H - 1:
                u, m, d = hm[c, y - 1, x], hm[c, y, x], hm[c, y + 1, x]; dy = 0.5 * (u - d) / (u - 2 * m + d + 1e-9) if (u - 2 * m + d) != 0 else 0.0
            out.append((c, float(x + np.clip(dx, -0.5, 0.5)), float(y + np.clip(dy, -0.5, 0.5)), float(hm[c, y, x])))
    return out


def predict(fold, variant, stem, step=1, which="best"):
    import torch
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    nch = len(NAMES) if variant == "landmark" else len(CLASSES)
    model = make_model(nch).to(dev); model.load_state_dict(torch.load(RUNS / f"heat_{variant}_{fold}" / f"{which}.pt", map_location=dev)); model.eval()
    out = {}
    t_all = []
    for f in af.frame_ids(stem)[::step]:
        img = af.read_frame(stem, f); h, w = img.shape[:2]
        H2, W2 = (h + 15) // 16 * 16, (w + 15) // 16 * 16
        pad = np.zeros((H2, W2, 3), np.uint8); pad[:h, :w] = img
        x = torch.from_numpy(pad.astype(np.float32).transpose(2, 0, 1)[None] / 255.0).to(dev)
        t0 = time.perf_counter()
        with torch.no_grad():
            hm = torch.sigmoid(model(x))[0].cpu().numpy()
        t_all.append(time.perf_counter() - t0)
        pk = peaks(hm)
        dets = []
        for c, px, py, conf in pk:
            X = (px + 0.5) * STRIDE - 0.5; Y = (py + 0.5) * STRIDE - 0.5
            if X < w and Y < h:
                dets.append({"ch": int(c), "name": NAMES[c] if variant == "landmark" else CLASSES[c], "x": round(float(X), 2), "y": round(float(Y), 2), "conf": round(conf, 3)})
        out[str(f)] = dets
    p = af.PRED / f"heat_{variant}_{fold}__{stem}.json"
    p.write_text(json.dumps({"fold": fold, "variant": variant, "stem": stem, "ms_median": round(1000 * float(np.median(t_all)), 1), "per_frame": out}))
    print("predicted", stem, fold, variant, len(out), "frames", round(1000 * float(np.median(t_all)), 1), "ms", flush=True)
    return p


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "train":
        train(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 3000)
    elif cmd == "predict":
        predict(sys.argv[2], sys.argv[3], sys.argv[4], which=sys.argv[5] if len(sys.argv) > 5 else "best")
