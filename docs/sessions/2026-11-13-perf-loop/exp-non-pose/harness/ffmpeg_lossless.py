#!/usr/bin/env python3
"""ffmpeg stand-in for the lossless reference render: same args, crf forced to 0."""
import os
import sys

args = sys.argv[1:]
args[args.index("-crf") + 1] = "0"
os.execvp("ffmpeg", ["ffmpeg"] + args)
