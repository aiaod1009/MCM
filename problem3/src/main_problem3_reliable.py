"""问题3：全向覆盖、保守交会与完整清除。纯Python，无问题4运行依赖。"""
import argparse
import json
import math
from pathlib import Path
import sys
import time
from reliable_core import (
    PublicClient, initial_region, add_bearing, covering_circle,
    distance, two_leg_clear_point, batch_order, feasible_strip_points,
)

def scan_path(ring_count=8):
    if ring_count not in (6, 8):
        raise ValueError("只支持已验证的7点或9点布局")
    return [(0.,0.)]+[(1200*math.cos(2*math.pi*k/ring_count),
                       1200*math.sin(2*math.pi*k/ring_count))
                      for k in range(ring_count)]

class Solver:
    def __init__(self, client, emit=print, ring_count=8):
        self.client, self.emit = client, emit
        self.points = scan_path(ring_count)
        self.observations = {}
        self.cleared = set()
        self.scanned = 0
        self.coverage_complete = False
        self.fallback_calls = 0
        self.pruned = 0
        self.max_gap = 0.
        self.phase_times = {}
        self.completion_reason = "未完成"

    def clear(self, point, channel):
        result = self.client.call("/clear",point,channel)
        if result["clear_result"]=="success":
            self.cleared.add(channel)
            self.emit("清除成功：频道%d；累计%d个；虚拟时间%.3f秒" %
                      (channel,len(self.cleared),self.client.virtual))
            return True
        return False

    def region(self, channel):
        poly=initial_region()
        for point,angle in self.observations[channel]:
            poly=add_bearing(poly,point,angle)
            if not poly:
                return []
        return poly

    def safe_clear(self, channel, poly, continuation):
        if not poly:
            return None
        point,gap,_=two_leg_clear_point(poly,self.client.position,continuation)
        if point is None:
            return None
        self.max_gap=max(self.max_gap,gap)
        return self.clear(point,channel)

    def clear_target(self, channel, continuation):
        observations=self.observations[channel]
        anchor,angle=observations[0]
        poly=self.region(channel)
        valid=bool(poly)
        visited={tuple(round(v,6) for v in p) for p,_ in observations}
        last_signal=observations[-1][0]
        opposite=None
        for _ in range(6):
            if not valid:
                break
            outcome=self.safe_clear(channel,poly,continuation)
            if outcome is True:
                return
            if outcome is False:
                valid=False
                self.emit("安全位置清除未成功，恢复首条示向度完整条带。")
                break
            if opposite is not None:
                point,opposite=opposite,None
            else:
                center,radius=covering_circle(poly)
                dx,dy=center[0]-last_signal[0],center[1]-last_signal[1]
                length=math.hypot(dx,dy)
                a=math.radians(angle)
                e=(dx/length,dy/length) if length>1e-8 else (math.cos(a),math.sin(a))
                v=(-e[1],e[0])
                b=min(250.,max(30.,radius/2))
                point=tuple(center[k]-b*e[k]+b*v[k] for k in (0,1))
                opposite=tuple(center[k]-b*e[k]-b*v[k] for k in (0,1))
            key=tuple(round(v,6) for v in point)
            if key in visited:
                continue
            visited.add(key)
            result=self.client.call("/measure",point,channel)
            kind=result["measure_result"]
            if kind=="near":
                if self.clear(point,channel):
                    return
                raise RuntimeError("near后清除失败；保留未完成状态")
            if kind=="direction":
                observations.append((point,result["svd_deg"]))
                last_signal,opposite=point,None
                poly=add_bearing(poly,point,result["svd_deg"])
                valid=bool(poly)
                if not valid:
                    self.emit("共同可行域为空；恢复首条示向度完整条带。")
        # The last observation in the loop must also get a clearance check.
        if valid:
            outcome=self.safe_clear(channel,poly,continuation)
            if outcome is True:
                return
            if outcome is False:
                valid=False
        self.fallback_calls+=1
        points=feasible_strip_points(anchor,angle,poly if valid else None)
        self.pruned+=102-len(points)
        self.emit("频道%d：条带兜底保留%d/102点，无信号不阻止光学清除。" % (channel,len(points)))
        for point in points:
            if self.clear(point,channel):
                return
        raise RuntimeError("条带执行后仍未成功；保留目标并报告未完成")

    def solve(self):
        start=self.client.virtual
        self.emit("阶段1：%d点全向覆盖，每点检测所有未清除频道。" % len(self.points))
        for index,point in enumerate(self.points,1):
            self.emit("覆盖点%d/%d：(%.3f, %.3f)" % (index,len(self.points),*point))
            for channel in range(1,21):
                if channel in self.cleared:
                    continue
                result=self.client.call("/measure",point,channel)
                kind=result["measure_result"]
                if kind=="no_signal":
                    continue
                self.observations.setdefault(channel,[])
                if kind=="near":
                    if not self.clear(point,channel):
                        raise RuntimeError("near后清除失败；保留目标")
                else:
                    self.observations[channel].append((point,result["svd_deg"]))
            self.scanned+=1  # Only fully accepted coverage points count.
        self.coverage_complete=True
        self.phase_times["scan_s"]=self.client.virtual-start
        self.emit("阶段2：全部有效示向度共同交会，保留单点与异常目标。")
        for ch in sorted(self.observations.keys()-self.cleared):
            circle=covering_circle(self.region(ch))
            self.emit("频道%d：有效测向%d次；%s" % (
                ch,len(self.observations[ch]),
                "保守覆盖半径%.3f米"%circle[1] if circle else "几何异常，保留完整兜底"))
        self.emit("阶段3：滚动路径规划与安全清除。")
        start=self.client.virtual
        while self.observations.keys()-self.cleared:
            pending=sorted(self.observations.keys()-self.cleared)
            centers=[]
            for ch in pending:
                circle=covering_circle(self.region(ch))
                centers.append(circle[0] if circle else self.observations[ch][0][0])
            order,_,_=batch_order(self.client.position,centers,centers,None)
            continuation=centers[order[1]] if len(order)>1 else None
            self.clear_target(pending[order[0]],continuation)
        self.phase_times["clear_s"]=self.client.virtual-start
        if not 10<=len(self.cleared)<=16:
            raise RuntimeError("成功源数不符合题目10至16个范围，不能确认任务完成")
        self.completion_reason="全部覆盖点完成且所有已发现频道清除成功"

    def summary(self):
        found=set(self.observations)
        unresolved=found-self.cleared
        completed=self.coverage_complete and not unresolved and 10<=len(self.cleared)<=16
        return dict(algorithm_version="problem3-reliable-v1",
                    scan_points=len(self.points),scanned_points=self.scanned,
                    discovered_channels=sorted(found),cleared_channels=sorted(self.cleared),
                    unresolved_channels=sorted(unresolved),completed=completed,
                    coverage_complete=self.coverage_complete,
                    completion_reason=self.completion_reason,
                    total_virtual_time_s=self.client.virtual,
                    average_location_clear_time_s=self.client.virtual/len(self.cleared) if self.cleared else None,
                    actual_total=None,official_clearance_ratio=None,
                    actions=self.client.counts,phase_times=self.phase_times,
                    fallback_calls=self.fallback_calls,fallback_points_pruned=self.pruned,
                    max_local_numeric_gap_m=self.max_gap)

