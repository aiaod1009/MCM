"""
几何算法模块

从问题1的MATLAB代码移植而来，用于问题3的交会定位计算。

包含的算法：
- ray_intersection: 射线交点计算
- point_in_sector: 判断点是否在扇形内
- convex_hull: 凸包计算（封装scipy）
- rotating_calipers: 旋转卡壳算法求凸包直径
"""

from .ray_intersection import ray_intersection
from .point_in_sector import point_in_sector, point_in_sectors
from .convex_hull import compute_convex_hull
from .rotating_calipers import rotating_calipers

__all__ = [
    'ray_intersection',
    'point_in_sector',
    'point_in_sectors',
    'compute_convex_hull',
    'rotating_calipers',
]
