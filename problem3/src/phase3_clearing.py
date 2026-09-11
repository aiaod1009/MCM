"""
阶段3：巡游清除

主流程模块，整合路径规划、清除策略、精修和兜底验证
"""

import numpy as np
from typing import List
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from clearing.path_planner import plan_clearing_path_priority_greedy, two_opt_optimize
from clearing.clear_strategy import clear_target
from clearing.verification import final_verification_scan, clear_remaining_sources


def phase3_patrol_and_clear(targets: List, robot, enable_2opt: bool = False) -> dict:
    """
    阶段3：巡游清除

    参数:
        targets: 阶段2输出的目标列表
        robot: 机器狗对象
        enable_2opt: 是否启用2-opt优化（默认False）

    返回:
        results: {
            'cleared': 已清除的目标列表,
            'failed': 清除失败的目标列表,
            'clear_times': 每个目标的清除时间,
            'total_time': 总虚拟时间,
            'clearing_ratio': 清除比例,
            'average_clear_time': 平均清除时间
        }

    流程:
        1. 路径规划
        2. 逐个清除
        3. 兜底验证
        4. 统计输出
    """
    print(f"\n{'='*60}")
    print(f"阶段3：巡游清除")
    print(f"{'='*60}\n")
    print(f"目标数量: {len(targets)}")

    if not targets:
        print(f"⚠️  无目标，跳过清除")
        return {
            'cleared': [],
            'failed': [],
            'clear_times': {},
            'total_time': 0,
            'clearing_ratio': 0,
            'average_clear_time': 0
        }

    start_time = robot.virtual_time  # 使用属性而不是方法
    start_position = robot.position.copy()  # 使用属性而不是方法

    # 步骤1：路径规划
    print(f"\n步骤1：路径规划...")
    path = plan_clearing_path_priority_greedy(targets, start_position)

    if enable_2opt:
        print(f"  启用2-opt优化...")
        path = two_opt_optimize(path, start_position)

    print(f"  访问顺序（按优先级）:")
    for i, target in enumerate(path, 1):
        print(f"    {i:2d}. 频道{target.channel_id:2d}: "
              f"中心({target.center[0]:6.1f}, {target.center[1]:6.1f}), "
              f"D={target.diameter:5.1f}m, conf={target.confidence:.2f}")

    # 步骤2：逐个清除
    print(f"\n步骤2：逐个清除...")

    cleared = []
    failed = []
    clear_times = {}

    for i, target in enumerate(path, 1):
        print(f"\n[{i}/{len(path)}] ", end='')

        success, clear_time = clear_target(robot, target, max_attempts=3)

        if success:
            cleared.append(target)
            clear_times[target.channel_id] = clear_time
            print(f"  ✓ 成功清除，用时: {clear_time:.1f}秒")
        else:
            failed.append(target)
            print(f"  ✗ 清除失败")

    # 步骤3：兜底验证
    print(f"\n步骤3：兜底验证...")

    # 增强版：接收遗漏频道列表和检测数据
    remaining_channels, channel_detections = final_verification_scan(robot, cleared)

    if remaining_channels:
        print(f"\n发现遗漏，启动补救...")
        success_count = clear_remaining_sources(robot, remaining_channels, channel_detections)

        # 更新统计
        if success_count > 0:
            # 将成功清除的遗漏源添加到cleared
            for ch in remaining_channels:
                # 检查是否在failed中
                matching_targets = [t for t in failed if t.channel_id == ch]
                if matching_targets:
                    # 从failed移到cleared
                    target = matching_targets[0]
                    failed.remove(target)
                    cleared.append(target)

    # 步骤4：最终统计
    total_time = robot.virtual_time - start_time
    clearing_ratio = len(cleared) / len(targets) if targets else 0

    if clear_times:
        average_clear_time = sum(clear_times.values()) / len(clear_times)
    else:
        average_clear_time = 0

    # 输出结果
    print(f"\n{'='*60}")
    print(f"阶段3完成")
    print(f"{'='*60}\n")
    print(f"成功清除: {len(cleared)}/{len(targets)} ({clearing_ratio*100:.1f}%)")
    print(f"清除失败: {len(failed)}")
    print(f"总虚拟时间: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    if clear_times:
        print(f"平均清除时间: {average_clear_time:.1f} 秒")

    print(f"\n清除详情:")
    for target in cleared:
        clear_time = clear_times.get(target.channel_id, 0)
        if clear_time > 0:
            print(f"  ✓ 频道{target.channel_id:2d}: {clear_time:6.1f}秒")
        else:
            print(f"  ✓ 频道{target.channel_id:2d}: (补救清除)")

    if failed:
        print(f"\n失败列表:")
        for target in failed:
            attempt_count = getattr(target, 'attempt_count', 0)
            print(f"  ✗ 频道{target.channel_id:2d}: "
                  f"中心({target.center[0]:.1f}, {target.center[1]:.1f}), "
                  f"尝试{attempt_count}次")

    return {
        'cleared': cleared,
        'failed': failed,
        'clear_times': clear_times,
        'total_time': total_time,
        'clearing_ratio': clearing_ratio,
        'average_clear_time': average_clear_time
    }


# 测试代码
if __name__ == '__main__':
    print("测试 phase3_clearing.py")
    print("=" * 60)

    print("\n注意：此模块需要模拟器连接才能完整测试")
    print("这里只展示接口定义和流程")

    print("\n阶段3完整流程：")
    print("  1. 路径规划")
    print("     - 优先级贪心")
    print("     - 可选：2-opt优化")
    print()
    print("  2. 逐个清除")
    print("     - 移动到目标")
    print("     - ⚠️  切换到目标频道（关键！）")
    print("     - 尝试清除")
    print("     - 失败则精修")
    print("     - 最多3次尝试")
    print()
    print("  3. 兜底验证")
    print("     - 回到原点")
    print("     - 扫描全部20个频道")
    print("     - 发现遗漏则补救")
    print()
    print("  4. 统计输出")
    print("     - 清除比例")
    print("     - 平均清除时间")
    print("     - 总虚拟时间")

    print("\n" + "=" * 60)
    print("接口定义验证完成！")
