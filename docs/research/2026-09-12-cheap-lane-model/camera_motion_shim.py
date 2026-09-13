"""affine_between copied from loop 1's camera_motion.py (which runs on import)."""
import cv2
import numpy as np


def affine_between(img_ref, img, orb, bf):
    k1, d1 = orb.detectAndCompute(img_ref, None)
    k2, d2 = orb.detectAndCompute(img, None)
    if d1 is None or d2 is None:
        return None, 0
    m = bf.match(d1, d2)
    if len(m) < 20:
        return None, len(m)
    p1 = np.float32([k1[x.queryIdx].pt for x in m])
    p2 = np.float32([k2[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3)
    return M, int(inl.sum()) if inl is not None else 0
