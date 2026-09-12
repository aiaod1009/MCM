# -*- coding: utf-8 -*-
"""
问题一 随机配置交叉验证 —— 参考解生成端（Python / 仅标准库）
==============================================================
职责：
  1. 生成 N 组随机交会配置（检测点数 2~6、随机站位、示向度指向共同中心并带抖动、误差 ±1°）；
  2. 只保留"定位区域非退化（凸包顶点数 >= 3）"的配置；
  3. 写出 inputs.csv 供 MATLAB 管线读取（保证两条链路输入完全一致）；
  4. 用"半平面求交 + 暴力枚举直径"算出参考解，写出 py_results.csv。

运行： python verify_random_python.py
"""

import csv
import math
import random

N_TARGET = 200          # 期望保留的非退化配置数
EPS = 1.0               # 误差 ±1°（题面规定）
SEED = 20260912


def ang(d):
    return d % 360.0


# ---------------------------- 参考解：半平面求交 ----------------------------
def _wedge_halfplanes(S, th, eps):
    dlo = (math.cos(math.radians(th - eps)), math.sin(math.radians(th - eps)))
    dhi = (math.cos(math.radians(th + eps)), math.sin(math.radians(th + eps)))
    return [(-dlo[1], dlo[0], dlo[1] * S[0] - dlo[0] * S[1]),
            (dhi[1], -dhi[0], dhi[0] * S[1] - dhi[1] * S[0])]


def _clip(poly, hp):
    a, b, c = hp
    out = []
    n = len(poly)
    if n == 0:
        return out
    for i in range(n):
        P, Q = poly[i], poly[(i + 1) % n]
        fp = a * P[0] + b * P[1] + c
        fq = a * Q[0] + b * Q[1] + c
        if fp >= -1e-12:
            out.append(P)
        if (fp > 1e-12 and fq < -1e-12) or (fp < -1e-12 and fq > 1e-12):
            t = fp / (fp - fq)
            out.append((P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1])))
    return out


def region_polygon(det, az, eps, box=1e6):
    poly = [(-box, -box), (box, -box), (box, box), (-box, box)]
    for S, th in zip(det, az):
        for hp in _wedge_halfplanes(S, th, eps):
            poly = _clip(poly, hp)
            if not poly:
                return []
    ded = []
    for p in poly:
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-7 * max(1.0, abs(p[0])) for q in ded):
            ded.append(p)
    return ded


def hull_of(points):
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(O, A, B):
        return (A[0] - O[0]) * (B[1] - O[1]) - (A[1] - O[1]) * (B[0] - O[0])

    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 1e-12:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 1e-12:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def diameter(hull):
    best = 0.0
    for i in range(len(hull)):
        for j in range(i + 1, len(hull)):
            d = math.hypot(hull[i][0] - hull[j][0], hull[i][1] - hull[j][1])
            if d > best:
                best = d
    return best


def solve(det, az, eps, box=1e6):
    poly = region_polygon(det, az, eps, box)
    if len(poly) < 3:
        return None
    # 若顶点落在大框边界上，说明区域无界（直径无穷大）——射线求交法无法表示，
    # 这类配置必须剔除，否则会与 MATLAB 结果产生假分歧。
    for (x, y) in poly:
        if abs(x) >= box - 1e-3 or abs(y) >= box - 1e-3:
            return None
    H = hull_of(poly)
    if len(H) < 3:
        return None
    D = diameter(H)
    if D <= 1e-9:
        return None
    # 覆盖圆：仅取过"直径端点"的一组；这里取使 d_max 最小的那组对踵点对
    best = None
    worst = None
    for i in range(len(H)):
        for j in range(i + 1, len(H)):
            d = math.hypot(H[i][0] - H[j][0], H[i][1] - H[j][1])
            if d < D - 1e-9:
                continue
            C = ((H[i][0] + H[j][0]) / 2, (H[i][1] + H[j][1]) / 2)
            dm = max(math.hypot(p[0] - C[0], p[1] - C[1]) for p in H)
            if best is None or dm < best[0]:
                best = (dm, C)
            if worst is None or dm > worst[0]:
                worst = (dm, C)
    dmax, C = best
    return dict(nverts=len(H), D=D, R=D / 2, dmax=dmax,
                cover=(dmax <= D / 2 + 1e-9), dmin=dmax - D / 2,
                dmax_worst=worst[0], cover_worst=(worst[0] <= D / 2 + 1e-9),
                cx=C[0], cy=C[1])


def main():
    rnd = random.Random(SEED)
    configs = []
    tried = 0
    while len(configs) < N_TARGET and tried < 20000:
        tried += 1
        n = rnd.randint(2, 6)
        det = [(rnd.uniform(0, 500), rnd.uniform(0, 500)) for _ in range(n)]
        cx = sum(p[0] for p in det) / n
        cy = sum(p[1] for p in det) / n
        az = []
        for (x, y) in det:
            th = ang(math.degrees(math.atan2(cy - y, cx - x)) + rnd.uniform(-10, 10))
            az.append(th)
        ref = solve(det, az, EPS)
        if ref is not None:
            configs.append((det, az, ref))

    with open("inputs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "n", "detectors", "azimuths", "error"])
        for k, (det, az, _) in enumerate(configs, 1):
            # 内部用 ';' 分隔各点、空格分隔坐标，避免出现逗号导致 CSV 需加引号
            w.writerow([k, len(det),
                        ";".join("%.10f %.10f" % p for p in det),
                        ";".join("%.10f" % t for t in az),
                        "%.10f" % EPS])

    with open("py_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "nverts", "D", "R", "dmax", "cover", "dmax_minus_R",
                    "dmax_worst", "cover_worst", "cx", "cy"])
        for k, (_, _, r) in enumerate(configs, 1):
            w.writerow([k, r["nverts"], "%.10f" % r["D"], "%.10f" % r["R"],
                        "%.10f" % r["dmax"], int(r["cover"]),
                        "%.10f" % r["dmin"],
                        "%.10f" % r["dmax_worst"], int(r["cover_worst"]),
                        "%.10f" % r["cx"], "%.10f" % r["cy"]])

    ncover = sum(1 for _, _, r in configs if r["cover"])
    print("随机配置生成完成：保留 %d 组非退化配置（共尝试 %d 组）" % (len(configs), tried))
    print("  其中 能覆盖 %d 组，不能覆盖 %d 组" % (ncover, len(configs) - ncover))
    print("  已写出 inputs.csv / py_results.csv")


if __name__ == "__main__":
    main()
