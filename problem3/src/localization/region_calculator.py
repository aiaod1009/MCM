"""
定位区域计算器

复用问题1的算法，计算两点交会定位的定位区域
"""

import numpy as np
import sys
import os

# 添加geometry模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from geometry.ray_intersection import ray_intersection
from geometry.point_in_sector import point_in_sectors
from geometry.rotating_calipers import rotating_calipers
from geometry.minimum_enclosing_circle import minimum_enclosing_circle

try:
    from geometry.convex_hull import compute_convex_hull
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("警告: scipy未安装，凸包计算将使用简化版本")


def compute_localization_region(
    detectors: np.ndarray,
    azimuths: np.ndarray,
    error: float = 1.0,
    tol: float = 1e-9
) -> dict:
    """
    计算定位区域（调用问题1算法，支持任意数量检测点全部观测求交）

    与问题一的模型 R = ∩ W_i 保持一致：定位区域为**所有**检测点示向度
    扇形约束的交集，而非仅取"交会角最佳的两个检测点"。多引入一个检测点
    只会额外增加一条扇形约束，使交集区域（在无误差意义下）不增大，
    因而能获得更紧、更可靠的定位区域。

    参数:
        detectors: 检测点坐标矩阵 n×2，n>=2
        azimuths: 示向度向量 n×1（度）
        error: 误差范围（度），默认±1°
        tol: 角度容差（度），默认 1e-9。
             定位区域的顶点必然落在扇区边界上，若用严格比较，浮点误差会
             随机把边界顶点判为"在扇区外"，导致凸包缺角甚至退化成单点。
             故边界判断必须带容差（与问题一 MATLAB 的角度容差 τ 一致）。

    返回:
        region_info: {
            'hull': 凸包顶点数组 m×2,
            'diameter': 直径（米）,
            'diameter_endpoints': (V_p, V_q) 直径端点,
            'center': 区域中心坐标 [x, y]（最小覆盖圆圆心）,
            'cover_radius': 最小覆盖圆半径 R_j（米）
        }

    算法流程（复用问题1）:
        1. 对每个检测点构造左右两条边界射线
        2. 计算所有射线对的交点
        3. 筛选在**所有**扇形内的有效顶点
        4. 计算凸包
        5. 使用旋转卡壳求直径
        6. 使用 Welzl 算法求最小覆盖圆（MEC），以其圆心为定位中心

    异常:
        ValueError: 无有效顶点（扇形无交集）
    """
    # 步骤0：归一化输入为数组
    detectors = np.asarray(detectors, dtype=float)
    azimuths = np.asarray(azimuths, dtype=float)
    if detectors.ndim == 1:
        detectors = detectors.reshape(1, -1)
    if detectors.shape[0] < 2:
        raise ValueError("交会定位至少需要 2 个检测点")
    n_detectors = detectors.shape[0]

    # 步骤2：构造边界射线
    rays = []

    for i, (detector, azimuth) in enumerate(zip(detectors, azimuths)):
        # 左边界射线
        theta_left = (azimuth - error) % 360
        direction_left = np.array([
            np.cos(np.deg2rad(theta_left)),
            np.sin(np.deg2rad(theta_left))
        ])
        rays.append({
            'origin': detector,
            'direction': direction_left,
            'type': 'left',
            'detector_id': i
        })

        # 右边界射线
        theta_right = (azimuth + error) % 360
        direction_right = np.array([
            np.cos(np.deg2rad(theta_right)),
            np.sin(np.deg2rad(theta_right))
        ])
        rays.append({
            'origin': detector,
            'direction': direction_right,
            'type': 'right',
            'detector_id': i
        })

    # 步骤3：计算所有射线交点
    candidates = []

    for i in range(len(rays)):
        for j in range(i + 1, len(rays)):
            P, is_valid = ray_intersection(
                rays[i]['origin'], rays[i]['direction'],
                rays[j]['origin'], rays[j]['direction']
            )
            if is_valid:
                candidates.append(P)

    if len(candidates) == 0:
        raise ValueError("未找到任何射线交点，请检查检测点配置")

    candidates = np.array(candidates)

    # 步骤4：筛选有效顶点（在所有扇形内的点，带角度容差 tol）
    valid_vertices = []

    for candidate in candidates:
        if point_in_sectors(candidate, detectors, azimuths, error, tol):
            valid_vertices.append(candidate)

    if len(valid_vertices) == 0:
        raise ValueError("未找到有效顶点，扇形区域无交集")

    # 去重：同一顶点可能同时是多条射线对的交点，需合并近重合点
    valid_vertices = np.array(valid_vertices)
    unique_vertices = []
    for v in valid_vertices:
        if not any(np.linalg.norm(v - u) < 1e-6 for u in unique_vertices):
            unique_vertices.append(v)
    valid_vertices = np.array(unique_vertices)

    # 步骤5：计算凸包
    if SCIPY_AVAILABLE and len(valid_vertices) >= 3:
        try:
            hull = compute_convex_hull(valid_vertices)
        except Exception:
            # 退化情形（共线等）导致 Qhull 失败时，回退为原始有效顶点
            hull = valid_vertices
    else:
        # 简化版本：少于3个点或无scipy时直接返回所有顶点
        hull = valid_vertices

    # 步骤6：旋转卡壳求直径
    diameter, V_p, V_q = rotating_calipers(hull)

    # 步骤7：最小覆盖圆（MEC）求定位中心与覆盖半径
    # 定位中心 c_j 取最小覆盖圆圆心（而非凸包顶点均值），
    # 覆盖半径 R_j 取最小覆盖圆半径。这样 c_j 具有"最坏误差最小化"意义：
    #   c_j = argmin_c  max_{x in Ω_j} ||x - c||,  R_j = max_x ||x - c_j||.
    # 与"直径的一半"不同，MEC 半径严格保证覆盖整个定位区域，
    # 可直接作为直接清除判据（R_j <= 20m）与精修停止条件。
    center, cover_radius = minimum_enclosing_circle(hull)

    return {
        'hull': hull,
        'diameter': diameter,
        'diameter_endpoints': (V_p, V_q),
        'center': center,
        'cover_radius': cover_radius
    }


