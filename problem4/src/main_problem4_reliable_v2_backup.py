# -*- coding: utf-8 -*-
"""Q4: bounded-bearing localization and optically complete clearing.
Independent baseline; only the four public simulator endpoints are used.
Run --self-test without connecting to the simulator.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time
import uuid

ANGLE_ERROR = 1.005  # Physical +/-1 degree plus <=0.005 degree display rounding.
EPS = 1e-7  # metres; outward numerical tolerance, not a changed physical rule.


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clip(poly, normal, bound):
    """Intersect with n.x <= bound, retaining an outward numerical margin."""
    if not poly:
        return []
    bound += EPS
    result = []
    previous = poly[-1]
    dp = dot(normal, previous) - bound
    for current in poly:
        dc = dot(normal, current) - bound
        if (dp <= 0) != (dc <= 0):
            t = dp / (dp - dc)
            result.append(tuple(previous[k] + t * (current[k] - previous[k])
                                for k in (0, 1)))
        if dc <= 0:
            result.append(current)
        previous, dp = current, dc
    return result


def clip_disk_outer(poly, center, radius):
    """64 tangent halfplanes form an OUTER approximation of the disk."""
    for i in range(64):
        angle = 2 * math.pi * i / 64
        normal = (math.cos(angle), math.sin(angle))
        poly = clip(poly, normal, radius + dot(normal, center))
    return poly


def initial_region():
    return clip_disk_outer(
        [(-1800., -1800.), (1800., -1800.), (1800., 1800.), (-1800., 1800.)],
        (0., 0.), 1800.)


def add_bearing(poly, point, angle):
    lower = math.radians(angle - ANGLE_ERROR)
    upper = math.radians(angle + ANGLE_ERROR)
    for normal in ((math.sin(lower), -math.cos(lower)),
                   (-math.sin(upper), math.cos(upper))):
        poly = clip(poly, normal, dot(normal, point))
    return clip_disk_outer(poly, point, 1500.)


def covering_circle(poly):
    """A verified covering circle, deliberately not called a minimum circle."""
    if not poly:
        return None
    center = tuple(sum(p[k] for p in poly) / len(poly) for k in (0, 1))
    return center, max(distance(center, p) for p in poly)


def strip_points(anchor, angle):
    """228 points cover EVERY position allowed by this single valid bearing."""
    a = math.radians(angle)
    forward = (math.cos(a), math.sin(a))
    lateral = (-forward[1], forward[0])
    # Centre lane first; alternate direction for a continuous lawnmower route.
    for row, offset in enumerate((0., 20., -20.)):
        along = range(0, 1501, 20) if row % 2 == 0 else range(1500, -1, -20)
        for x in along:
            yield tuple(anchor[k] + x * forward[k] + offset * lateral[k]
                        for k in (0, 1))


def scan_points():
    # Origin first; every other lattice point is visited exactly once.
    yield (0., 0.)
    for row, y in enumerate(range(-2000, 2001, 500)):
        xs = list(range(-2000, 2001, 500))
        if row % 2:
            xs.reverse()
        for x in xs:
            if x or y:
                yield (float(x), float(y))


class PublicClient:
    def __init__(self, url, robot_id, action_file):
        import requests
        self.requests = requests
        self.session = requests.Session()
        self.url = url.rstrip("/")
        self.robot_id = robot_id
        self.action_file = action_file
        self.deadline = None
        self.virtual = 0.
        self.virtual_limit = 360000.
        self.position = (0., 0.)
        self.channel = 1
        self.counts = dict(measures=0, clear_attempts=0, clear_successes=0,
                           moves=0, switches=0)

    def call(self, path, point=None, channel=None):
        payload = dict(arena_id="default", robot_id=self.robot_id,
                       request_id=uuid.uuid4().hex)
        if point is not None:
            if not all(math.isfinite(v) and abs(v) <= 2000000 for v in point):
                raise ValueError("Invalid action coordinates")
            payload.update(position=dict(x=float(point[0]), y=float(point[1])),
                           channel=channel)
        # Reuse the identical payload/ID only for an uncertain transport retry.
        for attempt in range(3):
            remaining = float("inf") if self.deadline is None else self.deadline - time.monotonic()
            reserve = 0. if path == "/exit" else 3.
            if remaining <= reserve:
                raise TimeoutError("Real-time budget reached; coverage is incomplete")
            if point is not None:
                upper_cost = distance(self.position, point) / 5. + (6 if path == "/measure" else 5)
                if self.virtual + upper_cost >= self.virtual_limit:
                    raise TimeoutError("Virtual-time budget reached; coverage is incomplete")
            began = time.monotonic()
            try:
                response = self.session.post(self.url + path, json=payload,
                                             timeout=max(.05, min(10., remaining - reserve)))
            except (self.requests.Timeout, self.requests.ConnectionError) as exc:
                self.action_file.write(json.dumps(dict(path=path, request=payload,
                                                       transport_error=str(exc)),
                                                  ensure_ascii=False) + "\n")
                self.action_file.flush()
                if attempt == 2:
                    raise
                continue
            response.raise_for_status()
            result = response.json()
            self.action_file.write(json.dumps(dict(path=path, request=payload,
                                                  response=result),
                                             ensure_ascii=False) + "\n")
            self.action_file.flush()
            if result.get("accepted") is not True:
                raise RuntimeError("Action rejected; it is NOT a no_signal observation")
            self.virtual = float(result["virtual_time_s"])
            if path == "/enter":
                self.deadline = began + float(result["remaining_real_duration_s"])
                self.virtual_limit = float(result["max_virtual_duration_s"])
            if point is not None:
                self.counts["moves"] += distance(self.position, point) > 1e-9
                self.position = tuple(point)
            if path == "/measure":
                self.counts["measures"] += 1
                self.counts["switches"] += channel != self.channel
                self.channel = channel
                if result.get("measure_result") not in ("direction", "near", "no_signal"):
                    raise RuntimeError("Missing/invalid measurement result")
                if result["measure_result"] == "direction":
                    angle = result.get("svd_deg")
                    if not isinstance(angle, (int, float)) or not math.isfinite(angle) or not 0 <= angle < 360:
                        raise RuntimeError("Missing/invalid bearing")
            if path == "/clear":
                self.counts["clear_attempts"] += 1
                if result.get("clear_result") not in ("success", "no_target_in_range"):
                    raise RuntimeError("Missing/invalid clearing result")
                self.counts["clear_successes"] += result["clear_result"] == "success"
            return result
        raise RuntimeError("Transport retries exhausted")


class ReliableSolver:
    def __init__(self, client, emit=print, refine=True, refinement="adaptive"):
        self.client, self.emit, self.refine = client, emit, refine
        self.refinement = refinement
        self.discovered = set()
        self.cleared = set()
        self.coverage_complete = False

    def clear_at(self, point, channel):
        response = self.client.call("/clear", point, channel)
        if response["clear_result"] == "success":
            self.cleared.add(channel)
            self.emit("清除成功：频道%d；累计%d；虚拟时间%.1f秒" %
                      (channel, len(self.cleared), self.client.virtual))
            return True
        return False

    def clear_detected(self, channel, anchor, observation):
        self.discovered.add(channel)
        self.emit("发现频道%d，优先完成该目标清除。" % channel)
        if observation["measure_result"] == "near":
            if not self.clear_at(anchor, channel):
                raise RuntimeError("near followed by failed clear: protocol/model inconsistency")
            return
        angle = observation["svd_deg"]
        region = add_bearing(initial_region(), anchor, angle)
        geometry_valid = bool(region)
        # Bounded acceleration. Every valid new bearing joins ALL old constraints.
        # no_signal does not remove any candidate source position.
        if self.refine:
            a = math.radians(angle)
            last_signal = anchor
            opposite = None
            visited = {tuple(round(v, 6) for v in anchor)}
            for index in range(6):
                if not geometry_valid:
                    break
                if self.refinement == "axial":
                    step = 250. * (index + 1)
                    point = (anchor[0] + step * math.cos(a), anchor[1] + step * math.sin(a))
                elif opposite is not None:
                    # A no-signal observation cannot exclude the target: try the other side.
                    point, opposite = opposite, None
                else:
                    center, radius = covering_circle(region)
                    dx, dy = center[0] - last_signal[0], center[1] - last_signal[1]
                    norm = math.hypot(dx, dy)
                    u = (dx / norm, dy / norm) if norm > 1e-8 else (math.cos(a), math.sin(a))
                    v = (-u[1], u[0])
                    offset = min(250., max(30., radius / 2.))
                    base = tuple(center[k] - offset * u[k] for k in (0, 1))
                    point = tuple(base[k] + offset * v[k] for k in (0, 1))
                    opposite = tuple(base[k] - offset * v[k] for k in (0, 1))
                key = tuple(round(v, 6) for v in point)
                if key in visited:
                    continue  # Same-location error is fixed; do not average repeated readings.
                visited.add(key)
                result = self.client.call("/measure", point, channel)
                kind = result["measure_result"]
                if kind == "near":
                    if not self.clear_at(point, channel):
                        raise RuntimeError("near followed by failed clear")
                    return
                if kind == "direction" and geometry_valid:
                    last_signal, opposite = point, None
                    region = add_bearing(region, point, result["svd_deg"])
                    geometry_valid = bool(region)
                    if not geometry_valid:
                        self.emit("共同交集为空：禁用精修结论，保留首条示向度的完整覆盖兜底。")
                        continue
                    center, radius = covering_circle(region)
                    self.emit("频道%d：保守覆盖半径%.3f米" % (channel, radius))
                    if radius <= 19.:
                        if self.clear_at(center, channel):
                            return
                        geometry_valid = False
                        self.emit("覆盖圆清除未成功：记录几何异常，启动完整条带兜底。")
                        break
        self.emit("频道%d：开始完整条带覆盖，最多228点；无信号不阻止清除。" % channel)
        for index, point in enumerate(strip_points(anchor, angle), 1):
            if self.clear_at(point, channel):
                return
            if index % 30 == 0:
                self.emit("频道%d：条带进度%d/228" % (channel, index))
        raise RuntimeError("Full bearing-strip exhausted: retain unresolved target and audit observations")

    def solve(self):
        points = list(scan_points())
        for index, point in enumerate(points, 1):
            self.emit("覆盖点%d/%d：(%g, %g)" % (index, len(points), *point))
            for channel in range(1, 21):
                if channel in self.cleared:
                    continue
                result = self.client.call("/measure", point, channel)
                if result["measure_result"] != "no_signal":
                    self.clear_detected(channel, point, result)
                    if len(self.cleared) == 16:
                        self.coverage_complete = True  # Source-count upper bound proves completion.
                        return
        self.coverage_complete = True

    def summary(self):
        count = len(self.cleared)
        return dict(algorithm_version="reliable-v2", refinement=self.refinement if self.refine else "none",
                    discovered_channels=sorted(self.discovered),
                    cleared_channels=sorted(self.cleared),
                    unresolved_channels=sorted(self.discovered - self.cleared),
                    coverage_complete=self.coverage_complete,
                    completed=self.coverage_complete and self.discovered == self.cleared and 10 <= count <= 16,
                    known_target_clearance=count / len(self.discovered) if self.discovered else None,
                    actual_total=None, official_clearance_ratio=None,
                    total_virtual_time_s=self.client.virtual,
                    average_location_clear_time_s=self.client.virtual / count if count else None,
                    actions=self.client.counts)


def self_test():
    # Pure offline deterministic checks: no HTTP, no simulator, no output files.
    points = list(scan_points())
    assert len(points) == len(set(points)) == 81
    for angle in (0., 1., 45., 179.99, 270., 359.99):
        anchor = (1039.2304845413264, 599.9999999999999)
        sweep = list(strip_points(anchor, angle))
        assert len(sweep) == 228
        for r in (0., 5., 19.9, 249.9, 750., 1490., 1500.):
            for error in (-ANGLE_ERROR, 0., ANGLE_ERROR):
                a = math.radians(angle + error)
                source = (anchor[0] + r * math.cos(a), anchor[1] + r * math.sin(a))
                assert min(distance(source, p) for p in sweep) < 20.
    # True source must survive simultaneous wedges, including wraparound/extreme errors.
    source = (500., 400.)
    poly = initial_region()
    for point, err in (((0., 0.), 1.), ((900., 0.), -1.), ((0., 900.), .2)):
        true_angle = math.degrees(math.atan2(source[1] - point[1], source[0] - point[0]))
        poly = add_bearing(poly, point, (true_angle + err) % 360.)
        assert poly
        for a, b in zip(poly, poly[1:] + poly[:1]):
            assert (b[0]-a[0])*(source[1]-a[1])-(b[1]-a[1])*(source[0]-a[0]) >= -1e-5
    center, radius = covering_circle(poly)
    assert distance(center, source) <= radius + 1e-6
    # Fake public interface; hidden source is confined to the TEST fixture.
    class Fake:
        def __init__(self, source, directional=True):
            self.source, self.directional = source, directional
            self.virtual, self.counts = 0., {}
        def call(self, path, point, channel):
            self.virtual += 5.
            d = distance(point, self.source)
            if path == "/clear":
                return dict(clear_result="success" if d <= 20 else "no_target_in_range")
            if d > 1000 or (self.directional and point[0] < self.source[0]):
                return dict(measure_result="no_signal")
            if d <= 5:
                return dict(measure_result="near")
            angle = math.degrees(math.atan2(self.source[1]-point[1], self.source[0]-point[0]))
            return dict(measure_result="direction", svd_deg=(angle + 1.) % 360.)
    for source, anchor, directional in (((1700., 0.), (2000., 0.), True),
                                        ((-700., -1000.), (0., -1000.), True),
                                        ((100., 100.), (900., 100.), False)):
        fake = Fake(source, directional)
        solver = ReliableSolver(fake, emit=lambda _: None)
        solver.clear_detected(1, anchor, fake.call("/measure", anchor, 1))
        assert solver.cleared == {1}
    print("Offline checks passed: strip boundaries, simultaneous wedges, mixed-source clearing.")
    print("These are synthetic checks, NOT official simulator performance tests.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robot-id", default="202619020062")
    parser.add_argument("--url", default="http://127.0.0.1:2026")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--refinement", choices=("adaptive", "axial"), default="adaptive",
                        help="Adaptive lateral refinement or the original axial baseline")
    parser.add_argument("--no-refine", action="store_true",
                        help="Use the pure coverage baseline for comparison")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    root = Path(__file__).resolve().parents[1]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log_dir = root / "test_logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / ("test_log_reliable_" + stamp + ".txt")
    with log_path.open("w", encoding="utf-8") as log, (log_dir / ("actions_reliable_" + stamp + ".jsonl")).open("w", encoding="utf-8") as actions:
        def emit(message):
            print(message, flush=True)
            log.write(message + "\n")
            log.flush()
        emit("可靠清除V2；补测策略=" + (args.refinement if not args.no_refine else "none"))
        client = PublicClient(args.url, args.robot_id, actions)
        solver = ReliableSolver(client, emit, refine=not args.no_refine, refinement=args.refinement)
        entered = False
        error = None
        try:
            client.call("/enter")
            entered = True
            solver.solve()
        except Exception as exc:
            error = str(exc)
            emit("未完成：" + error)
        finally:
            if entered:
                try:
                    client.call("/exit")
                except Exception as exc:
                    emit("退出响应不可用：" + str(exc))
            result = solver.summary()
            result["error"] = error
            emit(json.dumps(result, ensure_ascii=False, indent=2))
            emit("官方清除比例待演练结束后的实际总数计算；不以发现数替代。")
    print("日志已保存到: " + str(log_path))
    return 0 if result["completed"] and error is None else 1


if __name__ == "__main__":
    sys.exit(main())

