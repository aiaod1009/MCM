# -*- coding: utf-8 -*-
"""
问题一 定性示意图生成脚本（修正版）
==================================
生成两张图，用于说明"以定位区域直径为直径的圆能否覆盖该区域"：
  results/problem1_case1_corrected.png        案例1：能覆盖（D=3.4921 m）
  results/problem1_case4_counterexample.png   案例4：不能覆盖（超出 1.5154%）

每张图分左右两个子图：
  左：整体几何（检测点、示向度中心线、±1° 边界射线）
  右：定位区域放大图（区域、直径、覆盖圆、直径端点）

运行： python plot_verify.py
依赖： matplotlib
"""

import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

import verify_problem1 as V

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 语义配色（全文统一）
C_RAY_L = "#d98a8a"   # 左边界射线
C_RAY_R = "#8a9fd9"   # 右边界射线
C_CENTER = "#444444"  # 示向度中心线
C_REGION = "#7fd4d4"  # 定位区域填充
C_DIAM = "#c0398e"    # 直径
C_CIRCLE = "#2e9e4f"  # 覆盖圆
C_DET = "#e2b007"     # 检测点


def draw(case_name, fig_title, out_png, det, az, eps, zoom_halfwidth=None):
    poly = V.region_polygon(det, az, eps)
    H = V.convex_hull(poly)
    D, (Vp, Vq) = V.diameter(H)
    C = ((Vp[0] + Vq[0]) / 2.0, (Vp[1] + Vq[1]) / 2.0)
    R = D / 2.0
    dmax = max(math.hypot(p[0] - C[0], p[1] - C[1]) for p in H)
    cover = dmax <= R + 1e-9

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 6.2))

    # ---------------- 左：整体几何 ----------------
    reach = max(math.hypot(x, y) for x, y in det) * 1.15
    L = reach
    first = True
    for (S, th) in zip(det, az):
        for d, col in ((th - eps, C_RAY_L), (th + eps, C_RAY_R)):
            axL.plot([S[0], S[0] + L * math.cos(math.radians(d))],
                     [S[1], S[1] + L * math.sin(math.radians(d))],
                     "--", color=col, lw=0.9,
                     label="±1° 边界射线" if first else None)
        axL.plot([S[0], S[0] + L * math.cos(math.radians(th))],
                 [S[1], S[1] + L * math.sin(math.radians(th))],
                 "-", color=C_CENTER, lw=1.3,
                 label="示向度中心线" if first else None)
        first = False
    axL.plot([p[0] for p in det], [p[1] for p in det], "o",
             color=C_DET, ms=9, mec="k", mew=1.1, label="检测点", zorder=5)
    for i, S in enumerate(det):
        axL.annotate("$S_%d$" % (i + 1), S, textcoords="offset points",
                     xytext=(7, 5), fontsize=11)
    axL.plot(C[0], C[1], "s", color=C_CIRCLE, ms=7, zorder=6, label="定位区域位置")
    axL.set_aspect("equal")
    axL.set_xlabel("x / m")
    axL.set_ylabel("y / m")
    axL.set_title("(a) 检测点与示向度约束")
    axL.grid(alpha=0.25)
    axL.legend(loc="best", fontsize=9, framealpha=0.9)

    # ---------------- 右：定位区域放大 ----------------
    if zoom_halfwidth is None:
        zoom_halfwidth = max(2 * R, 1e-3)
    hw = zoom_halfwidth

    # 边界射线在该窗口内的可见段
    for (S, th) in zip(det, az):
        for d, col in ((th - eps, C_RAY_L), (th + eps, C_RAY_R)):
            ux, uy = math.cos(math.radians(d)), math.sin(math.radians(d))
            # 求射线与窗口边界的交点
            ts = []
            for tx in ((axR.get_xlim()[0], "x0"),):
                pass
            x0, x1 = C[0] - hw, C[0] + hw
            y0, y1 = C[1] - hw, C[1] + hw
            cand = []
            if abs(ux) > 1e-12:
                for X in (x0, x1):
                    t = (X - S[0]) / ux
                    Y = S[1] + t * uy
                    if t >= 0 and y0 <= Y <= y1:
                        cand.append((t, X, Y))
            if abs(uy) > 1e-12:
                for Y in (y0, y1):
                    t = (Y - S[1]) / uy
                    X = S[0] + t * ux
                    if t >= 0 and x0 <= X <= x1:
                        cand.append((t, X, Y))
            if len(cand) >= 2:
                cand.sort()
                (_, xa, ya), (_, xb, yb) = cand[0], cand[-1]
                axR.plot([xa, xb], [ya, yb], "--", color=col, lw=1.0, alpha=0.85)

    axR.add_patch(MplPolygon(H, closed=True, facecolor=C_REGION,
                             edgecolor="#1f7a7a", lw=1.8, alpha=0.55,
                             label="交会定位区域"))
    axR.plot([Vp[0], Vq[0]], [Vp[1], Vq[1]], "-", color=C_DIAM, lw=2.6,
             label="区域直径 $D=%.4f$ m" % D)
    axR.plot([Vp[0], Vq[0]], [Vp[1], Vq[1]], "o", color=C_DIAM, ms=7, zorder=6)

    tc = [i * 2 * math.pi / 400 for i in range(401)]
    axR.plot([C[0] + R * math.cos(t) for t in tc],
             [C[1] + R * math.sin(t) for t in tc],
             "-", color=C_CIRCLE, lw=2.2,
             label="以 $D$ 为直径的圆（$R=%.4f$ m）" % R)
    axR.plot(C[0], C[1], "+", color="k", ms=11, mew=1.6)

    # 标出最远顶点
    worst = max(H, key=lambda p: math.hypot(p[0] - C[0], p[1] - C[1]))
    axR.plot(worst[0], worst[1], "o", mfc="none", mec="#c0392b",
             ms=13, mew=2.0, label="离圆心最远的顶点 ($d_{max}$)")

    axR.set_xlim(C[0] - hw, C[0] + hw)
    axR.set_ylim(C[1] - hw, C[1] + hw)
    axR.set_aspect("equal")
    axR.set_xlabel("x / m")
    axR.set_ylabel("y / m")
    axR.set_title("(b) 定位区域放大：直径、覆盖圆与最远顶点")
    axR.grid(alpha=0.25)
    axR.legend(loc="best", fontsize=9, framealpha=0.9)

    verdict = ("能覆盖" if cover else "不能覆盖") + \
              "（$d_{max}=%.4f$, $R=%.4f$, 超出 %.4f m / %.4f%%）" % (
                  dmax, R, max(dmax - R, 0.0), 100.0 * (dmax - R) / R)

    fig.suptitle("%s\n%s" % (fig_title, verdict),
                 fontsize=13.5, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_png, dpi=190)
    plt.close(fig)
    print("已生成:", out_png, "|", verdict)


def main():
    # 案例1：能覆盖
    draw("case1", "案例1  三个检测点交会（$\\pm1^\\circ$）：以直径为直径的圆能覆盖定位区域",
         "results/problem1_case1_corrected.png",
         zoom_halfwidth=2.6,
         det=[(0, 0), (100, 0), (50, 80)], az=[45, 135, 270], eps=1.0)

    # 案例4：不能覆盖（反例）
    Rr = 300.0
    draw("case4", "案例4  等边三角形布站（$\\pm1^\\circ$）：以直径为直径的圆不能覆盖定位区域",
         "results/problem1_case4_counterexample.png",
         zoom_halfwidth=9.0,
         det=[(Rr, 0.0), (-Rr / 2, Rr * math.sqrt(3) / 2), (-Rr / 2, -Rr * math.sqrt(3) / 2)],
         az=[180.0, 300.0, 60.0], eps=1.0)


if __name__ == "__main__":
    main()
