"""
检测点选择策略

为单个频道选择最优的两个检测点进行交会定位
"""

import numpy as np
from typing import List, Tuple, Optional


def select_detection_points(
    scan_data_channel: List
) -> Tuple[Optional[np.ndarray], Optional[float], Optional[np.ndarray],
           Optional[float], float]:
    """
    为单个频道选择最优的两个检测点

    参数:
        scan_data_channel: 该频道的所有测向数据
            格式：[[[x1, y1], theta1], [[x2, y2], theta2], ...]
            例如：[[[0.0, 0.0], 197.56], [[900.0, 0.0], 229.45], ...]

    返回:
        S1: 检测点1坐标 [x, y]，若无有效组合则为 None
        theta1: 示向度1（度）
        S2: 检测点2坐标 [x, y]
        theta2: 示向度2（度）
        quality_score: 质量评分 (0.0-1.0)

    算法逻辑:
        - n < 2: 返回 None（无法交会）
        - n == 2: 别无选择，直接返回
        - n > 2: 暴力枚举所有组合，选择质量最高的

    示例:
        >>> scan_data = [
        ...     [[0.0, 0.0], 197.56],
        ...     [[900.0, 0.0], 229.45],
        ...     [[0.0, 900.0], 225.03]
        ... ]
        >>> S1, theta1, S2, theta2, quality = select_detection_points(scan_data)
        >>> print(f"最优组合: {S1}, {S2}, 质量: {quality:.2f}")
    """
    # 防御性过滤：剔除示向度为 None（来自"距离过近"测量）的数据点，
    # 它们没有方位信息，不能参与交会计算。
    scan_data_channel = [d for d in scan_data_channel if d[1] is not None]

    n = len(scan_data_channel)

    # 情况1：只有1个数据点，无法交会
    if n < 2:
        return None, None, None, None, 0.0

    # 情况2：只有2个数据点，别无选择
    if n == 2:
        [[x1, y1], theta1] = scan_data_channel[0]
        [[x2, y2], theta2] = scan_data_channel[1]
        S1 = np.array([x1, y1])
        S2 = np.array([x2, y2])

        quality = evaluate_point_pair_quality(S1, theta1, S2, theta2)

        return S1, theta1, S2, theta2, quality

    # 情况3：有多个数据点，选择最优组合
    best_pair = None
    best_quality = -1

    # 数据点<=20，直接暴力枚举所有组合（最多190种组合）
    for i in range(n):
        for j in range(i + 1, n):
            [[x1, y1], theta1] = scan_data_channel[i]
            [[x2, y2], theta2] = scan_data_channel[j]
            S1 = np.array([x1, y1])
            S2 = np.array([x2, y2])

            quality = evaluate_point_pair_quality(S1, theta1, S2, theta2)

            if quality > best_quality:
                best_quality = quality
                best_pair = (S1, theta1, S2, theta2)

    if best_pair is None:
        return None, None, None, None, 0.0

    return (*best_pair, best_quality)


def evaluate_point_pair_quality(
    S1: np.ndarray,
    theta1: float,
    S2: np.ndarray,
    theta2: float
) -> float:
    """
    评估检测点对的质量

    评分因素:
        1. 交会角（权重0.6）：越接近90°越好
        2. 基线长度（权重0.3）：800-1000米最佳
        3. 平行性检查（权重0.1）：避免示向度差<10°或>170°

    参数:
        S1: 检测点1坐标 [x, y]
        theta1: 示向度1（度）
        S2: 检测点2坐标 [x, y]
        theta2: 示向度2（度）

    返回:
        quality: 质量评分 (0.0-1.0)，越高越好

    示例:
        >>> S1 = np.array([0.0, 0.0])
        >>> theta1 = 45.0
        >>> S2 = np.array([900.0, 0.0])
        >>> theta2 = 135.0
        >>> quality = evaluate_point_pair_quality(S1, theta1, S2, theta2)
        >>> print(f"质量评分: {quality:.2f}")
    """
    # 1. 交会角评分（权重0.6）
    alpha = compute_intersection_angle(S1, theta1, S2, theta2)
    angle_score = 1.0 - abs(alpha - 90) / 90

    # 2. 基线长度评分（权重0.3）
    baseline = np.linalg.norm(S2 - S1)
    if 800 <= baseline <= 1000:
        baseline_score = 1.0
    elif baseline < 800:
        baseline_score = baseline / 800
    else:
        baseline_score = min(1000 / baseline, 1.0)

    # 3. 平行性检查（权重0.1）
    theta_diff = abs(theta1 - theta2)
    if theta_diff > 180:
        theta_diff = 360 - theta_diff

    if theta_diff < 10 or theta_diff > 170:
        # 接近平行或对向，严重惩罚
        parallel_penalty = 0.1
    else:
        parallel_penalty = 1.0

    # 综合评分
    quality = (0.6 * angle_score +
               0.3 * baseline_score +
               0.1 * parallel_penalty)

    return quality


