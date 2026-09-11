"""
清除模块

阶段3专用：巡游清除算法

包含的模块：
- path_planner: 路径规划
- clear_strategy: 清除策略
- refine_strategy: 精修策略
- verification: 兜底验证
"""

from .path_planner import (
    plan_clearing_path_priority_greedy,
    two_opt_optimize
)
from .clear_strategy import clear_target
from .refine_strategy import (
    spiral_search,
    refine_and_retry
)
from .verification import (
    final_verification_scan,
    clear_remaining_sources
)

__all__ = [
    'plan_clearing_path_priority_greedy',
    'two_opt_optimize',
    'clear_target',
    'spiral_search',
    'refine_and_retry',
    'final_verification_scan',
    'clear_remaining_sources',
]
