"""
模拟器连接测试工具

诊断模拟器连接问题
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simulator_client import SimulatorClient


def test_connection(robot_id):
    """测试模拟器连接"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*18 + "模拟器连接测试" + " "*18 + "║")
    print("╚" + "="*58 + "╝\n")

    print(f"参赛队号: {robot_id}")
    print(f"测试项目:")
    print(f"  1. 连接模拟器")
    print(f"  2. 进入测试区域")
    print(f"  3. 测试移动")
    print(f"  4. 测试频道切换")
    print(f"  5. 测试测向")
    print(f"  6. 测试清除")
    print()

    try:
        # 测试1：连接
        print(f"[1/6] 连接模拟器...")
        robot = SimulatorClient(robot_id=robot_id)
        print(f"  ✓ 连接成功")

        # 测试2：进入
        print(f"\n[2/6] 进入测试区域...")
        result = robot.enter()
        print(f"  返回: {result}")

        if result.get('accepted'):
            print(f"  ✓ 进入成功")
        else:
            print(f"  ✗ 进入失败: {result.get('reason', '未知')}")
            return False

        # 测试3：移动
        print(f"\n[3/6] 测试移动...")
        test_pos = [100.0, 100.0]
        result = robot.move_to(test_pos)
        print(f"  目标位置: ({test_pos[0]}, {test_pos[1]})")
        print(f"  返回: {result}")

        if result.get('accepted'):
            print(f"  ✓ 移动成功")
            pos = robot.get_position()
            print(f"  当前位置: ({pos[0]:.1f}, {pos[1]:.1f})")
        else:
            print(f"  ✗ 移动失败: {result.get('reason', '未知')}")
            return False

        # 测试4：切换频道
        print(f"\n[4/6] 测试频道切换...")
        test_channel = 1
        result = robot.switch_channel(test_channel)
        print(f"  目标频道: {test_channel}")
        print(f"  返回: {result}")

        if result.get('accepted'):
            print(f"  ✓ 切换成功")
            print(f"  当前频道: {robot.current_channel}")
        else:
            print(f"  ✗ 切换失败: {result.get('reason', '未知')}")

        # 测试5：测向
        print(f"\n[5/6] 测试测向...")
        result = robot.measure(test_pos, test_channel)
        print(f"  位置: ({test_pos[0]}, {test_pos[1]})")
        print(f"  频道: {test_channel}")
        print(f"  返回: {result}")

        if result.get('code') == 0:
            angle = result.get('direction')
            print(f"  ✓ 测向成功: θ={angle:.2f}°")
            print(f"  说明: 频道{test_channel}有信号")
        elif result.get('code') == 1:
            print(f"  ✓ 测向响应正常（无信号）")
            print(f"  说明: 频道{test_channel}无信号（这是正常的）")
        else:
            print(f"  ✗ 测向失败: code={result.get('code')}")
            return False

        # 测试6：清除
        print(f"\n[6/6] 测试清除...")
        result = robot.clear()
        print(f"  返回: {result}")

        if result.get('accepted'):
            eliminated = result.get('eliminated', 0)
            if eliminated > 0:
                print(f"  ✓ 清除成功！清除了 {eliminated} 个干扰源")
            else:
                print(f"  ✓ 清除响应正常（未清除，这是正常的）")
                print(f"  说明: 当前位置无干扰源")
        else:
            print(f"  ✗ 清除失败: {result.get('reason', '未知')}")

        # 总结
        print(f"\n╔" + "="*58 + "╗")
        print(f"║" + " "*18 + "✓ 所有测试通过！" + " "*17 + "║")
        print(f"╚" + "="*58 + "╝\n")

        print(f"模拟器连接正常，可以运行完整程序。")
        print(f"\n建议：")
        print(f"  1. 如果刚才测向显示'无信号'，可能是测试场景中确实无干扰源")
        print(f"  2. 如果需要有干扰源的场景，请在模拟器中设置")
        print(f"  3. 现在可以运行完整程序：")
        print(f"     cd problem3/src")
        print(f"     python main_problem3.py {robot_id}")

        return True

    except Exception as e:
        print(f"\n✗ 连接测试失败: {e}")
        import traceback
        traceback.print_exc()

        print(f"\n检查清单：")
        print(f"  [ ] 模拟器程序是否已启动？")
        print(f"  [ ] 是否点击了'开始测试'按钮？")
        print(f"  [ ] robot_id 是否正确？（{robot_id}）")
        print(f"  [ ] 网络连接是否正常？")

        return False


def main():
    """主函数"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*16 + "模拟器连接诊断工具" + " "*16 + "║")
    print("╚" + "="*58 + "╝")

    if len(sys.argv) > 1:
        robot_id = sys.argv[1]
    else:
        robot_id = input("\n请输入参赛队号（robot_id）: ").strip()

    if not robot_id:
        print("错误：必须提供参赛队号")
        return False

    success = test_connection(robot_id)

    if not success:
        print(f"\n提示：")
        print(f"  1. 确保模拟器已启动并点击'开始测试'")
        print(f"  2. 检查robot_id是否正确")
        print(f"  3. 尝试重启模拟器")

    return success


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
