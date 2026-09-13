"""V3冻结候选的独立留出验证，全部为人工场景，不连接官方接口。"""
import json
import sys
from pathlib import Path
from test_reliable_problem3 import Arena
from fast_solver import SectorSolver, EfficientSectorSolver
from reliable_core import distance

def quick_checks():
    for seed in (3000, 3001, 3002):
        arena = Arena(seed)
        solver = EfficientSectorSolver(arena, emit=lambda _: None)
        solver.solve()
        assert not arena.remaining and solver.summary()['completed']
    print('V3导航候选三场自检通过。')

def checks():
    for error in (-1., 1.):
        for seed in range(3300, 3330):
            arena = Arena(seed, extreme=error)
            solver = EfficientSectorSolver(arena, emit=lambda _: None)
            solver.solve()
            assert not arena.remaining and solver.summary()['completed']
            for source, _ in arena.sources.values():
                assert min(distance(source, p) for p in solver.scan_positions) <= 1000+1e-6
    class Invalid(EfficientSectorSolver):
        def region(self, ch): return []
    arena = Arena(3400)
    solver = Invalid(arena, emit=lambda _: None)
    solver.solve()
    assert not arena.remaining and solver.fallback_calls == len(arena.sources)

def run():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for seed in range(3000, 3200):
        row = {'seed': seed}
        for name, cls in [('v2', SectorSolver), ('v3', EfficientSectorSolver)]:
            arena = Arena(seed)
            solver = cls(arena, emit=lambda _: None)
            solver.solve()
            assert not arena.remaining and solver.summary()['completed']
            row['sources'] = len(arena.sources)
            row[name] = arena.virtual/len(arena.sources)
        rows.append(row)
    checks()
    result = {'kind': 'offline_synthetic_not_official', 'cases': len(rows),
              'sources': sum(r['sources'] for r in rows),
              'v2_mean': sum(r['v2'] for r in rows)/len(rows),
              'v3_mean': sum(r['v3'] for r in rows)/len(rows),
              'faster_cases': sum(r['v3']<r['v2'] for r in rows),
              'worst_ratio': max(r['v3']/r['v2'] for r in rows),
              'extreme_error_cases': 60, 'rows': rows}
    path = Path(__file__).resolve().parent/'results'/'sector_v3_holdout.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}, ensure_ascii=False, indent=2))

if __name__ == '__main__': run()
