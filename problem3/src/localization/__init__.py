"""
定位模块

阶段2专用：交会定位算法

包含的模块：
- region_calculator: 定位区域计算（复用问题1的算法）
- point_selector: 检测点选择策略
- single_point_estimator: 单点估计
"""

from .region_calculator import compute_localization_region
from .point_selector import (
    select_detection_points,
    evaluate_point_pair_quality,
    compute_intersection_angle
)
from .single_point_estimator import single_point_estimation

__all__ = [
    'compute_localization_region',
    'select_detection_points',
    'evaluate_point_pair_quality',
    'compute_intersection_angle',
    'single_point_estimation',
]
