# -*- coding: utf-8 -*-
"""
生成问题二「几何理论分析」小节的 Thales 圆示意图：
展示两检测点交会定位的几何结构、交会角 phi、以及垂直交会(phi=90度)
时第二检测点落在以 S1G 为直径的 Thales 圆上。
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def plot_thales(out_path):
    # 局部坐标系：S1=(0,0), 源 G=(r1,0), 取 r1=900
    S1 = (0.0, 0.0)
    r1 = 900.0
    G = (r1, 0.0)

    fig, ax = plt.subplots(figsize=(8, 7))

    # Thales 圆：以 S1G 为直径，圆心 (r1/2, 0)，半径 r1/2
    cx, cy = r1 / 2.0, 0.0
    R = r1 / 2.0
    th = [i * math.pi / 180 for i in range(0, 361)]
    ax.plot([cx + R * math.cos(t) for t in th],
            [cy + R * math.sin(t) for t in th],
            "b-", lw=1.5, label="Thales 圆（以 $S_1G$ 为直径）")

    # 直径线段 S1G
    ax.plot([S1[0], G[0]], [S1[1], G[1]], "k-", lw=1.2)

    # 一个垂直交会点 S2（在 Thales 圆上，∠S1GS2=90°）
    # 取圆上一点，使其对 G 的夹角为 90°
    ang = math.radians(70)  # 圆上参数角
    S2 = (cx + R * math.cos(ang), cy + R * math.sin(ang))

    # 两条测向线：S1->G 与 S2->G
    ax.plot([S1[0], G[0]], [S1[1], G[1]], "k-", lw=2.0, label="测向线 $S_1\\to G$")
    ax.plot([S2[0], G[0]], [S2[1], G[1]], "r-", lw=2.0, label="测向线 $S_2\\to G$")

    # 标记点
    ax.scatter([S1[0]], [S1[1]], s=140, c="black", marker="s", zorder=6, label="$S_1=(0,0)$")
    ax.scatter([G[0]], [G[1]], s=160, c="green", marker="^", zorder=6, label="$G=(r_1,0)$")
    ax.scatter([S2[0]], [S2[1]], s=160, c="red", marker="o", zorder=6, label="$S_2$（垂直交会）")

    # 标注直角
    ax.annotate("", xy=G, xytext=(G[0], 0), ha="center")
    # 直角标记
    ax.text(S1[0] + 60, -45, r"$\phi$", fontsize=14)
    # 交会角标注
    ax.annotate(r"交会角 $\phi=90^\circ$",
                xy=(S2[0] + 20, S2[1] + 20), fontsize=12, color="red")

    # 直角符号
    ax.text(G[0] + 40, 10, r"$90^\circ$", fontsize=13, color="red")

    # r1 标注
    ax.annotate("", xy=(r1 / 2, 0), xytext=(0, 0),
                arrowprops=dict(arrowstyle="<->", color="gray"))
    ax.text(r1 / 2 - 20, -70, r"$r_1$", fontsize=13)

    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("垂直交会几何与 Thales 圆（$\\angle S_1GS_2=90^\\circ$）")
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-250, 1150)
    ax.set_ylim(-250, 950)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print("已生成:", out_path)


if __name__ == "__main__":
    plot_thales("E:/lunwen/figures/problem2_thales_circle.png")
