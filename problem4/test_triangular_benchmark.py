"""Paired synthetic coverage benchmark; no official simulator requests."""
import argparse
import json
import math
from pathlib import Path
from test_reliable_benchmark import Arena,m


def run():
    points=set(m.triangle_scan_points(950.))
    assert len(points)==31
    h=950.*math.sqrt(3.)/2
    def vertex(i,j):
        return (950.*(i+j/2.),h*j)
    for r in (0.,5.,650.,1000.,1799.999,1800.):
        for angle in range(720):
            a=math.radians(angle/2)
            x,y=r*math.cos(a),r*math.sin(a)
            beta=y/h; alpha=x/950.-beta/2
            i,j=math.floor(alpha),math.floor(beta)
            corners=[vertex(i,j),vertex(i+1,j),vertex(i,j+1)] if alpha-i+beta-j<=1 else [vertex(i+1,j),vertex(i+1,j+1),vertex(i,j+1)]
            assert set(corners)<=points,(x,y,corners)
            assert all(math.dist((x,y),p)<=950.+1e-8 for p in corners)
    records=[]
    for seed in range(130):
        pair=dict(seed=seed,group="development" if seed<30 else "held_out")
        for label,cls in (("v3",m.CompactSolver),("v4",m.TriangularSolver)):
            arena=Arena(seed)
            solver=cls(arena,emit=lambda _:None)
            solver.solve()
            assert not arena.remaining,(seed,label)
            assert solver.summary()["completed"]
            assert arena.virtual<360000
            pair[label]=dict(total=len(arena.sources),time=arena.virtual,**arena.counts)
        records.append(pair)
    groups={}
    for group in ("development","held_out"):
        subset=[r for r in records if r["group"]==group]
        groups[group]=dict(cases=len(subset),sources=sum(r["v3"]["total"] for r in subset),
                          faster_cases=sum(r["v4"]["time"]<r["v3"]["time"] for r in subset),
                          mean_time_s={v:sum(r[v]["time"] for r in subset)/len(subset) for v in ("v3","v4")},
                          worst_time_ratio=max(r["v4"]["time"]/r["v3"]["time"] for r in subset))
    print(json.dumps(groups,indent=2))
    return dict(label="SYNTHETIC ONLY; V4 official simulator results pending",groups=groups,results=records)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output")
    args=parser.parse_args()
    result=run()
    if args.output:
        Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8")

