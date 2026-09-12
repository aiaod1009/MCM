# -*- coding: utf-8 -*-
"""问题3 策略流程图（严格依据 E:/problem/problem3/src 现行实现绘制）

流程来源：
  src/main_problem3.py
    ├─ 阶段1  src/phase1_frequency_scan.py   FrequencyScan.run('hybrid')
    ├─ 阶段2  src/phase2_localization.py     两点交会 / 单点估计
    └─ 阶段3  src/phase3_clearing.py         优先级贪心+真2-opt/Or-opt → clear_target → review_cleared

输出：figures/fig_q3_flowchart.png（300dpi）与 .pdf（矢量）
运行：python tools/fig_q3_flowchart.py
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ---------------- 画布参数 ----------------
X_MAIN, W_MAIN = 32.0, 44.0      # 主流程列
X_SIDE, W_SIDE = 77.0, 42.0      # 右侧注释列
DIA_W = 33.0                     # 菱形宽度

C_BLUE, C_GREEN, C_ORANGE, C_GRAY = "#1f6fb2", "#2e8b57", "#c1651a", "#5f5e5a"
F_BLUE, F_GREEN, F_ORANGE, F_GRAY = "#e8f1fa", "#e7f5ee", "#fdf0e3", "#f1efea"

fig, ax = plt.subplots(figsize=(10.0, 14.8))
ax.set_xlim(0, 100)
ax.set_ylim(-10, 138)
ax.axis("off")


# ---------------- 图元函数 ----------------
def box(y, text, color, fill, h=9.5, fs=10.5, w=W_MAIN, x=X_MAIN):
    """圆角矩形处理框"""
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0,rounding_size=1.4",
                                linewidth=1.3, edgecolor=color, facecolor=fill,
                                zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color="#1a1a1a",
            zorder=4, linespacing=1.55)


def side(y, text, h=7.5, fs=9.2):
    """右侧虚线注释框"""
    ax.add_patch(FancyBboxPatch((X_SIDE - W_SIDE / 2, y - h / 2), W_SIDE, h,
                                boxstyle="round,pad=0,rounding_size=1.2",
                                linewidth=1.0, edgecolor="#9a9a9a", facecolor="#fbfbf8",
                                linestyle=(0, (4, 2)), zorder=3))
    ax.text(X_SIDE, y, text, ha="center", va="center", fontsize=fs, color="#3a3a3a",
            zorder=4, linespacing=1.55)


def diamond(y, text, h=12.5, w=DIA_W, fs=10.5):
    """判断菱形"""
    pts = [(X_MAIN, y + h / 2), (X_MAIN + w / 2, y),
           (X_MAIN, y - h / 2), (X_MAIN - w / 2, y)]
    ax.add_patch(Polygon(pts, closed=True, linewidth=1.3, edgecolor="#b8860b",
                         facecolor="#fff8e1", zorder=3))
    ax.text(X_MAIN, y, text, ha="center", va="center", fontsize=fs,
            color="#1a1a1a", zorder=4, linespacing=1.4)


def term(y, text, h=8.5, w=30.0, fs=11.0):
    """起止椭圆"""
    ax.add_patch(Ellipse((X_MAIN, y), w, h, linewidth=1.3, edgecolor=C_GRAY,
                         facecolor="#ececea", zorder=3))
    ax.text(X_MAIN, y, text, ha="center", va="center", fontsize=fs,
            color="#1a1a1a", zorder=4)


def v_arrow(y1, y2):
    """主流程竖向箭头"""
    ax.add_patch(FancyArrowPatch((X_MAIN, y1), (X_MAIN, y2),
                                 arrowstyle="-|>", mutation_scale=15,
                                 linewidth=1.3, color="#4a4a4a", zorder=2,
                                 shrinkA=0, shrinkB=0))


def h_arrow(y, label="", from_x=X_MAIN + W_MAIN / 2, to_x=X_SIDE - W_SIDE / 2):
    """主流程 → 右侧注释的横向箭头"""
    ax.add_patch(FancyArrowPatch((from_x, y), (to_x, y),
                                 arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.1, color="#8a8a8a", zorder=2,
                                 shrinkA=0, shrinkB=0))
    if label:
        ax.text((from_x + to_x) / 2, y + 1.2, label, ha="center", va="bottom",
                fontsize=9.5, color="#c1651a")


# ---------------- 标题 ----------------
ax.text(50, 134, "问题3：全向干扰源自动搜索—定位—清除策略流程",
        ha="center", va="center", fontsize=15, fontweight="bold", color="#111111")


# ---------------- 主流程节点 ----------------
term(128, "开始")

box(117, "连接模拟器（HTTP 127.0.0.1:2026）\nPOST /enter 进入目标区域",
    C_GRAY, F_GRAY, h=9.5)

diamond(103, "进入成功？")
side(103, "输出失败原因并退出程序", h=7.0)
h_arrow(103, "否", from_x=X_MAIN + DIA_W / 2)

box(88.5, "① 阶段1：9 个扫描点 × 20 个频道 全频扫描\n（圆心 C + 8 个环点，r = 1200 m，间隔 45°）",
    C_BLUE, F_BLUE, h=9.5)
side(95.0, "POST /measure(position, channel)", h=7.0)
side(84.0, "direction → 记录示向度 θ；near → 记为有源\nno_signal → 忽略（超距或该频道无源）", h=10.0)
h_arrow(95.0)

box(76.5, "汇总有源频道 {ch} 与测向数据 {(pos, θ)}", C_BLUE, F_BLUE, h=7.5)

box(65.5, "② 阶段2：逐频道交会定位", C_GREEN, F_GREEN, h=7.5)
side(70.5, "数据点 ≥ 2：选最优点对 → 两点交会（±1° 楔形交集）")
side(61.5, "数据点 < 2：单点估计（直径 = 2 × 不确定度）")

box(54.5, "得到各源定位中心与区域直径\n按直径升序排序 → 目标列表 targets",
    C_GREEN, F_GREEN, h=9.5)

box(43.5, "③ 阶段3：优先级贪心 + 2-opt / Or-opt 规划清除路径", C_ORANGE, F_ORANGE, h=7.5)
side(43.5, "按直径分 3 个优先级组作为初始解，\n再边反转 2-opt + 单点重定位 Or-opt")

box(32.5, "逐个目标 POST /clear（最多 3 次尝试）", C_ORANGE, F_ORANGE, h=7.5)
side(32.5, "失败 → 精修：区域边界补测 → 重新定位 → 20 m 螺旋搜索")

box(21.5, "清除复核（零检测）\n/clear 返回 success 即已清除", C_ORANGE, F_ORANGE, h=9.5)
side(21.5, "未确认清除的频道 → 用阶段1测向数据交会/单点/near 点直清\n仍失败则围绕估计中心做 40 m 螺旋搜索")

box(10.5, "统计输出：清除比例、平均定位清除时间", C_ORANGE, F_ORANGE, h=7.5)

term(-1, "POST /exit 结束")

# ---------------- 主流程纵向箭头 ----------------
v_arrow(123.75, 121.75)   # 开始 → 连接
v_arrow(112.25, 109.25)   # 连接 → 判断
v_arrow(96.75, 93.25)     # 判断 → 阶段1
v_arrow(83.75, 80.25)     # 阶段1 → 汇总
v_arrow(72.75, 69.25)     # 汇总 → 阶段2
v_arrow(61.75, 59.25)     # 阶段2 → 排序
v_arrow(49.75, 47.25)     # 排序 → 阶段3规划
v_arrow(39.75, 36.25)     # 规划 → 清除
v_arrow(28.75, 26.25)     # 清除 → 复核
v_arrow(16.75, 14.25)     # 复核 → 统计
v_arrow(6.75, 3.25)       # 统计 → 退出

# ---------------- 保存 ----------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "figures")
os.makedirs(OUT, exist_ok=True)

png = os.path.join(OUT, "fig_q3_flowchart.png")
pdf = os.path.join(OUT, "fig_q3_flowchart.pdf")
fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(pdf, bbox_inches="tight", facecolor="white")
plt.close(fig)

names = {f.name for f in font_manager.fontManager.ttflist}
print("中文字体 Microsoft YaHei 可用:", "Microsoft YaHei" in names)
print("已保存:", png)
print("已保存:", pdf)
