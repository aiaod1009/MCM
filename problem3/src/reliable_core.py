"""Frozen geometry and public protocol primitives for Problem 3.
Derived from reviewed Q4 V7 primitives; no runtime dependency on Problem 4.
"""

import math
import json
import time
import uuid
ANGLE_ERROR=1.005
EPS=1e-7

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

def nearest_safe_clear_point(poly, position, radius=19.9):
    """Projection onto the intersection of vertex-centred disks; None if empty."""
    if not poly:
        return None
    vertices = list(dict.fromkeys(poly))
    def feasible(q):
        return all(distance(q,v) <= radius + 1e-8 for v in vertices)
    if feasible(position):
        return tuple(position)
    best, best_distance = None, float("inf")
    def consider(q):
        nonlocal best, best_distance
        d = distance(position,q)
        if d < best_distance and feasible(q):
            best, best_distance = q, d
    for v in vertices:
        d = distance(position,v)
        if d > 1e-12:
            consider(tuple(v[k]+radius*(position[k]-v[k])/d for k in (0,1)))
    for i,a in enumerate(vertices):
        for b in vertices[i+1:]:
            d = distance(a,b)
            if d < 1e-10 or d > 2*radius:
                continue
            middle = ((a[0]+b[0])/2,(a[1]+b[1])/2)
            h = math.sqrt(max(0.,radius**2-d**2/4))
            perpendicular = (-(b[1]-a[1])/d,(b[0]-a[0])/d)
            consider(tuple(middle[k]+h*perpendicular[k] for k in (0,1)))
            consider(tuple(middle[k]-h*perpendicular[k] for k in (0,1)))
    return best

def two_lane_points(anchor, angle):
    """102-point complete covering of the single-bearing strip."""
    a = math.radians(angle)
    forward = (math.cos(a),math.sin(a))
    lateral = (-forward[1],forward[0])
    offset = 1500*math.sin(math.radians(ANGLE_ERROR))/2
    for row,y in enumerate((offset,-offset)):
        xs = range(0,1501,30) if row == 0 else range(1500,-1,-30)
        for x in xs:
            yield tuple(anchor[k]+x*forward[k]+y*lateral[k] for k in (0,1))

def disk_intersection_vertices(poly, radius=19.9):
    vertices=list(dict.fromkeys(poly))
    candidates=[]
    for i,a in enumerate(vertices):
        for b in vertices[i+1:]:
            d=distance(a,b)
            if d<1e-10 or d>2*radius:
                continue
            mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
            h=math.sqrt(max(0.,radius*radius-d*d/4))
            normal=(-(b[1]-a[1])/d,(b[0]-a[0])/d)
            for sign in (-1,1):
                q=tuple(mid[k]+sign*h*normal[k] for k in (0,1))
                if all(distance(q,v)<=radius+1e-8 for v in vertices):
                    candidates.append(q)
    return vertices,candidates

def two_leg_clear_point(poly, start, end, tolerance=.1, max_iterations=40):
    """Feasible convex optimization; returns point, numerical gap, saving (metres)."""
    initial=nearest_safe_clear_point(poly,start)
    if initial is None or end is None:
        return initial,0.,0.
    vertices,corners=disk_intersection_vertices(poly)
    def cost(q):
        return distance(start,q)+distance(q,end)
    def linear_min(gradient):
        candidates=list(corners)
        norm=math.hypot(*gradient)
        if norm<1e-12:
            return initial
        for v in vertices:
            q=tuple(v[k]-19.9*gradient[k]/norm for k in (0,1))
            if all(distance(q,w)<=19.9+1e-8 for w in vertices):
                candidates.append(q)
        return min(candidates,key=lambda q:dot(gradient,q)) if candidates else None
    current=initial
    best=initial
    upper=cost(initial)
    lower=distance(start,end)  # Triangle inequality is a global lower bound.
    for _ in range(max_iterations):
        ds,de=distance(current,start),distance(current,end)
        gradient=tuple((current[k]-start[k])/ds if ds>1e-12 else 0. for k in (0,1))
        gradient=tuple(gradient[k]+((current[k]-end[k])/de if de>1e-12 else 0.) for k in (0,1))
        support=linear_min(gradient)
        if support is None:
            break
        gap=dot(gradient,(current[0]-support[0],current[1]-support[1]))
        lower=max(lower,cost(current)-max(0.,gap)-1e-6)
        if upper-lower<=tolerance:
            break
        def interpolate(t):
            return tuple(current[k]+t*(support[k]-current[k]) for k in (0,1))
        # Convex one-dimensional line search, bounded CPU and no simulator actions.
        lo,hi=0.,1.
        for _ in range(32):
            a=lo+(hi-lo)/3; b=hi-(hi-lo)/3
            if cost(interpolate(a))<=cost(interpolate(b)):
                hi=b
            else:
                lo=a
        candidate=min((current,support,interpolate((lo+hi)/2)),key=cost)
        if cost(candidate)<upper:
            best,upper=candidate,cost(candidate)
        if distance(candidate,current)<1e-9:
            break
        current=candidate
    # Numerical validation, and never increase the chosen two-leg baseline objective.
    if not all(distance(best,v)<20. for v in vertices) or cost(best)>cost(initial)+1e-8:
        return initial,max(0.,cost(initial)-lower),0.
    return best,max(0.,upper-lower),max(0.,cost(initial)-upper)

