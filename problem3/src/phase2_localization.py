"""
阶段2：逐源交会定位

主流程模块，整合所有定位算法
"""

import numpy as np
from typing import List
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from localization.point_selector import select_detection_points
from localization.region_calculator import compute_localization_region
from localization.single_point_estimator import single_point_estimation
from target import Target


def phase2_localization(
    scan_result: dict,
    enable_single_point: bool = True,
    verbose: bool = True
) -> List[Target]:
    """
    阶段2：逐源交会定位

    参数:
        scan_result: 阶段1输出结果
            {
                'active_channels': [1, 2, 3, ...],
                'scan_data': {
                    '1': [[[x, y], theta], ...],
                    '2': [...],
                    ...
                }
            }
        enable_single_point: 是否对单点频道使用估计（默认True）
        verbose: 是否打印详细信息（默认True）

    返回:
        targets: 目标列表（按直径排序）

    算法流程:
        1. 遍历所有活跃频道
        2. 对每个频道:
           - 数据点<2: 单点估计或跳过
           - 数据点>=2: 选择最优检测点对，进行两点交会定位
        3. 按直径排序（小→大）

    输出示例:
        Target(CH1, center=(100.0, 200.0), diameter=15.2m, conf=0.85, method=two_point)
        Target(CH2, center=(300.0, 400.0), diameter=22.5m, conf=0.72, method=two_point)
        Target(CH10, center=(800.0, -500.0), diameter=504.0m, conf=0.30, method=single_point)
    """
    active_channels = scan_result['active_channels']
    scan_data = scan_result['scan_data']

    targets = []

    if verbose:
        print(f"\n{'='*60}")
        print(f"阶段2：逐源交会定位")
        print(f"{'='*60}\n")
        print(f"活跃频道数: {len(active_channels)}")
        print(f"频道列表: {active_channels}\n")

    for channel_id in active_channels:
        if verbose:
            print(f"{'─'*60}")
            print(f"频道 {channel_id}:")

        channel_scan_data = scan_data[str(channel_id)]
        n_points = len(channel_scan_data)

        if verbose:
            print(f"  数据点数量: {n_points}")

        # 情况1：数据点不足（<2）
        if n_points < 2:
            if verbose:
                print(f"  ⚠️  数据点不足，无法两点交会")

            if enable_single_point:
                [[x1, y1], theta1] = channel_scan_data[0]
                S1 = np.array([x1, y1])

                position, uncertainty = single_point_estimation(S1, theta1)

                target = Target(
                    channel_id=channel_id,
                    detection_points=[(S1, theta1)],
                    center=position,
                    diameter=uncertainty * 2,
                    confidence=0.3,
                    method='single_point'
                )
                targets.append(target)

                if verbose:
                    print(f"  ➜  使用单点估计")
                    print(f"      检测点: ({S1[0]:.1f}, {S1[1]:.1f}), 示向度: {theta1:.2f}°")
                    print(f"      估计中心: ({position[0]:.1f}, {position[1]:.1f})")
                    print(f"      不确定度: {uncertainty:.1f} 米")
                    print(f"      置信度: {target.confidence:.2f}")
            else:
                if verbose:
                    print(f"  ✗  跳过（单点估计已禁用）")

        # 情况2：数据点充足（>=2）
        else:
            S1, theta1, S2, theta2, quality = select_detection_points(channel_scan_data)

            if S1 is not None:
                if verbose:
                    print(f"  ✓  检测点选择完成")
                    print(f"      检测点1: ({S1[0]:.1f}, {S1[1]:.1f}), 示向度: {theta1:.2f}°")
                    print(f"      检测点2: ({S2[0]:.1f}, {S2[1]:.1f}), 示向度: {theta2:.2f}°")
                    print(f"      质量评分: {quality:.4f}")

                try:
                    region_info = compute_localization_region(S1, theta1, S2, theta2)

                    target = Target(
                        channel_id=channel_id,
                        detection_points=[(S1, theta1), (S2, theta2)],
                        region_info=region_info,
                        method='two_point'
                    )
                    targets.append(target)

                    if verbose:
                        print(f"  ➜  两点交会定位成功")
                        print(f"      定位中心: ({target.center[0]:.1f}, {target.center[1]:.1f})")
                        print(f"      区域直径: {target.diameter:.2f} 米")
                        print(f"      凸包顶点: {len(target.hull)}")
                        print(f"      置信度: {target.confidence:.2f}")

                except Exception as e:
                    if verbose:
                        print(f"  ✗  定位失败: {e}")
            else:
                if verbose:
                    print(f"  ✗  检测点选择失败")

        if verbose:
            print()

    # 按直径排序（小到大）
    targets.sort(key=lambda t: t.diameter)

    if verbose:
        print(f"{'='*60}")
        print(f"阶段2完成：成功定位 {len(targets)} 个干扰源")
        print(f"{'='*60}\n")

        if len(targets) > 0:
            print("定位结果汇总（按直径排序）:")
            print(f"{'─'*60}")
            for i, target in enumerate(targets, 1):
                status = "✓" if target.method == 'two_point' else "⚠"
                print(f"{i:2d}. {status} {target}")
            print()

    return targets


