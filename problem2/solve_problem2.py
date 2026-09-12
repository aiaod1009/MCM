# -*- coding: utf-8 -*-
"""
问题二：基于不确定可行域的鲁棒第二检测点选择模型
=================================================================
重构目标（依据《问题二客观重构修改报告》的修正版）：
  1. 不再用固定距离 d0=600 m 点估计源位置；
  2. 第一次有效示向度后，构造由题意严格支持的源位置可行域
         G1 = W1 ∩ B(S1, 1500)
     其中 W1 为第一示向度的 ±1° 角域，B(S1,1500) 为"源距 S1 不超过真实
     接收半径上界 1500 m"的确定约束（不再引入题目未给出的 1800 m 圆域）；
  3. 第二检测点候选区用最坏接收半径 1000 m 构造，保证"对所有可能真实源
     都能收到信号"，而不是错误地用 1500 m 冒充"保证接收"；
  4. 交会角降级为几何预筛选指标，最终评价用问题一定义的定位区域直径 D，
     建立鲁棒优化  S2* = argmin_{S2 in C} max_{G in G1} D(S2, G)；
  5. 输出推荐点与近优候选区域，并与"随机可行点""沿示向线移动点"两个
     基准策略对比。

依赖：仅 Python 标准库（复用问题一 verify_problem1.py 的定位区域逻辑）。
运行：  python solve_problem2.py
"""

import math
import random

# =====================================================================
# 复用问题一的定位区域计算（半平面求交 → 凸包 → 直径）
# =====================================================================
def _ang(d):
    return d % 360.0


def _wedge_halfplanes(S, th, eps):
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


def localization_diameter(S1, th1, S2, th2, eps=1.0):
    """对两个检测点 (S1,th1),(S2,th2) 调用问题一模型，返回定位区域直径 D。
    若区域退化或为空，返回一个大数表示失效。"""
    poly = region_polygon([S1, S2], [th1, th2], eps)
    if len(poly) < 3:
        return float("inf")
    H = convex_hull(poly)
    if len(H) < 3:
        return float("inf")
    D, _ = diameter(H)
    return D


# =====================================================================
# 第一次观测后的源位置可行域 G1 = W1 ∩ B(S1, 1500)
# =====================================================================
def _in_w1(G, S1, th1, eps=1.0):
    vx, vy = G[0] - S1[0], G[1] - S1[1]
    a = math.degrees(math.atan2(vy, vx)) % 360.0
    tmin = (th1 - eps) % 360.0
    tmax = (th1 + eps) % 360.0
    # 环绕角差
    d = (a - th1 + 180.0) % 360.0 - 180.0
    return -eps - 1e-9 <= d <= eps + 1e-9


def sample_G1(S1, th1, R_max=1500.0, n_samples=2000, seed=0):
    """在 W1 ∩ B(S1,1500) 内均匀采样得到源位置离散可行集。
    W1 是顶角 2° 的细楔形，直接在极坐标 (ρ, θ) 上采样再筛选。"""
    random.seed(seed)
    pts = []
    while len(pts) < n_samples:
        rho = R_max * math.sqrt(random.random())
        theta = th1 + 2.0 * (random.random() - 0.5)  # ±1°
        x = S1[0] + rho * math.cos(math.radians(theta))
        y = S1[1] + rho * math.sin(math.radians(theta))
        G = (x, y)
        if _in_w1(G, S1, th1):
            pts.append(G)
    return pts


# =====================================================================
# 交会角与几何质量
# =====================================================================
def intersection_angle(S1, th1, S2, G):
    """真实源 G 下，S1 与 S2 的交会角（S2 处的真实示向度指向 G）"""
    th2 = math.degrees(math.atan2(G[1] - S2[1], G[0] - S2[0])) % 360.0
    alpha = abs(th2 - th1)
    alpha = min(alpha, 360.0 - alpha)
    return alpha


def worst_geometry_quality(S1, th1, S2, G_samples):
    """Q(S2) = min_{G in G1} |sin α(S2,G)|：最坏交会几何质量"""
    q = 1.0
    for G in G_samples:
        a = math.radians(intersection_angle(S1, th1, S2, G))
        q = min(q, abs(math.sin(a)))
    return q


# =====================================================================
# 第二检测点候选区域：最坏接收半径 1000 m 的强鲁棒接收区
# =====================================================================
def worst_receive_distance(S2, G_samples, S1, th1, R_max=1500.0):
    """max_{G in G1} ||S2 - G|| 的精确值（解析）。
    G1 是从 S1 沿 ±1° 角域到距离 R_max 的楔形段（极细，可近似为线段
    S1 → G_far，其中 G_far = S1 + R_max*(cosθ1, sinθ1)）。
    因此 G1 内到 S2 的最远点必在两个端点 S1 或 G_far 之一取到。
    """
    d_to_S1 = math.hypot(S2[0] - S1[0], S2[1] - S1[1])
    G_far = (S1[0] + R_max * math.cos(math.radians(th1)),
             S1[1] + R_max * math.sin(math.radians(th1)))
    d_to_far = math.hypot(S2[0] - G_far[0], S2[1] - G_far[1])
    return max(d_to_S1, d_to_far)