# 测试代码
if __name__ == '__main__':
    print("测试 region_calculator.py")
    print("=" * 60)

    # 测试1：问题1的sample_case1配置
    print("测试1 - 问题1的sample_case1配置:")
    print("  检测点1: (0, 0), 示向度 45°")
    print("  检测点2: (100, 0), 示向度 135°")
    print("  误差范围: ±1°")

    S1 = np.array([0.0, 0.0])
    theta1 = 45.0
    S2 = np.array([100.0, 0.0])
    theta2 = 135.0
    error = 1.0

    try:
        region_info = compute_localization_region(
            np.array([S1, S2]), np.array([theta1, theta2]), error)

        print(f"\n  结果:")
        print(f"    凸包顶点数: {len(region_info['hull'])}")
        print(f"    直径: {region_info['diameter']:.4f} 米")
        print(f"    中心: {region_info['center']}")
        print(f"    直径端点1: {region_info['diameter_endpoints'][0]}")
        print(f"    直径端点2: {region_info['diameter_endpoints'][1]}")
        print()

        print("  凸包顶点坐标:")
        for i, vertex in enumerate(region_info['hull']):
            print(f"    顶点{i+1}: ({vertex[0]:.2f}, {vertex[1]:.2f})")

        print("\n  ✓ 测试1通过")

    except Exception as e:
        print(f"\n  ✗ 测试1失败: {e}")
        import traceback
        traceback.print_exc()

    print()

    # 测试2：阶段1实测数据（频道1，真实可交会的一对）
    print("测试2 - 阶段1实测数据（频道1）:")
    print("  检测点1: (0, 0), 示向度 326.37°")
    print("  检测点2: (900, 0), 示向度 264.09°")
    print("  误差范围: ±1°")

    S1 = np.array([0.0, 0.0])
    theta1 = 326.37
    S2 = np.array([900.0, 0.0])
    theta2 = 264.09
    error = 1.0

    try:
        region_info = compute_localization_region(
            np.array([S1, S2]), np.array([theta1, theta2]), error)

        print(f"\n  结果:")
        print(f"    凸包顶点数: {len(region_info['hull'])}")
        print(f"    直径: {region_info['diameter']:.4f} 米")
        print(f"    中心: {region_info['center']}")

        print("\n  ✓ 测试2通过")

    except Exception as e:
        print(f"\n  ✗ 测试2失败: {e}")

    print()

    # 测试3：无交集情况（两检测点的示向度背向，射线互不相交）
    print("测试3 - 无交集情况（示向度背向）:")
    print("  检测点1: (0, 0), 示向度 180°")
    print("  检测点2: (100, 0), 示向度 0°")
    print("  误差范围: ±1°")

    S1 = np.array([0.0, 0.0])
    theta1 = 180.0
    S2 = np.array([100.0, 0.0])
    theta2 = 0.0
    error = 1.0

    try:
        region_info = compute_localization_region(
            np.array([S1, S2]), np.array([theta1, theta2]), error)
        print(f"\n  ✗ 测试3失败: 应该抛出异常但没有")

    except ValueError as e:
        print(f"\n  ✓ 测试3通过: 正确抛出异常 - {e}")

    except Exception as e:
        print(f"\n  ✗ 测试3失败: 抛出了错误的异常 - {e}")

    print()
    print("=" * 60)
    print("测试完成！")
