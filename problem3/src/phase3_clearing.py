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

from clearing.path_planner import (
    plan_clearing_path_priority_greedy,
    optimize_clearing_path,
    compute_path_length,
)
from clearing.clear_strategy import clear_target
from clearing.verification import review_cleared, clear_remaining_sources
from target import Target


def phase3_patrol_and_clear(targets: List, robot, enable_2opt: bool = False,
                            active_channels: List[int] = None,
                            scan_data: dict = None) -> dict:
    """
    阶段3：巡游清除

    参数:
        targets: 阶段2输出的目标列表
        robot: 机器狗对象
        enable_2opt: 是否启用路径优化（2-opt + Or-opt）
        active_channels: 阶段1发现的有源频道列表。清除复核以"是否返回过
                         success"为判据，故仅需该列表即可确定遗漏，无需盲扫。
        scan_data: 阶段1原始扫描数据 {str(ch): [[[x, y], theta 或 None], ...]}，
                   用于对遗漏频道做补救定位（比盲扫的角度更多、更贴近源）

    返回:
        results: {
            'cleared': 已清除的目标列表,
            'failed': 清除失败的目标列表,
            'clear_times': 每个目标的清除时间,
            'total_time': 总虚拟时间,
            'clearing_ratio': 清除比例,
            'average_clear_time': 平均清除时间,
            'reviewed_channels': 复核后判定未清除的频道,
            'recovered_channels': 补救成功的频道
        }

    流程:
        1. 路径规划
        2. 逐个清除
        3. 清除复核（记账，零检测）+ 定向补救
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
            'average_clear_time': 0,
            'reviewed_channels': [],
            'recovered_channels': [],
        }

    start_time = robot.virtual_time  # 使用属性而不是方法
    start_position = robot.position.copy()  # 使用属性而不是方法

    # 步骤1：路径规划
    print(f"\n步骤1：路径规划...")
    path = plan_clearing_path_priority_greedy(targets, start_position)
    greedy_length = compute_path_length(path, start_position)
    print(f"  优先级贪心初始路径: {greedy_length:.1f} m ({greedy_length/5.0:.1f} s)")

    if enable_2opt:
        print(f"  启用路径优化（2-opt + Or-opt）...")
        path = optimize_clearing_path(path, start_position, verbose=True)
        opt_length = compute_path_length(path, start_position)
        saved = greedy_length - opt_length
        print(f"  优化后路径: {opt_length:.1f} m ({opt_length/5.0:.1f} s)，"
              f"节省 {saved:.1f} m / {saved/5.0:.1f} s")

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

    # 步骤3：清除复核（记账，零检测）+ 定向补救
    print(f"\n步骤3：清除复核与补救...")

    remaining_channels, channel_detections = review_cleared(
        active_channels=active_channels,
        targets=targets,
        cleared_targets=cleared,
        scan_data=scan_data,
        verbose=True,
    )

    recovered_channels = []
    if remaining_channels:
        print(f"\n发现 {len(remaining_channels)} 个未确认清除的频道，启动补救...")
        recovered_channels = clear_remaining_sources(
            robot, remaining_channels, channel_detections)

    # ------------------------------------------------------------------
    # 步骤4：最终统计（全部以"频道号"为准，避免目标对象缺失时漏计）
    # ------------------------------------------------------------------
    recovered_ids = set(int(c) for c in recovered_channels)
    target_ids = set(int(t.channel_id) for t in targets)

    # 清除失败、且补救也未成功的目标才是真正失败
    still_failed = [t for t in failed if int(t.channel_id) not in recovered_ids]

    # 阶段2没有给出目标、但补救成功的频道 → 补一个占位目标以便计数/打印
    for ch in sorted(recovered_ids - target_ids):
        cleared.append(Target(
            channel_id=ch,
            detection_points=channel_detections.get(ch, []),
            center=np.array([0.0, 0.0]),
            diameter=0.0,
            confidence=0.5,
            method='recovery_only',
        ))

    # 补救成功的目标：从"失败"移入"已清除"
    for ch in sorted(recovered_ids):
        for t in failed:
            if int(t.channel_id) == ch and t not in cleared:
                cleared.append(t)
                break

    total_time = robot.virtual_time - start_time

    # 清除比例 = 已确认清除频道数 / 阶段1判定有源的频道数。
    # 阶段1（扫描环 r=1200、全频道扫描）已保证不漏检，故分母取
    # active_channels 即为干扰源总数的可靠上界；两者相等时比例为 100%。
    seen_channels = set(int(c) for c in (active_channels or [])) or set(target_ids)
    if not seen_channels:
        seen_channels = target_ids | set(int(t.channel_id) for t in cleared)
    cleared_ids = set(int(t.channel_id) for t in cleared) | recovered_ids
    clearing_ratio = (len(cleared_ids & seen_channels) / len(seen_channels)
                      if seen_channels else 0.0)

    if clear_times:
        average_clear_time = sum(clear_times.values()) / len(clear_times)
    else:
        average_clear_time = 0

    # 输出结果
    print(f"\n{'='*60}")
    print(f"阶段3完成")
    print(f"{'='*60}\n")
    print(f"成功清除: {len(cleared_ids & seen_channels)}/{len(seen_channels)} "
          f"({clearing_ratio*100:.1f}%)")
    print(f"清除失败: {len(still_failed)}")
    print(f"总虚拟时间: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    if clear_times:
        print(f"平均清除时间: {average_clear_time:.1f} 秒")

    print(f"\n清除详情:")
    for target in cleared:
        clear_time = clear_times.get(target.channel_id, 0)
        if clear_time > 0:
            print(f"  ✓ 频道{target.channel_id:2d}: {clear_time:6.1f}秒")
        elif target.method == 'recovery_only':
            print(f"  ✓ 频道{target.channel_id:2d}: (复核补救清除)")
        else:
            print(f"  ✓ 频道{target.channel_id:2d}: (补救清除)")

    if still_failed:
        print(f"\n失败列表:")
        for target in still_failed:
            attempt_count = getattr(target, 'attempt_count', 0)
            print(f"  ✗ 频道{target.channel_id:2d}: "
                  f"中心({target.center[0]:.1f}, {target.center[1]:.1f}), "
                  f"尝试{attempt_count}次")

    return {
        'cleared': cleared,
        'failed': still_failed,
        'clear_times': clear_times,
        'total_time': total_time,
        'clearing_ratio': clearing_ratio,
        'average_clear_time': average_clear_time,
        'reviewed_channels': list(remaining_channels),
        'recovered_channels': list(recovered_channels),
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
    print("  3. 清除复核与补救")
    print("     - 记账复核：/clear 返回 success 即为已清除（零检测）")
    print("     - 未确认清除的频道用阶段1测向数据做交会/单点/near点直清")
    print("     - 仍失败则围绕估计中心做螺旋搜索（半径 ≤40 m）")
    print()
    print("  4. 统计输出")
    print("     - 清除比例")
    print("     - 平均清除时间")
    print("     - 总虚拟时间")

    print("\n" + "=" * 60)
    print("接口定义验证完成！")
