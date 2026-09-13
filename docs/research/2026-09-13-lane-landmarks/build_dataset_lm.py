"""YOLO seg dataset with two classes: 0 = lane (annotated quad polygon, as loop 3),
1 = arrow (tiny quad around each E1 arrow position projected into every frame
through that frame's truth homography). Folds lovo_<stem> + all3, val = every
10th frame of the TRAINING videos. Writes $LM_SCRATCH/ds/seg2/..."""
import os
import numpy as np
import yaml
import common as C
import landmarks as LM

C.use_full_camera()
DS = C.SCRATCH / "ds" / "seg2"
ORDER = ("top_left", "top_right", "bottom_right", "bottom_left")
ARROW_HALF_W_IN = 0.8   # +- boards*1.064/2 ~ a little wider than the inlay
ARROW_HALF_L_IN = 4.0   # arrows are ~6-7 in long; centroid box


def arrow_polys(stem, f):
    H = LM.truth_h(stem, f, "all")
    V = C.landmark_doc(stem)["all_fit"]["V"] or {"centre_ft": 15.3, "ft_per_5_boards": 0.43}
    polys = []
    for b, x in LM.arrow_x_in().items():
        y = (V["centre_ft"] - V["ft_per_5_boards"] * abs(b - 20) / 5.0) * 12
        q = [(x - ARROW_HALF_W_IN, y + ARROW_HALF_L_IN), (x + ARROW_HALF_W_IN, y + ARROW_HALF_L_IN), (x + ARROW_HALF_W_IN, y - ARROW_HALF_L_IN), (x - ARROW_HALF_W_IN, y - ARROW_HALF_L_IN)]
        polys.append(LM.to_image(H, q))
    return polys


def main():
    for stem in C.STEMS:
        (DS / "images" / stem).mkdir(parents=True, exist_ok=True); (DS / "labels" / stem).mkdir(parents=True, exist_ok=True)
        img0 = C.read_frame(stem, C.frame_ids(stem)[0]); h, w = img0.shape[:2]
        n_arrow = 0
        for f in C.frame_ids(stem):
            link = DS / "images" / stem / f"{f:05d}.jpg"
            if not link.exists():
                os.symlink(C.FRAMES / stem / f"{f:05d}.jpg", link)
            q = L_truth = C.truth_corners(stem, f, "annotated")
            xs = np.clip([q[k][0] / w for k in ORDER], 0, 1); ys = np.clip([q[k][1] / h for k in ORDER], 0, 1)
            lines = ["0 " + " ".join(f"{x:.6f} {y:.6f}" for x, y in zip(xs, ys))]
            for poly in arrow_polys(stem, f):
                px = poly[:, 0] / w; py = poly[:, 1] / h
                if px.min() < 0 or px.max() > 1 or py.min() < 0 or py.max() > 1:
                    continue
                lines.append("1 " + " ".join(f"{x:.6f} {y:.6f}" for x, y in zip(px, py))); n_arrow += 1
            (DS / "labels" / stem / f"{f:05d}.txt").write_text("\n".join(lines) + "\n")
        print(stem, "frames", len(C.frame_ids(stem)), "arrow boxes", n_arrow, "size", (w, h))
    folds = {f"lovo_{s}": [t for t in C.STEMS if t != s] for s in C.STEMS}; folds["all3"] = list(C.STEMS)
    for name, train_stems in folds.items():
        tr, va = [], []
        for stem in train_stems:
            for i, f in enumerate(C.frame_ids(stem)):
                (va if i % 10 == 5 else tr).append(str(DS / "images" / stem / f"{f:05d}.jpg"))
        (DS / f"{name}_train.txt").write_text("\n".join(tr) + "\n"); (DS / f"{name}_val.txt").write_text("\n".join(va) + "\n")
        (DS / f"{name}.yaml").write_text(yaml.safe_dump({"path": str(DS), "train": f"{name}_train.txt", "val": f"{name}_val.txt", "names": {0: "lane", 1: "arrow"}}, sort_keys=False))
        print(name, "train", len(tr), "val", len(va))


if __name__ == "__main__":
    main()
