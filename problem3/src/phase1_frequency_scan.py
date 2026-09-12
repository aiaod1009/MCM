"""
阶段1：枚举频道扫描策略
实现混合扫描策略，快速发现所有有源频道
"""
import numpy as np
from typing import List, Dict, Tuple, Set
import time


# ======================================================================
# 扫描布局参数
# ======================================================================
# 目标区域为半径 1800 m 的圆域；每个干扰源的有效接收半径各自在 1000~1500 m。
# "确保探测"要求：圆域内任意一点到"最近一个扫描点"的距离 ≤ 1000 m
# （取源的最小有效接收半径作为最坏情况阈值）。
# 数值扫描（圆心 + 8 个环点，细网格采样整个圆域）：
#   r = 900  → 最远点距 1027.9 m  ✗ 不保证（存在扫不到的边角）
#   r = 1000 → 最远点距  956   m  △ 临界，余量仅 44 m
#   r = 1100 → 最远点距  890   m  ✓
#   r = 1200 → 最远点距  830   m  ✓ 余量 170 m（本程序采用）
# 代价：环点半径增大 → 阶段1移动距离增大 → 虚拟时间增加约 380 s。
SCAN_RING_RADIUS = 1200.0   # 扫描环半径（米）
SCAN_RING_POINTS = 8        # 环上扫描点数
# 做"全频道扫描"的扫描点个数；None 表示所有扫描点都全频道扫描（默认，确保不漏检）。
# 设为小于 9 的值可减少检测次数、缩短阶段1时间，但会牺牲探测完备性保证。
FULL_SCAN_POINTS = None
# ======================================================================


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

    def generate_scan_points(self, r: float = SCAN_RING_RADIUS, k: int = SCAN_RING_POINTS, add_outer_ring: bool = False, r_outer: float = 1400, k_outer: int = 4) -> List[np.ndarray]:
        """
        生成扫描点坐标

        Args:
            r: 内圈半径（米），默认 1200（见模块顶部 SCAN_RING_RADIUS 的覆盖性论证）
            k: 内圈点数，默认 8（45° 间隔，配合 r=1200 可保证圆域全域覆盖）
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
        混合扫描策略（推荐）

        策略：
        1. 每个扫描点都扫描全部 20 个频道（发现新源 + 为已发现源积累测向数据）

        为什么不是"前几个点全扫、其余点只扫有源频道"：
        ---------------------------------------------------------------
        一个源只有在"机器狗距它 ≤ 其有效接收半径"时才能被检测到。若只在
        前 m 个扫描点上做全频道扫描，则位于第 m+1..k 个扫描点附近（而离前
        m 个点都超过 1000 m）的源会被漏掉。以 r=1200、8 环点为例：环点
        E5=(-1200,0) 处的源到 E1=(1200,0) 的距离为 2400 m > 1000 m，
        若 E5 不做全频道扫描就会整片漏检。
        因此，只有在【每个扫描点】都做全频道扫描时，"全域任一点距最近扫描
        点 ≤ 1000 m"这一覆盖性保证（见 SCAN_RING_RADIUS 注释）才能转化为
        "任一源至少被检测到一次"的保证。
        ---------------------------------------------------------------
        代价：9 点 × 20 频道 = 180 次检测（虚拟时间 180×6 = 1080 s），
        这是阶段1的主要开销，属"确保不漏检"的必要成本。

        Args:
            scan_points: 扫描点列表 [C, E1, E2, ..., Ek]

        Returns:
            ScanResult: 扫描结果
        """
        print("\n" + "="*60)
        print("阶段1：枚举频道扫描（混合策略）")
        print("="*60)

        result = ScanResult()
        active_channels = set()
        scan_data = {}

        start_time = time.time()

        # 全频道扫描点数：默认全部扫描点（确保发现全部有源频道，见上方论证）
        total_points = len(scan_points)
        full_scan_count = FULL_SCAN_POINTS if FULL_SCAN_POINTS is not None else total_points
        full_scan_count = min(full_scan_count, total_points)

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
        - 仅适用于快速试跑

        警告：
        - 只在 3 个点做全扫，放弃"不漏检"保证；阶段3的清除复核
          （review_cleared）以"阶段1不漏检"为前提，故正式测试必须用
          strategy='hybrid'。本策略保留仅作速度对比。

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

    def run(self, strategy: str = 'hybrid') -> ScanResult:
        """
        执行阶段1扫描

        Args:
            strategy: 扫描策略
                - 'hybrid': 混合策略（默认，推荐）——圆心 + 8 个环点，
                  9 个点全部做 20 频道全扫。此时"圆域内任一点距最近扫描点
                  ≤ 830 m ≤ 1000 m"才成立，阶段1才能保证不漏检任何全向源。
                - 'naive': 全点全扫（与 hybrid 同为完备扫描，仅打印/统计口径更啰嗦）
                - 'smart': 快速策略（仅前 3 个点做全扫）——检测次数更少，
                  但**放弃"不漏检"的保证**，只应用于快速试跑；
                  阶段3的记账复核（review_cleared）以"阶段1不漏检"为前提，
                  故正式测试必须使用 hybrid。

        Returns:
            ScanResult: 扫描结果
        """
        # 生成扫描点（r=1200 满足"圆域内任一点距最近扫描点 ≤1000m"的探测保证）
        if strategy == 'smart':
            # 快速策略：只有前 3 个点做全扫 → 不保证不漏检，仅用于快速试跑
            scan_points = self.generate_scan_points(r=SCAN_RING_RADIUS, k=SCAN_RING_POINTS)
        elif strategy == 'hybrid':
            # 混合策略：圆心+8环点，9个点全频道扫描（确保发现全部有源频道）
            scan_points = self.generate_scan_points(r=SCAN_RING_RADIUS, k=SCAN_RING_POINTS)
        else:
            # 朴素策略：保守全扫
            scan_points = self.generate_scan_points(r=SCAN_RING_RADIUS, k=SCAN_RING_POINTS)

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
