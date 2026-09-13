# -*- coding: utf-8 -*-
"""
问题4增强清除策略

针对定向源和大容错直径优化的清除策略
"""
import sys
import os
import numpy as np

# 添加问题3路径
problem3_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../问题3/MCM/problem3/src'))
sys.path.append(problem3_src_path)


def enhanced_spiral_search(robot, target, search_radius: float = None, step: float = 15) -> bool:
    """
    增强螺旋搜索（针对问题4的大直径）

    参数:
        robot: 机器狗对象
        target: 目标对象
        search_radius: 搜索半径（如果None，自动根据直径计算）
        step: 步长（米）

    关键优化：
    1. 搜索半径自动匹配定位直径（diameter/2 + 20m缓冲）
    2. 最大搜索半径提升到80m（覆盖2.5倍容错的情况）
    3. 步长15m（平衡覆盖和时间）
    """
    # 自动计算搜索半径
    if search_radius is None:
        # 直径的一半 + 20m缓冲
        search_radius = target.diameter / 2 + 20
        # 限制在合理范围：20-80m
        search_radius = max(20, min(search_radius, 80))

    print(f"    → 增强螺旋搜索（半径{search_radius:.1f}米，步长{step:.1f}米）")
    print(f"      （目标直径：{target.diameter:.1f}米）")

    # 确保center是numpy数组
    if isinstance(target.center, (list, tuple)):
        center = np.array(target.center)
    else:
        center = target.center

    channel = target.channel_id

    # 生成螺旋搜索点
    search_points = generate_spiral_points(center, search_radius, step)

    print(f"      生成 {len(search_points)} 个搜索点")

    for i, point in enumerate(search_points):
        if i % 10 == 0:  # 每10个点打印一次
            print(f"      搜索点 {i+1}/{len(search_points)}: ({point[0]:.1f}, {point[1]:.1f})")

        # 移动到点并尝试清除
        result = robot.clear(tuple(point), channel)

        if result.get('code') == 0 and result.get('result') == 'success':
            print(f"      ✓ 在 ({point[0]:.1f}, {point[1]:.1f}) 成功清除！")
            return True

    print(f"      ✗ 螺旋搜索未找到")
    return False


def generate_spiral_points(center: np.ndarray, radius: float, step: float) -> list:
    """
    生成螺旋搜索点（阿基米德螺线）

    参数:
        center: 中心点
        radius: 最大半径
        step: 步长

    返回:
        points: 搜索点列表
    """
    points = [center.copy()]  # 从中心开始

    # 阿基米德螺线参数
    a = step / (2 * np.pi)  # 螺距

    theta = 0
    d_theta = 0.5  # 角度增量（弧度）

    while True:
        r = a * theta
        if r > radius:
            break

        x = center[0] + r * np.cos(theta)
        y = center[1] + r * np.sin(theta)

        points.append(np.array([x, y]))

        theta += d_theta

    return points


def enhanced_clear_target(robot, target, max_attempts: int = 3) -> tuple:
    """
    增强清除策略（问题4专用）

    参数:
        robot: 机器狗对象
        target: 目标对象
        max_attempts: 最大尝试次数

    返回:
        success: 是否成功清除
        clear_time: 清除时间

    流程：
    1. 首次尝试：直接在定位中心清除
    2. 如果失败，使用增强螺旋搜索（半径自动匹配直径）
    3. 如果还失败，扩大螺旋搜索到80m
    """
    start_time = robot.virtual_time

    print(f"\n{'='*60}")
    print(f"增强清除目标：频道 {target.channel_id}")
    print(f"{'='*60}")

    # 确保center是tuple或numpy数组
    if isinstance(target.center, (list, tuple)):
        center = tuple(target.center) if isinstance(target.center, list) else target.center
    else:
        center = tuple(target.center)

    print(f"  定位中心: ({center[0]:.1f}, {center[1]:.1f})")
    print(f"  区域直径: {target.diameter:.1f} 米")
    print(f"  置信度: {target.confidence:.2f}")

    for attempt in range(1, max_attempts + 1):
        print(f"\n  尝试 {attempt}/{max_attempts}:")

        # 第1次：直接清除
        if attempt == 1:
            print(f"    → 移动到中心并清除")
            result = robot.clear(center, target.channel_id)

            if result.get('code') == 0 and result.get('result') == 'success':
                print(f"    ✓ 成功清除！")
                clear_time = robot.virtual_time - start_time
                target.cleared = True
                target.attempt_count = attempt
                return True, clear_time
            else:
                print(f"    ✗ 清除失败: {result.get('result', 'unknown')}")

        # 第2次：螺旋搜索（自动半径）
        elif attempt == 2:
            success = enhanced_spiral_search(robot, target, search_radius=None)
            if success:
                clear_time = robot.virtual_time - start_time
                target.cleared = True
                target.attempt_count = attempt
                return True, clear_time

        # 第3次：扩大螺旋搜索（强制80m）
        elif attempt == 3:
            print(f"    → 最后尝试：扩大搜索范围到80米")
            success = enhanced_spiral_search(robot, target, search_radius=80, step=20)
            if success:
                clear_time = robot.virtual_time - start_time
                target.cleared = True
                target.attempt_count = attempt
                return True, clear_time

    # 所有尝试都失败
    print(f"  ✗ 所有尝试失败")
    target.attempt_count = max_attempts
    return False, robot.virtual_time - start_time
