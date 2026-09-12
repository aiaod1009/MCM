"""
补救清除路径的离线单元测试（不需要真实模拟器）

覆盖 review_cleared() + clear_remaining_sources() 的四条策略分支：
  1. 两点交会 → 直接清除
  2. near 点直清（阶段2拿不到示向度、旧实现会"无人过问"的那类频道）
  3. 交会中心偏差 20~40 m → 螺旋搜索兜住
  4. 完全无测向信息 → 回退原点 + 大半径螺旋

运行:
    python tests/test_recovery.py
"""
import os
import sys
import math

import numpy as np

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, SRC)

from clearing.verification import review_cleared, clear_remaining_sources  # noqa: E402
from target import Target                                                  # noqa: E402


class MockRobot:
    """只保留补救清除所需接口的极简替身"""

    CLEAR_RADIUS = 20.0
    MOVE_SPEED = 5.0

    def __init__(self, sources):
        self.sources = dict(sources)
        self.position = np.array([0.0, 0.0])
        self.virtual_time = 0.0
        self.clear_calls = 0

    def clear(self, position, channel):
        self.clear_calls += 1
        self.virtual_time += float(
            np.linalg.norm(np.array(position) - self.position)) / self.MOVE_SPEED
        self.virtual_time += 3.0
        self.position = np.array(position, dtype=float)

        if channel not in self.sources:
            return {'code': 0, 'result': 'no_target_in_range'}
        sx, sy = self.sources[channel]
        if math.hypot(sx - self.position[0], sy - self.position[1]) <= self.CLEAR_RADIUS:
            self.virtual_time += 2.0
            del self.sources[channel]
            return {'code': 0, 'result': 'success'}
        return {'code': 0, 'result': 'no_target_in_range'}


def bearing(frm, to):
    return math.degrees(math.atan2(to[1] - frm[1], to[0] - frm[0])) % 360.0


def main():
    ok = True

    # ---------------------------------------------------------------
    # 场景：4 个未确认清除的频道，分别命中 4 条策略分支
    # ---------------------------------------------------------------
    sources = {
        1: (500.0, 500.0),    # 交会中心即为真值 → 直接清除成功
        2: (898.0, 2.0),      # 只有 near 点（(900,0) 距其 2.83 m）
        3: (500.0, 535.0),    # 交会中心 (500,500) 偏差 35 m → 需螺旋
        4: (30.0, 0.0),       # 无任何测向信息 → 回退原点 + 螺旋
    }
    robot = MockRobot(sources)

    targets = [
        Target(1, [], center=np.array([500.0, 500.0]), diameter=10.0,
               confidence=0.9, method='two_point'),
    ]

    scan_data = {
        # 频道1：两个带示向度的扫描点（正演于真值，无误差）
        '1': [[[0.0, 0.0], bearing((0, 0), (500, 500))],
              [[900.0, 0.0], bearing((900, 0), (500, 500))]],
        # 频道2：全部为 near（无示向度）
        '2': [[[900.0, 0.0], None]],
        # 频道3：两个带示向度的扫描点，指向 (500,535)
        '3': [[[0.0, 0.0], bearing((0, 0), (500, 535))],
              [[900.0, 0.0], bearing((900, 0), (500, 535))]],
        # 频道4：阶段1有源，但没有任何可用检测点
        '4': [],
    }

    remaining, detections = review_cleared(
        active_channels=[1, 2, 3, 4, 99],   # 99 从未返回 success → 也应进复核
        targets=targets,
        cleared_targets=[],                 # 没有任何目标返回过 success
        scan_data=scan_data,
        verbose=True,
    )

    print("\n" + "=" * 64)
    if remaining != [1, 2, 3, 4, 99]:
        print(f"✗ review_cleared 输出异常: {remaining}")
        ok = False
    else:
        print(f"✓ review_cleared 正确列出待补救频道: {remaining}")

    recovered = clear_remaining_sources(robot, remaining, detections)

    print("\n" + "=" * 64)
    print("补救结果核对")
    print("=" * 64)
    print(f"补救成功频道: {sorted(recovered)}")
    print(f"剩余未清除源: {sorted(robot.sources)}")
    print(f"清除指令调用次数: {robot.clear_calls}，虚拟时间 {robot.virtual_time:.1f} s")

    expected_ok = {1, 2, 3, 4}
    if set(recovered) != expected_ok:
        print(f"✗ 应补救成功 {sorted(expected_ok)}，实际 {sorted(recovered)}")
        ok = False
    else:
        print("✓ 分支 1/2/3/4 全部补救成功")

    # 频道 99 本来就不存在 → 不允许被记成"已清除"
    if 99 in recovered:
        print("✗ 不存在的频道 99 被误记为已清除")
        ok = False
    else:
        print("✓ 不存在的频道 99 未被误记为已清除（清除比例不会被虚增）")

    print("\n" + "=" * 64)
    print("结果:", "通过" if ok else "存在异常")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
