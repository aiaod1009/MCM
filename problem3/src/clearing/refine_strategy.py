"""
精修策略

当首次清除失败时，通过精修定位或螺旋搜索来找到干扰源
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def spiral_search(robot, target, search_radius: float = 20, step: float = 10) -> bool:
    """
    螺旋搜索清除

    参数:
        robot: 机器狗对象
        target: 目标对象
        search_radius: 搜索半径（米），默认20米（清除半径上限）
        step: 步长（米）

    返回:
        success: 是否成功清除

    算法:
        使用阿基米德螺线生成搜索点
        从中心向外螺旋搜索

    适用场景:
        定位区域直径<40米的小范围搜索

    注意:
        清除半径为20米，搜索半径不应超过20米
    """
    # 确保搜索半径不超过清除半径20米
    search_radius = min(search_radius, 20.0)

    print(f"    → 螺旋搜索（半径{search_radius:.1f}米，步长{step:.1f}米）")

    center = target.center
    channel = target.channel_id

    # 生成螺旋搜索点
    search_points = generate_spiral_points(center, search_radius, step)

    print(f"      生成 {len(search_points)} 个搜索点")

    for i, point in enumerate(search_points):
        if i % 5 == 0:  # 每5个点打印一次，避免输出过多
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
    生成螺旋搜索点

    参数:
        center: 中心点
        radius: 最大半径
        step: 步长

    返回:
        points: 搜索点列表

    算法:
        使用阿基米德螺线：r = a * theta
        a = step / (2π) 确保每圈间距为step
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


def refine_and_retry(robot, target) -> bool:
    """
    精修定位后重试

    策略:
    1. 在定位区域边界采样2-3个点
    2. 测向，获得新数据
    3. 结合原有数据，重新定位
    4. 移动到新中心，清除

    参数:
        robot: 机器狗对象
        target: 目标对象

    返回:
        success: 是否成功清除

    适用场景:
        定位区域直径≥40米的大范围精修
    """
    print(f"    → 精修定位...")

    channel = target.channel_id

    # 步骤1：在区域边界采样
    if target.hull is not None and len(target.hull) >= 3:
        # 使用凸包顶点作为采样点
        sample_points = target.hull[:min(3, len(target.hull))]
        print(f"      使用凸包顶点作为采样点（{len(sample_points)}个）")
    else:
        # 如果没有凸包，在中心周围采样
        radius = target.diameter / 2
        angles = [0, 120, 240]  # 三个方向
        sample_points = [
            target.center + radius * np.array([np.cos(np.deg2rad(a)),
                                                np.sin(np.deg2rad(a))])
            for a in angles
        ]
        print(f"      在中心周围采样3个点（半径{radius:.1f}米）")

    # 步骤2：补充测向
    new_measurements = []
    for point in sample_points:
        # 使用 measure() 移动并测向
        result = robot.measure(tuple(point), channel)

        if result.get('code') == 0 and result.get('result') == 'direction':
            angle = result.get('svd_deg')
            if angle is not None:
                print(f"      采样点 ({point[0]:.1f}, {point[1]:.1f}): θ={angle:.2f}°")
                new_measurements.append((point, angle))

    if len(new_measurements) < 2:
        print(f"      ✗ 补充测向数据不足")
        return False

    # 步骤3：重新定位
    try:
        from localization.point_selector import select_detection_points
        from localization.region_calculator import compute_localization_region

        # 转换为阶段2的数据格式
        scan_data_refined = [[list(point), angle] for point, angle in new_measurements]

        S1, theta1, S2, theta2, quality = select_detection_points(scan_data_refined)

        if S1 is None:
            print(f"      ✗ 无法选择有效检测点对")
            return False

        # 重新计算定位区域
        region_info_refined = compute_localization_region(S1, theta1, S2, theta2)

        new_center = region_info_refined['center']
        new_diameter = region_info_refined['diameter']

        print(f"      精修后中心: ({new_center[0]:.1f}, {new_center[1]:.1f})")
        print(f"      精修后直径: {new_diameter:.1f} 米")

    except Exception as e:
        print(f"      ✗ 精修定位失败: {e}")
        return False

    # 步骤4：移动到新中心，清除
    result = robot.clear(tuple(new_center), channel)

    if result.get('code') == 0 and result.get('result') == 'success':
        print(f"      ✓ 精修后成功清除！")
        # 更新目标信息
        target.center = new_center
        target.diameter = new_diameter
        return True
    else:
        print(f"      ✗ 精修后仍未清除")

        # 如果精修后区域仍然很大，不进行螺旋搜索
        if new_diameter < 40:
            # 尝试小范围螺旋搜索（限制在清除半径20米内）
            print(f"      → 启动螺旋搜索（精修后）")
            # 更新target的center和diameter
            target.center = new_center
            target.diameter = new_diameter
            # 搜索半径取直径的一半，但不超过20米（清除半径）
            effective_radius = min(new_diameter / 2, 20.0)
            return spiral_search(robot, target, search_radius=effective_radius, step=10)
        else:
            return False


# 测试代码
if __name__ == '__main__':
    print("测试 refine_strategy.py")
    print("=" * 60)

    # 测试1：生成螺旋搜索点
    print("\n测试1 - 生成螺旋搜索点:")
    center = np.array([100, 100])
    radius = 30
    step = 10

    points = generate_spiral_points(center, radius, step)

    print(f"  中心: ({center[0]:.0f}, {center[1]:.0f})")
    print(f"  半径: {radius} 米")
    print(f"  步长: {step} 米")
    print(f"  生成点数: {len(points)}")

    print(f"\n  前10个搜索点:")
    for i, point in enumerate(points[:10], 1):
        dist = np.linalg.norm(point - center)
        print(f"    {i:2d}. ({point[0]:6.1f}, {point[1]:6.1f}), 距离中心: {dist:5.1f}米")

    # 测试2：验证螺旋覆盖
    print("\n测试2 - 验证螺旋覆盖:")

    # 计算点之间的最大间隙
    max_gap = 0
    for i in range(len(points) - 1):
        gap = np.linalg.norm(points[i+1] - points[i])
        if gap > max_gap:
            max_gap = gap

    print(f"  相邻点最大间隙: {max_gap:.2f} 米")
    print(f"  步长设置: {step} 米")
    print(f"  验证: {'✓ 覆盖良好' if max_gap <= step * 1.5 else '✗ 覆盖有间隙'}")

    print("\n" + "=" * 60)
    print("测试完成！")
