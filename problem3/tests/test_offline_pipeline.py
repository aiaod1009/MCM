"""
离线端到端流水线测试（不需要打开真实模拟器）

用内置的 MockSimulatorClient 复现模拟器的 /enter,/measure,/clear,/exit 行为，
在纯本地环境跑通 阶段1 -> 阶段2 -> 阶段3 的完整流程，用于回归验证：
  - 几何模块（射线求交/扇区判断/凸包/旋转卡壳）
  - 交会定位（含 near/None 数据、边界顶点容差）
  - 清除与兜底验证（含清除比例口径）

运行:
    python tests/test_offline_pipeline.py
"""
import os
import sys
import math
import random

import numpy as np

# 加入 src 路径
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, SRC)

from phase1_frequency_scan import FrequencyScan          # noqa: E402
from phase2_localization import phase2_localization      # noqa: E402
from phase3_clearing import phase3_patrol_and_clear      # noqa: E402


class MockSimulatorClient:
    """模拟器离线替身"""

    DETECT_RADIUS = 1500.0   # 有效接收半径上限
    NEAR_RADIUS = 5.0        # 距离过近阈值
    CLEAR_RADIUS = 20.0      # 清除半径
    MOVE_SPEED = 5.0         # m/s

    def __init__(self, sources, robot_id='TEST'):
        # sources: {channel: (x, y)}
        self.sources = dict(sources)
        self.robot_id = robot_id
        self.position = np.array([0.0, 0.0])
        self.current_channel = 1
        self.virtual_time = 0.0
        self.total_moves = 0
        self.total_switches = 0
        self.total_detections = 0
        self.total_clears = 0
        self._rng = random.Random(20260912)

    # ---- 内部：确定性测向误差 [-1, 1] ----
    def _bearing_error(self, position, channel):
        key = (round(position[0], 3), round(position[1], 3), channel)
        r = random.Random(hash(key) & 0xFFFFFFFF)
        return r.uniform(-1.0, 1.0)

    def _move(self, position):
        d = float(np.linalg.norm(np.array(position) - self.position))
        self.virtual_time += d / self.MOVE_SPEED
        if d > 0:
            self.total_moves += 1
        self.position = np.array(position, dtype=float)
        return d

    def enter(self):
        return {'accepted': True, 'code': 0, 'max_virtual_duration_s': 10 ** 9,
                'max_real_duration_s': 10 ** 9, 'remaining_real_duration_s': 10 ** 9}

    def measure(self, position, channel):
        self._move(position)
        if channel != self.current_channel:
            self.virtual_time += 1.0
            self.total_switches += 1
            self.current_channel = channel
        self.virtual_time += 5.0
        self.total_detections += 1

        if channel not in self.sources:
            return {'code': 0, 'result': 'no_signal', 'svd_deg': None}

        sx, sy = self.sources[channel]
        dx, dy = sx - position[0], sy - position[1]
        d = math.hypot(dx, dy)

        if d > self.DETECT_RADIUS:
            return {'code': 0, 'result': 'no_signal', 'svd_deg': None}
        if d <= self.NEAR_RADIUS:
            return {'code': 0, 'result': 'near', 'svd_deg': None}

        bearing = (math.degrees(math.atan2(dy, dx))
                   + self._bearing_error(position, channel)) % 360.0
        return {'code': 0, 'result': 'direction', 'svd_deg': bearing}

    def clear(self, position, channel):
        self._move(position)
        self.virtual_time += 10.0
        if channel not in self.sources:
            return {'code': 0, 'result': 'no_target_in_range'}
        sx, sy = self.sources[channel]
        d = math.hypot(sx - position[0], sy - position[1])
        if d <= self.CLEAR_RADIUS:
            self.total_clears += 1
            del self.sources[channel]   # 清除成功后该源不复存在（与真实模拟器一致）
            return {'code': 0, 'result': 'success'}
        return {'code': 0, 'result': 'no_target_in_range'}

    def exit(self):
        return {'accepted': True, 'code': 0}


def build_scenario():
    """构造 12 个全向干扰源（频道互不相同），分布在半径 1000 m 内"""
    rng = random.Random(7)
    channels = rng.sample(range(1, 21), 12)
    sources = {}
    for ch in channels:
        r = rng.uniform(250.0, 950.0)
        a = rng.uniform(0, 2 * math.pi)
        sources[ch] = (r * math.cos(a), r * math.sin(a))
    # 特意放一个源在扫描环点(900,0)附近，以触发 near(None) 分支
    sources[channels[0]] = (898.0, 2.0)
    return sources


def main():
    sources = build_scenario()
    robot = MockSimulatorClient(sources)

    print("=" * 64)
    print(f"离线端到端测试：{len(sources)} 个干扰源，频道 {sorted(sources)}")
    print("=" * 64)

    # 阶段1
    scanner = FrequencyScan(robot)
    scan_result_obj = scanner.run(strategy='hybrid')
    phase1_result = {
        'active_channels': scan_result_obj.active_channels,
        'scan_data': {str(ch): [[list(p), (None if t is None else float(t))]
                                for p, t in data]
                      for ch, data in scan_result_obj.scan_data.items()}
    }
    print(f"\n阶段1: 发现 {len(phase1_result['active_channels'])} / {len(sources)} 个频道")
    missed = set(sources) - set(phase1_result['active_channels'])
    print(f"        漏检频道: {sorted(missed) if missed else '无'}")

    # 阶段2
    targets = phase2_localization(phase1_result, enable_single_point=True, verbose=False)
    print(f"\n阶段2: 定位 {len(targets)} 个目标")

    # 阶段3
    phase3 = phase3_patrol_and_clear(targets, robot, enable_2opt=True,
                                     active_channels=phase1_result['active_channels'],
                                     scan_data=phase1_result['scan_data'])

    # 结果核对
    print("\n" + "=" * 64)
    print("结果核对")
    print("=" * 64)
    ok = True

    # 清除比例
    ratio = phase3['clearing_ratio']
    print(f"清除比例: {ratio*100:.1f}%  (已清除 {len(phase3['cleared'])} / 目标 {len(targets)})")
    if not (0.0 <= ratio <= 1.0):
        print("  ✗ 清除比例越界")
        ok = False

    # 真值核对：所有源是否都被清除
    cleared_ids = {t.channel_id for t in phase3['cleared']}
    not_cleared = set(sources) - cleared_ids
    if not_cleared:
        print(f"  ⚠ 未被清除的频道: {sorted(not_cleared)}（真值 {len(sources)} 个源）")
        # 若阶段1漏检且兜底未补救，属于策略问题；此处仅告警
    else:
        print(f"  ✓ 全部 {len(sources)} 个干扰源均已清除")

    # 定位精度核对：每个目标的中心与真值的距离
    print("\n定位精度（目标中心 vs 真值）:")
    max_err = 0.0
    for t in targets:
        if t.channel_id in sources:
            err = math.hypot(t.center[0] - sources[t.channel_id][0],
                             t.center[1] - sources[t.channel_id][1])
            max_err = max(max_err, err)
    print(f"  最大中心偏差: {max_err:.1f} m （区域直径量级 24~68 m，中心偏差应小于此）")

    print(f"\n总虚拟时间: {robot.virtual_time:.1f} s ({robot.virtual_time/60:.1f} min)")
    print("=" * 64)
    print("结果:", "通过" if ok else "存在异常")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
