"""Synthetic paired V2/V3 benchmark. No HTTP or simulator access."""
import argparse
import json
import math
from pathlib import Path
from test_reliable_benchmark import Arena, m


def run():
    m.self_test()
    compact = set(m.compact_scan_points())
    assert len(compact) == 45
    # Verify every source-intersecting cell retains all four corner detectors.
    axis = [650 * i for i in range(-3, 4)]
    for x0, x1 in zip(axis, axis[1:]):
        for y0, y1 in zip(axis, axis[1:]):
            dx = 0 if x0 <= 0 <= x1 else min(abs(x0), abs(x1))
            dy = 0 if y0 <= 0 <= y1 else min(abs(y0), abs(y1))
            if math.hypot(dx, dy) <= 1800:
                assert {(x0,y0),(x0,y1),(x1,y0),(x1,y1)} <= compact
    assert 650 * math.sqrt(2) < 1000
    results = []
    for seed in range(130):
        pair = {"seed": seed, "group": "development" if seed < 30 else "held_out"}
        for label, cls in (("v2", m.ReliableSolver), ("v3", m.CompactSolver)):
            arena = Arena(seed)
            solver = cls(arena, emit=lambda _: None, refinement="adaptive")
            solver.solve()
            assert not arena.remaining, (seed, label, arena.remaining)
            assert solver.summary()["completed"]
            assert arena.virtual < 360000
            pair[label] = dict(total=len(arena.sources), time=arena.virtual, **arena.counts)
        results.append(pair)
    groups = {}
    for group in ("development", "held_out"):
        subset = [r for r in results if r["group"] == group]
        groups[group] = dict(cases=len(subset), sources=sum(r["v2"]["total"] for r in subset),
                             faster_cases=sum(r["v3"]["time"] < r["v2"]["time"] for r in subset),
                             mean_time_s={v:sum(r[v]["time"] for r in subset)/len(subset) for v in ("v2","v3")},
                             max_ratio=max(r["v3"]["time"]/r["v2"]["time"] for r in subset))
    output = dict(label="SYNTHETIC ONLY; V3 official simulator tests pending", groups=groups, results=results)
    print(json.dumps(groups, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run()
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")

