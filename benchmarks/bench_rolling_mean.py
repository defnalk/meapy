"""Micro-benchmark for meapy.utils.rolling_mean.

Run with:
    python benchmarks/bench_rolling_mean.py

Profiles the rolling-mean computation across array sizes representative of
plant data: 1k samples (a single short steady-state run), 10k (a full hour
at 1 Hz), 100k (a multi-hour campaign), and 1M (a week of 1 Hz logging).

Baseline numbers captured on Apple M-series, Python 3.13, NumPy 2.x.
See the commit message of the perf optimisation for before/after deltas.
"""

from __future__ import annotations

import cProfile
import pstats
import time
from io import StringIO

import numpy as np

from meapy.utils import rolling_mean

SIZES = (1_000, 10_000, 100_000, 1_000_000)
WINDOW = 60  # 1-minute trailing window at 1 Hz
REPEATS = 5


def time_one(size: int, window: int, repeats: int) -> float:
    """Return best-of-N wall-clock time for a single rolling_mean call."""
    arr = np.random.default_rng(0).standard_normal(size)
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        rolling_mean(arr, window)
        dt = time.perf_counter() - t0
        if dt < best:
            best = dt
    return best


def main() -> None:
    print(f"rolling_mean benchmark — window={WINDOW}, best-of-{REPEATS}")
    print("-" * 56)
    print(f"{'size':>10}  {'time (ms)':>12}  {'throughput (M-elem/s)':>22}")
    print("-" * 56)
    for size in SIZES:
        t = time_one(size, WINDOW, REPEATS)
        thr = size / t / 1e6
        print(f"{size:>10}  {t * 1e3:>12.3f}  {thr:>22.2f}")
    print("-" * 56)

    # cProfile dump for the largest size — useful for spotting hotspots.
    arr = np.random.default_rng(0).standard_normal(100_000)
    pr = cProfile.Profile()
    pr.enable()
    rolling_mean(arr, WINDOW)
    pr.disable()
    buf = StringIO()
    pstats.Stats(pr, stream=buf).sort_stats("cumulative").print_stats(10)
    print("\ncProfile (size=100_000, top 10 by cumulative):")
    print(buf.getvalue())


if __name__ == "__main__":
    main()
