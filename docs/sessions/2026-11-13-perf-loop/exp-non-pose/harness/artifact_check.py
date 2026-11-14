#!/usr/bin/env python3
"""Gate the uploaded video artifacts: artifact_check.py <old.mp4> <new.mp4> [--min-ssim 0.93]

old = what the cv2 + re-encode path uploads, new = what the candidate uploads.
FAILS unless new is H.264 / yuv420p / faststart with the same size, frame count,
frame rate and duration as old, and every plane (Y, U, V) of the decoded frames is close (SSIM).
"""
import json
import re
import subprocess
import sys


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
         "stream=codec_name,pix_fmt,width,height,nb_read_frames,r_frame_rate,avg_frame_rate:format=duration,size",
         "-of", "json", path], capture_output=True, text=True, check=True)
    d = json.loads(out.stdout)
    s = d["streams"][0]
    s["duration"] = float(d["format"]["duration"])
    s["size"] = int(d["format"]["size"])
    return s


def faststart(path):
    with open(path, "rb") as f:
        data = f.read()
    moov, mdat = data.find(b"moov"), data.find(b"mdat")
    return 0 <= moov < mdat


def ssim(old, new):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", new, "-i", old, "-lavfi",
                          # pair frames by index: timestamps differ by microseconds between the two muxers
                          "[0:v]settb=AVTB,setpts=N/30/TB[a];[1:v]settb=AVTB,setpts=N/30/TB[b];[a][b]ssim",
                          "-f", "null", "-"],
                         capture_output=True, text=True)
    m = re.search(r"Y:([\d.]+).*U:([\d.]+).*V:([\d.]+).*All:([\d.]+)", out.stderr)
    return min(float(g) for g in m.groups()) if m else None


def fps(rate):
    n, d = rate.split("/")
    return float(n) / float(d)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    min_ssim = float(sys.argv[sys.argv.index("--min-ssim") + 1]) if "--min-ssim" in sys.argv else 0.95
    args = [a for a in args if a != str(min_ssim)] if "--min-ssim" in sys.argv else args
    old_p, new_p = args[:2]
    old, new = probe(old_p), probe(new_p)
    fails = []
    if new["codec_name"] != "h264":
        fails.append(f"codec {new['codec_name']}")
    if new["pix_fmt"] != "yuv420p":
        fails.append(f"pix_fmt {new['pix_fmt']}")
    if not faststart(new_p):
        fails.append("moov after mdat (no faststart)")
    for k in ("width", "height", "nb_read_frames"):
        if old[k] != new[k]:
            fails.append(f"{k} {old[k]} -> {new[k]}")
    if abs(fps(old["r_frame_rate"]) - fps(new["r_frame_rate"])) > 0.01:
        fails.append(f"fps {old['r_frame_rate']} -> {new['r_frame_rate']}")
    if abs(old["duration"] - new["duration"]) > 1.5 / fps(old["r_frame_rate"]):
        fails.append(f"duration {old['duration']} -> {new['duration']}")
    score = ssim(old_p, new_p)
    if score is None or score < min_ssim:
        fails.append(f"min plane ssim {score} < {min_ssim}")
    print(json.dumps({
        "new": new_p.split("/")[-2] + "/" + new_p.split("/")[-1], "verdict": "FAIL" if fails else "PASS", "fails": fails,
        "frames": new["nb_read_frames"], "fps": new["r_frame_rate"], "size_px": f"{new['width']}x{new['height']}",
        "duration_old_new": [old["duration"], new["duration"]], "old_faststart": faststart(old_p),
        "old_codec": old["codec_name"], "min_plane_ssim_vs_old": score,
        "bytes_old_new": [old["size"], new["size"]], "bytes_delta_pct": round(100 * (new["size"] - old["size"]) / old["size"], 1)}))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
