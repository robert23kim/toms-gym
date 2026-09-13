"""SAM 2 through ultralytics with the image encoded once and any number of
prompt sets decoded against the cached features, returning float logits at
source resolution instead of a thresholded mask.

The encoder is ~95 % of a SAM call on CPU (0.7 s tiny / 1.5 s base at 1024 px);
the prompt encoder + mask decoder are a few ms. Prompt ensembles, multi-object
prompts (lane + gutters) and candidate masks are therefore nearly free once the
image is encoded. Crops are encoded separately: the mask decoder works on a
256-cell grid, so a 1080x1920 frame gives ~7.5 source px per cell, and a crop
of the pin end at 1024 px gives 1-3 px per cell.
"""
import os

import numpy as np
import torch

import common as C

_models = {}


def _model(weights, imgsz):
    key = (weights, imgsz)
    if key not in _models:
        from ultralytics import SAM
        cwd = os.getcwd()
        os.chdir(C.L.WEIGHTS_DIR)
        try:
            m = SAM(weights)
        finally:
            os.chdir(cwd)
        # first call builds the predictor with this imgsz; the prompt is a throwaway
        m.predict(np.zeros((64, 64, 3), np.uint8), points=[[[8, 8]]], labels=[[1]], imgsz=imgsz, verbose=False)
        _models[key] = m
    return _models[key]


class SamImage:
    """Encode one BGR image, then decode prompts as often as needed."""

    def __init__(self, img, weights="sam2.1_b.pt", imgsz=1024):
        self.weights = weights
        self.imgsz = imgsz
        self.p = _model(weights, imgsz).predictor
        self.p.setup_source(None)
        im = self.p.preprocess([img])
        with torch.no_grad():
            self.feats = self.p.get_im_features(im)
        self.im_shape = tuple(im.shape[2:])
        self.src_shape = tuple(img.shape[:2])

    def logits(self, objects, labels=None, bboxes=None, multimask=False):
        """objects: list of point lists, one per object ([[x, y], ...] each;
        ragged lists are padded with SAM's not-a-point label). Returns
        (logits[N, H, W] float32 at source resolution, scores[N])."""
        n = max(len(o) for o in objects)
        pts = np.zeros((len(objects), n, 2), np.float32)
        lab = -np.ones((len(objects), n), np.int32)
        for i, o in enumerate(objects):
            for j, (x, y) in enumerate(o):
                pts[i, j] = (x, y)
                lab[i, j] = 1 if labels is None else labels[i][j]
        with torch.no_grad():
            tp, tl, _ = self.p._prepare_prompts(self.im_shape, self.src_shape, bboxes=bboxes, points=pts, labels=lab)
            masks, scores = self.p._inference_features(self.feats, tp, tl, multimask_output=multimask)
            from ultralytics.utils import ops
            masks = ops.scale_masks(masks[None].float(), self.src_shape, padding=False)[0]
        return masks.cpu().numpy().astype(np.float32), [float(s) for s in scores]

    def logit(self, points, labels=None, bboxes=None):
        """One object. Returns (logits[H, W], score)."""
        lg, sc = self.logits([points], None if labels is None else [labels], bboxes=bboxes)
        return lg[0], sc[0]


def crop_logit(img, box, points, weights="sam2.1_b.pt", labels=None):
    """Encode the crop img[y1:y2, x1:x2] on its own (upscaled to imgsz by the
    letterbox) and decode `points` given in full-image coordinates. Returns
    logits for the crop region only, shape (y2-y1, x2-x1)."""
    x1, y1, x2, y2 = box
    crop = img[y1:y2, x1:x2]
    local = [[x - x1, y - y1] for x, y in points]
    si = SamImage(crop, weights)
    lg, sc = si.logit(local, labels)
    return lg, sc
