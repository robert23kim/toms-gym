"""Mutation check of the hook selector on synthetic lane-coordinate series with 185645-level noise
(alternate-frame jitter of +-1.2 boards plus 0.3 gaussian). Over 40 seeds: a straight series must choose straight,
a 5.3 -> 7.95 hook in the last 15 ft must choose hook, and a shallow 1-board rise should mostly be refused.
usage: selector_check.py"""
import numpy as np
import run as R

ft = np.linspace(24.0, 60.0, 30)
w = ((ft + 6) / 66.0) ** 2
SEEDS = 40


def noise(rng, n):
    return np.where(np.arange(n) % 2 == 0, 1.0, -1.0) * 1.2 * rng.uniform(0.6, 1.0, n) + rng.normal(0, 0.3, n)


shapes = {
    'straight 15 -> 6': lambda: 15.0 - 0.25 * (ft - 24.0),
    'hook 5.3@45 -> 7.95@60': lambda: np.where(ft < 45, 5.3 + (45 - ft) * 0.38, 5.3 + 0.0118 * (ft - 45) ** 2),
    'shallow rise 0.8 board': lambda: np.where(ft < 48, 6.0 + (48 - ft) * 0.3, 6.0 + 0.0056 * (ft - 48) ** 2),
}
for name, fn in shapes.items():
    counts = {}
    entries = []
    for seed in range(SEEDS):
        rng = np.random.default_rng(seed)
        fit, beta, bp = R.fit_path(ft, fn() + noise(rng, len(ft)), w)
        counts[fit['kind']] = counts.get(fit['kind'], 0) + 1
        entries.append(fit['board_at_60ft'])
    print(f"{name}: {counts} entry mean {np.mean(entries):.2f} sd {np.std(entries):.2f} (true 60 ft board {fn()[-1]:.2f})")
