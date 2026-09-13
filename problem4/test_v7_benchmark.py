"""V7 deterministic coverage checks and paired offline evaluation; no network."""
import argparse
import json
import math
from pathlib import Path
from test_reliable_benchmark import Arena, m

def checks():
    full=list(m.two_lane_points((0.,0.),0.))
    assert m.feasible_strip_points((0.,0.),0.,[])==full
    for angle in (0.,45.,179.99,359.99):
        anchor=(100.,-70.)
        original=list(m.two_lane_points(anchor,angle))
        a=math.radians(angle)
        for x in (0.,15.,750.,1499.,1500.):
            for y in (-26.309,0.,26.309):
                g=(anchor[0]+x*math.cos(a)-y*math.sin(a),
                   anchor[1]+x*math.sin(a)+y*math.cos(a))
                region=[(g[0]-1,g[1]-1),(g[0]+1,g[1]-1),
                        (g[0]+1,g[1]+1),(g[0]-1,g[1]+1)]
                kept=m.feasible_strip_points(anchor,angle,region)
                assert kept
                # Stronger than coverage: every formerly successful attempt remains.
                assert all(q in kept for q in original if m.distance(q,g)<=20.)
                assert min(m.distance(q,g) for q in kept)<20.
                assert [q for q in original if q in kept]==kept
    print("coverage and preservation checks PASS",flush=True)

def run(count):
    checks()
    rows=[]
    for seed in range(count):
        row=dict(seed=seed,group="development" if seed<30 else "validation")
        for name,cls in (("v6",m.JointSolver),("v7",m.FinalSolver)):
            arena=Arena(seed)
            solver=cls(arena,emit=lambda _:None)
            solver.solve()
            assert not arena.remaining,(seed,name)
            assert solver.summary()["completed"]
            row[name]=dict(total=len(arena.sources),time=arena.virtual,**arena.counts)
            if name=="v7":
                row[name]["pruned"]=solver.fallback_skipped
        rows.append(row)
        if seed%25==24: print("completed",seed+1,flush=True)
    groups={}
    for group in ("development","validation"):
        sub=[r for r in rows if r["group"]==group]
        if not sub: continue
        groups[group]=dict(cases=len(sub),sources=sum(r["v7"]["total"] for r in sub),
            mean_time_s={v:sum(r[v]["time"] for r in sub)/len(sub) for v in ("v6","v7")},
            faster=sum(r["v7"]["time"]<r["v6"]["time"]-1e-6 for r in sub),
            slower=sum(r["v7"]["time"]>r["v6"]["time"]+1e-6 for r in sub),
            worst_ratio=max(r["v7"]["time"]/r["v6"]["time"] for r in sub),
            pruned=sum(r["v7"]["pruned"] for r in sub))
    return dict(label="Synthetic paired evidence, not official results",groups=groups,rows=rows)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--cases",type=int,default=230)
    parser.add_argument("--output",default="results/v7_offline_benchmark.json")
    args=parser.parse_args()
    result=run(args.cases)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result["groups"],indent=2))