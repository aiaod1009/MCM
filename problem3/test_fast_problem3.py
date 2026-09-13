"""独立种子同场景比较及边界检查；不连接官方模拟器。"""
import json
import math
import sys
from pathlib import Path
from test_reliable_problem3 import Arena, m, checks
from fast_solver import SectorSolver
from reliable_core import distance


def quick_checks():
    for seed in (1000, 1001, 1002):
        arena = Arena(seed)
        solver = SectorSolver(arena, emit=lambda _: None)
        solver.solve()
        assert not arena.remaining and solver.summary()['completed']
    print('联合规划版三场离线自检通过。')


def run():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    checks()
    records = []
    for seed in range(1000, 1200):
        row = {'seed': seed}
        for name, cls in [('baseline', m.Solver), ('fast', SectorSolver)]:
            arena = Arena(seed)
            solver = cls(arena, emit=lambda _: None)
            solver.solve()
            assert not arena.remaining and solver.summary()['completed']
            row[name] = arena.virtual/len(arena.sources)
            row['sources'] = len(arena.sources)
            if name == 'fast':
                assert not solver.sectors
                # Independent dense sampling verifies the union of actual scans.
                for radius in (0, 999.99, 1000.01, 1400, 1800):
                    for k in range(360):
                        p = (radius*math.cos(k*math.pi/180), radius*math.sin(k*math.pi/180))
                        assert min(distance(p, q) for q in solver.scan_positions) <= 1000+1e-6
        records.append(row)
    for error in (-1., 1.):
        for seed in range(1200, 1230):
            arena = Arena(seed, extreme=error)
            solver = SectorSolver(arena, emit=lambda _: None)
            solver.solve()
            assert not arena.remaining and solver.summary()['completed']
    # Explicitly force the original full strip fallback for every discovered source.
    class Invalid(SectorSolver):
        def region(self, ch):
            return []
    arena = Arena(1234)
    solver = Invalid(arena, emit=lambda _: None)
    solver.solve()
    assert not arena.remaining and solver.fallback_calls == len(arena.sources)
    class Rejected:
        virtual = 0.; position = (0., 0.); counts = {}
        def call(self, *args):
            raise RuntimeError('rejected')
    solver = SectorSolver(Rejected(), emit=lambda _: None)
    try:
        solver.solve()
    except RuntimeError:
        pass
    else:
        raise AssertionError('rejection swallowed')
    assert not solver.summary()['completed'] and solver.scanned == 0
    result = {
        'kind': 'offline_synthetic_not_official',
        'paired_cases': len(records),
        'sources': sum(r['sources'] for r in records),
        'baseline_mean_s_per_source': sum(r['baseline'] for r in records)/len(records),
        'fast_mean_s_per_source': sum(r['fast'] for r in records)/len(records),
        'faster_cases': sum(r['fast'] < r['baseline'] for r in records),
        'fast_under_200_cases': sum(r['fast'] < 200 for r in records),
        'fast_min_s_per_source': min(r['fast'] for r in records),
        'fast_max_s_per_source': max(r['fast'] for r in records),
        'extreme_error_cases': 60,
        'records': records,
    }
    path = Path(__file__).resolve().parent/'results'/'fast_vs_baseline.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}, ensure_ascii=False, indent=2))
    print('全部覆盖、清除、误差边界、完整兜底、拒绝动作检查通过。')


if __name__ == '__main__':
    run()
