"""
单点估计器

当只有一个检测点的数据时，使用单点估计给出大致位置
"""

import numpy as np
from typing import Tuple


# 目标区域为半径 1800 m 的圆域（干扰源必在域内），据此对单点估计作投影约束。
TARGET_REGION_RADIUS = 1800.0


def single_point_estimation(
    S: np.ndarray,
    theta: float,
    R_avg: float = 1250.0
) -> Tuple[np.ndarray, float]:
    """
    单点估计干扰源位置

    参数:
        S: 检测点坐标 [x, y]
        theta: 示向度（度）
        R_avg: 假设距离（米），默认1250（1000-1500的中点）

    返回:
        estimated_position: 估计位置 [x, y]
        uncertainty: 不确定度（米）

    算法原理:
        假设干扰源在示向度方向，距离为有效接收半径的平均值

    不确定度计算:
        - 径向不确定度：距离范围的一半 = (1500-1000)/2 = 250米
        - 切向不确定度：角度误差导致的偏移 = R_avg * tan(1°) ≈ 22米
        - 综合不确定度：sqrt(250² + 22²) ≈ 252米

    注意:
        这是一个粗略估计，仅用于无法进行两点交会定位的情况
        不确定度约252米，远大于清除半径20米

    约束:
        干扰源必在半径 1800 m 的目标圆域内，而单点估计（沿示向度取
        R_avg=1250 m）可能落到域外（例如 S=(900,0)、θ=304.24° 会估计出
        y≈-1033 m，若 θ 指向域外则可能更远）。因此估计结果会被投影回
        圆域：|P| > 1800 时按比例缩到圆周上，避免机器狗跑到无源区域空跑。

    示例:
        >>> S = np.array([900.0, 0.0])
        >>> theta = 304.24
        >>> position, uncertainty = single_point_estimation(S, theta)
        >>> print(f"估计位置: {position}")
        >>> print(f"不确定度: {uncertainty:.1f} 米")
    """
    # 计算估计位置
    theta_rad = np.deg2rad(theta)
    dx = R_avg * np.cos(theta_rad)
    dy = R_avg * np.sin(theta_rad)

    estimated_position = S + np.array([dx, dy])

    # 投影约束：干扰源必在半径 1800 m 的目标圆域内。
    # 单点估计沿示向度外推 R_avg，可能落在域外；此时缩到圆周上，
    # 避免机器狗为清除一个"不可能的域外位置"而长距离空跑。
    est_norm = float(np.linalg.norm(estimated_position))
    if est_norm > TARGET_REGION_RADIUS:
        estimated_position = estimated_position * (TARGET_REGION_RADIUS / est_norm)

    # 不确定度：考虑距离范围和角度误差

    # 径向不确定度：距离范围的一半
    # 有效接收半径：1000-1500米
    radial_uncertainty = (1500 - 1000) / 2  # 250米

    # 切向不确定度：角度误差导致的偏移
    # 误差范围：±1°
    tangential_uncertainty = R_avg * np.tan(np.deg2rad(1))  # ≈22米

    # 综合不确定度（欧氏距离）
    uncertainty = np.sqrt(radial_uncertainty**2 + tangential_uncertainty**2)
    # ≈252米

    return estimated_position, uncertainty


# 测试代码
if __name__ == '__main__':
    print("测试 single_point_estimator.py")
    print("=" * 60)

    # 测试1：频道10的实际数据
    print("测试1 - 频道10的实际数据:")
    S = np.array([900.0, 0.0])
    theta = 304.24

    position, uncertainty = single_point_estimation(S, theta)

    print(f"  检测点: {S}")
    print(f"  示向度: {theta}°")
    print(f"\n  估计位置: ({position[0]:.2f}, {position[1]:.2f})")
    print(f"  不确定度: {uncertainty:.2f} 米")

    # 验证不确定度计算
    radial = 250.0
    tangential = 1250 * np.tan(np.deg2rad(1))
    expected = np.sqrt(radial**2 + tangential**2)
    print(f"\n  不确定度分解:")
    print(f"    径向不确定度: {radial:.2f} 米")
    print(f"    切向不确定度: {tangential:.2f} 米")
    print(f"    综合不确定度: {expected:.2f} 米")
    print(f"  ✓ 与计算结果一致: {np.isclose(uncertainty, expected)}")

    print()

    # 测试2：不同示向度
    print("测试2 - 不同示向度的估计:")
    S = np.array([0.0, 0.0])

    test_cases = [
        (0.0, "正东"),
        (90.0, "正北"),
        (180.0, "正西"),
        (270.0, "正南"),
        (45.0, "东北"),
    ]

    for theta, direction in test_cases:
        position, uncertainty = single_point_estimation(S, theta)
        distance = np.linalg.norm(position - S)
        print(f"  示向度 {theta:5.1f}° ({direction:4s}): "
              f"估计位置 ({position[0]:7.2f}, {position[1]:7.2f}), "
              f"距离 {distance:.2f} 米")

    print()

    # 测试3：不同假设距离
    print("测试3 - 不同假设距离的影响:")
    S = np.array([0.0, 0.0])
    theta = 45.0

    for R_avg in [1000, 1250, 1500]:
        position, uncertainty = single_point_estimation(S, theta, R_avg)
        print(f"  R_avg={R_avg}米: "
              f"估计位置 ({position[0]:.2f}, {position[1]:.2f}), "
              f"不确定度 {uncertainty:.2f} 米")

    print()

    # 测试4：与清除半径的对比
    print("测试4 - 与清除半径的对比:")
    S = np.array([900.0, 0.0])
    theta = 304.24
    position, uncertainty = single_point_estimation(S, theta)

    clearance_radius = 20.0  # 清除半径
    diameter_for_coverage = 2 * clearance_radius  # 直径需要≤40米才能保证覆盖

    print(f"  不确定度: {uncertainty:.2f} 米")
    print(f"  清除半径: {clearance_radius:.2f} 米")
    print(f"  需要直径: ≤{diameter_for_coverage:.2f} 米")
    print(f"\n  结论: 单点估计不确定度 >> 清除半径")
    print(f"        无法保证在估计位置清除时能覆盖干扰源")
    print(f"        必须在阶段3进行精修或增加检测点")

    print()

    # 测试5：域外估计的投影约束
    print("测试5 - 目标圆域投影约束（半径1800m）:")
    for S, theta in [
        (np.array([900.0, 0.0]), 304.24),
        (np.array([900.0, 0.0]), 90.0),
        (np.array([0.0, 900.0]), 200.0),
    ]:
        raw = S + 1250.0 * np.array([np.cos(np.deg2rad(theta)), np.sin(np.deg2rad(theta))])
        pos, _ = single_point_estimation(S, theta)
        print(f"  S=({S[0]:.0f},{S[1]:.0f}) θ={theta:6.2f}°: "
              f"未约束({raw[0]:8.1f},{raw[1]:8.1f}) |{np.linalg.norm(raw):7.1f}m|  "
              f"→ 约束后({pos[0]:8.1f},{pos[1]:8.1f}) |{np.linalg.norm(pos):7.1f}m|")

    print()
    print("=" * 60)
    print("测试完成！")