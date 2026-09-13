"""Offline synthetic paired benchmark, never connects to the official simulator."""
import importlib.util
import json
import math
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location("reliable", Path(__file__).parent / "src/main_problem4_reliable.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Arena:
    def __init__(self, seed):
        rng = random.Random(seed)
        n = rng.randint(10, 16)
        self.sources = {}
        for ch in rng.sample(range(1, 21), n):
            a = rng.uniform(0, 2 * math.pi)
            r = 1800 if seed % 3 == 0 else 1800 * math.sqrt(rng.random())
            p = (r * math.cos(a), r * math.sin(a))
            phi = a if seed % 2 == 0 else rng.uniform(0, 2 * math.pi)
            directional = seed % 3 != 1 or rng.random() < .5
            self.sources[ch] = (p, rng.choice([1000., 1250., 1500.]), phi, directional)
        self.remaining = set(self.sources)
        self.position = (0., 0.)
        self.channel = 1
        self.virtual = 0.
        self.counts = dict(measures=0, clear_attempts=0)
        self.seed = seed

    def call(self, path, point, channel):
        self.virtual += m.distance(self.position, point) / 5
        self.position = point
        if path == "/clear":
            self.counts["clear_attempts"] += 1
            ok = channel in self.remaining and m.distance(point, self.sources[channel][0]) <= 20
            self.virtual += 5 if ok else 3
            if ok:
                self.remaining.remove(channel)
            return dict(clear_result="success" if ok else "no_target_in_range")
        self.counts["measures"] += 1
        self.virtual += 5 + (self.channel != channel)
        self.channel = channel
        if channel not in self.remaining:
            return dict(measure_result="no_signal")
        source, radius, phi, directional = self.sources[channel]
        delta = (point[0]-source[0], point[1]-source[1])
        d = math.hypot(*delta)
        if d > radius or (directional and delta[0]*math.cos(phi)+delta[1]*math.sin(phi) < 0):
            return dict(measure_result="no_signal")
        if d <= 5:
            return dict(measure_result="near")
        error = .999 * math.sin(point[0]*.013 + point[1]*.017 + channel + self.seed)
        angle = math.degrees(math.atan2(-delta[1], -delta[0]))
        return dict(measure_result="direction", svd_deg=round((angle+error) % 360, 2) % 360)


def run():
    m.self_test()
    results = []
    for seed in range(30):
        pair = {}
        for strategy in ("axial", "adaptive"):
            arena = Arena(seed)
            solver = m.ReliableSolver(arena, emit=lambda _: None, refinement=strategy)
            solver.solve()
            assert not arena.remaining, (seed, strategy, arena.remaining)
            assert solver.summary()["completed"]
            assert arena.virtual < 360000
            pair[strategy] = dict(total=len(arena.sources), time=arena.virtual, **arena.counts)
        results.append(pair)
    output = dict(label="SYNTHETIC ONLY; not official simulator measurements", cases=len(results),
                  total_sources=sum(x["axial"]["total"] for x in results),
                  mean_time_s={s:sum(x[s]["time"] for x in results)/len(results)
                               for s in ("axial","adaptive")},
                  clear_attempts={s:sum(x[s]["clear_attempts"] for x in results)
                                  for s in ("axial","adaptive")},
                  faster_cases=sum(x["adaptive"]["time"] < x["axial"]["time"] for x in results),
                  results=results)
    print(json.dumps({k:v for k,v in output.items() if k != "results"}, indent=2))
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    output = run()
    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")

