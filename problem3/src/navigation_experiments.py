"""离线探索候选，未用于比赛默认入口。"""
from fast_solver import SectorSolver
from reliable_core import distance, batch_order, two_leg_clear_point

class SmoothSectorSolver(SectorSolver):
    """联合优化访问次序与可移动扫描点，保留原规划作为候选。"""
    def plan_tasks(self, centers):
        scans, nodes, order = super().plan_tasks(centers)
        scale = 999.9/19.9
        def length(points, route):
            prev = self.client.position
            total = 0.
            for index in route:
                total += distance(prev, points[index])
                prev = points[index]
            return total
        best = length(nodes, order)
        for _ in range(2):
            candidate = list(nodes)
            for j, index in enumerate(order):
                if index >= len(scans):
                    continue
                before = candidate[order[j-1]] if j else self.client.position
                after = candidate[order[j+1]] if j+1 < len(order) else None
                poly = self.sectors[index]
                q, _, _ = two_leg_clear_point(
                    [(x/scale, y/scale) for x, y in poly],
                    tuple(x/scale for x in before),
                    tuple(x/scale for x in after) if after is not None else None,
                    tolerance=.01, max_iterations=20)
                if q is None:
                    continue
                q = tuple(x*scale for x in q)
                old = distance(before, candidate[index]) + (distance(candidate[index], after) if after else 0.)
                new = distance(before, q) + (distance(q, after) if after else 0.)
                if new <= old and all(distance(q, v)<=999.9+1e-7 for v in poly):
                    candidate[index] = q
            proposed, _, _ = batch_order(self.client.position, candidate, candidate, None)
            # Heuristic reordering may be worse; retain the old order in that case.
            if length(candidate, order) < length(candidate, proposed):
                proposed = order
            cost = length(candidate, proposed)
            if cost >= best-1e-7:
                break
            nodes, order, best = candidate, proposed, cost
        return nodes[:len(scans)], nodes, order

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-sector-v3'
        return r


class RouteSectorSolver(SectorSolver):
    """对较大任务集合用多个起始候选改善开放路线。"""
    def plan_tasks(self, centers):
        scans, nodes, original = super().plan_tasks(centers)
        n = len(nodes)
        if n <= 9:
            return scans, nodes, original
        ds = [[distance(a,b) for b in nodes] for a in nodes]
        start = [distance(self.client.position, p) for p in nodes]
        def cost(order):
            return start[order[0]]+sum(ds[a][b] for a,b in zip(order, order[1:]))
        best, best_cost = original, cost(original)
        for first in range(n):
            route = [first]
            left = set(range(n))-{first}
            while left:
                nxt = min(left, key=lambda k: ds[route[-1]][k])
                route.append(nxt); left.remove(nxt)
            current = cost(route)
            for _ in range(12):
                chosen, value = route, current
                for i in range(n):
                    for j in range(i+1,n):
                        candidate = route[:i]+route[i:j+1][::-1]+route[j+1:]
                        c = cost(candidate)
                        if c < value-1e-7:
                            chosen, value = candidate, c
                if value >= current-1e-7:
                    break
                route, current = chosen, value
            if current < best_cost:
                best, best_cost = route, current
        return scans, nodes, best

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-route-v3'
        return r
