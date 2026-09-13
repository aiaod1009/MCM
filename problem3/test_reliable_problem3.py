"""Offline Q3 comparison of repaired 9-point and 7-point pipelines; no HTTP."""
import argparse
import json
import math
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
import main_problem3_reliable as m
from reliable_core import add_bearing, initial_region, distance, nearest_safe_clear_point

class Arena:
    def __init__(self,seed,extreme=None):
        rng=random.Random(seed)
        n=rng.randint(10,16)
        self.sources={}
        for ch in rng.sample(range(1,21),n):
            angle=rng.uniform(0,2*math.pi)
            r=1800 if seed%3==0 else 1800*math.sqrt(rng.random())
            self.sources[ch]=((r*math.cos(angle),r*math.sin(angle)),rng.choice((1000.,1250.,1500.)))
        self.remaining=set(self.sources)
        self.position=(0.,0.);self.channel=1;self.virtual=0.
        self.seed=seed;self.extreme=extreme
        self.counts=dict(measures=0,clear_attempts=0,clear_successes=0,switches=0,moves=0)
    def call(self,path,point,channel):
        d=distance(point,self.position)
        self.virtual+=d/5;self.counts["moves"]+=d>1e-9;self.position=point
        if path=="/clear":
            self.counts["clear_attempts"]+=1
            ok=channel in self.remaining and distance(point,self.sources[channel][0])<=20.
            self.virtual+=5 if ok else 3
            if ok:self.remaining.remove(channel);self.counts["clear_successes"]+=1
            return dict(clear_result="success" if ok else "no_target_in_range")
        self.counts["measures"]+=1;self.counts["switches"]+=channel!=self.channel
        self.virtual+=5+(channel!=self.channel);self.channel=channel
        if channel not in self.remaining:return dict(measure_result="no_signal")
        source,radius=self.sources[channel]
        d=distance(point,source)
        if d>radius:return dict(measure_result="no_signal")
        if d<=5:return dict(measure_result="near")
        error=self.extreme if self.extreme is not None else .999*math.sin(point[0]*.013+point[1]*.017+channel+self.seed)
        a=math.degrees(math.atan2(source[1]-point[1],source[0]-point[0]))
        return dict(measure_result="direction",svd_deg=round((a+error)%360,2)%360)

def checks():
    # Same-direction wedges must retain distant feasible locations.
    p=add_bearing(add_bearing(initial_region(),(0.,0.),0.),(100.,0.),0.)
    assert max(v[0] for v in p)>1500
    assert nearest_safe_clear_point(p,(100.,0.)) is None
    # A short source distance is feasible, not constrained to >=1000.
    p=add_bearing(initial_region(),(0.,0.),0.)
    for a,b in zip(p,p[1:]+p[:1]):
        assert (b[0]-a[0])*(-a[1])-(b[1]-a[1])*(100-a[0])>=-1e-5
    # Global all-bearing retention at bounded error endpoints.
    g=(500.,400.);p=initial_region()
    for s,err in (((0.,0.),1.005),((900.,0.),-1.005),((0.,900.),0.)):
        angle=math.degrees(math.atan2(g[1]-s[1],g[0]-s[0]))
        p=add_bearing(p,s,(angle+err)%360)
        assert p
        for a,b in zip(p,p[1:]+p[:1]):
            assert (b[0]-a[0])*(g[1]-a[1])-(b[1]-a[1])*(g[0]-a[0])>=-1e-5
    # Near-only channel is cleared and accounted without a bearing.
    a=Arena(0);a.sources={1:((0.,0.),1000.)};a.remaining={1}
    s=m.Solver(a,emit=lambda _:None)
    try:s.solve()
    except RuntimeError as exc:
        assert len(s.cleared)==1
    assert s.cleared=={1} and set(s.observations)=={1}
    # Rejected coverage action cannot be marked complete.
    class Reject:
        virtual=0.;position=(0.,0.);counts={}
        def call(self,*args):raise RuntimeError("rejected")
    s=m.Solver(Reject(),emit=lambda _:None)
    try:s.solve()
    except RuntimeError:pass
    else:raise AssertionError("rejection swallowed")
    assert s.scanned==0 and not s.summary()["completed"]
    # Force empty-region handling: every found channel must still reach fallback.
    class Invalid(m.Solver):
        def region(self,ch):return []
    a=Arena(9);s=Invalid(a,emit=lambda _:None);s.solve()
    assert not a.remaining and s.fallback_calls==len(a.sources)
    protocol_checks()
    print("Geometry, near, rejected actions and full fallback checks PASS",flush=True)


