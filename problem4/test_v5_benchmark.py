"""Offline V5 proofs, geometry regression and paired synthetic runs. No HTTP."""
import argparse
import json
import math
from pathlib import Path
from test_reliable_benchmark import Arena, m


def geometry_tests():
    path=m.ring_scan_path()
    assert len(set(path))==25
    tree={0}; lower=0.
    while len(tree)<25:
        d,j=min((math.dist(path[i],path[j]),j) for i in tree for j in range(25) if j not in tree)
        tree.add(j); lower+=d
    length=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
    assert abs(length-lower)<1e-7
    inside=path[1:13]
    outer=path[14:]+[path[13]]
    triangles=[]
    for k in range(12):
        j=(k+1)%12
        triangles.extend([[(0.,0.),inside[k],inside[j]],[inside[k],inside[j],outer[k]],[outer[k],outer[j],inside[j]]])
    assert max(math.dist(a,b) for t in triangles for a in t for b in t)<1000
    def contains(t,p):
        cross=[(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) for a,b in zip(t,t[1:]+t[:1])]
        return min(cross)>=-1e-6 or max(cross)<=1e-6
    for r in (0.,965.,1799.999,1800.):
        for k in range(720):
            a=math.pi*k/360;p=(r*math.cos(a),r*math.sin(a))
            assert any(contains(t,p) for t in triangles)
    R=19.9
    cases=[([(0.,0.)],(30.,0.),(R,0.)),
           ([(-10.,0.),(10.,0.)],(0.,50.),(0.,math.sqrt(R*R-100))),
           ([(-5.,-5.),(-5.,5.),(5.,5.),(5.,-5.)],(40.,0.),(math.sqrt(R*R-25)-5,0.))]
    for poly,p,expected in cases:
        q=m.nearest_safe_clear_point(poly,p)
        assert q is not None and math.dist(q,expected)<1e-6,(q,expected)
        assert max(math.dist(q,v) for v in poly)<20
    assert m.nearest_safe_clear_point([(0.,0.),(50.,0.)],(0.,0.)) is None
    assert m.nearest_safe_clear_point([(-5.,0.),(5.,0.)],(0.,0.))==(0.,0.)
    w=1500*math.sin(math.radians(m.ANGLE_ERROR))
    for angle in (0.,45.,180.,359.99):
        anchor=(125.,-99.);a=math.radians(angle)
        points=list(m.two_lane_points(anchor,angle))
        assert len(points)==102
        for x in (0.,15.,750.,1485.,1500.):
            for y in (-w,0.,w):
                p=(anchor[0]+x*math.cos(a)-y*math.sin(a),anchor[1]+x*math.sin(a)+y*math.cos(a))
                assert min(math.dist(p,q) for q in points)<20
    print("离线几何检查通过：25点覆盖、最短扫描路、最近安全点、102点兜底。")


def run():
    geometry_tests()
    rows=[]
    for seed in range(130):
        pair=dict(seed=seed,group="development" if seed<30 else "held_out")
        for label,cls in (("v4",m.TriangularSolver),("v5",m.RingSolver)):
            arena=Arena(seed)
            solver=cls(arena,emit=lambda _:None)
            solver.solve()
            assert not arena.remaining,(seed,label,arena.remaining)
            assert solver.summary()["completed"]
            assert arena.virtual<360000
            pair[label]=dict(total=len(arena.sources),time=arena.virtual,**arena.counts)
            if label=="v5" and seed==0:
                output=m.chinese_summary(solver.summary())
                assert "平均定位清除时间" in output and "成功清除个数" in output
        rows.append(pair)
    groups={}
    for group in ("development","held_out"):
        sub=[r for r in rows if r["group"]==group]
        groups[group]=dict(cases=len(sub),sources=sum(r["v5"]["total"] for r in sub),
                          faster_cases=sum(r["v5"]["time"]<r["v4"]["time"] for r in sub),
                          mean_time_s={v:sum(r[v]["time"] for r in sub)/len(sub) for v in ("v4","v5")},
                          worst_time_ratio=max(r["v5"]["time"]/r["v4"]["time"] for r in sub))
    print(json.dumps(groups,ensure_ascii=False,indent=2))
    return dict(label="人工场景，不是模拟器实测",groups=groups,results=rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output")
    args=parser.parse_args()
    result=run()
    if args.output:
        Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

