"""
兜底验证

确保100%清除率的最后一道防线
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def final_verification_scan(robot, cleared_targets: list) -> tuple:
    """
    最终验证扫描（兜底） - 增强版多点扫描

    策略:
    1. 在多个验证点扫描全部20个频道
    2. 验证点布局：原点 + 4个方向点（东西南北）
    3. 覆盖逻辑：任意验证点发现信号即认为有遗漏
    4. 返回遗漏的频道列表和检测数据

    参数:
        robot: 机器狗对象
        cleared_targets: 已清除的目标列表

    返回:
        (remaining_channels, channel_detections):
            remaining_channels: 遗漏的频道列表
            channel_detections: 检测数据 {channel: [(point_idx, angle), ...]}

    重要性:
        这是确保100%清除率的关键步骤！
        多点验证解决单点覆盖盲区问题
    """
    print(f"\n{'='*60}")
    print(f"最终验证扫描（增强版-多点覆盖）")
    print(f"{'='*60}\n")

    # 多点验证布局：原点 + 4个方向
    # 覆盖半径：每个点1500米，确保整个1800米半径区域无盲区
    verification_points = [
        (0.0, 0.0),      # 原点（中心覆盖）
        (900.0, 0.0),    # 东（覆盖东部区域）
        (0.0, 900.0),    # 北（覆盖北部区域）
        (-900.0, 0.0),   # 西（覆盖西部区域）
        (0.0, -900.0)    # 南（覆盖南部区域）
    ]

    point_names = ["原点", "东点", "北点", "西点", "南点"]

    print(f"验证策略：5点覆盖")
    for i, (point, name) in enumerate(zip(verification_points, point_names)):
        print(f"  验证点{i+1} - {name}: ({point[0]:7.1f}, {point[1]:7.1f})")
    print(f"\n开始扫描全部20个频道...\n")

    # 记录每个频道在哪些点被检测到
    channel_detections = {}  # {channel: [(point_idx, angle), ...]}

    # 遍历所有验证点
    for point_idx, (point, name) in enumerate(zip(verification_points, point_names)):
        print(f"[验证点{point_idx+1}] {name}: ({point[0]:.1f}, {point[1]:.1f})")

        found_count = 0
        for channel in range(1, 21):
            # 使用 measure() 移动到验证点并检测频道
            result = robot.measure(point, channel)

            if result.get('code') == 0:
                measure_result = result.get('result')

                if measure_result == 'direction':
                    angle = result.get('svd_deg')

                    if channel not in channel_detections:
                        channel_detections[channel] = []
                    channel_detections[channel].append((point_idx, angle))
                    found_count += 1

                    print(f"  频道 {channel:2d}: ⚠️  检测到信号！ θ={angle:.2f}°")

                elif measure_result == 'near':
                    # 距离过近也算检测到
                    if channel not in channel_detections:
                        channel_detections[channel] = []
                    channel_detections[channel].append((point_idx, None))
                    found_count += 1

                    print(f"  频道 {channel:2d}: ⚠️  检测到信号（距离过近）")

        if found_count == 0:
            print(f"  → 本点未检测到遗漏频道")
        else:
            print(f"  → 本点检测到 {found_count} 个遗漏频道")
        print()

    # 汇总遗漏频道
    remaining_channels = sorted(channel_detections.keys())

    if not remaining_channels:
        print(f"\n✓ 验证完成：所有干扰源已清除（5点验证均无信号）")
    else:
        print(f"\n⚠️  发现 {len(remaining_channels)} 个遗漏频道: {remaining_channels}")
        print(f"\n遗漏频道详细信息:")
        for ch in remaining_channels:
            detections = channel_detections[ch]
            detected_points = [point_names[idx] for idx, _ in detections]
            print(f"  频道 {ch:2d}: 在 {len(detections)} 个验证点检测到 - {', '.join(detected_points)}")

    return remaining_channels, channel_detections


def clear_remaining_sources(robot, remaining_channels: list, channel_detections: dict = None) -> int:
    """
    清除遗漏的干扰源 - 增强版

    策略:
    1. 利用验证扫描时获得的多点测向数据
    2. 如果有2个以上数据点，使用两点交会定位
    3. 否则使用单点估计
    4. 移动到估计位置并尝试清除
    5. 失败则螺旋搜索

    参数:
        robot: 机器狗对象
        remaining_channels: 遗漏的频道列表
        channel_detections: 验证扫描时的检测数据 {channel: [(point_idx, angle), ...]}

    返回:
        success_count: 成功清除的数量

    重要性:
        补救措施，确保不漏掉任何干扰源
    """
    print(f"\n{'='*60}")
    print(f"清除遗漏的干扰源（增强版）")
    print(f"{'='*60}\n")

    # 验证点坐标映射
    verification_points = [
        np.array([0.0, 0.0]),      # 原点
        np.array([900.0, 0.0]),    # 东
        np.array([0.0, 900.0]),    # 北
        np.array([-900.0, 0.0]),   # 西
        np.array([0.0, -900.0])    # 南
    ]

    success_count = 0

    for channel in remaining_channels:
        print(f"频道 {channel}:")

        # 尝试利用验证时的测向数据
        detection_data = []
        if channel_detections and channel in channel_detections:
            detections = channel_detections[channel]
            print(f"  验证时检测点数: {len(detections)}")

            # 收集有效的测向数据（排除距离过近的）
            for point_idx, angle in detections:
                if angle is not None:  # 有示向度数据
                    point = verification_points[point_idx]
                    detection_data.append((point, angle))
                    print(f"    验证点{point_idx+1}: ({point[0]:.0f}, {point[1]:.0f}), θ={angle:.2f}°")

        # 策略选择：根据数据点数量
        if len(detection_data) >= 2:
            # 有足够数据，使用两点交会定位
            print(f"  → 使用两点交会定位（精度高）")

            try:
                from localization.point_selector import select_detection_points
                from localization.region_calculator import compute_localization_region

                # 转换为阶段2的数据格式
                scan_data_refined = [[list(point), angle] for point, angle in detection_data]

                S1, theta1, S2, theta2, quality = select_detection_points(scan_data_refined)

                if S1 is not None:
                    # 计算定位区域
                    region_info = compute_localization_region(S1, theta1, S2, theta2)
                    estimated_position = region_info['center']
                    uncertainty = region_info['diameter']

                    print(f"    交会定位中心: ({estimated_position[0]:.1f}, {estimated_position[1]:.1f})")
                    print(f"    区域直径: {uncertainty:.1f} 米")
                else:
                    raise ValueError("无法选择有效检测点对")

            except Exception as e:
                print(f"    ✗ 交会定位失败: {e}")
                print(f"    → 回退到单点估计")

                # 回退：使用第一个检测点的单点估计
                point, angle = detection_data[0]
                from localization.single_point_estimator import single_point_estimation
                estimated_position, uncertainty = single_point_estimation(point, angle)

                print(f"    单点估计位置: ({estimated_position[0]:.1f}, {estimated_position[1]:.1f})")
                print(f"    不确定度: {uncertainty:.1f} 米")

        elif len(detection_data) == 1:
            # 只有1个数据点，单点估计
            print(f"  → 使用单点估计")

            point, angle = detection_data[0]
            from localization.single_point_estimator import single_point_estimation
            estimated_position, uncertainty = single_point_estimation(point, angle)

            print(f"    估计位置: ({estimated_position[0]:.1f}, {estimated_position[1]:.1f})")
            print(f"    不确定度: {uncertainty:.1f} 米")

        else:
            # 没有测向数据（全是距离过近），从原点估计
            print(f"  ⚠️  无测向数据，从原点中心估计")
            estimated_position = np.array([0.0, 0.0])
            uncertainty = 1800.0  # 最大不确定度

        # 尝试清除
        clear_result = robot.clear(tuple(estimated_position), channel)

        if clear_result.get('code') == 0 and clear_result.get('result') == 'success':
            print(f"  ✓ 直接清除成功")
            success_count += 1
        else:
            print(f"  → 直接清除失败，启动螺旋搜索")

            # 创建临时目标对象
            from target import Target
            temp_target = Target(
                channel_id=channel,
                detection_points=detection_data if detection_data else [(np.array([0.0, 0.0]), 0.0)],
                center=estimated_position,
                diameter=uncertainty * 2,
                confidence=0.4,
                method='verification_recovery'
            )

            # 导入螺旋搜索
            from clearing.refine_strategy import spiral_search

            # 搜索半径：根据不确定度动态调整
            # 如果不确定度很大（>100米），使用更大的搜索半径
            if uncertainty > 100:
                effective_radius = 40.0  # 增加到40米以提高搜索覆盖
                print(f"    高不确定度({uncertainty:.1f}米)，使用扩展搜索半径: {effective_radius}米")
            else:
                effective_radius = min(uncertainty, 20.0)

            print(f"    螺旋搜索半径: {effective_radius:.1f} 米")

            if spiral_search(robot, temp_target, search_radius=effective_radius, step=10):
                print(f"  ✓ 螺旋搜索成功清除")
                success_count += 1
            else:
                print(f"  ✗ 螺旋搜索失败")

        print()  # 空行分隔

    print(f"最终补救清除: {success_count}/{len(remaining_channels)}")

    return success_count


# 测试代码
if __name__ == '__main__':
    print("测试 verification.py")
    print("=" * 60)

    print("\n注意：此模块需要模拟器连接才能完整测试")
    print("这里只展示接口定义和流程")

    print("\n兜底验证流程：")
    print("  1. 回到原点(0, 0)")
    print("  2. 扫描全部20个频道")
    print("  3. 检查是否有遗漏")
    print("  4. 如果有遗漏：")
    print("     a. 重新单点定位")
    print("     b. 移动到估计位置")
    print("     c. 螺旋搜索清除")

    print("\n重要性：")
    print("  ⚠️  这是确保100%清除率的最后一道防线！")
    print("  ⚠️  绝对不能省略！")

    print("\n" + "=" * 60)
    print("接口定义验证完成！")
