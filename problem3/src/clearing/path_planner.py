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

    算法:
        - 直径小 = 不确定度低 = 精度高 = 优先清除
        - 将目标分为3个优先级组：
          * 高优先级（D<25m）
          * 中优先级（25m≤D<45m）
          * 低优先级（D≥45m）
        - 在每组内按距离优化

    说明:
        本函数给出的是"优先级贪心"的初始解。它按分组顺序依次访问，
        组间不交叉，因此总移动距离通常明显长于最优解。请在得到本路径后
        调用 optimize_clearing_path() 做 2-opt + Or-opt 优化，
        在"总移动时间最小"这一目标下压缩路径。
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


def compute_path_length(path_list: List, start_pos: np.ndarray) -> float:
    """计算给定访问顺序的总移动距离（米）"""
    if not path_list:
        return 0.0
    total = float(np.linalg.norm(path_list[0].center - start_pos))
    for i in range(len(path_list) - 1):
        total += float(np.linalg.norm(path_list[i + 1].center - path_list[i].center))
    return total


def two_opt_optimize(
    path: List,
    start_position: np.ndarray,
    max_iterations: int = 200,
    max_span: int = None
) -> List:
    """
    2-opt 局部优化（真正的"边反转"版本）

    参数:
        path: 初始路径（通常由优先级贪心给出）
        start_position: 起点
        max_iterations: 最大改进轮数
        max_span: 允许反转的片段最大长度；None 表示不限制。
                  若希望"尽量保留优先级顺序"，可设为 2~3，
                  但会牺牲大部分可压缩的距离。

    返回:
        optimized_path: 优化后的路径

    算法:
        对任意 i < j，把 path[i..j] 整段反转（等价于删除两条边
        (path[i-1],path[i]) 与 (path[j],path[j+1])，换成
        (path[i-1],path[j]) 与 (path[i],path[j+1])），
        若总移动距离下降则接受，反复迭代直到无法改进。

    说明:
        旧实现名为 2-opt，实际做的是"同优先级组内两两交换"，且
        abs(ΔD) > 20 会跳过跨组交换、j 从 i+2 起又会跳过相邻交换，
        受 3 档分组（D<25 / 25~45 / ≥45）约束后路线仍保留大量跨组绕行。
        本实现为标准 2-opt：以优先级贪心路径作为初始解，在"总移动时间
        最小"这一目标下自由反转片段。优先级只影响初始解与先清除顺序的
        倾向，最终以任务总时间（竞赛计分项）为优化目标。
    """
    if len(path) < 3:
        return list(path)

    best_path = list(path)
    best_length = compute_path_length(best_path, start_position)
    n = len(best_path)

    for _ in range(max_iterations):
        improved = False

        for i in range(n - 1):
            for j in range(i + 1, n):
                if max_span is not None and (j - i + 1) > max_span:
                    continue

                # 反转 path[i..j] 整段
                candidate = best_path[:i] + best_path[i:j + 1][::-1] + best_path[j + 1:]
                cand_length = compute_path_length(candidate, start_position)

                if cand_length < best_length - 1e-9:
                    best_path = candidate
                    best_length = cand_length
                    improved = True

        if not improved:
            break

    return best_path


def or_opt_optimize(
    path: List,
    start_position: np.ndarray,
    max_iterations: int = 200
) -> List:
    """
    Or-opt 局部优化（单点重定位）

    把某个目标摘下后插入到序列中的另一个位置，若总移动距离下降则接受。
    与 2-opt 互补：2-opt 反转片段，Or-opt 平移单点。

    参数:
        path: 初始路径
        start_position: 起点
        max_iterations: 最大改进轮数

    返回:
        optimized_path: 优化后的路径
    """
    if len(path) < 3:
        return list(path)

    best_path = list(path)
    best_length = compute_path_length(best_path, start_position)
    n = len(best_path)

    for _ in range(max_iterations):
        improved = False

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue

                moved = best_path[i]
                candidate = best_path[:i] + best_path[i + 1:]
                candidate.insert(j, moved)
                cand_length = compute_path_length(candidate, start_position)

                if cand_length < best_length - 1e-9:
                    best_path = candidate
                    best_length = cand_length
                    improved = True

        if not improved:
            break

    return best_path


def optimize_clearing_path(
    path: List,
    start_position: np.ndarray,
    max_rounds: int = 20,
    verbose: bool = False
) -> List:
    """
    交替执行 2-opt 与 Or-opt，直到不再改进（收敛）。

    参数:
        path: 初始路径（优先级贪心解）
        start_position: 起点
        max_rounds: 最大交替轮数（防死循环）
        verbose: 是否打印每轮长度

    返回:
        optimized_path: 优化后的路径
    """
    best_path = list(path)
    best_length = compute_path_length(best_path, start_position)

    if verbose and best_path:
        print(f"    初始路径长度: {best_length:.1f} m")

    for round_idx in range(1, max_rounds + 1):
        candidate = two_opt_optimize(best_path, start_position)
        candidate = or_opt_optimize(candidate, start_position)
        cand_length = compute_path_length(candidate, start_position)

        if verbose:
            print(f"    第{round_idx}轮(2-opt+Or-opt): {cand_length:.1f} m")

        if cand_length < best_length - 1e-9:
            best_path = candidate
            best_length = cand_length
            continue

        break

    if verbose and best_path:
        print(f"    优化后路径长度: {best_length:.1f} m")

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

    # 测试2：路径优化（2-opt + Or-opt）
    print("\n测试2 - 路径优化（2-opt + Or-opt）:")
    optimized_path = optimize_clearing_path(path, start_pos, verbose=True)

    print(f"  优化后访问顺序:")
    for i, t in enumerate(optimized_path, 1):
        print(f"    {i}. 频道{t.channel_id}: ({t.center[0]:.0f}, {t.center[1]:.0f}), D={t.diameter:.0f}m")

    # 计算优化后路径长度
    opt_dist = compute_path_length(optimized_path, start_pos)
    print(f"  优化后总距离: {opt_dist:.1f} 米")
    print(f"  优化比例: {(total_dist - opt_dist) / total_dist * 100:.1f}%")

    print("\n" + "=" * 60)
    print("测试完成！")
