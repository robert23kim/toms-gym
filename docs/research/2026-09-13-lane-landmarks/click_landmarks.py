"""Correct a landmark by clicking. usage: click_landmarks.py <stem> <frame> [name]
Opens the frame (zoomable: scroll to zoom, drag to pan is not supported - use the
z/x keys), click = set the named landmark, n/p = next/previous landmark name,
s = save to results/landmarks_<stem>.json (source: clicked, confidence 1.0), q = quit."""
import sys
import cv2
import common as C

stem, frame = sys.argv[1], int(sys.argv[2])
path = C.landmarks_path(stem)
doc = C.load(path) if path.exists() else {"stem": stem, "frame": frame, "landmarks": {}}
names = sorted(doc["landmarks"]) or [f"pin_{i}_base" for i in range(1, 11)] + [f"arrow_{b}" for b in C.ARROW_BOARDS] + ["foul_left", "foul_right"]
idx = names.index(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] in names else 0
img0 = C.read_frame(stem, frame)
zoom, ox, oy = 1.0, 0.0, 0.0


def render():
    v = cv2.resize(img0, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
    for n, lm in doc["landmarks"].items():
        p = (int(lm["x"] * zoom), int(lm["y"] * zoom))
        col = (0, 255, 0) if lm.get("source") == "clicked" else (0, 200, 255)
        cv2.circle(v, p, 4, col, 1); cv2.putText(v, n.replace("_base", ""), (p[0] + 5, p[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
    cv2.putText(v, f"{names[idx]}  (click to set; n/p next/prev; z/x zoom; s save; q quit)", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return v


def on_click(ev, x, y, flags, param):
    if ev == cv2.EVENT_LBUTTONDOWN:
        doc["landmarks"][names[idx]] = {"x": x / zoom, "y": y / zoom, "frame": frame, "source": "clicked", "confidence": 1.0}


cv2.namedWindow("landmarks", cv2.WINDOW_NORMAL); cv2.setMouseCallback("landmarks", on_click)
while True:
    cv2.imshow("landmarks", render()); k = cv2.waitKey(30) & 0xFF
    if k == ord("q"): break
    if k == ord("n"): idx = (idx + 1) % len(names)
    if k == ord("p"): idx = (idx - 1) % len(names)
    if k == ord("z"): zoom = min(8.0, zoom * 1.5)
    if k == ord("x"): zoom = max(0.5, zoom / 1.5)
    if k == ord("s"): C.dump(path, doc); print("saved", path)
cv2.destroyAllWindows()
