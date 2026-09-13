"""全向专用：可移动分区覆盖、联合路线与有限步清除兜底。"""
import math
from main_problem3_reliable import Solver
from reliable_core import distance, covering_circle, batch_order, initial_region, clip, nearest_safe_clear_point


class FastSolver(Solver):
    def __init__(self, client, emit=print):
        super().__init__(client, emit)
        self.speculative_attempts = 0

    def estimate(self, channel):
        poly = self.region(channel)
        if not poly:
            return None
        center, _ = covering_circle(poly)
        aa = ab = bb = ac = bc = 0.
        for point, angle in self.observations[channel]:
            angle = math.radians(angle)
            a, b = -math.sin(angle), math.cos(angle)
            c = a*point[0]+b*point[1]
            aa += a*a; ab += a*b; bb += b*b; ac += a*c; bc += b*c
        det = aa*bb-ab*ab
        if det <= 1e-8:
            return center
        q = ((ac*bb-bc*ab)/det, (bc*aa-ac*ab)/det)
        # Least squares is a navigation estimate only; project onto feasible polygon.
        inside = all((b[0]-a[0])*(q[1]-a[1])-(b[1]-a[1])*(q[0]-a[0]) >= -1e-7
                     for a, b in zip(poly, poly[1:]+poly[:1]))
        if inside:
            return q
        candidates = []
        for a, b in zip(poly, poly[1:]+poly[:1]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            t = max(0., min(1., ((q[0]-a[0])*dx+(q[1]-a[1])*dy)/max(dx*dx+dy*dy, 1e-20)))
            candidates.append((a[0]+t*dx, a[1]+t*dy))
        return min(candidates, key=lambda p: distance(p, q))

    def clear_target(self, channel, continuation):
        tried = set()
        for _ in range(3):
            poly = self.region(channel)
            if not poly:
                break
            outcome = self.safe_clear(channel, poly, continuation)
            if outcome is True:
                return
            if outcome is False:
                break
            q = self.estimate(channel)
            key = tuple(round(x, 5) for x in q)
            if key in tried:
                break
            tried.add(key)
            if len(self.observations[channel]) >= 2:
                self.speculative_attempts += 1
                if self.clear(q, channel):
                    return
            else:
                # A lateral baseline avoids approaching on the same bearing line.
                q = self.single_probe(q, channel, continuation)
            result = self.client.call('/measure', q, channel)
            if result['measure_result'] == 'near':
                if self.clear(q, channel):
                    return
                raise RuntimeError('near后清除失败，任务未完成')
            if result['measure_result'] == 'direction':
                self.observations[channel].append((q, result['svd_deg']))
        super().clear_target(channel, continuation)

    def single_probe(self, q, channel, continuation):
        a = math.radians(self.observations[channel][0][1])
        return (q[0]-80*math.sin(a), q[1]+80*math.cos(a))

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-fast-v2'
        r['speculative_attempts'] = self.speculative_attempts
        return r


class SectorSolver(FastSolver):
    """原点加六个可移动覆盖任务；外包扇区顶点给出覆盖证书。"""
    def __init__(self, client, emit=print):
        super().__init__(client, emit)
        self.sectors = []
        for k in range(6):
            a = k*math.pi/3
            lo, hi = a-math.pi/6, a+math.pi/6
            p = clip(initial_region(), (math.sin(lo), -math.cos(lo)), 0.)
            p = clip(p, (-math.sin(hi), math.cos(hi)), 0.)
            p = clip(p, (-math.cos(a), -math.sin(a)), -1000*math.cos(math.pi/6))
            self.sectors.append(p)
        self.scan_positions = []
        self.absence = {}

    def scan_at(self, point):
        for ch in range(1, 21):
            if ch in self.cleared:
                continue
            if ch in self.observations and not self.should_measure_known(ch, point):
                continue
            r = self.client.call('/measure', point, ch)
            if r['measure_result'] == 'no_signal':
                self.absence.setdefault(ch, []).append(point)
                continue
            self.observations.setdefault(ch, [])
            if r['measure_result'] == 'near':
                if not self.clear(point, ch):
                    raise RuntimeError('near后清除失败')
            else:
                self.observations[ch].append((point, r['svd_deg']))
        self.scan_positions.append(point)
        self.scanned += 1
        self.sectors = [p for p in self.sectors if not all(distance(v, point)<=999.9+1e-7 for v in p)]
        self.emit('联合扫描%d次，剩余覆盖分区%d个；发现%d个，清除%d个' %
                  (self.scanned, len(self.sectors), len(self.observations), len(self.cleared)))

    def should_measure_known(self, channel, point):
        return True

    def solve(self):
        began = self.client.virtual
        self.scan_at((0., 0.))
        while self.sectors or self.observations.keys()-self.cleared:
            pending = sorted(self.observations.keys()-self.cleared)
            centers = [self.estimate(ch) or self.observations[ch][0][0] for ch in pending]
            scanpoints, nodes, order = self.plan_tasks(centers)
            index = order[0]
            if index < len(scanpoints):
                self.scan_at(scanpoints[index])
            else:
                self.clear_target(pending[index-len(scanpoints)], nodes[order[1]] if len(order)>1 else None)
                if any(all(distance(v, self.client.position)<=999.9 for v in p) for p in self.sectors):
                    self.scan_at(self.client.position)
        self.coverage_complete = True
        self.phase_times['integrated_s'] = self.client.virtual-began
        if not 10 <= len(self.cleared) <= 16:
            raise RuntimeError('源数不符合题目范围，未确认完成')
        self.completion_reason = '原点与六个环域分区全部取得覆盖证书，所有发现目标清除成功'

    def plan_tasks(self, centers):
        scanpoints = [nearest_safe_clear_point(p, self.client.position, radius=999.9) for p in self.sectors]
        if any(p is None for p in scanpoints):
            raise RuntimeError('覆盖位置求解失败，未确认完成')
        nodes = scanpoints + centers
        order, _, _ = batch_order(self.client.position, nodes, nodes, None)
        return scanpoints, nodes, order

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-sector-v2'
        r['scan_points'] = self.scanned
        r['scan_positions'] = self.scan_positions
        r['uncovered_sectors'] = len(self.sectors)
        return r




class EfficientSectorSolver(SectorSolver):
    """利用全向无信号约束改善单点导航，选择顺路的侧向补测。"""
    def single_probe(self, q, channel, continuation):
        a = math.radians(self.observations[channel][0][1])
        points = [(q[0]+sign*80*math.sin(a), q[1]-sign*80*math.cos(a)) for sign in (-1, 1)]
        return min(points, key=lambda p: distance(self.client.position, p)
                   + (distance(p, continuation) if continuation is not None else 0.))

    def estimate(self, channel):
        estimate = super().estimate(channel)
        if estimate is None or len(self.observations[channel]) != 1 or not self.absence.get(channel):
            return estimate
        anchor, angle = self.observations[channel][0]
        a = math.radians(angle)
        e = (math.cos(a), math.sin(a))
        poly = self.region(channel)
        values = [(v[0]-anchor[0])*e[0]+(v[1]-anchor[1])*e[1] for v in poly]
        intervals = [(max(0., min(values)), min(1500., max(values)))]
        # The entire error strip lies within w of its projected centerline.
        radius = 1000.-1500.*math.sin(math.radians(1.005))-1e-6
        for p in self.absence[channel]:
            dx, dy = p[0]-anchor[0], p[1]-anchor[1]
            along = dx*e[0]+dy*e[1]
            side = dx*e[1]-dy*e[0]
            if abs(side) >= radius:
                continue
            half = math.sqrt(radius*radius-side*side)
            lo, hi = along-half, along+half
            updated = []
            for left, right in intervals:
                if hi <= left or lo >= right:
                    updated.append((left, right))
                else:
                    if left < lo: updated.append((left, lo))
                    if right > hi: updated.append((hi, right))
            intervals = updated
        if not intervals:
            return estimate  # Navigation only; never invalidate the reliable region.
        left, right = max(intervals, key=lambda ab: ab[1]-ab[0])
        t = (left+right)/2
        return (anchor[0]+t*e[0], anchor[1]+t*e[1])

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-sector-v3'
        return r
