"""
清除模块

阶段3专用：巡游清除算法

包含的模块：
- path_planner: 路径规划（优先级贪心 + 真 2-opt/Or-opt）
- clear_strategy: 清除策略
- refine_strategy: 精修策略
- verification: 清除复核与补救（基于 /clear 返回值，零盲扫）
"""

from .path_planner import (
    plan_clearing_path_priority_greedy,
    two_opt_optimize,
    or_opt_optimize,
    optimize_clearing_path,
    compute_path_length,
)
from .clear_strategy import clear_target
from .refine_strategy import (
    spiral_search,
    refine_and_retry
)
from .verification import (
    review_cleared,
    clear_remaining_sources
)

__all__ = [
    'plan_clearing_path_priority_greedy',
    'two_opt_optimize',
    'or_opt_optimize',
    'optimize_clearing_path',
    'compute_path_length',
    'clear_target',
    'spiral_search',
    'refine_and_retry',
    'review_cleared',
    'clear_remaining_sources',
]
