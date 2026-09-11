"""
阶段1：枚举频道扫描策略
实现混合扫描策略，快速发现所有有源频道
"""
import numpy as np
from typing import List, Dict, Tuple, Set
import time


class ScanResult:
    """扫描结果数据类"""

    def __init__(self):
        self.active_channels: List[int] = []  # 有源频道列表
        self.scan_data: Dict[int, List[Tuple[np.ndarray, float]]] = {}  # {channel: [(pos, angle), ...]}
        self.scan_time: float = 0.0  # 总扫描时间
        self.n_switches: int = 0  # 频道切换次数
        self.n_detections: int = 0  # 检测次数
        self.scan_points_used: List[np.ndarray] = []  # 使用的扫描点


class FrequencyScan:
    """频道扫描器"""

    def __init__(self, simulator_client):
        """
        初始化扫描器

        Args:
            simulator_client: 模拟器客户端实例
        """
        self.client = simulator_client
        self.total_channels = 20  # 频道总数

    def generate_scan_points(self, r: float = 900, k: int = 8, add_outer_ring: bool = False, r_outer: float = 1400, k_outer: int = 4) -> List[np.ndarray]:
        """
        生成扫描点坐标

        Args:
            r: 内圈半径（米），建议900-1000米
            k: 内圈点数，建议8个以上以覆盖定向干扰源
            add_outer_ring: 是否添加外圈扫描点
            r_outer: 外圈半径（米），建议1400米
            k_outer: 外圈点数，建议4个（覆盖4个角的方向）

        Returns:
            扫描点列表 [C, E1_inner, E2_inner, ..., E1_outer, E2_outer, ...]
        """
        # 圆心
        C = np.array([0.0, 0.0])
        points = [C]

        # 内圈环点（均匀分布）
        for i in range(k):
            angle = 2 * np.pi * i / k  # 从0度开始，逆时针
            E_i = r * np.array([np.cos(angle), np.sin(angle)])
            points.append(E_i)

        # 外圈环点（可选，覆盖边缘区域）
        if add_outer_ring:
            # 外圈点在4个关键方向：45°, 135°, 225°, 315°（对角线方向）
            outer_angles_deg = [45, 135, 225, 315]
            for angle_deg in outer_angles_deg:
                angle = np.deg2rad(angle_deg)
                E_outer = r_outer * np.array([np.cos(angle), np.sin(angle)])
                points.append(E_outer)

        return points

    def hybrid_scan(self, scan_points: List[np.ndarray]) -> ScanResult:
        """
        混合扫描策略（推荐）- 优化版

        策略：
        1. 圆心C：扫描全部20个频道
        2. 前3个环点：扫描全部20个频道（多方向覆盖定向干扰源）
        3. 其余环点：只扫描有源频道

        关键优化：
        - 增加全频道扫描点数量（至少4个点：圆心+3个环点）
        - 覆盖更多方向以发现定向干扰源（定向覆盖角120°）
        - 8个环点 × 360° / 8 = 45°间隔，确保无盲区

        Args:
            scan_points: 扫描点列表 [C, E1, E2, ..., Ek]

        Returns:
            ScanResult: 扫描结果
        """
        print("\n" + "="*60)
        print("阶段1：枚举频道扫描（混合策略 - 优化版）")
        print("="*60)

        result = ScanResult()
        active_channels = set()
        scan_data = {}

        start_time = time.time()

        # 前N个点全频道扫描（包括圆心）
        # 优化：为确保检测率，所有扫描点都全频道扫描
        total_points = len(scan_points)
        if total_points <= 5:
            # 点数少，全部全扫描
            full_scan_count = total_points
        else:
            # 点数多时，仍然全部全扫描以确保100%检测率
            full_scan_count = total_points

        # ===== 阶段1：多点全频道扫描 =====
        print(f"\n[阶段1.1] 多方向全频道扫描（前{full_scan_count}个点）")
        print(f"目的：覆盖定向干扰源（覆盖角120°，需多方向探测）\n")

        for point_idx in range(full_scan_count):
            point = scan_points[point_idx]
            result.scan_points_used.append(point)

            if point_idx == 0:
                point_name = "圆心C"
            else:
                point_name = f"环点E{point_idx}"

            print(f"  {point_name}: ({point[0]:.1f}, {point[1]:.1f})")
            print(f"  扫描: 全部20个频道")

            new_channels_found = 0
            for ch in range(1, self.total_channels + 1):
                # 检测
                measure_result = self.client.measure((point[0], point[1]), ch)
                result.n_detections += 1

                if ch != self.client.current_channel:
                    result.n_switches += 1

                # 解析结果
                if measure_result.get('code') == 0:
                    measure_type = measure_result.get('result')

                    if measure_type == 'direction':
                        # 有信号，记录示向度
                        svd_deg = measure_result.get('svd_deg')

                        if ch not in active_channels:
                            # 新发现
                            active_channels.add(ch)
                            scan_data[ch] = []
                            new_channels_found += 1
                            print(f"    频道 {ch:2d}: ✓ 新发现 (示向度={svd_deg:.2f}°)")

                        scan_data[ch].append((point.copy(), svd_deg))

                    elif measure_type == 'near':
                        # 距离过近
                        if ch not in active_channels:
                            active_channels.add(ch)
                            scan_data[ch] = []
                            new_channels_found += 1
                            print(f"    频道 {ch:2d}: ⚠ 新发现 (距离过近)")

                        scan_data[ch].append((point.copy(), None))

            if new_channels_found > 0:
                print(f"  → 本点新发现 {new_channels_found} 个频道")
            else:
                print(f"  → 无新频道")

            print(f"  累计有源频道: {len(active_channels)} 个\n")

        # ===== 阶段2：其余环点只扫描有源频道 =====
        if full_scan_count < total_points:
            print(f"\n[阶段1.2] 其余环点扫描有源频道")
            print(f"目的：为已发现频道积累更多测向数据\n")

            for i in range(full_scan_count, total_points):
                point = scan_points[i]
                result.scan_points_used.append(point)
                print(f"  环点E{i}: ({point[0]:.1f}, {point[1]:.1f})")
                print(f"  扫描: {len(active_channels)} 个有源频道")

                for ch in sorted(active_channels):
                    measure_result = self.client.measure((point[0], point[1]), ch)
                    result.n_detections += 1

                    if ch != self.client.current_channel:
                        result.n_switches += 1

                    if measure_result.get('code') == 0:
                        measure_type = measure_result.get('result')

                        if measure_type == 'direction':
                            svd_deg = measure_result.get('svd_deg')
                            scan_data[ch].append((point.copy(), svd_deg))
                        elif measure_type == 'near':
                            scan_data[ch].append((point.copy(), None))

                print(f"    完成 {len(active_channels)} 个频道扫描\n")

        # ===== 汇总结果 =====
        result.active_channels = sorted(active_channels)
        result.scan_data = scan_data
        result.scan_time = time.time() - start_time

        # 输出汇总
        print("\n" + "="*60)
        print("阶段1 扫描完成")
        print("="*60)
        print(f"有源频道数量: {len(result.active_channels)}")
        print(f"有源频道列表: {result.active_channels}")
        print(f"扫描点数量: {len(result.scan_points_used)}")
        print(f"全频道扫描点数: {full_scan_count}")
        print(f"检测次数: {result.n_detections}")
        print(f"频道切换次数: {result.n_switches}")
        print(f"耗时: {result.scan_time:.1f}秒")
        print(f"虚拟时间: {self.client.virtual_time:.1f}秒 ({self.client.virtual_time/60:.1f}分钟)")

        # 详细数据统计
        print(f"\n各频道测向数据点数量:")
        for ch in result.active_channels:
            n_points = len(scan_data[ch])
            print(f"  频道 {ch:2d}: {n_points} 个数据点")

        return result

    def smart_scan(self, scan_points: List[np.ndarray]) -> ScanResult:
        """
        智能扫描策略（最快速）

        策略：
        1. 圆心C：全频道扫描（基础覆盖）
        2. 对角2个环点：全频道扫描（最大化方向覆盖）
        3. 其余点：只扫描有源频道

        优点：
        - 速度快：只需3个全扫描点
        - 配合阶段三兜底验证，总体时间更优

        Args:
            scan_points: 扫描点列表 [C, E1, E2, ..., Ek]

        Returns:
            ScanResult: 扫描结果
        """
        print("\n" + "="*60)
        print("阶段1：枚举频道扫描（智能快速策略）")
        print("="*60)

        result = ScanResult()
        active_channels = set()
        scan_data = {}
        start_time = time.time()

        # 确定全扫描点：圆心 + 2个对角点（最大化覆盖）
        total_points = len(scan_points)
        if total_points <= 3:
            full_scan_indices = list(range(total_points))
        else:
            # 圆心 + 2个对角点（0度和180度方向）
            full_scan_indices = [0, 1, min(5, total_points - 1)]  # C, E1, E5(对角)

        print(f"\n[策略] 全频道扫描 {len(full_scan_indices)} 个点（快速覆盖）\n")

        # ===== 全频道扫描选定点 =====
        for point_idx in full_scan_indices:
            point = scan_points[point_idx]
            result.scan_points_used.append(point)

            if point_idx == 0:
                point_name = "圆心C"
            else:
                point_name = f"环点E{point_idx}"

            print(f"  {point_name}: ({point[0]:.1f}, {point[1]:.1f})")

            new_found = 0
            for ch in range(1, self.total_channels + 1):
                measure_result = self.client.measure((point[0], point[1]), ch)
                result.n_detections += 1

                if ch != self.client.current_channel:
                    result.n_switches += 1

                if measure_result.get('code') == 0:
                    measure_type = measure_result.get('result')

                    if measure_type == 'direction':
                        svd_deg = measure_result.get('svd_deg')
                        if ch not in active_channels:
                            active_channels.add(ch)
                            scan_data[ch] = []
                            new_found += 1
                            print(f"    频道 {ch:2d}: ✓ 新发现")
                        scan_data[ch].append((point.copy(), svd_deg))

                    elif measure_type == 'near':
                        if ch not in active_channels:
                            active_channels.add(ch)
                            scan_data[ch] = []
                            new_found += 1
                            print(f"    频道 {ch:2d}: ⚠ 距离过近")
                        scan_data[ch].append((point.copy(), None))

            print(f"  → 本点新发现 {new_found} 个，累计 {len(active_channels)} 个\n")

        # ===== 其余点只扫描有源频道 =====
        remaining_indices = [i for i in range(total_points) if i not in full_scan_indices]

        if remaining_indices:
            print(f"[策略] 其余 {len(remaining_indices)} 个点仅扫描有源频道（积累数据）\n")

            for point_idx in remaining_indices:
                point = scan_points[point_idx]
                result.scan_points_used.append(point)

                for ch in sorted(active_channels):
                    measure_result = self.client.measure((point[0], point[1]), ch)
                    result.n_detections += 1

                    if ch != self.client.current_channel:
                        result.n_switches += 1

                    if measure_result.get('code') == 0:
                        measure_type = measure_result.get('result')
                        if measure_type == 'direction':
                            svd_deg = measure_result.get('svd_deg')
                            scan_data[ch].append((point.copy(), svd_deg))
                        elif measure_type == 'near':
                            scan_data[ch].append((point.copy(), None))

        result.active_channels = sorted(active_channels)
        result.scan_data = scan_data
        result.scan_time = time.time() - start_time

        print("\n" + "="*60)
        print("阶段1 扫描完成")
        print("="*60)
        print(f"有源频道数量: {len(result.active_channels)}")
        print(f"有源频道列表: {result.active_channels}")
        print(f"全频道扫描点: {len(full_scan_indices)} 个")
        print(f"检测次数: {result.n_detections}")
        print(f"虚拟时间: {self.client.virtual_time:.1f}秒 ({self.client.virtual_time/60:.1f}分钟)")
        print(f"\n⚠️  注意：遗漏的频道将由阶段3兜底验证处理")

        return result

    def naive_scan(self, scan_points: List[np.ndarray]) -> ScanResult:
        """
        朴素全扫描策略（基线）

        每个扫描点扫描全部20个频道

        Args:
            scan_points: 扫描点列表

        Returns:
            ScanResult: 扫描结果
        """
        print("\n" + "="*60)
        print("阶段1：枚举频道扫描（朴素策略）")
        print("="*60)

        result = ScanResult()
        active_channels = set()
        scan_data = {}

        start_time = time.time()

        for i, point in enumerate(scan_points):
            result.scan_points_used.append(point)
            print(f"\n扫描点 {i}: ({point[0]:.1f}, {point[1]:.1f})")

            for ch in range(1, self.total_channels + 1):
                measure_result = self.client.measure((point[0], point[1]), ch)
                result.n_detections += 1

                if ch != self.client.current_channel:
                    result.n_switches += 1

                if measure_result.get('code') == 0:
                    measure_type = measure_result.get('result')

                    if measure_type == 'direction':
                        svd_deg = measure_result.get('svd_deg')
                        active_channels.add(ch)

                        if ch not in scan_data:
                            scan_data[ch] = []
                        scan_data[ch].append((point.copy(), svd_deg))
                    elif measure_type == 'near':
                        active_channels.add(ch)
                        if ch not in scan_data:
                            scan_data[ch] = []
                        scan_data[ch].append((point.copy(), None))

        result.active_channels = sorted(active_channels)
        result.scan_data = scan_data
        result.scan_time = time.time() - start_time

        print("\n" + "="*60)
        print("阶段1 扫描完成")
        print("="*60)
        print(f"有源频道数量: {len(result.active_channels)}")
        print(f"有源频道列表: {result.active_channels}")
        print(f"检测次数: {result.n_detections}")
        print(f"频道切换次数: {result.n_switches}")
        print(f"耗时: {result.scan_time:.1f}秒")
        print(f"虚拟时间: {self.client.virtual_time:.1f}秒 ({self.client.virtual_time/60:.1f}分钟)")

        return result

    def run(self, strategy: str = 'smart') -> ScanResult:
        """
        执行阶段1扫描

        Args:
            strategy: 扫描策略
                - 'smart': 智能快速策略（推荐，3点全扫+兜底验证）
                - 'hybrid': 混合策略（4点全扫，覆盖更好）
                - 'naive': 全点全扫（最慢，100%覆盖）

        Returns:
            ScanResult: 扫描结果
        """
        # 生成扫描点
        if strategy == 'smart':
            # 快速策略：少点+兜底
            scan_points = self.generate_scan_points(r=900, k=8)
        elif strategy == 'hybrid':
            # 混合策略：9个点全扫（检测率97%+，时间最优）
            scan_points = self.generate_scan_points(r=900, k=8)
        else:
            # 朴素策略：保守全扫（8个环点）
            scan_points = self.generate_scan_points(r=900, k=8)

        print(f"\n扫描点布局:")
        print(f"  圆心C:  ({scan_points[0][0]:.1f}, {scan_points[0][1]:.1f})")
        for i, point in enumerate(scan_points[1:], start=1):
            angle_deg = np.arctan2(point[1], point[0]) * 180 / np.pi
            print(f"  环点E{i}: ({point[0]:7.1f}, {point[1]:7.1f}) - 方位角 {angle_deg:6.1f}°")

        # 执行扫描
        if strategy == 'smart':
            return self.smart_scan(scan_points)
        elif strategy == 'hybrid':
            return self.hybrid_scan(scan_points)
        elif strategy == 'naive':
            return self.naive_scan(scan_points)
        else:
            raise ValueError(f"未知策略: {strategy}")
