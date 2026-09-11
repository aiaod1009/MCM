"""
凸包计算

从 problem1/utils/compute_convex_hull.m 移植
使用 scipy.spatial.ConvexHull 封装
"""

import numpy as np
from scipy.spatial import ConvexHull


def compute_convex_hull(vertices: np.ndarray) -> np.ndarray:
    """
    计算有效顶点的凸包

    参数:
        vertices: 有效顶点坐标矩阵 m×2

    返回:
        hull: 凸包顶点坐标矩阵，按逆时针排列（不包含首尾重复点）

    算法实现:
        使用 scipy.spatial.ConvexHull 计算凸包
        scipy 的 ConvexHull 返回顶点索引，需要提取坐标

    示例:
        >>> vertices = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]])
        >>> hull = compute_convex_hull(vertices)
        >>> print(hull)
        [[0. 0.]
         [1. 0.]
         [1. 1.]
         [0. 1.]]
    """
    # 边界情况处理
    if len(vertices) < 3:
        return vertices

    # 使用 scipy 的 ConvexHull
    hull_obj = ConvexHull(vertices)

    # 提取凸包顶点坐标
    # hull_obj.vertices 是凸包顶点的索引（已按逆时针排列）
    hull = vertices[hull_obj.vertices]

    return hull


# 测试代码
if __name__ == '__main__':
    print("测试 convex_hull.py")
    print("=" * 60)

    # 测试1：正方形加一个内点
    print("测试1 - 正方形加一个内点:")
    vertices = np.array([
        [0.0, 0.0],
        [10.0, 0.0],
        [10.0, 10.0],
        [0.0, 10.0],
        [5.0, 5.0]  # 内点，不应在凸包上
    ])
    hull = compute_convex_hull(vertices)
    print(f"  输入顶点数: {len(vertices)}")
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  凸包顶点:")
    for i, v in enumerate(hull):
        print(f"    {i+1}: {v}")
    print(f"  预期: 4个顶点（正方形的四个角）")
    print()

    # 测试2：三角形
    print("测试2 - 三角形:")
    vertices = np.array([
        [0.0, 0.0],
        [100.0, 0.0],
        [50.0, 80.0]
    ])
    hull = compute_convex_hull(vertices)
    print(f"  输入顶点数: {len(vertices)}")
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  凸包顶点:")
    for i, v in enumerate(hull):
        print(f"    {i+1}: {v}")
    print(f"  预期: 3个顶点（三角形本身）")
    print()

    # 测试3：共线点（退化情况）
    print("测试3 - 两个点（退化情况）:")
    vertices = np.array([
        [0.0, 0.0],
        [10.0, 0.0]
    ])
    hull = compute_convex_hull(vertices)
    print(f"  输入顶点数: {len(vertices)}")
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  凸包顶点:")
    for i, v in enumerate(hull):
        print(f"    {i+1}: {v}")
    print(f"  预期: 2个顶点（直接返回原顶点）")
    print()

    # 测试4：单点（退化情况）
    print("测试4 - 单点（退化情况）:")
    vertices = np.array([
        [5.0, 5.0]
    ])
    hull = compute_convex_hull(vertices)
    print(f"  输入顶点数: {len(vertices)}")
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  凸包顶点:")
    for i, v in enumerate(hull):
        print(f"    {i+1}: {v}")
    print(f"  预期: 1个顶点（直接返回原顶点）")
    print()

    # 测试5：问题1的实际数据（sample_case1）
    print("测试5 - 问题1的sample_case1数据:")
    vertices = np.array([
        [49.50, 51.26],
        [50.50, 51.26],
        [50.00, 51.79]
    ])
    hull = compute_convex_hull(vertices)
    print(f"  输入顶点数: {len(vertices)}")
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  凸包顶点:")
    for i, v in enumerate(hull):
        print(f"    {i+1}: {v}")
    print(f"  预期: 3个顶点（三角形）")
    print()

    print("=" * 60)
    print("测试完成！")
