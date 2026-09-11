"""
路径规划器

为阶段3的清除任务规划最优访问路径
"""

import numpy as np
from typing import List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def plan_clearing_path_priority_greedy(targets: List, start_position: np.ndarray) -> List:
    """
    优先级贪心路径规划

    策略：
    1. 按直径（不确定度）排序（阶段2已完成）
    2. 在相同优先级内，选择距离近的
    3. 动态调整（清除失败后可能重新排序）

    参数：
        targets: 目标列表（已按直径排序）
        start_position: 起始位置

    返回：
        path: 访问顺序 [target1, target2, ...]

    算法：
        - 直径小 = 不确定度低 = 精度高 = 优先清除
        - 将目标分为3个优先级组：
          * 高优先级（D<25m）
          * 中优先级（25m≤D<45m）
          * 低优先级（D≥45m）
        - 在每组内按距离优化
    """
    if not targets:
        return []

    # 策略：targets已经按直径排序，我们只需要在同优先级内优化距离

    # 将目标分为3个优先级组
    high_priority = [t for t in targets if t.diameter < 25]
    medium_priority = [t for t in targets if 25 <= t.diameter < 45]
    low_priority = [t for t in targets if t.diameter >= 45]

    def sort_by_distance(group, current_pos):
        """在组内按距离当前位置排序"""
        if not group:
            return []
        return sorted(group, key=lambda t: np.linalg.norm(t.center - current_pos))

    current_pos = start_position.copy()
    optimized_path = []

    # 依次处理三个优先级组
    for group in [high_priority, medium_priority, low_priority]:
        if not group:
            continue

        # 在组内按距离排序
        sorted_group = sort_by_distance(group, current_pos)
        optimized_path.extend(sorted_group)

        # 更新当前位置为组内最后一个目标
        if sorted_group:
            current_pos = sorted_group[-1].center.copy()

    return optimized_path


def two_opt_optimize(path: List, start_position: np.ndarray, max_iterations: int = 100) -> List:
    """
    2-opt局部优化

    在不改变优先级分组的前提下，优化组内路径

    参数:
        path: 初始路径
        start_position: 起点
        max_iterations: 最大迭代次数

    返回:
        optimized_path: 优化后的路径

    算法:
        - 尝试交换任意两个目标（在相同优先级组内）
        - 如果交换后路径更短，接受交换
        - 重复直到无法改进或达到最大迭代次数
    """
    if len(path) < 2:
        return path

    def compute_path_length(path_list, start_pos):
        """计算路径总距离"""
        if not path_list:
            return 0.0

        total = np.linalg.norm(path_list[0].center - start_pos)
        for i in range(len(path_list) - 1):
            total += np.linalg.norm(path_list[i+1].center - path_list[i].center)
        return total

    best_path = path.copy()
    best_length = compute_path_length(best_path, start_position)

    improved = True
    iteration = 0

    while improved and iteration < max_iterations:
        improved = False

        # 尝试交换任意两个目标（在相同优先级组内）
        for i in range(len(best_path)):
            for j in range(i + 2, len(best_path)):
                # 检查i和j是否在相同优先级组
                # 直径差>20米认为不在同一组
                if abs(best_path[i].diameter - best_path[j].diameter) > 20:
                    continue  # 不同优先级，跳过

                # 交换i和j
                new_path = best_path.copy()
                new_path[i], new_path[j] = new_path[j], new_path[i]

                new_length = compute_path_length(new_path, start_position)

                if new_length < best_length:
                    best_path = new_path
                    best_length = new_length
                    improved = True

        iteration += 1

    return best_path


# 测试代码
if __name__ == '__main__':
    print("测试 path_planner.py")
    print("=" * 60)

    # 创建测试目标
    from target import Target

    test_targets = [
        Target(1, [], center=np.array([100, 100]), diameter=15, confidence=0.9, method='two_point'),
        Target(2, [], center=np.array([500, -500]), diameter=35, confidence=0.8, method='two_point'),
        Target(3, [], center=np.array([-300, 400]), diameter=20, confidence=0.85, method='two_point'),
        Target(4, [], center=np.array([800, 800]), diameter=50, confidence=0.6, method='single_point'),
        Target(5, [], center=np.array([0, 1000]), diameter=18, confidence=0.88, method='two_point'),
    ]

    # 按直径排序（模拟阶段2的输出）
    test_targets.sort(key=lambda t: t.diameter)

    print("\n初始目标列表（按直径排序）:")
    for i, t in enumerate(test_targets, 1):
        print(f"  {i}. 频道{t.channel_id}: 中心({t.center[0]:.0f}, {t.center[1]:.0f}), D={t.diameter:.0f}m")

    # 测试1：优先级贪心
    print("\n测试1 - 优先级贪心路径规划:")
    start_pos = np.array([0, 0])
    path = plan_clearing_path_priority_greedy(test_targets, start_pos)

    print(f"  起点: ({start_pos[0]:.0f}, {start_pos[1]:.0f})")
    print(f"  访问顺序:")
    for i, t in enumerate(path, 1):
        print(f"    {i}. 频道{t.channel_id}: ({t.center[0]:.0f}, {t.center[1]:.0f}), D={t.diameter:.0f}m")

    # 计算路径长度
    total_dist = np.linalg.norm(path[0].center - start_pos)
    for i in range(len(path) - 1):
        total_dist += np.linalg.norm(path[i+1].center - path[i].center)
    print(f"  总距离: {total_dist:.1f} 米")

    # 测试2：2-opt优化
    print("\n测试2 - 2-opt优化:")
    optimized_path = two_opt_optimize(path, start_pos, max_iterations=50)

    print(f"  优化后访问顺序:")
    for i, t in enumerate(optimized_path, 1):
        print(f"    {i}. 频道{t.channel_id}: ({t.center[0]:.0f}, {t.center[1]:.0f}), D={t.diameter:.0f}m")

    # 计算优化后路径长度
    opt_dist = np.linalg.norm(optimized_path[0].center - start_pos)
    for i in range(len(optimized_path) - 1):
        opt_dist += np.linalg.norm(optimized_path[i+1].center - optimized_path[i].center)
    print(f"  优化后总距离: {opt_dist:.1f} 米")
    print(f"  优化比例: {(total_dist - opt_dist) / total_dist * 100:.1f}%")

    print("\n" + "=" * 60)
    print("测试完成！")
