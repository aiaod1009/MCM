"""
旋转卡壳算法

从 problem1/utils/rotating_calipers.m 移植
用于计算凸包的直径（最远点对距离）
"""

import numpy as np
from typing import Tuple


def rotating_calipers(hull: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
    """
    使用旋转卡壳算法计算凸包的直径

    参数:
        hull: 凸包顶点矩阵 m×2（按逆时针排列）

    返回:
        D: 直径长度（凸包中任意两点之间的最大距离）
        V_p: 直径对应的第一个端点坐标 [x, y]
        V_q: 直径对应的第二个端点坐标 [x, y]

    算法原理:
        旋转卡壳算法通过旋转一对平行线（"卡壳"）扫描凸包，
        在O(m)时间内找到最远点对，其中m是凸包顶点数。

    关键点:
        - Python索引从0开始，使用 % m 处理循环索引
        - 叉积 cross_prod > 0 表示应该继续移动 j 指针

    示例:
        >>> hull = np.array([[0, 0], [10, 0], [10, 10], [0, 10]])
        >>> D, V_p, V_q = rotating_calipers(hull)
        >>> print(f"直径: {D:.2f}")
        >>> print(f"端点1: {V_p}")
        >>> print(f"端点2: {V_q}")
    """
    m = len(hull)

    # 边界情况处理
    if m < 2:
        return 0.0, hull[0], hull[0]

    # 对于小的凸包（顶点数<=3），直接暴力枚举所有点对
    if m <= 3:
        D = 0.0
        V_p = hull[0]
        V_q = hull[0]

        for i in range(m):
            for j in range(i + 1, m):
                dist = np.linalg.norm(hull[i] - hull[j])
                if dist > D:
                    D = dist
                    V_p = hull[i]
                    V_q = hull[j]

        return D, V_p, V_q

    # 初始化
    D = 0.0  # 最大直径
    V_p = hull[0]  # 直径端点1
    V_q = hull[0]  # 直径端点2

    # 找初始最远点对（找距离hull[0]最远的点）
    j = 0
    max_dist_init = 0.0
    for k in range(m):
        dist_k = np.linalg.norm(hull[k] - hull[0])
        if dist_k > max_dist_init:
            max_dist_init = dist_k
            j = k

    # 遍历凸包的每条边
    for i in range(m):
        i_idx = i % m  # 当前顶点索引
        j_idx = j % m  # 对偶顶点索引

        # 当前边向量
        i_next_idx = (i + 1) % m
        edge = hull[i_next_idx] - hull[i_idx]

        # 旋转j指针直到不能再增加投影
        # 防止无限循环，最多旋转m次
        for _ in range(m):
            j_next_idx = (j + 1) % m
            vec_j = hull[j_next_idx] - hull[j_idx]

            # 计算叉积判断是否继续旋转
            # cross_prod = edge × vec_j
            cross_prod = edge[0] * vec_j[1] - edge[1] * vec_j[0]

            if cross_prod > 0:
                # 继续移动j指针
                j = j + 1
                j_idx = j % m
            else:
                # 停止旋转
                break

        # 计算当前点对的距离
        dist = np.linalg.norm(hull[i_idx] - hull[j_idx])
        if dist > D:
            D = dist
            V_p = hull[i_idx]
            V_q = hull[j_idx]

    return D, V_p, V_q


# 测试代码
if __name__ == '__main__':
    print("测试 rotating_calipers.py")
    print("=" * 60)

    # 测试1：正方形
    print("测试1 - 正方形:")
    hull = np.array([
        [0.0, 0.0],
        [10.0, 0.0],
        [10.0, 10.0],
        [0.0, 10.0]
    ])
    D, V_p, V_q = rotating_calipers(hull)
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  直径: {D:.4f} 米")
    print(f"  端点1: {V_p}")
    print(f"  端点2: {V_q}")
    print(f"  预期直径: {np.sqrt(200):.4f} 米 (对角线)")
    print()

    # 测试2：三角形（问题1的sample_case1）
    print("测试2 - 三角形（问题1的sample_case1）:")
    hull = np.array([
        [49.50, 51.26],
        [50.50, 51.26],
        [50.00, 51.79]
    ])
    D, V_p, V_q = rotating_calipers(hull)
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  直径: {D:.4f} 米")
    print(f"  端点1: {V_p}")
    print(f"  端点2: {V_q}")
    print(f"  预期直径: 1.0034 米")
    print()

    # 测试3：单点（退化情况）
    print("测试3 - 单点（退化情况）:")
    hull = np.array([
        [50.0, 51.78]
    ])
    D, V_p, V_q = rotating_calipers(hull)
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  直径: {D:.4f} 米")
    print(f"  端点1: {V_p}")
    print(f"  端点2: {V_q}")
    print(f"  预期直径: 0.0000 米")
    print()

    # 测试4：两点（退化情况）
    print("测试4 - 两点（退化情况）:")
    hull = np.array([
        [0.0, 0.0],
        [100.0, 0.0]
    ])
    D, V_p, V_q = rotating_calipers(hull)
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  直径: {D:.4f} 米")
    print(f"  端点1: {V_p}")
    print(f"  端点2: {V_q}")
    print(f"  预期直径: 100.0000 米")
    print()

    # 测试5：长方形
    print("测试5 - 长方形:")
    hull = np.array([
        [0.0, 0.0],
        [20.0, 0.0],
        [20.0, 10.0],
        [0.0, 10.0]
    ])
    D, V_p, V_q = rotating_calipers(hull)
    expected_D = np.sqrt(20**2 + 10**2)
    print(f"  凸包顶点数: {len(hull)}")
    print(f"  直径: {D:.4f} 米")
    print(f"  端点1: {V_p}")
    print(f"  端点2: {V_q}")
    print(f"  预期直径: {expected_D:.4f} 米 (对角线)")
    print()

    # 测试6：暴力验证（对比暴力枚举）
    print("测试6 - 暴力验证（对比暴力枚举）:")
    hull = np.array([
        [0.0, 0.0],
        [10.0, 2.0],
        [15.0, 10.0],
        [8.0, 12.0],
        [2.0, 8.0]
    ])

    # 旋转卡壳结果
    D_rc, V_p_rc, V_q_rc = rotating_calipers(hull)

    # 暴力枚举结果
    D_bf = 0.0
    V_p_bf = hull[0]
    V_q_bf = hull[0]
    for i in range(len(hull)):
        for j in range(i + 1, len(hull)):
            dist = np.linalg.norm(hull[i] - hull[j])
            if dist > D_bf:
                D_bf = dist
                V_p_bf = hull[i]
                V_q_bf = hull[j]

    print(f"  凸包顶点数: {len(hull)}")
    print(f"  旋转卡壳直径: {D_rc:.4f} 米")
    print(f"  暴力枚举直径: {D_bf:.4f} 米")
    print(f"  差异: {abs(D_rc - D_bf):.6f} 米")
    print(f"  验证: {'✓ 通过' if abs(D_rc - D_bf) < 1e-6 else '✗ 失败'}")
    print()

    print("=" * 60)
    print("测试完成！")
