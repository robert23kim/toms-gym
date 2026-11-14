"""Raw equivalence: PoseEstimator output with LIFT_POSE_WORKERS=N vs 1, exact dataclass equality."""
import json, os, sys, time, resource

def main():
    mode = sys.argv[1]            # candidates | video
    workers = [int(x) for x in sys.argv[2].split(",")]
    from src.lifting.pose.estimator import PoseEstimator
    import src.lifting.pose.parallel as par
    for path in sys.argv[3:]:
        ref = None
        for n in [1] + workers:
            os.environ["LIFT_POSE_WORKERS"] = str(n)
            par.LAST_STATS = None
            est = PoseEstimator()
            c0 = time.process_time(); t = time.time()
            out, fps = (est.estimate_video_candidates if mode == "candidates" else est.estimate_video)(path)
            wall = time.time() - t; cpu = time.process_time() - c0
            row = {"fixture": os.path.basename(path), "mode": mode, "workers": n, "frames": len(out), "wall_s": round(wall, 2)}
            if n == 1:
                ref = (out, fps)
                row["parent_cpu_over_wall"] = round(cpu / wall, 2)
            else:
                row["identical"] = (out == ref[0] and fps == ref[1])
                row["stats"] = par.LAST_STATS
                if not row["identical"]:
                    row["first_diff"] = next((i for i, (a, b) in enumerate(zip(out, ref[0])) if a != b), None)
                    row["len"] = [len(out), len(ref[0])]
            print(json.dumps(row), flush=True)

if __name__ == "__main__":
    main()
