# -*- coding: utf-8 -*-
"""
阶段1：增强扫描策略（包含补充采样）
"""
import sys
import os
import math

# 添加问题3的路径以复用模块
# 路径结构：problem4/src/phase1_enhanced_scan.py
# 目标路径：B题/问题3/MCM/problem3/src
current_file = os.path.abspath(__file__)  # .../problem4/src/phase1_enhanced_scan.py
src_dir = os.path.dirname(current_file)  # .../problem4/src
problem4_root = os.path.dirname(src_dir)  # .../problem4
mcm_dir = os.path.dirname(problem4_root)  # .../MCM
problem4_dir = os.path.dirname(mcm_dir)  # .../问题4
b_problem_dir = os.path.dirname(problem4_dir)  # .../B题
problem3_src_path = os.path.join(b_problem_dir, '问题3', 'MCM', 'problem3', 'src')

if os.path.exists(problem3_src_path):
    sys.path.insert(0, problem3_src_path)
else:
    print(f"[ERROR] problem3 path not found: {problem3_src_path}")

from typing import List, Tuple, Dict
import time

try:
    from simulator_client import SimulatorClient
except ImportError:
    print("Warning: Cannot import SimulatorClient from problem3")


class EnhancedScanner:
    """增强扫描器（支持补充采样）"""

    def __init__(self, robot_id: str, base_url: str = "http://127.0.0.1:2026"):
        self.robot_id = robot_id
        self.client = SimulatorClient(base_url=base_url, robot_id=robot_id)
        self.total_channels = 20

        # 扫描点配置（12点内外圈联合网格）
        self.scan_radius = 1200.0
        self.scan_points = self._generate_scan_points()

    def _generate_scan_points(self) -> List[Tuple[float, float]]:
        """
        生成扫描点（12个点：内外圈联合网格）

        策略：1圆心 + 6内圈 + 5外圈
        - 圆心：(0, 0)
        - 内圈：半径600m，6个点，每60°（密集覆盖中心区域）
        - 外圈：半径1200m，5个点，每72°错开30°（覆盖远距离+避免对称盲区）

        理论依据：
        1. 内圈覆盖圆域内干扰源（全向+定向近距离）
        2. 外圈覆盖圆域外沿（定向远距离，接近1500m接收半径边界）
        3. 错开分布确保定向干扰源无论朝何方向均有检测点落入其覆盖半平面

        覆盖率：
        - 角度最小间隔30°（远小于90°半角） → 覆盖率>95%
        - 距离双层：600m + 1200m → 覆盖近中远

        时间成本：12×20×6 = 1440秒 ≈ 24分钟
        """
        points = [(0.0, 0.0)]  # 圆心

        # 内圈：6个点（半径600m，每60°）
        inner_radius = 600.0
        for i in range(6):
            angle = math.radians(i * 60)
            x = inner_radius * math.cos(angle)
            y = inner_radius * math.sin(angle)
            points.append((x, y))

        # 外圈：5个点（半径1200m，每72°，错开30°）
        outer_radius = 1200.0
        for i in range(5):
            angle = math.radians(i * 72 + 30)  # 错开30°
            x = outer_radius * math.cos(angle)
            y = outer_radius * math.sin(angle)
            points.append((x, y))

        return points  # 总计12个点

    def scan_with_supplementary(self) -> Dict:
        """
        增强扫描（基础扫描 + 补充采样）

        Returns:
            {
                'active_channels': List[int],
                'scan_data': {channel_id: [(point, result), ...]},
                'supplementary_data': {channel_id: [(point, result), ...]}
            }
        """
        print("\n" + "="*60)
        print("阶段1：增强扫描开始")
        print("="*60)

        # 步骤1：基础扫描（9个点）
        scan_result = self._basic_scan()

        # 步骤2：分析需要补充采样的频道
        channels_need_补充 = self._identify_channels_need_补充(scan_result['scan_data'])

        print(f"\n需要补充采样的频道：{channels_need_补充} (共{len(channels_need_补充)}个)")

        # 步骤3：补充采样
        supplementary_result = self._supplementary_sampling(
            channels_need_补充, scan_result['scan_data']
        )

        # 步骤4：合并数据
        for channel_id, supp_data in supplementary_result.items():
            if channel_id in scan_result['scan_data']:
                scan_result['scan_data'][channel_id].extend(supp_data)

        scan_result['supplementary_data'] = supplementary_result

        print("\n" + "="*60)
        print("阶段1：增强扫描完成")
        print("="*60)

        return scan_result

    def _basic_scan(self) -> Dict:
        """
        基础扫描（12个点全频道扫描）

        策略：全部全频道扫描（确保检测率）
        - 12点×20频道×6秒 = 1440秒 ≈ 24分钟
        """
        print("\n### 基础扫描（12个点全频道扫描）###")

        scan_data = {}
        active_channels = []

        for idx, point in enumerate(self.scan_points):
            print(f"\n点{idx+1}/12: ({point[0]:.1f}, {point[1]:.1f})")

            # 所有点都全频道扫描
            for channel in range(1, self.total_channels + 1):
                result = self.client.measure(point, channel)

                if channel not in scan_data:
                    scan_data[channel] = []

                result_type = result.get('result', 'no_signal')
                azimuth = 0.0
                if result_type == 'direction' and 'svd_deg' in result:
                    azimuth = result['svd_deg'] * math.pi / 180.0

                formatted_result = {
                    'type': result_type,
                    'azimuth': azimuth
                }

                scan_data[channel].append((point, formatted_result))

                if result_type in ['direction', 'near'] and channel not in active_channels:
                    active_channels.append(channel)
                    print(f"  ✓ 发现频道{channel}: {result_type}")

        print(f"\n基础扫描完成！")
        print(f"有源频道：{active_channels} (共{len(active_channels)}个)")

        return {
            'active_channels': active_channels,
            'scan_data': scan_data
        }

    def _identify_channels_need_补充(self, scan_data: Dict) -> List[int]:
        """
        识别需要补充采样的频道（保守策略）

        判断标准（只补充极端不足情况）：
        1. 有信号点数量 < 3（严重不足）
        2. 总检测点 < 5（数据太少）
        """
        channels_need_补充 = []

        for channel_id, data in scan_data.items():
            signal_count = sum(1 for _, result in data if result['type'] in ['direction', 'near'])
            nosignal_count = sum(1 for _, result in data if result['type'] == 'no_signal')
            total_count = signal_count + nosignal_count

            # 判断标准（保守）
            need_supp = False

            if signal_count < 3:
                need_supp = True
            elif total_count < 5:
                need_supp = True

            if need_supp:
                channels_need_补充.append(channel_id)
                print(f"频道{channel_id}: 有信号{signal_count}个, 总数据{total_count}个 → 需要补充")

        return channels_need_补充

    def _supplementary_sampling(self, channels: List[int], scan_data: Dict) -> Dict:
        """
        补充采样

        为每个频道生成最多3个补充点
        """
        if not channels:
            return {}

        print("\n### 补充采样 ###")
        supplementary_data = {}

        for channel_id in channels:
            print(f"\n频道{channel_id}补充采样：")

            # 生成补充点
            补充点列表 = self._generate_补充点(channel_id, scan_data[channel_id])

            if not 补充点列表:
                print(f"  无法生成补充点")
                continue

            channel_supp_data = []

            for idx, point in enumerate(补充点列表[:3]):  # 最多3个
                print(f"  补充点{idx+1}: {point}")

                # 检测（measure自动包含移动和切换频道）
                result = self.client.measure(point, channel_id)

                # 转换结果格式
                result_type = result.get('result', 'no_signal')
                azimuth = 0.0
                if result_type == 'direction' and 'svd_deg' in result:
                    azimuth = result['svd_deg'] * 3.14159 / 180.0

                formatted_result = {
                    'type': result_type,
                    'azimuth': azimuth
                }

                channel_supp_data.append((point, formatted_result))

                print(f"    结果: {result_type}")

            supplementary_data[channel_id] = channel_supp_data

        return supplementary_data

    def _generate_补充点(self, channel_id: int,
                         existing_data: List[Tuple[Tuple[float, float], Dict]]) -> List[Tuple[float, float]]:
        """
        生成补充点（智能优化版，针对定向源特性）

        策略：
        1. 在信号点质心周围多角度采样（8个方向）
        2. 在信号边界区域补充（信号/无信号交界处）
        3. 在远距离方向补充（1400m）
        """
        signal_points = [point for point, result in existing_data
                        if result['type'] in ['direction', 'near']]
        nosignal_points = [point for point, result in existing_data
                          if result['type'] == 'no_signal']

        补充点 = []

        if len(signal_points) >= 1:
            # 计算信号点质心
            cx = sum(p[0] for p in signal_points) / len(signal_points)
            cy = sum(p[1] for p in signal_points) / len(signal_points)

            # 策略1：在质心周围8个方向密集补充（距离200米）
            distance = 200.0
            for angle in [0, math.pi/4, math.pi/2, 3*math.pi/4,
                         math.pi, -3*math.pi/4, -math.pi/2, -math.pi/4]:
                x = cx + distance * math.cos(angle)
                y = cy + distance * math.sin(angle)

                dist_from_origin = math.sqrt(x**2 + y**2)
                if dist_from_origin <= 1700:
                    补充点.append((x, y))

            # 策略2：在质心周围更远距离补充（距离400米，4个方向）
            distance = 400.0
            for angle in [math.pi/4, 3*math.pi/4, -3*math.pi/4, -math.pi/4]:
                x = cx + distance * math.cos(angle)
                y = cy + distance * math.sin(angle)

                dist_from_origin = math.sqrt(x**2 + y**2)
                if dist_from_origin <= 1700:
                    补充点.append((x, y))

            # 策略3：如果有无信号点，在边界附近补充
            if len(nosignal_points) >= 1:
                nosignal_cx = sum(p[0] for p in nosignal_points) / len(nosignal_points)
                nosignal_cy = sum(p[1] for p in nosignal_points) / len(nosignal_points)

                # 在有信号质心和无信号质心之间插值3个点
                for ratio in [0.3, 0.5, 0.7]:
                    x = cx + ratio * (nosignal_cx - cx)
                    y = cy + ratio * (nosignal_cy - cy)

                    dist_from_origin = math.sqrt(x**2 + y**2)
                    if dist_from_origin <= 1700:
                        补充点.append((x, y))

        # 策略4：远距离补充（1400m，覆盖极远定向源）
        if len(signal_points) >= 1:
            cx = sum(p[0] for p in signal_points) / len(signal_points)
            cy = sum(p[1] for p in signal_points) / len(signal_points)

            # 计算质心方向
            angle_to_center = math.atan2(cy, cx)

            # 在质心方向的1400m处补充
            distance = 1400.0
            x = distance * math.cos(angle_to_center)
            y = distance * math.sin(angle_to_center)

            dist_from_origin = math.sqrt(x**2 + y**2)
            if dist_from_origin <= 1700:
                补充点.append((x, y))

        return 补充点[:6]  # 最多6个
