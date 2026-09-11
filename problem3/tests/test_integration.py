"""
集成测试

测试三阶段的完整集成流程（使用模拟数据）
"""

import numpy as np
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from target import Target
from phase2_localization import phase2_localization
from phase3_clearing import phase3_patrol_and_clear


def create_mock_robot():
    """创建模拟机器狗"""
    class MockRobot:
        def __init__(self):
            self.position = np.array([0.0, 0.0])
            self.current_channel = 1
            self.virtual_time = 0.0
            self.cleared_targets = {}

            # 模拟干扰源位置
            self.sources = {
                1: np.array([100, 100]),
                2: np.array([500, -500]),
                3: np.array([-300, 400]),
            }

        def get_position(self):
            return self.position.copy()

        def get_virtual_time(self):
            return self.virtual_time

        def move_to(self, position):
            """模拟移动"""
            if isinstance(position, (list, tuple)):
                position = np.array(position)

            distance = np.linalg.norm(position - self.position)
            move_time = distance / 10.0  # 假设速度10m/s

            self.virtual_time += move_time
            self.position = position.copy()

            print(f"    移动到 ({self.position[0]:.1f}, {self.position[1]:.1f}), "
                  f"用时 {move_time:.1f}秒")

        def switch_channel(self, channel):
            """模拟切换频道"""
            if self.current_channel != channel:
                self.virtual_time += 0.5  # 切换耗时0.5秒
                self.current_channel = channel
                print(f"    切换到频道 {channel}")

        def clear(self):
            """模拟清除"""
            self.virtual_time += 1.0  # 清除耗时1秒

            # 检查是否在干扰源附近
            if self.current_channel in self.sources:
                source_pos = self.sources[self.current_channel]
                distance = np.linalg.norm(self.position - source_pos)

                if distance <= 20:  # 清除半径20米
                    self.cleared_targets[self.current_channel] = True
                    print(f"    ✓ 成功清除频道 {self.current_channel}")
                    return {'accepted': True, 'eliminated': 1}
                else:
                    print(f"    ✗ 距离干扰源 {distance:.1f}m，超出清除半径")
                    return {'accepted': True, 'eliminated': 0}
            else:
                print(f"    ✗ 频道 {self.current_channel} 无干扰源")
                return {'accepted': True, 'eliminated': 0}

        def detect_direction(self):
            """模拟测向"""
            self.virtual_time += 2.0  # 测向耗时2秒

            if self.current_channel in self.sources:
                source_pos = self.sources[self.current_channel]
                vec = source_pos - self.position
                angle = np.rad2deg(np.arctan2(vec[1], vec[0])) % 360
                return angle
            else:
                return None

    return MockRobot()


def test_phase2_integration():
    """测试阶段2集成"""
    print("\n" + "="*60)
    print("测试：阶段2集成")
    print("="*60)

    # 构造测试数据（模拟阶段1输出）
    scan_result = {
        'active_channels': [1, 2, 3],
        'scan_data': {
            # 频道1: 干扰源在(100, 100)
            '1': [
                [[0.0, 0.0], 45.0],      # 从原点看
                [[200.0, 0.0], 153.4]    # 从(200,0)看
            ],
            # 频道2: 干扰源在(500, -500)
            '2': [
                [[0.0, 0.0], 315.0],     # 从原点看
                [[900.0, 0.0], 231.3]    # 从(900,0)看
            ],
            # 频道3: 干扰源在(-300, 400)
            '3': [
                [[0.0, 0.0], 126.9]      # 从原点看（单点）
            ]
        }
    }

    print("\n输入数据:")
    print(f"  活跃频道: {scan_result['active_channels']}")
    for ch in scan_result['active_channels']:
        data = scan_result['scan_data'][str(ch)]
        print(f"  频道 {ch}: {len(data)} 个检测点")

    # 运行阶段2
    targets = phase2_localization(scan_result, enable_single_point=True, verbose=False)

    print(f"\n输出结果:")
    print(f"  定位目标: {len(targets)} 个")

    for i, target in enumerate(targets, 1):
        print(f"  {i}. 频道{target.channel_id}: "
              f"中心({target.center[0]:.1f}, {target.center[1]:.1f}), "
              f"D={target.diameter:.1f}m, conf={target.confidence:.2f}")

    # 验证
    assert len(targets) > 0, "应该至少定位到1个目标"
    assert all(t.center is not None for t in targets), "所有目标应该有中心坐标"
    assert all(t.diameter > 0 for t in targets), "所有目标应该有正的直径"

    print(f"\n✓ 阶段2集成测试通过")

    return targets