def chinese_summary(r):
    average=r["average_location_clear_time_s"]
    lines=["="*60,"问题3最终统计","算法版本："+r["algorithm_version"],
           "扫描布局：%d点；已完成%d点"%(r["scan_points"],r["scanned_points"]),
           "已发现个数：%d"%len(r["discovered_channels"]),
           "成功清除个数：%d"%len(r["cleared_channels"]),
           "已发现未清除个数：%d"%len(r["unresolved_channels"]),
           "总虚拟时间：%.3f秒"%r["total_virtual_time_s"],
           "平均定位清除时间："+("%.3f秒/个"%average if average is not None else "无成功目标，无法计算"),
           "条带兜底目标数：%d；剔除候选点数：%d"%(r["fallback_calls"],r["fallback_points_pruned"]),
           "完成状态："+("已完成" if r["completed"] and not r.get("error") else "未完成"),
           "结束依据："+r["completion_reason"],
           "实际总数、发现率、官方清除比例：请依据测试界面总数核算"]
    for key,label in (("measures","检测次数"),("switches","频道切换次数"),
                      ("clear_attempts","光学尝试次数"),("clear_successes","光学成功次数")):
        lines.append("%s：%d"%(label,r["actions"].get(key,0)))
    if r.get("error"):
        lines.append("异常信息："+r["error"])
    return "\n".join(lines)

def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):
            stream.reconfigure(encoding="utf-8",errors="backslashreplace")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robot-id",default="202619020062")
    parser.add_argument("--url",default="http://127.0.0.1:2026")
    parser.add_argument("--scan-points",type=int,choices=(7,9),default=9)
    parser.add_argument("--strategy",choices=("fast","v2","v3","baseline"),default="fast",
                        help="fast/v2为已实测V2；v3为导航优化候选；baseline为原9点可靠版")
    parser.add_argument("--self-test",action="store_true",help="离线自检，不连接模拟器")
    args=parser.parse_args()
    if args.self_test:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from test_reliable_problem3 import checks
        checks()
        from test_fast_problem3 import quick_checks
        quick_checks()
        from test_sector_v3 import quick_checks as v3_checks
        v3_checks()
        return 0
    root=Path(__file__).resolve().parents[1]
    folder=root/"test_logs";folder.mkdir(exist_ok=True)
    stamp=time.strftime("%Y%m%d_%H%M%S")
    log_path=folder/f"test_log_reliable_{stamp}.txt"
    with log_path.open("w",encoding="utf-8") as log, (folder/f"actions_reliable_{stamp}.jsonl").open("w",encoding="utf-8") as actions:
        def emit(text):
            print(text,flush=True);log.write(text+"\n");log.flush()
        client=PublicClient(args.url,args.robot_id,actions)
        if args.strategy in ("fast", "v2"):
            from fast_solver import SectorSolver
            solver=SectorSolver(client,emit)
        elif args.strategy == "v3":
            from fast_solver import EfficientSectorSolver
            solver=EfficientSectorSolver(client,emit)
        else:
            solver=Solver(client,emit,ring_count=args.scan_points-1)
        emit("本次运行算法："+solver.summary()["algorithm_version"])
        emit("所选策略："+args.strategy+"；平均定位清除时间包含全部搜索与移动耗时。")
        entered=False;error=None;exit_error=None;began=time.monotonic()
        try:
            client.call("/enter");entered=True;began=time.monotonic()
            solver.solve()
        except Exception as exc:
            error=str(exc)
        finally:
            if entered:
                try:client.call("/exit")
                except Exception as exc:exit_error=str(exc)
            result=solver.summary()
            result.update(error=error,exit_error=exit_error,program_runtime_s=time.monotonic()-began)
            if error or exit_error:
                result["completed"]=False
                if not error:result["error"]="退出未确认："+exit_error
            (folder/f"summary_reliable_{stamp}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
            emit(chinese_summary(result))
            emit("程序运行时间：%.3f秒"%result["program_runtime_s"])
            client.session.close()
    print("日志已保存到："+str(log_path))
    return 0 if result["completed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
