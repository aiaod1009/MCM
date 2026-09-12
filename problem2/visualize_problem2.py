# -*- coding: utf-8 -*-
"""
问题二 重构版可视化：从 problem2_results.json 读取结果绘图，保证与求解器数字一致。
"""
import json
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def plot_case(case_name, data, out_path):
    S1 = tuple(data["S1"])
    th1 = data["theta1"]
    S2_star = tuple(data["S2_star"])
    D_worst = data["D_worst"]
    G = data["G_samples"]
    feasible = data["feasible"]
    near_opt = data["near_opt"]

    fig, ax = plt.subplots(figsize=(8, 8))

    gx = [g[0] for g in G]
    gy = [g[1] for g in G]
    ax.scatter(gx, gy, s=2, c="#e0c040", alpha=0.5, label="源可行域 G1 (采样)")

    if feasible:
        fx = [s[0] for s in feasible]
        fy = [s[1] for s in feasible]
        ax.scatter(fx, fy, s=14, c="#4c8bf5", alpha=0.55, label="接收+几何筛选后候选点")

    if near_opt:
        nx = [s[0] for s in near_opt]
        ny = [s[1] for s in near_opt]
        ax.scatter(nx, ny, s=30, c="#2ca02c", alpha=0.75, label="近优候选区域 (eta=0.2)")

    ax.scatter([S2_star[0]], [S2_star[1]], s=180, c="#d62728", marker="*",
               edgecolors="black", linewidths=1.2, zorder=5,
               label="推荐点 S2*=({:.0f},{:.0f})".format(S2_star[0], S2_star[1]))

    ax.scatter([S1[0]], [S1[1]], s=140, c="black", marker="s", zorder=6,
               label="第一检测点 S1")

    ax.plot([S1[0], S1[0] + 1600 * math.cos(math.radians(th1))],
            [S1[1], S1[1] + 1600 * math.sin(math.radians(th1))],
            "k--", lw=1, alpha=0.6, label="第一示向线 theta1")

    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("{}：源可行域与鲁棒第二检测点候选区域（最坏直径 {:.1f} m）".format(
        "案例1" if case_name == "case1" else "案例2", D_worst))
    ax.set_aspect("equal")
    ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    # 根据 S1 自适应坐标范围
    ax.set_xlim(S1[0] - 400, S1[0] + 1700)
    ax.set_ylim(S1[1] - 700, S1[1] + 1700)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print("已生成:", out_path, " 推荐点={} 最坏直径={:.2f}m".format(S2_star, D_worst))


if __name__ == "__main__":
    with open("E:/problem/problem2/problem2_results.json", encoding="utf-8") as f:
        data = json.load(f)
    out_dir = "E:/lunwen/figures"
    plot_case("case1", data["case1"], out_dir + "/problem2_case1_region.png")
    plot_case("case2", data["case2"], out_dir + "/problem2_case2_region.png")