# 测试代码
if __name__ == '__main__':
    print("测试 phase2_localization.py")
    print("=" * 60)

    # 模拟阶段1的输出数据（基于2026-09-11的实测结果）
    scan_result = {
        'active_channels': [1, 2, 3, 4, 5, 7, 10, 20],
        'scan_data': {
            # 频道1: 5个数据点
            '1': [
                [[0.0, 0.0], 197.56],
                [[900.0, 0.0], 229.45],
                [[0.0, 900.0], 225.03],
                [[-900.0, 0.0], 170.87],
                [[0.0, -900.0], 169.55]
            ],
            # 频道2: 5个数据点
            '2': [
                [[0.0, 0.0], 210.12],
                [[900.0, 0.0], 242.87],
                [[0.0, 900.0], 238.45],
                [[-900.0, 0.0], 184.32],
                [[0.0, -900.0], 182.91]
            ],
            # 频道3: 3个数据点
            '3': [
                [[0.0, 0.0], 185.34],
                [[900.0, 0.0], 217.89],
                [[0.0, 900.0], 213.21]
            ],
            # 频道4: 2个数据点（最低）
            '4': [
                [[0.0, 0.0], 195.78],
                [[900.0, 0.0], 228.34]
            ],
            # 频道5: 3个数据点
            '5': [
                [[0.0, 0.0], 205.45],
                [[900.0, 0.0], 237.91],
                [[0.0, 900.0], 233.12]
            ],
            # 频道7: 2个数据点（最低）
            '7': [
                [[0.0, 0.0], 192.34],
                [[900.0, 0.0], 224.89]
            ],
            # 频道10: 1个数据点（无法交会）
            '10': [
                [[900.0, 0.0], 304.24]
            ],
            # 频道20: 4个数据点
            '20': [
                [[0.0, 0.0], 200.23],
                [[900.0, 0.0], 232.78],
                [[0.0, 900.0], 228.09],
                [[-900.0, 0.0], 174.56]
            ]
        }
    }

    print("\n使用模拟数据测试阶段2主流程:\n")

    # 运行阶段2
    targets = phase2_localization(scan_result, enable_single_point=True, verbose=True)

    # 输出统计信息
    print("\n统计信息:")
    print(f"{'─'*60}")
    print(f"总目标数: {len(targets)}")

    two_point_count = sum(1 for t in targets if t.method == 'two_point')
    single_point_count = sum(1 for t in targets if t.method == 'single_point')

    print(f"两点交会定位: {two_point_count} 个")
    print(f"单点估计: {single_point_count} 个")

    if len(targets) > 0:
        avg_diameter = np.mean([t.diameter for t in targets])
        avg_confidence = np.mean([t.confidence for t in targets])
        print(f"\n平均直径: {avg_diameter:.2f} 米")
        print(f"平均置信度: {avg_confidence:.2f}")

        # 找出直径最小和最大的
        min_target = min(targets, key=lambda t: t.diameter)
        max_target = max(targets, key=lambda t: t.diameter)

        print(f"\n直径最小: {min_target}")
        print(f"直径最大: {max_target}")

    print()
    print("=" * 60)
    print("测试完成！")
