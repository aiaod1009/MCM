"""
清除策略

实现单个干扰源的清除逻辑，包括多次尝试和精修
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def clear_target(robot, target, max_attempts: int = 3) -> tuple:
    """
    清除单个干扰源（完整流程）

    参数:
        robot: 机器狗对象
        target: 目标对象
        max_attempts: 最大尝试次数

    返回:
        success: 是否成功清除（布尔值）
        clear_time: 清除时间（虚拟时间，秒）

    流程:
        1. 直接调用 robot.clear(position, channel)
        2. 检查结果
        3. 如果失败，启动精修策略
        4. 最多尝试max_attempts次

    ⚠️  关键：clear() 方法会自动移动到位置并清除该频道的干扰源
    """
    start_time = robot.virtual_time  # 使用属性而不是方法

    print(f"\n{'='*60}")
    print(f"清除目标：频道 {target.channel_id}")
    print(f"{'='*60}")
    print(f"  定位中心: ({target.center[0]:.1f}, {target.center[1]:.1f})")
    print(f"  区域直径: {target.diameter:.1f} 米")
    print(f"  置信度: {target.confidence:.2f}")

    for attempt in range(1, max_attempts + 1):
        print(f"\n  尝试 {attempt}/{max_attempts}:")

        # 步骤1：移动到目标位置并清除
        print(f"    → 移动到 ({target.center[0]:.1f}, {target.center[1]:.1f}) 并清除频道 {target.channel_id}")
        result = robot.clear(target.center, target.channel_id)

        # 步骤2：检查结果
        if result.get('code') == 0:
            clear_result = result.get('result', 'no_target_in_range')

            if clear_result == 'success':
                print(f"    ✓ 成功清除！")
                clear_time = robot.virtual_time - start_time
                target.cleared = True
                target.attempt_count = attempt
                return True, clear_time
            else:
                print(f"    ✗ 清除失败: {clear_result}")
        else:
            print(f"    ✗ 清除请求失败: {result.get('message', '未知错误')}")

        if attempt < max_attempts:
            # 精修策略
            print(f"    → 启动精修...")

            # 导入精修函数
            from clearing.refine_strategy import refine_and_retry

            success = refine_and_retry(robot, target)
            if success:
                clear_time = robot.virtual_time - start_time
                target.cleared = True
                target.attempt_count = attempt
                return True, clear_time

    # 所有尝试都失败
    print(f"  ✗ 所有尝试失败")
    target.attempt_count = max_attempts
    return False, robot.virtual_time - start_time


# 测试代码
if __name__ == '__main__':
    print("测试 clear_strategy.py")
    print("=" * 60)

    print("\n注意：此模块需要模拟器连接才能完整测试")
    print("这里只展示接口定义和流程")

    print("\n清除流程：")
    print("  1. 移动到目标位置")
    print("  2. ⚠️  切换到目标频道（关键！）")
    print("  3. 尝试清除")
    print("  4. 检查结果")
    print("  5. 如果失败，启动精修")
    print("  6. 最多尝试3次")

    print("\n" + "=" * 60)
    print("接口定义验证完成！")
