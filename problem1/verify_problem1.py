# -*- coding: utf-8 -*-
"""
问题一 独立验证脚本（与 MATLAB 主程序完全独立的第二条求解链路）
=================================================================
目的：
  1. 用"半平面求交(Sutherland-Hodgman)"直接解析求出交会定位区域，
     这是定位区域的精确定义，与 MATLAB 的"边界射线求交+筛选+凸包"链路无关；
  2. 用蒙特卡洛采样独立校验区域直径；
  3. 复算直径端点、覆盖圆与覆盖性判定，给出可写进论文的规范数值。

运行：  python verify_problem1.py
输出：  控制台表格 + problem1_verify_results.txt

注意：本脚本只用 Python 标准库，不依赖 numpy / scipy / MATLAB。
"""

import math
import random

# --------------------------------------------------------------------------
# 测试案例定义：与 generate_test_data.m 保持一致
# 每个案例: (名称, 检测点列表, 示向度列表, 误差(度))
# --------------------------------------------------------------------------
_R3 = 300.0
CASES = [
    ("case1 三角形配置", [(0, 0), (100, 0), (50, 80)], [45, 135, 270], 1.0),
    ("case2 五检测点", [(0, 0), (200, 0), (200, 200), (0, 200), (100, 100)],
     [45, 135, 225, 315, 0], 1.0),
    ("case3 两检测点", [(0, 0), (100, 0)], [45, 135], 1.0),
    # 新增：3 个检测点位于半径 300 m 的等边三角形顶点上，示向度均指向原点。
    # 该配置在 ±1° 误差下得到的定位区域"不能被以直径为直径的圆覆盖"，
    # 是回答"能否覆盖"的关键反例（尺度不变，d_max/R = 1.015154）。
    ("case4 等边三检测点(反例)",
     [(_R3, 0.0), (-_R3 / 2, _R3 * math.sqrt(3) / 2), (-_R3 / 2, -_R3 * math.sqrt(3) / 2)],
     [180.0, 300.0, 60.0], 1.0),
]


def _ang(d):
    return d % 360.0


# ------------------------------ 半平面求交 ------------------------------
def _wedge_halfplanes(S, th, eps):
    """扇形约束 = 两个半平面之交集，半平面用 (a,b,c) 表示 a*x+b*y+c >= 0"""
    dlo = (math.cos(math.radians(th - eps)), math.sin(math.radians(th - eps)))
    dhi = (math.cos(math.radians(th + eps)), math.sin(math.radians(th + eps)))
    return [
        (-dlo[1], dlo[0], dlo[1] * S[0] - dlo[0] * S[1]),
        (dhi[1], -dhi[0], dhi[0] * S[1] - dhi[1] * S[0]),
    ]


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


def region_polygon(detectors, azimuths, eps, box=200000.0):
    """交会定位区域（凸多边形，逆时针或顺时针）"""
    poly = [(-box, -box), (box, -box), (box, box), (-box, box)]
    for S, th in zip(detectors, azimuths):
        for hp in _wedge_halfplanes(S, th, eps):
            poly = _clip(poly, hp)
            if not poly:
                return []
    ded = []
    for p in poly:
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-6 for q in ded):
            ded.append(p)
    return ded


def convex_hull(points):
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in points))
    if len(pts) <= 1:
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
    best, pair = 0.0, (hull[0], hull[0])
    for i in range(len(hull)):
        for j in range(i + 1, len(hull)):
            d = math.hypot(hull[i][0] - hull[j][0], hull[i][1] - hull[j][1])
            if d > best:
                best, pair = d, (hull[i], hull[j])
    return best, pair


def _feasible(P, detectors, azimuths, eps, tol=1e-7):
    for S, th in zip(detectors, azimuths):
        v = (P[0] - S[0], P[1] - S[1])
        a = 0.0 if math.hypot(v[0], v[1]) < 1e-12 else _ang(math.degrees(math.atan2(v[1], v[0])))
        tmin, tmax = _ang(th - eps), _ang(th + eps)
        if tmin <= tmax:
            if a < tmin - tol or a > tmax + tol:
                return False
        else:
            if not (a >= tmin - tol or a <= tmax + tol):
                return False
    return True


def monte_carlo_maxdist(hull, detectors, azimuths, eps, samples=400000, seed=0):
    """在凸包包围盒内采样可行点，估计直径下界（应略小于真实 D）"""
    random.seed(seed)
    xs = [p[0] for p in hull]
    ys = [p[1] for p in hull]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pts = []
    for _ in range(samples):
        x, y = random.uniform(x0, x1), random.uniform(y0, y1)
        if _feasible((x, y), detectors, azimuths, eps):
            pts.append((x, y))
    if len(pts) < 2:
        return 0.0, len(pts)
    best = 0.0
    for i in range(len(pts)):
        for _ in range(8):
            j = random.randrange(len(pts))
            best = max(best, math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]))
    return best, len(pts)


def main():
    lines = []
    lines.append("=" * 78)
    lines.append("问题一：交会定位区域直径与覆盖性 —— 独立验证（半平面求交 + 蒙特卡洛）")
    lines.append("=" * 78)

    for name, det, az, eps in CASES:
        poly = region_polygon(det, az, eps)
        lines.append("")
        lines.append("-" * 78)
        lines.append("%s   检测点=%s   示向度=%s   误差=±%g°" % (name, det, az, eps))
        if len(poly) < 2:
            lines.append("  定位区域退化/为空（顶点数=%d）" % len(poly))
            continue

        H = convex_hull(poly)
        D, (Vp, Vq) = diameter(H)
        C = ((Vp[0] + Vq[0]) / 2, (Vp[1] + Vq[1]) / 2)
        R = D / 2.0
        dmax = max(math.hypot(p[0] - C[0], p[1] - C[1]) for p in H)
        cover = dmax <= R + 1e-9
        mc, npts = monte_carlo_maxdist(H, det, az, eps)

        lines.append("  定位区域凸包顶点数: %d" % len(H))
        for p in H:
            lines.append("      (%.4f, %.4f)" % p)
        lines.append("  直径 D            = %.4f m" % D)
        lines.append("  直径端点          = (%.4f, %.4f) 与 (%.4f, %.4f)"
                     % (Vp[0], Vp[1], Vq[0], Vq[1]))
        lines.append("  覆盖圆圆心 C      = (%.4f, %.4f)" % C)
        lines.append("  覆盖圆半径 R=D/2  = %.4f m" % R)
        lines.append("  顶点到圆心最大距离 = %.4f m" % dmax)
        lines.append("  覆盖性结论        = %s   超出 %.6f m（%.4f%%）"
                     % ("能覆盖" if cover else "不能覆盖", dmax - R,
                        100.0 * (dmax - R) / R))
        lines.append("  [独立校验] 蒙特卡洛采样 %d 个可行点，最大点对距离 = %.4f m（应略小于 D）"
                     % (npts, mc))

    txt = "\n".join(lines)
    print(txt)
    with open("problem1_verify_results.txt", "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\n结果已写入 problem1_verify_results.txt")


if __name__ == "__main__":
    main()
