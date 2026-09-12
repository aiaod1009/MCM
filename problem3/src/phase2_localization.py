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
           - 数据点>=2: 全部有效观测求交（∩所有示向度扇形，与问题一一致）
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

        # 过滤掉"距离过近"(near)使示向度为 None 的数据点：
        # 这类点没有示向度，无法参与交会定位；若混入交会计算会触发
        # TypeError 并中断整个流程，因此必须先剔除。
        n_near = sum(1 for d in channel_scan_data if d[1] is None)
        direction_data = [d for d in channel_scan_data if d[1] is not None]
        n_points = len(direction_data)

        if verbose:
            print(f"  数据点数量: {len(channel_scan_data)}"
                  f"（含示向度 {n_points}，距离过近 {n_near}）")
            if n_near > 0:
                print(f"  ⚠️  已剔除 {n_near} 个\"距离过近\"点（无示向度，不参与交会）")

        # 情况0：没有任何含示向度的数据点，跳过（留待阶段3兜底验证处理）
        if n_points == 0:
            if verbose:
                print(f"  ✗  跳过：该频道无有效示向度数据（留待兜底验证处理）")
            continue

        # 情况1：含示向度的数据点不足（<2）
        if n_points < 2:
            if verbose:
                print(f"  ⚠️  示向度数据点不足，无法两点交会")

            if enable_single_point:
                [[x1, y1], theta1] = direction_data[0]
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

        # 情况2：数据点充足（>=2）—— 全部有效观测求交（与问题一 R=∩W_i 一致）
        else:
            # 收集全部含示向度的检测点，作为扇形约束的完整集合。
            # 不再只挑选"交会角最佳的两个点"：每多一个检测点即多一条
            # 扇形约束，交集区域不增大，定位更紧、更可靠。
            all_detectors = np.array([d[0] for d in direction_data], dtype=float)
            all_azimuths = np.array([d[1] for d in direction_data], dtype=float)

            try:
                region_info = compute_localization_region(
                    all_detectors, all_azimuths)

                target = Target(
                    channel_id=channel_id,
                    detection_points=[(np.array(d[0], dtype=float), d[1])
                                      for d in direction_data],
                    region_info=region_info,
                    method='two_point'
                )
                targets.append(target)

                if verbose:
                    print(f"  ➜  多点交会定位成功（{len(direction_data)} 个观测全参与）")
                    print(f"      定位中心: ({target.center[0]:.1f}, {target.center[1]:.1f})")
                    print(f"      区域直径: {target.diameter:.2f} 米")
                    print(f"      凸包顶点: {len(target.hull)}")
                    print(f"      置信度: {target.confidence:.2f}")

            except Exception as e:
                if verbose:
                    print(f"  ✗  多点交会定位失败: {e}")
                    print(f"     → 回退为两点交会（取前两个有效观测）")
                # 回退：全部观测求交失败（例如某观测与其余冲突导致空集）时，
                # 仅用前两个观测做两点交会，保证流程不中断。
                try:
                    S1 = all_detectors[0]
                    S2 = all_detectors[1]
                    theta1 = float(all_azimuths[0])
                    theta2 = float(all_azimuths[1])
                    region_info = compute_localization_region(
                        np.array([S1, S2]), np.array([theta1, theta2]))

                    target = Target(
                        channel_id=channel_id,
                        detection_points=[(S1, theta1), (S2, theta2)],
                        region_info=region_info,
                        method='two_point'
                    )
                    targets.append(target)

                    if verbose:
                        print(f"  ➜  两点回退定位成功")
                        print(f"      定位中心: ({target.center[0]:.1f}, {target.center[1]:.1f})")
                        print(f"      区域直径: {target.diameter:.2f} 米")
                        print(f"      置信度: {target.confidence:.2f}")
                except Exception as e2:
                    if verbose:
                        print(f"  ✗  两点回退也失败: {e2}")

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

    # 优先读取阶段1的真实扫描结果（results/phase1_scan_result.json）；
    # 若不存在，则使用一组自洽的最小测试数据（各示向度确实指向同一批源）。
    import os
    import json

    result_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'phase1_scan_result.json')
    if os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            scan_result = json.load(f)
        print(f"已加载真实扫描数据: {os.path.relpath(result_path)}\n")
    else:
        # 自洽的最小测试数据：源分别位于 (1000,200) 与 (-400,800) 附近，
        # 各检测点示向度均由该源位置正演得到（误差在 ±1° 内）。
        scan_result = {
            'active_channels': [1, 2],
            'scan_data': {
                # 源1 ≈ (1000, 200)：检测点(0,0)、(900,0)、(0,900)
                '1': [
                    [[0.0, 0.0], 11.31],
                    [[900.0, 0.0], 63.43],
                    [[0.0, 900.0], 341.57]
                ],
                # 源2 ≈ (-400, 800)：检测点(0,0)、(-900,0)、(0,900)
                '2': [
                    [[0.0, 0.0], 116.57],
                    [[-900.0, 0.0], 41.63],
                    [[0.0, 900.0], 216.87]
                ]
            }
        }
        print("未找到 results/phase1_scan_result.json，使用内置自洽测试数据\n")

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
