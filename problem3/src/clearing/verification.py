"""
兜底验证

确保100%清除率的最后一道防线
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def final_verification_scan(robot, cleared_targets: list) -> list:
    """
    最终验证扫描（兜底）

    策略:
    1. 回到原点(0,0)
    2. 扫描全部20个频道
    3. 检查是否有遗漏的干扰源
    4. 返回遗漏的频道列表

    参数:
        robot: 机器狗对象
        cleared_targets: 已清除的目标列表

    返回:
        remaining_channels: 遗漏的频道列表

    重要性:
        这是确保100%清除率的关键步骤！
    """
    print(f"\n{'='*60}")
    print(f"最终验证扫描")
    print(f"{'='*60}\n")

    # 回到原点，扫描全部20个频道
    print(f"移动到原点 (0, 0) 并扫描全部频道...")

    remaining_channels = []

    for channel in range(1, 21):
        # 使用 measure() 移动到原点并检测频道
        result = robot.measure((0.0, 0.0), channel)

        if result.get('code') == 0:
            measure_result = result.get('result')

            if measure_result == 'direction':
                angle = result.get('svd_deg')
                print(f"  频道 {channel:2d}: ⚠️  仍有信号！ θ={angle:.2f}°")
                remaining_channels.append(channel)
            elif channel % 5 == 0:  # 每5个频道打印一次
                print(f"  频道 1-{channel}: ✓ 已清除")

    if not remaining_channels:
        print(f"\n✓ 验证完成：所有干扰源已清除")
    else:
        print(f"\n⚠️  发现 {len(remaining_channels)} 个遗漏频道: {remaining_channels}")

    return remaining_channels


def clear_remaining_sources(robot, remaining_channels: list) -> int:
    """
    清除遗漏的干扰源

    策略:
    1. 对每个遗漏频道，重新单点定位
    2. 移动到估计位置
    3. 螺旋搜索清除

    参数:
        robot: 机器狗对象
        remaining_channels: 遗漏的频道列表

    返回:
        success_count: 成功清除的数量

    重要性:
        补救措施，确保不漏掉任何干扰源
    """
    print(f"\n{'='*60}")
    print(f"清除遗漏的干扰源")
    print(f"{'='*60}\n")

    success_count = 0

    for channel in remaining_channels:
        print(f"频道 {channel}:")

        # 从原点测向
        result = robot.measure((0.0, 0.0), channel)

        if result.get('code') != 0 or result.get('result') != 'direction':
            print(f"  ✗ 未检测到信号")
            continue

        angle = result.get('svd_deg')

        # 单点估计
        from localization.single_point_estimator import single_point_estimation

        estimated_position, uncertainty = single_point_estimation(
            np.array([0.0, 0.0]), angle
        )

        print(f"  估计位置: ({estimated_position[0]:.1f}, {estimated_position[1]:.1f})")
        print(f"  不确定度: {uncertainty:.1f} 米")

        # 移动到估计位置并尝试清除
        clear_result = robot.clear(tuple(estimated_position), channel)

        if clear_result.get('code') == 0 and clear_result.get('result') == 'success':
            print(f"  ✓ 成功清除")
            success_count += 1
        else:
            print(f"  → 启动螺旋搜索")

            # 创建临时目标对象
            from target import Target
            temp_target = Target(
                channel_id=channel,
                detection_points=[(np.array([0.0, 0.0]), angle)],
                center=estimated_position,
                diameter=uncertainty * 2,
                confidence=0.3,
                method='single_point'
            )

            # 导入螺旋搜索
            from clearing.refine_strategy import spiral_search

            # 搜索半径不超过清除半径20米
            effective_radius = min(uncertainty, 20.0)
            if spiral_search(robot, temp_target, search_radius=effective_radius, step=20):
                print(f"  ✓ 螺旋搜索成功清除")
                success_count += 1
            else:
                print(f"  ✗ 螺旋搜索失败")

    print(f"\n最终补救清除: {success_count}/{len(remaining_channels)}")

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
