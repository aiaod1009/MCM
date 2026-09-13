"""V4候选：把扫描服务时间纳入滚动任务顺序优化。"""
from fast_solver import SectorSolver
from reliable_core import distance


class FinalSectorSolver(SectorSolver):
    def plan_tasks(self, centers):
        scans, nodes, route = super().plan_tasks(centers)
        n, ns = len(nodes), len(scans)
        if not ns or not centers:
            return scans, nodes, route
        ds = [[distance(a,b)/5 for b in nodes] for a in nodes]
        start = [distance(self.client.position, p)/5 for p in nodes]
        def cost(order):
            # Approximate switching at 1 s per measured channel; future unknown
            # sources and refinement costs are deliberately not invented.
            total = start[order[0]]
            cleared = len(self.cleared)
            for j, index in enumerate(order):
                if j: total += ds[order[j-1]][index]
                if index < ns:
                    total += 6*(20-cleared)
                else:
                    total += 5
                    cleared += 1
            return total
        current = cost(route)
        for _ in range(8):
            best, value = route, current
            for i in range(n):
                for j in range(n):
                    if i == j: continue
                    rest = route[:i]+route[i+1:]
                    candidate = rest[:j]+[route[i]]+rest[j:]
                    c = cost(candidate)
                    if c < value-1e-7: best, value = candidate, c
                    if i < j:
                        candidate = route[:i]+route[i:j+1][::-1]+route[j+1:]
                        c = cost(candidate)
                        if c < value-1e-7: best, value = candidate, c
            if value >= current-1e-7: break
            route, current = best, value
        return scans, nodes, route

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-service-v4'
        return r


class SelectiveSectorSolver(SectorSolver):
    def should_measure_known(self, channel, point):
        return len(self.observations[channel]) < 2

    def summary(self):
        r = super().summary()
        r['algorithm_version'] = 'problem3-selective-v4'
        return r
