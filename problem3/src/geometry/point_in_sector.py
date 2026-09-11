"""
扇形区域判断

从 problem1/utils/point_in_sectors.m 移植
"""

import numpy as np
from typing import Union


def point_in_sector(
    P: np.ndarray,
    detector: np.ndarray,
    azimuth: float,
    error: float
) -> bool:
    """
    判断点是否在单个检测点的扇形区域内

    参数:
        P: 待判断点坐标 [x, y]
        detector: 检测点坐标 [x, y]
        azimuth: 示向度（度）
        error: 误差范围（度）

    返回:
        is_inside: 布尔值，True表示点在扇形内，False表示不在

    算法原理:
        1. 计算从检测点到P的方位角
        2. 判断该角度是否在 [azimuth-error, azimuth+error] 范围内
        3. 需要特别处理跨越0度的情况
    """
    # 计算从检测点到P的向量
    vec = P - detector

    # 计算方位角（使用atan2得到[-180, 180]范围的角度）
    angle_to_P = np.rad2deg(np.arctan2(vec[1], vec[0]))

    # 转换到[0, 360)范围
    angle_to_P = angle_to_P % 360

    # 计算扇形的角度范围
    theta_min = (azimuth - error) % 360
    theta_max = (azimuth + error) % 360

    # 判断是否在扇形内（需要处理跨越0度的情况）
    if theta_min <= theta_max:
        # 正常情况：扇形不跨越0度
        # 例如：扇形范围 [44, 46]，点的角度应该在此范围内
        if angle_to_P < theta_min or angle_to_P > theta_max:
            return False
    else:
        # 跨越0度的情况：扇形范围如 [359, 1]
        # 点的角度应该 >= 359 或 <= 1
        if angle_to_P < theta_min and angle_to_P > theta_max:
            return False

    return True


def point_in_sectors(
    P: np.ndarray,
    detectors: np.ndarray,
    azimuths: np.ndarray,
    error: float
) -> bool:
    """
    判断点是否在所有检测点的扇形区域内

    参数:
        P: 待判断点坐标 [x, y]
        detectors: 检测点坐标矩阵 n×2
        azimuths: 示向度向量 n×1（度）
        error: 误差范围（度）

    返回:
        is_inside: 布尔值，True表示点在所有扇形内，False表示至少有一个不在

    示例:
        >>> P = np.array([50.0, 50.0])
        >>> detectors = np.array([[0.0, 0.0], [100.0, 0.0]])
        >>> azimuths = np.array([45.0, 135.0])
        >>> error = 1.0
        >>> result = point_in_sectors(P, detectors, azimuths, error)
        >>> print(result)  # True 或 False
    """
    n = len(detectors)

    for i in range(n):
        if not point_in_sector(P, detectors[i], azimuths[i], error):
            return False

    return True


# 测试代码
if __name__ == '__main__':
    print("测试 point_in_sector.py")
    print("=" * 60)

    # 测试1：点在扇形内（正常情况）
    P = np.array([1.0, 1.0])
    detector = np.array([0.0, 0.0])
    azimuth = 45.0
    error = 5.0

    result = point_in_sector(P, detector, azimuth, error)
    angle_to_P = np.rad2deg(np.arctan2(P[1] - detector[1], P[0] - detector[0]))
    print(f"测试1 - 点在扇形内（正常情况）:")
    print(f"  P={P}, detector={detector}")
    print(f"  azimuth={azimuth}°, error=±{error}°")
    print(f"  扇形范围: [{azimuth - error}°, {azimuth + error}°]")
    print(f"  点的方位角: {angle_to_P}°")
    print(f"  结果: {result}")
    print(f"  预期: True")
    print()

    # 测试2：点在扇形外
    P = np.array([1.0, 0.0])
    detector = np.array([0.0, 0.0])
    azimuth = 45.0
    error = 5.0

    result = point_in_sector(P, detector, azimuth, error)
    angle_to_P = np.rad2deg(np.arctan2(P[1] - detector[1], P[0] - detector[0]))
    print(f"测试2 - 点在扇形外:")
    print(f"  P={P}, detector={detector}")
    print(f"  azimuth={azimuth}°, error=±{error}°")
    print(f"  扇形范围: [{azimuth - error}°, {azimuth + error}°]")
    print(f"  点的方位角: {angle_to_P}°")
    print(f"  结果: {result}")
    print(f"  预期: False")
    print()

    # 测试3：跨越0度的扇形
    P = np.array([1.0, 0.1])
    detector = np.array([0.0, 0.0])
    azimuth = 0.0
    error = 10.0

    result = point_in_sector(P, detector, azimuth, error)
    angle_to_P = np.rad2deg(np.arctan2(P[1] - detector[1], P[0] - detector[0]))
    print(f"测试3 - 跨越0度的扇形:")
    print(f"  P={P}, detector={detector}")
    print(f"  azimuth={azimuth}°, error=±{error}°")
    print(f"  扇形范围: [{(azimuth - error) % 360}°, {(azimuth + error) % 360}°]")
    print(f"  点的方位角: {angle_to_P}°")
    print(f"  结果: {result}")
    print(f"  预期: True")
    print()

    # 测试4：多个检测点
    P = np.array([50.0, 51.0])
    detectors = np.array([
        [0.0, 0.0],
        [100.0, 0.0],
        [50.0, 80.0]
    ])
    azimuths = np.array([45.0, 135.0, 270.0])
    error = 1.0

    result = point_in_sectors(P, detectors, azimuths, error)
    print(f"测试4 - 多个检测点（问题1的sample_case1）:")
    print(f"  P={P}")
    print(f"  检测点数量: {len(detectors)}")
    for i in range(len(detectors)):
        vec = P - detectors[i]
        angle = np.rad2deg(np.arctan2(vec[1], vec[0])) % 360
        in_sector = point_in_sector(P, detectors[i], azimuths[i], error)
        print(f"    检测点{i+1}: {detectors[i]}, 示向度{azimuths[i]}°, "
              f"点的角度{angle:.2f}°, 在扇形内: {in_sector}")
    print(f"  结果: {result}")
    print()

    print("=" * 60)
    print("测试完成！")
