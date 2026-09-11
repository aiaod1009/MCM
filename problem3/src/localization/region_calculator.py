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

try:
    from geometry.convex_hull import compute_convex_hull
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("警告: scipy未安装，凸包计算将使用简化版本")


def compute_localization_region(
    S1: np.ndarray,
    theta1: float,
    S2: np.ndarray,
    theta2: float,
    error: float = 1.0
) -> dict:
    """
    计算定位区域（调用问题1算法）

    参数:
        S1: 检测点1坐标 [x, y]
        theta1: 示向度1（度）
        S2: 检测点2坐标 [x, y]
        theta2: 示向度2（度）
        error: 误差范围（度），默认±1°

    返回:
        region_info: {
            'hull': 凸包顶点数组 m×2,
            'diameter': 直径（米）,
            'diameter_endpoints': (V_p, V_q) 直径端点,
            'center': 区域中心坐标 [x, y]
        }

    算法流程（复用问题1）:
        1. 构造4条边界射线（左边界和右边界）
        2. 计算所有射线对的交点
        3. 筛选在两个扇形内的有效顶点
        4. 计算凸包
        5. 使用旋转卡壳求直径

    异常:
        ValueError: 无有效顶点（扇形无交集）
    """
    # 步骤1：构造检测点和示向度数组
    detectors = np.array([S1, S2])
    azimuths = np.array([theta1, theta2])

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

    # 步骤4：筛选有效顶点（在所有扇形内的点）
    valid_vertices = []

    for candidate in candidates:
        if point_in_sectors(candidate, detectors, azimuths, error):
            valid_vertices.append(candidate)

    if len(valid_vertices) == 0:
        raise ValueError("未找到有效顶点，扇形区域无交集")

    valid_vertices = np.array(valid_vertices)

    # 步骤5：计算凸包
    if SCIPY_AVAILABLE and len(valid_vertices) >= 3:
        hull = compute_convex_hull(valid_vertices)
    else:
        # 简化版本：少于3个点或无scipy时直接返回所有顶点
        hull = valid_vertices

    # 步骤6：旋转卡壳求直径
    diameter, V_p, V_q = rotating_calipers(hull)

    # 步骤7：计算中心
    center = np.mean(hull, axis=0)

    return {
        'hull': hull,
        'diameter': diameter,
        'diameter_endpoints': (V_p, V_q),
        'center': center
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
        region_info = compute_localization_region(S1, theta1, S2, theta2, error)

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

    # 测试2：阶段1实测数据（频道1）
    print("测试2 - 阶段1实测数据（频道1）:")
    print("  检测点1: (0, 0), 示向度 197.56°")
    print("  检测点2: (900, 0), 示向度 229.45°")
    print("  误差范围: ±1°")

    S1 = np.array([0.0, 0.0])
    theta1 = 197.56
    S2 = np.array([900.0, 0.0])
    theta2 = 229.45
    error = 1.0

    try:
        region_info = compute_localization_region(S1, theta1, S2, theta2, error)

        print(f"\n  结果:")
        print(f"    凸包顶点数: {len(region_info['hull'])}")
        print(f"    直径: {region_info['diameter']:.4f} 米")
        print(f"    中心: {region_info['center']}")

        print("\n  ✓ 测试2通过")

    except Exception as e:
        print(f"\n  ✗ 测试2失败: {e}")

    print()

    # 测试3：无交集情况
    print("测试3 - 无交集情况（示向度背向）:")
    print("  检测点1: (0, 0), 示向度 0°")
    print("  检测点2: (100, 0), 示向度 180°")
    print("  误差范围: ±1°")

    S1 = np.array([0.0, 0.0])
    theta1 = 0.0
    S2 = np.array([100.0, 0.0])
    theta2 = 180.0
    error = 1.0

    try:
        region_info = compute_localization_region(S1, theta1, S2, theta2, error)
        print(f"\n  ✗ 测试3失败: 应该抛出异常但没有")

    except ValueError as e:
        print(f"\n  ✓ 测试3通过: 正确抛出异常 - {e}")

    except Exception as e:
        print(f"\n  ✗ 测试3失败: 抛出了错误的异常 - {e}")

    print()
    print("=" * 60)
    print("测试完成！")
