"""
射线交点计算

从 problem1/utils/ray_intersection.m 移植
"""

import numpy as np
from typing import Tuple, Optional


def ray_intersection(
    O1: np.ndarray,
    D1: np.ndarray,
    O2: np.ndarray,
    D2: np.ndarray
) -> Tuple[Optional[np.ndarray], bool]:
    """
    计算两条射线的交点

    参数:
        O1: 射线1的起点 [x1, y1]
        D1: 射线1的方向向量 [dx1, dy1]
        O2: 射线2的起点 [x2, y2]
        D2: 射线2的方向向量 [dx2, dy2]

    返回:
        P: 交点坐标 [x, y]，若无有效交点则为 None
        is_valid: 布尔值，True表示有效交点，False表示平行或反向

    算法原理:
        射线1: P = O1 + t1 * D1  (t1 >= 0)
        射线2: P = O2 + t2 * D2  (t2 >= 0)
        求解线性方程组，判断 t1 和 t2 是否非负

    示例:
        >>> O1 = np.array([0.0, 0.0])
        >>> D1 = np.array([1.0, 0.0])
        >>> O2 = np.array([0.0, 0.0])
        >>> D2 = np.array([0.0, 1.0])
        >>> P, is_valid = ray_intersection(O1, D1, O2, D2)
        >>> print(P)  # [0.0, 0.0]
        >>> print(is_valid)  # True
    """
    # 计算行列式 (D1 × D2)
    delta = D1[0] * D2[1] - D1[1] * D2[0]

    # 判断平行（行列式接近0）
    if abs(delta) < 1e-10:
        return None, False

    # 计算从 O1 到 O2 的向量
    dx = O2[0] - O1[0]
    dy = O2[1] - O1[1]

    # 求解参数 t1 和 t2
    # t1 = ((O2 - O1) × D2) / (D1 × D2)
    # t2 = ((O2 - O1) × D1) / (D1 × D2)
    t1 = (dx * D2[1] - dy * D2[0]) / delta
    t2 = (dx * D1[1] - dy * D1[0]) / delta

    # 判断有效性（两个参数都必须 >= 0，表示交点在两条射线的正向上）
    if t1 >= 0 and t2 >= 0:
        P = O1 + t1 * D1
        return P, True
    else:
        return None, False


# 测试代码
if __name__ == '__main__':
    print("测试 ray_intersection.py")
    print("=" * 60)

    # 测试1：垂直相交
    O1 = np.array([0.0, 0.0])
    D1 = np.array([1.0, 0.0])
    O2 = np.array([5.0, -5.0])
    D2 = np.array([0.0, 1.0])

    P, is_valid = ray_intersection(O1, D1, O2, D2)
    print(f"测试1 - 垂直相交:")
    print(f"  O1={O1}, D1={D1}")
    print(f"  O2={O2}, D2={D2}")
    print(f"  结果: P={P}, is_valid={is_valid}")
    print(f"  预期: P=[5.0, 0.0], is_valid=True")
    print()

    # 测试2：平行射线（无交点）
    O1 = np.array([0.0, 0.0])
    D1 = np.array([1.0, 0.0])
    O2 = np.array([0.0, 1.0])
    D2 = np.array([1.0, 0.0])

    P, is_valid = ray_intersection(O1, D1, O2, D2)
    print(f"测试2 - 平行射线:")
    print(f"  O1={O1}, D1={D1}")
    print(f"  O2={O2}, D2={D2}")
    print(f"  结果: P={P}, is_valid={is_valid}")
    print(f"  预期: P=None, is_valid=False")
    print()

    # 测试3：反向射线（无交点）
    O1 = np.array([0.0, 0.0])
    D1 = np.array([1.0, 0.0])
    O2 = np.array([5.0, 0.0])
    D2 = np.array([1.0, 0.0])

    P, is_valid = ray_intersection(O1, D1, O2, D2)
    print(f"测试3 - 反向射线:")
    print(f"  O1={O1}, D1={D1}")
    print(f"  O2={O2}, D2={D2}")
    print(f"  结果: P={P}, is_valid={is_valid}")
    print(f"  预期: P=None, is_valid=False")
    print()

    print("=" * 60)
    print("测试完成！")