def protocol_checks():
    import io
    import types
    from reliable_core import PublicClient
    client=PublicClient("http://unused.invalid","offline",io.StringIO())
    actual_session=client.session
    class Response:
        def __init__(self,body):self.body=body
        def raise_for_status(self):pass
        def json(self):return self.body
    class Transport:
        def __init__(self):self.payloads=[]
        def post(self,url,json,timeout):
            self.payloads.append(dict(json))
            if len(self.payloads)==1:
                raise client.requests.Timeout("synthetic transport uncertainty")
            return Response(dict(accepted=True,virtual_time_s=5,measure_result="near"))
    transport=Transport();client.session=transport
    response=client.call("/measure",(0.,0.),1)
    assert response["measure_result"]=="near"
    assert transport.payloads[0]==transport.payloads[1]
    assert client.counts["measures"]==1
    class Denied:
        def post(self,*args,**kwargs):return Response(dict(accepted=False))
    before=(client.position,client.virtual,dict(client.counts))
    client.session=Denied()
    try:client.call("/measure",(100.,0.),2)
    except RuntimeError:pass
    else:raise AssertionError("rejected action accepted")
    assert before==(client.position,client.virtual,client.counts)
    actual_session.close()
    print("Identical-ID retry and rejected-state checks PASS",flush=True)


def cli_checks():
    import contextlib
    import io
    import types
    saved_client,saved_file,saved_argv=m.PublicClient,m.__file__,sys.argv
    root=Path(__file__).resolve().parent/"results"/"offline_cli_checks"
    try:
        for mode in ("success","rejected","exit_failure"):
            folder=root/mode
            folder.mkdir(parents=True,exist_ok=True)
            class FakeClient(Arena):
                def __init__(self,url,robot_id,action_file):
                    super().__init__(0)
                    self.action_file=action_file
                    self.session=types.SimpleNamespace(close=lambda:None)
                def call(self,path,point=None,channel=None):
                    if path=="/enter":
                        return dict(accepted=True,virtual_time_s=0)
                    if path=="/exit":
                        if mode=="exit_failure":raise RuntimeError("synthetic exit rejection")
                        return dict(accepted=True,virtual_time_s=self.virtual)
                    if mode=="rejected":raise RuntimeError("synthetic measure rejection")
                    result=super().call(path,point,channel)
                    self.action_file.write(json.dumps(dict(synthetic=True,path=path,result=result))+"\n")
                    return result
            m.PublicClient=FakeClient
            m.__file__=str(folder/"src"/"main_problem3_reliable.py")
            sys.argv=["main_problem3.py"]
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status=m.main()
            summaries=list((folder/"test_logs").glob("summary_reliable_*.json"))
            r=json.loads(max(summaries,key=lambda p:p.stat().st_mtime).read_text(encoding="utf-8"))
            assert r["scan_points"]==9
            assert (status==0)==(mode=="success")
            assert r["completed"]==(mode=="success")
            assert len(output.getvalue().splitlines())>10
            if mode=="rejected":assert r["scanned_points"]==0
            if mode=="exit_failure":assert r["exit_error"]
    finally:
        m.PublicClient,m.__file__,sys.argv=saved_client,saved_file,saved_argv
    print("Full CLI lifecycle, Chinese logs and failure exit codes PASS",flush=True)

def run(cases):
    checks()
    cli_checks()
    rows=[]
    for seed in range(cases):
        row=dict(seed=seed,group="development" if seed<30 else "validation")
        for points in (9,7):
            a=Arena(seed);s=m.Solver(a,emit=lambda _:None,ring_count=points-1)
            s.solve();assert not a.remaining and s.summary()["completed"],(seed,points)
            row[str(points)]=dict(sources=len(a.sources),time=a.virtual,**a.counts,fallback=s.fallback_calls)
        rows.append(row)
        if seed%25==24:print("paired cases",seed+1,flush=True)
    groups={}
    for group in ("development","validation"):
        sub=[r for r in rows if r["group"]==group]
        if not sub:continue
        groups[group]=dict(cases=len(sub),sources=sum(r["7"]["sources"] for r in sub),
            mean_time_s={p:sum(r[p]["time"] for r in sub)/len(sub) for p in ("9","7")},
            faster=sum(r["7"]["time"]<r["9"]["time"] for r in sub),
            worst_ratio=max(r["7"]["time"]/r["9"]["time"] for r in sub))
    extremes=0
    for error in (-1.,0.,1.):
        for seed in range(130,140):
            a=Arena(seed,error);s=m.Solver(a,emit=lambda _:None,ring_count=6);s.solve()
            assert not a.remaining and s.summary()["completed"]
            extremes+=len(a.sources)
    return dict(label="Synthetic all-omnidirectional sources; NOT simulator results",
                baseline="Repaired 9-point solver, NOT historical legacy implementation",
                groups=groups,extreme_error_cases=30,extreme_error_sources=extremes,rows=rows)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--cases",type=int,default=130)
    p.add_argument("--output",default="results/reliable_7_vs_9.json")
    args=p.parse_args()
    r=run(args.cases)
    dest=Path(args.output);dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(r,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="rows"},indent=2))