def compute_intersection_angle(
    S1: np.ndarray,
    theta1: float,
    S2: np.ndarray,
    theta2: float
) -> float:
    """
    计算交会角（精确方法）

    参数:
        S1: 检测点1坐标 [x, y]
        theta1: 示向度1（度）
        S2: 检测点2坐标 [x, y]
        theta2: 示向度2（度）

    返回:
        alpha: 交会角（度），范围[0, 90]

    算法:
        计算两个方向向量的夹角，取绝对值确保在[0, 90]范围内

    示例:
        >>> S1 = np.array([0.0, 0.0])
        >>> theta1 = 0.0
        >>> S2 = np.array([100.0, 0.0])
        >>> theta2 = 90.0
        >>> angle = compute_intersection_angle(S1, theta1, S2, theta2)
        >>> print(f"交会角: {angle:.2f}°")
        交会角: 90.00°
    """
    # 方向向量
    dir1 = np.array([
        np.cos(np.deg2rad(theta1)),
        np.sin(np.deg2rad(theta1))
    ])
    dir2 = np.array([
        np.cos(np.deg2rad(theta2)),
        np.sin(np.deg2rad(theta2))
    ])

    # 计算夹角
    dot_product = np.dot(dir1, dir2)
    dot_product = np.clip(dot_product, -1.0, 1.0)

    angle = np.arccos(np.abs(dot_product))
    angle_deg = np.rad2deg(angle)

    return angle_deg


# 测试代码
if __name__ == '__main__':
    print("测试 point_selector.py")
    print("=" * 60)

    # 测试1：两个数据点（别无选择）
    print("测试1 - 两个数据点（频道4或7的情况）:")
    scan_data = [
        [[0.0, 0.0], 197.56],
        [[900.0, 0.0], 229.45]
    ]

    S1, theta1, S2, theta2, quality = select_detection_points(scan_data)

    print(f"  数据点数量: {len(scan_data)}")
    print(f"  选择结果:")
    print(f"    检测点1: {S1}, 示向度: {theta1}°")
    print(f"    检测点2: {S2}, 示向度: {theta2}°")
    print(f"    质量评分: {quality:.4f}")

    baseline = np.linalg.norm(S2 - S1)
    angle = compute_intersection_angle(S1, theta1, S2, theta2)
    print(f"  评估:")
    print(f"    基线长度: {baseline:.2f} 米")
    print(f"    交会角: {angle:.2f}°")
    print()

    # 测试2：多个数据点（选择最优）
    print("测试2 - 多个数据点（频道1的情况）:")
    scan_data = [
        [[0.0, 0.0], 197.56],
        [[900.0, 0.0], 229.45],
        [[0.0, 900.0], 225.03],
        [[-900.0, 0.0], 170.87],
        [[0.0, -900.0], 169.55]
    ]

    S1, theta1, S2, theta2, quality = select_detection_points(scan_data)

    print(f"  数据点数量: {len(scan_data)}")
    print(f"  选择结果:")
    print(f"    检测点1: {S1}, 示向度: {theta1}°")
    print(f"    检测点2: {S2}, 示向度: {theta2}°")
    print(f"    质量评分: {quality:.4f}")

    baseline = np.linalg.norm(S2 - S1)
    angle = compute_intersection_angle(S1, theta1, S2, theta2)
    print(f"  评估:")
    print(f"    基线长度: {baseline:.2f} 米")
    print(f"    交会角: {angle:.2f}°")
    print()

    # 测试3：枚举所有组合并排序
    print("  所有组合的质量评分（前3名）:")
    combinations = []
    for i in range(len(scan_data)):
        for j in range(i + 1, len(scan_data)):
            [[x1, y1], t1] = scan_data[i]
            [[x2, y2], t2] = scan_data[j]
            s1 = np.array([x1, y1])
            s2 = np.array([x2, y2])
            q = evaluate_point_pair_quality(s1, t1, s2, t2)
            combinations.append((i, j, q))

    combinations.sort(key=lambda x: x[2], reverse=True)

    for rank, (i, j, q) in enumerate(combinations[:3], 1):
        print(f"    第{rank}名: 数据点{i+1}-{j+1}, 质量: {q:.4f}")

    print()

    # 测试4：单个数据点（无法交会）
    print("测试3 - 单个数据点（频道10的情况）:")
    scan_data = [
        [[900.0, 0.0], 304.24]
    ]

    S1, theta1, S2, theta2, quality = select_detection_points(scan_data)

    print(f"  数据点数量: {len(scan_data)}")
    print(f"  选择结果: {S1}")
    print(f"  质量评分: {quality}")
    print(f"  ✓ 正确返回 None（数据点不足）")
    print()

    # 测试5：交会角计算
    print("测试4 - 交会角计算:")
    test_cases = [
        (0.0, 90.0, "垂直相交"),
        (0.0, 45.0, "45°夹角"),
        (0.0, 0.0, "平行"),
        (0.0, 180.0, "对向")
    ]

    for theta1, theta2, desc in test_cases:
        S1 = np.array([0.0, 0.0])
        S2 = np.array([100.0, 0.0])
        angle = compute_intersection_angle(S1, theta1, S2, theta2)
        print(f"  {desc}: theta1={theta1}°, theta2={theta2}° → 交会角={angle:.2f}°")

    print()
    print("=" * 60)
    print("测试完成！")
