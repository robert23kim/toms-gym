"""Camera-compensated frame differencing for the glasses-POV cuts.

Global motion between consecutive frames: ORB + RANSAC homography on a downscaled grey
(the ball area is not masked explicitly: the ball covers < 1 % of the frame except at release,
where RANSAC treats it as outliers). Residual at frame t = min(|I_t - warp(I_{t-1})|, |I_t - warp(I_{t+1})|)
so the ghost at the previous ball position cancels. Blobs of the residual are the candidates.
"""
import cv2
import json
import numpy as np

L = "/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking"


def load_cut(stem):
    cuts = json.load(open(f"{L}/work/cuts/cuts.json"))
    cut = next(c for c in cuts if c["stem"] == stem)
    cap = cv2.VideoCapture(cut["cut_path"])
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    cap.release()
    assert len(frames) == cut["nb_frames"], (len(frames), cut["nb_frames"])
    return cut, frames


class Motion:
    """Homographies H[t] taking frame t-1 onto frame t (full-res pixels)."""

    def __init__(self, frames, scale=0.5, n_features=3000, min_inliers=40):
        self.scale = scale
        self.orb = cv2.ORB_create(n_features)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.min_inliers = min_inliers
        self.greys = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
        self.small = [cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) for g in self.greys]
        self.feat = [self.orb.detectAndCompute(s, None) for s in self.small]
        self.H = [None] * len(frames)
        self.inliers = [0] * len(frames)
        S = np.diag([1 / scale, 1 / scale, 1.0])
        Si = np.diag([scale, scale, 1.0])
        for t in range(1, len(frames)):
            H, n = self._pair(t - 1, t)
            self.inliers[t] = n
            self.H[t] = None if H is None else S @ H @ Si

    def _pair(self, a, b):
        ka, da = self.feat[a]
        kb, db = self.feat[b]
        if da is None or db is None or len(ka) < 8 or len(kb) < 8:
            return None, 0
        m = self.bf.match(da, db)
        if len(m) < 8:
            return None, 0
        pa = np.float32([ka[x.queryIdx].pt for x in m])
        pb = np.float32([kb[x.trainIdx].pt for x in m])
        H, mask = cv2.findHomography(pa, pb, cv2.RANSAC, 2.0)
        n = int(mask.sum()) if mask is not None else 0
        if H is None or n < self.min_inliers:
            return None, n
        return H, n

    def warp(self, img, t, direction):
        """Warp a neighbour image onto frame t. direction -1: image is frame t-1 (use H[t]);
        direction +1: image is frame t+1 (use inverse of H[t+1]). None when the motion is unknown."""
        if direction == -1:
            H = self.H[t]
        else:
            H = None if t + 1 >= len(self.H) or self.H[t + 1] is None else np.linalg.inv(self.H[t + 1])
        if H is None:
            return None
        h, w = img.shape[:2]
        return cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    def point_fwd(self, t, x, y):
        """Point in frame t-1 -> frame t."""
        H = self.H[t]
        if H is None:
            return x, y
        p = H @ np.array([x, y, 1.0])
        return float(p[0] / p[2]), float(p[1] / p[2])

    def point_bwd(self, t, x, y):
        """Point in frame t -> frame t-1."""
        H = self.H[t]
        if H is None:
            return x, y
        p = np.linalg.inv(H) @ np.array([x, y, 1.0])
        return float(p[0] / p[2]), float(p[1] / p[2])


def residual(motion, frames, t, blur=3):
    """Three-frame camera-compensated residual (uint8, full res) and a validity mask."""
    g = motion.greys
    cur = g[t]
    if blur:
        cur = cv2.GaussianBlur(cur, (blur, blur), 0)
    outs, valid = [], np.ones(cur.shape, np.uint8)
    for d in (-1, 1):
        n = t + d
        if n < 0 or n >= len(g):
            continue
        w = motion.warp(g[n], t, d)
        if w is None:
            continue
        v = motion.warp(np.full(cur.shape, 255, np.uint8), t, d)
        if blur:
            w = cv2.GaussianBlur(w, (blur, blur), 0)
        outs.append(cv2.absdiff(cur, w))
        valid &= (v > 200).astype(np.uint8)
    if not outs:
        return None, None
    r = outs[0] if len(outs) == 1 else np.minimum(outs[0], outs[1])
    r[valid == 0] = 0
    return r, valid