def batch_order(start, entries, exits, terminal):
    """Exact DP for <=9 estimated tasks, bounded 2-opt otherwise."""
    n=len(entries)
    if not n:
        return [],0.,True
    first=[distance(start,p) for p in entries]
    edge=[[distance(exits[i],entries[j]) for j in range(n)] for i in range(n)]
    last=[distance(p,terminal) if terminal is not None else 0. for p in exits]
    def cost(order):
        return first[order[0]]+sum(edge[a][b] for a,b in zip(order,order[1:]))+last[order[-1]]
    if n<=9:
        dp={(1<<j,j):(first[j],None) for j in range(n)}
        for mask in range(1,1<<n):
            for j in range(n):
                key=(mask,j)
                if key not in dp:
                    continue
                value=dp[key][0]
                for k in range(n):
                    if mask>>k&1:
                        continue
                    nxt=(mask|1<<k,k)
                    candidate=value+edge[j][k]
                    if nxt not in dp or candidate<dp[nxt][0]:
                        dp[nxt]=(candidate,j)
        mask=(1<<n)-1
        end=min(range(n),key=lambda j:dp[mask,j][0]+last[j])
        order=[]
        while end is not None:
            order.append(end)
            previous=dp[mask,end][1]
            mask^=1<<end
            end=previous
        return list(reversed(order)),0.,True
    unused=set(range(n)); order=[]
    while unused:
        j=min(unused,key=lambda k:first[k] if not order else edge[order[-1]][k])
        unused.remove(j);order.append(j)
    for _ in range(2):
        changed=False
        for i in range(n-1):
            for j in range(i+1,n):
                trial=order[:i]+list(reversed(order[i:j+1]))+order[j+1:]
                if cost(trial)<cost(order)-1e-6:
                    order=trial;changed=True
        if not changed:
            break
    # Outgoing-edge relaxation: cycles/duplicate successors allowed -> valid lower bound.
    lower=min(first)+sum(min([last[i]]+[edge[i][j] for j in range(n) if i!=j]) for i in range(n))
    return order,max(0.,cost(order)-lower),False

def feasible_strip_points(anchor, angle, region):
    """Keep every original point that could clear any source in region.

    A closed 20m disk is contained in its axis-aligned 40m square.
    Empty region-square intersection proves that this attempt cannot succeed.
    EPS expands the square; uncertain or invalid geometry retains all points.
    Original order is retained: no successful V6 attempt is removed.
    """
    full = list(two_lane_points(anchor, angle))
    if not region or not all(math.isfinite(v) for p in region for v in p):
        return full
    kept = []
    for q in full:
        intersection = list(region)
        for normal, bound in (((1.,0.),q[0]+20.),((-1.,0.),20.-q[0]),
                              ((0.,1.),q[1]+20.),((0.,-1.),20.-q[1])):
            intersection = clip(intersection, normal, bound)
            if not intersection:
                break
        if intersection:
            kept.append(q)
    return kept or full