def is_robust_receive(S2, G_samples, R_min=1000.0, S1=None, th1=None, R_max=1500.0):
    """是否对 G1 内所有可能源都在 1000 m 内（保证收到信号）。
    解析判据（不依赖采样点）：G1 近似为 S1→G_far 线段，最远点必在端点取到。"""
    if S1 is None or th1 is None:
        # 回退到采样估计
        return worst_receive_distance(S2, G_samples) <= R_min
    return worst_receive_distance(S2, G_samples, S1, th1, R_max) <= R_min


# =====================================================================
# 候选点网格生成（二维搜索，替代固定 r=600 圆）
# =====================================================================
def candidate_grid(S1, r_min=0.0, r_max=1000.0, dr=25.0, dphi=3.0):
    pts = []
    r = r_min
    while r <= r_max + 1e-9:
        phi = 0.0
        while phi < 360.0:
            x = S1[0] + r * math.cos(math.radians(phi))
            y = S1[1] + r * math.sin(math.radians(phi))
            pts.append((round(x, 3), round(y, 3)))
            phi += dphi
        r += dr
    return pts


# =====================================================================
# 鲁棒优化：S2* = argmin_{S2 in C} max_{G in G1} D(S2, G)
# =====================================================================
def worst_diameter(S1, th1, S2, G_samples, eps=1.0):
    """max_{G in G1} D(S2,G)：对给定 S2，遍历所有可能源，取最坏定位直径"""
    worst = 0.0
    for G in G_samples:
        th2 = math.degrees(math.atan2(G[1] - S2[1], G[0] - S2[0])) % 360.0
        D = localization_diameter(S1, th1, S2, th2, eps)
        if D == float("inf"):
            return float("inf")
        worst = max(worst, D)
    return worst


def solve(S1, th1, eps=1.0, n_G=400, seed=0):
    """主求解：返回 (S2_star, 详细结果字典)"""
    # 1. 源可行域采样
    G_samples = sample_G1(S1, th1, R_max=1500.0, n_samples=n_G, seed=seed)

    # 2. 候选点网格
    grid = candidate_grid(S1)

    # 3. 筛选：强鲁棒接收（解析判据）+ 几何预筛选（|sin α| 下界阈值）
    feasible = []
    for S2 in grid:
        if not is_robust_receive(S2, G_samples, S1=S1, th1=th1):
            continue
        q = worst_geometry_quality(S1, th1, S2, G_samples)
        if q < 0.5:  # 最坏交会角 < 30° 或 > 150°，几何太差，筛掉
            continue
        feasible.append((S2, q))

    # 4. 鲁棒优化：最小化最坏定位直径
    best_S2, best_D = None, float("inf")
    for S2, q in feasible:
        D = worst_diameter(S1, th1, S2, G_samples, eps)
        if D < best_D:
            best_D, best_S2 = D, S2

    # 5. 近优候选区域：最坏直径在 (1+η) 倍最优内的点
    eta = 0.2
    near_opt = []
    for S2, q in feasible:
        D = worst_diameter(S1, th1, S2, G_samples, eps)
        if D <= (1 + eta) * best_D and D != float("inf"):
            near_opt.append((S2, D))

    return best_S2, best_D, G_samples, feasible, near_opt


# =====================================================================
# 基准策略
# =====================================================================
def baseline_random(S1, th1, G_samples, eps=1.0, n_try=50, seed=1):
    """基准1：随机可行点（在接收区内随机取 S2）"""
    random.seed(seed)
    best_D = float("inf")
    best_S2 = None
    for _ in range(n_try):
        # 在 S1 周围随机取点，且满足鲁棒接收
        r = 1000 * math.sqrt(random.random())
        phi = random.uniform(0, 360)
        S2 = (S1[0] + r * math.cos(math.radians(phi)),
              S1[1] + r * math.sin(math.radians(phi)))
        if not is_robust_receive(S2, G_samples, S1=S1, th1=th1):
            continue
        D = worst_diameter(S1, th1, S2, G_samples, eps)
        if D < best_D:
            best_D, best_S2 = D, S2
    return best_S2, best_D


def baseline_alongline(S1, th1, G_samples, eps=1.0):
    """基准2：沿第一示向线移动固定距离（传统做法，如 600 m）"""
    S2 = (S1[0] + 600 * math.cos(math.radians(th1)),
          S1[1] + 600 * math.sin(math.radians(th1)))
    return S2, worst_diameter(S1, th1, S2, G_samples, eps)


