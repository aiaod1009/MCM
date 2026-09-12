"""量化对比两种兜底验证策略的耗时（用最近一次真实运行的目标中心）。

旧：5 点网格（圆心+东南西北各 900 m，每点扫全部有源频道）
新：逐已清除目标中心复测（只测该目标自己的频道）
"""
import sys
import os
import json

import numpy as np

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, _SRC)

from clearing.path_planner import (
    plan_clearing_path_priority_greedy,
    optimize_clearing_path,
    compute_path_length,
)
from target import Target

SPEED = 5.0           # m/s
DETECT_TIME = 5.0     # s / 次检测
SWITCH_TIME = 1.0     # s / 次切频道

res = os.path.join(_SRC, '..', 'results', 'final_results.json')
with open(res, 'r', encoding='utf-8') as f:
    data = json.load(f)

targets = []
for t in data['phase2']['targets']:
    c = t['center']
    c = (c['x'], c['y']) if isinstance(c, dict) else tuple(c)
    targets.append(Target(t['channel_id'], [], center=np.array(c, float),
                          diameter=t['diameter'], confidence=t.get('confidence', 0.6),
                          method=t.get('method', 'two_point')))

start = np.zeros(2)
greedy = plan_clearing_path_priority_greedy(targets, start)
L_greedy = compute_path_length(greedy, start)
opt = optimize_clearing_path(greedy, start)
L_opt = compute_path_length(opt, start)

print(f"优先级贪心路径: {L_greedy:.1f} m")
print(f"优化后路径    : {L_opt:.1f} m")
print(f"访问顺序      : {[t.channel_id for t in opt]}")
print(f"最后一个目标  : CH{opt[-1].channel_id} @ {opt[-1].center}")

last = opt[-1].center
n_ch = len(targets)

# ---- 旧：5 点网格 ----
grid_travel = float(np.linalg.norm(last - np.zeros(2))) + 900.0 + 3 * np.hypot(900.0, 900.0)
grid_det = (5 * n_ch) * (DETECT_TIME + SWITCH_TIME)
grid_total = grid_travel / SPEED + grid_det
print("\n--- 旧：5 点网格（5×N 次检测）---")
print(f"  移动 {grid_travel:8.1f} m = {grid_travel/SPEED:7.1f} s")
print(f"  检测+切换 {5*n_ch}×6 = {grid_det:6.1f} s")
print(f"  合计 ≈ {grid_total:.1f} s")

# ---- 新：逐目标中心复测（最优回访路线）----
new_route = optimize_clearing_path(list(opt), last)
new_travel = compute_path_length(new_route, last)
new_det = n_ch * (DETECT_TIME + SWITCH_TIME)
new_total = new_travel / SPEED + new_det
print("\n--- 新：逐目标中心复测（N 次检测，最优回访）---")
print(f"  移动 {new_travel:8.1f} m = {new_travel/SPEED:7.1f} s")
print(f"  检测+切换 {n_ch}×6 = {new_det:6.1f} s")
print(f"  合计 ≈ {new_total:.1f} s")

print(f"\n节省 ≈ {grid_total - new_total:.1f} s "
      f"({(grid_total-new_total)/grid_total*100:.1f}%)")
