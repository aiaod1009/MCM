"""导航候选同场景对照，不连接官方模拟器。"""
import json
import sys
from pathlib import Path
from test_reliable_problem3 import Arena
from fast_solver import SectorSolver, EfficientSectorSolver
from navigation_experiments import SmoothSectorSolver

def run():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for seed in range(2000, 2200):
        row = {'seed': seed}
        for name, cls in [('v2', SectorSolver), ('smooth', SmoothSectorSolver), ('range', EfficientSectorSolver)]:
            arena = Arena(seed)
            solver = cls(arena, emit=lambda _: None)
            solver.solve()
            assert not arena.remaining and solver.summary()['completed']
            row['sources'] = len(arena.sources)
            row[name] = arena.virtual/len(arena.sources)
        rows.append(row)
        if len(rows)%50 == 0:
            print('已完成%d/200组配对验证'%len(rows), flush=True)
    result = {'kind': 'offline_synthetic_not_official', 'cases': len(rows),
              'sources': sum(r['sources'] for r in rows), 'rows': rows}
    for name in ('v2', 'smooth', 'range'):
        result[name] = {'mean_s_per_source': sum(r[name] for r in rows)/len(rows),
                        'faster_than_v2': sum(r[name]<r['v2'] for r in rows),
                        'worst_case_ratio_to_v2': max(r[name]/r['v2'] for r in rows)}
    path = Path(__file__).resolve().parent/'results'/'navigation_candidates.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    run()