def test_phase3_integration():
    """测试阶段3集成"""
    print("\n" + "="*60)
    print("测试：阶段3集成")
    print("="*60)

    # 创建模拟目标
    targets = [
        Target(1, [], center=np.array([100, 100]), diameter=20, confidence=0.85, method='two_point'),
        Target(2, [], center=np.array([500, -500]), diameter=35, confidence=0.80, method='two_point'),
        Target(3, [], center=np.array([-300, 400]), diameter=500, confidence=0.30, method='single_point'),
    ]

    print(f"\n输入数据:")
    print(f"  目标数量: {len(targets)}")
    for i, t in enumerate(targets, 1):
        print(f"  {i}. 频道{t.channel_id}: D={t.diameter:.1f}m, conf={t.confidence:.2f}")

    # 创建模拟机器狗
    robot = create_mock_robot()

    # 运行阶段3
    print(f"\n运行阶段3...")
    result = phase3_patrol_and_clear(targets, robot, enable_2opt=False)

    print(f"\n输出结果:")
    print(f"  成功清除: {len(result['cleared'])}/{len(targets)}")
    print(f"  清除失败: {len(result['failed'])}")
    print(f"  清除比例: {result['clearing_ratio']*100:.1f}%")
    print(f"  总时间: {result['total_time']:.1f}秒")

    # 验证
    assert result['clearing_ratio'] > 0, "应该至少清除1个目标"
    assert result['total_time'] > 0, "总时间应该>0"

    print(f"\n✓ 阶段3集成测试通过")

    return result


def test_full_pipeline():
    """测试完整流程（阶段2→阶段3）"""
    print("\n" + "="*60)
    print("测试：完整流程（阶段2→阶段3）")
    print("="*60)

    # 阶段2
    print("\n步骤1: 阶段2定位")
    scan_result = {
        'active_channels': [1, 2, 3],
        'scan_data': {
            '1': [[[0.0, 0.0], 45.0], [[200.0, 0.0], 153.4]],
            '2': [[[0.0, 0.0], 315.0], [[900.0, 0.0], 231.3]],
            '3': [[[0.0, 0.0], 126.9]]
        }
    }

    targets = phase2_localization(scan_result, enable_single_point=True, verbose=False)
    print(f"  定位结果: {len(targets)} 个目标")

    # 阶段3
    print("\n步骤2: 阶段3清除")
    robot = create_mock_robot()
    result = phase3_patrol_and_clear(targets, robot, enable_2opt=False)
    print(f"  清除结果: {len(result['cleared'])}/{len(targets)}")

    # 验证
    assert len(targets) > 0, "阶段2应该定位到目标"
    assert result['clearing_ratio'] > 0, "阶段3应该清除目标"

    print(f"\n✓ 完整流程测试通过")

    return targets, result


def run_all_integration_tests():
    """运行所有集成测试"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*20 + "集成测试" + " "*20 + "║")
    print("╚" + "="*58 + "╝")

    try:
        # 测试1: 阶段2
        test_phase2_integration()

        # 测试2: 阶段3
        test_phase3_integration()

        # 测试3: 完整流程
        test_full_pipeline()

        print("\n╔" + "="*58 + "╗")
        print("║" + " "*16 + "✓ 所有集成测试通过！" + " "*16 + "║")
        print("╚" + "="*58 + "╝\n")

        return True

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}\n")
        return False

    except Exception as e:
        print(f"\n✗ 测试出现异常: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_integration_tests()
    exit(0 if success else 1)
