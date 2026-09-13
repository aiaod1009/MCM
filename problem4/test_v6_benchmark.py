"""Offline joint-planning regression and synthetic paired V5/V6 benchmark."""
import argparse
import itertools
import json
import math
from pathlib import Path
from test_reliable_benchmark import Arena,m


def checks():
    entries=[(1.,2.),(4.,0.),(-3.,1.),(2.,-4.)]
    exits=[(2.,3.),(5.,1.),(-2.,2.),(3.,-3.)]
    start=(0.,0.);end=(10.,10.)
    def route_cost(order,entries,exits,end):
        return m.distance(start,entries[order[0]])+sum(m.distance(exits[a],entries[b]) for a,b in zip(order,order[1:]))+(m.distance(exits[order[-1]],end) if end else 0.)
    for terminal in (end,None):
        order,gap,exact=m.batch_order(start,entries,exits,terminal)
        assert exact and gap==0
        assert abs(route_cost(order,entries,exits,terminal)-min(route_cost(p,entries,exits,terminal) for p in itertools.permutations(range(4))))<1e-8
    many=[(math.cos(i)*100,math.sin(i)*100) for i in range(12)]
    order,gap,exact=m.batch_order(start,many,many,end)
    assert not exact and len(set(order))==12 and gap>=0
    q,gap,saving=m.two_leg_clear_point([(0.,0.)],(40.,0.),(0.,40.))
    optimum=(19.9/math.sqrt(2),)*2
    f=lambda p:m.distance(p,(40.,0.))+m.distance(p,(0.,40.))
    assert q and f(q)-f(optimum)<=gap+1e-6
    assert gap<=.1 and saving>0
    for k in range(40):
        poly=[(-4.,-3.),(4.,-3.),(4.,3.),(-4.,3.)]
        start=(50*math.cos(k),50*math.sin(k))
        end=(60*math.cos(k+.6),60*math.sin(k+.6))
        q,gap,saving=m.two_leg_clear_point(poly,start,end)
        old=m.nearest_safe_clear_point(poly,start)
        assert max(m.distance(q,v) for v in poly)<20
        assert m.distance(start,q)+m.distance(q,end)<=m.distance(start,old)+m.distance(old,end)+1e-8
    assert m.two_leg_clear_point([(0.,0.),(50.,0.)],start,end)[0] is None
    print("离线检查通过：批次精确顺序、有限计算回退、安全清除位置与两段成本。")


def run():
    checks()
    rows=[]
    for seed in range(130):
        row=dict(seed=seed,group="development" if seed<30 else "held_out")
        for label,cls in (("v5",m.RingSolver),("v6",m.JointSolver)):
            arena=Arena(seed)
            solver=cls(arena,emit=lambda _:None)
            solver.solve()
            assert not arena.remaining,(seed,label)
            assert solver.summary()["completed"]
            assert arena.virtual<360000
            row[label]=dict(total=len(arena.sources),time=arena.virtual,**arena.counts)
            if label=="v6":
                row[label]["max_local_gap_m"]=solver.max_local_gap_m
        rows.append(row)
    groups={}
    for group in ("development","held_out"):
        sub=[r for r in rows if r["group"]==group]
        groups[group]=dict(cases=len(sub),sources=sum(r["v6"]["total"] for r in sub),
                          faster_cases=sum(r["v6"]["time"]<r["v5"]["time"] for r in sub),
                          mean_time_s={v:sum(r[v]["time"] for r in sub)/len(sub) for v in ("v5","v6")},
                          worst_time_ratio=max(r["v6"]["time"]/r["v5"]["time"] for r in sub),
                          max_local_numeric_gap_m=max(r["v6"]["max_local_gap_m"] for r in sub))
    print(json.dumps(groups,ensure_ascii=False,indent=2))
    return dict(label="人工场景，不是模拟器实测",groups=groups,results=rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output")
    args=parser.parse_args()
    result=run()
    if args.output:
        Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

