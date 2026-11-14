#!/usr/bin/env bash
cd "$(dirname "$0")"
./image_gate.sh flag-off all
./image_gate.sh np1 "squat_f47a8848.mov pushup_3c66c85e.mov pushup_97b4aaf2.mp4 pushup_e18a31d1.mp4 situp_16b6ca35.mov situp_667a8480.mp4 situp_c9dec98b.mp4" POSE_NUM_POSES=1
./image_gate.sh stride2 "squat_f47a8848.mov pushup_3c66c85e.mov situp_c9dec98b.mp4" POSE_FRAME_STRIDE=2
./image_gate.sh side640 "pushup_e18a31d1.mp4 situp_667a8480.mp4" POSE_MAX_SIDE=640
echo IMAGEALLDONE