def baseline_thales(S1, th1, G_samples, eps=1.0, r1=900.0):
    """基准3：解析垂直交会理论点（参考论文路线 A）。
    在“假设源距离已知 r1”的前提下，取以 S1G 为直径的 Thales 圆上、
    使 ∠S1GS2=90° 的第二点。这里固定 r1=900 m（参考论文 5.2.4 取值），
    第二点 S2 取与 S1G 垂直、距 G 为 r2 的侧向点。
    由于真实源距离未知，该点对“真实 G 分布”的最坏直径可能并不好，
    用于凸显纯解析模型在未知源下的鲁棒性缺陷。"""
    G_assumed = (S1[0] + r1 * math.cos(math.radians(th1)),
                 S1[1] + r1 * math.sin(math.radians(th1)))
    # 取垂直方向偏移 r2（对称取 r2=r1 的侧向点，落在 Thales 圆上）
    r2 = r1
    # 两个对称的垂直点，取其一（逆时针旋转 90°）
    perp = (-math.sin(math.radians(th1)), math.cos(math.radians(th1)))
    S2 = (G_assumed[0] + r2 * perp[0], G_assumed[1] + r2 * perp[1])
    return S2, worst_diameter(S1, th1, S2, G_samples, eps)


# =====================================================================
# 主流程与报告输出
# =====================================================================
def run_case(name, S1, th1):
    lines = []
    lines.append("=" * 70)
    lines.append("%s   S1=%s   θ1=%.1f°" % (name, S1, th1))
    lines.append("=" * 70)

    best_S2, best_D, G_samples, feasible, near_opt = solve(S1, th1)

    if best_S2 is None:
        lines.append("  [警告] 无满足鲁棒接收+几何筛选的候选点")
        return "\n".join(lines)

    lines.append("  源可行域采样点数 |G1|      = %d" % len(G_samples))
    lines.append("  接收+几何筛选后候选点数   = %d" % len(feasible))
    lines.append("")
    lines.append("  推荐第二检测点 S2*        = (%.2f, %.2f)" % best_S2)
    lines.append("  距 S1 距离                = %.2f m" %
                 math.hypot(best_S2[0] - S1[0], best_S2[1] - S1[1]))
    lines.append("  最坏定位直径 max D        = %.4f m" % best_D)
    lines.append("  近优候选点数 (η=0.2)      = %d" % len(near_opt))

    # 基准对比
    rS2, rD = baseline_random(S1, th1, G_samples)
    lS2, lD = baseline_alongline(S1, th1, G_samples)
    tS2, tD = baseline_thales(S1, th1, G_samples)
    lines.append("")
    lines.append("  --- 基准策略对比（最坏定位直径 D_worst）---")
    if rS2 is not None:
        lines.append("  随机可行点基准   : D_worst = %.4f m" % rD)
    else:
        lines.append("  随机可行点基准   : 未找到满足接收的点")
    lines.append("  沿示向线 600m 基准: D_worst = %.4f m" % lD)
    lines.append("  垂直理论点基准(Thales): D_worst = %.4f m" % tD)
    if lD > 0:
        lines.append("  相对沿示向线基准的改善 : %.1f%%" %
                     (100.0 * (lD - best_D) / lD))
    if rS2 is not None and rD > 0:
        lines.append("  相对随机基准的改善     : %.1f%%" %
                     (100.0 * (rD - best_D) / rD))
    if tD > 0:
        lines.append("  相对垂直理论点基准的改善 : %.1f%%" %
                     (100.0 * (tD - best_D) / tD))
    return "\n".join(lines)


def export_json():
    """导出各案例的详细结果到 JSON，供可视化脚本读取，保证数字一致。"""
    import json
    data = {}
    for name, S1, th1 in [("case1", (0.0, 0.0), 45.0),
                          ("case2", (100.0, 200.0), 135.0)]:
        best_S2, best_D, G_samples, feasible, near_opt = solve(S1, th1)
        rS2, rD = baseline_random(S1, th1, G_samples)
        lS2, lD = baseline_alongline(S1, th1, G_samples)
        tS2, tD = baseline_thales(S1, th1, G_samples)
        data[name] = {
            "S1": list(S1), "theta1": th1,
            "S2_star": list(best_S2), "D_worst": best_D,
            "G_samples": [list(g) for g in G_samples],
            "feasible": [list(s) for s, _ in feasible],
            "near_opt": [list(s) for s, _ in near_opt],
            "random_baseline_D": rD,
            "alongline_baseline_D": lD,
            "thales_baseline_D": tD,
            "thales_baseline_S2": list(tS2),
        }
    with open("problem2_results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("详细结果已写入 problem2_results.json")


def main():
    out = []
    out.append("=" * 70)
    out.append("问题二：基于不确定可行域的鲁棒第二检测点选择模型（重构版）")
    out.append("=" * 70)
    out.append("")
    out.append(run_case("案例1", (0.0, 0.0), 45.0))
    out.append("")
    out.append(run_case("案例2", (100.0, 200.0), 135.0))
    out.append("")

    txt = "\n".join(out)
    print(txt)
    with open("problem2_solve_results.txt", "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\n结果已写入 problem2_solve_results.txt")

    export_json()


if __name__ == "__main__":
    main()
