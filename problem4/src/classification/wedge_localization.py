# -*- coding: utf-8 -*-
"""
楔形交会定位算法（定向干扰源专用）
"""
import math
import sys
import os

# 添加问题3的路径以复用geometry模块
# 路径结构：problem4/src/classification/wedge_localization.py
# 目标路径：B题/问题3/MCM/problem3/src
current_file = os.path.abspath(__file__)  # .../problem4/src/classification/wedge_localization.py
classification_dir = os.path.dirname(current_file)  # .../problem4/src/classification
src_dir = os.path.dirname(classification_dir)  # .../problem4/src
problem4_root = os.path.dirname(src_dir)  # .../problem4
mcm_dir = os.path.dirname(problem4_root)  # .../MCM
problem4_dir = os.path.dirname(mcm_dir)  # .../问题4
b_problem_dir = os.path.dirname(problem4_dir)  # .../B题
problem3_src_path = os.path.join(b_problem_dir, '问题3', 'MCM', 'problem3', 'src')

if os.path.exists(problem3_src_path):
    sys.path.insert(0, problem3_src_path)
else:
    print(f"[ERROR] problem3 path not found: {problem3_src_path}")
    print(f"[DEBUG] current_file: {current_file}")
    print(f"[DEBUG] b_problem_dir: {b_problem_dir}")

from typing import List, Tuple, Dict, Optional
import numpy as np

# 复用问题3的几何模块（正确的导入）
try:
    from geometry.ray_intersection import ray_intersection
    from geometry.point_in_sector import point_in_sectors, point_in_sector
    from geometry.convex_hull import compute_convex_hull  # 正确的函数名
    from geometry.rotating_calipers import rotating_calipers
    _GEOMETRY_AVAILABLE = True
    print("[INFO] 成功导入问题3几何模块")
except ImportError as e:
    print(f"[ERROR] 无法导入问题3几何模块: {e}")
    print(f"[ERROR] 问题4依赖问题3的定位算法，请检查问题3代码完整性")
    _GEOMETRY_AVAILABLE = False
    raise ImportError("问题3几何模块导入失败，无法继续") from e


class WedgeLocalizer:
    """楔形交会定位器（定向干扰源专用）"""

    def __init__(self, error_angle_deg=1.0):
        """
        Args:
            error_angle_deg: 示向度误差角度（度）
        """
        self.error_angle_deg = error_angle_deg  # 保存度数
        self.error_angle = math.radians(error_angle_deg)  # 弧度（用于内部计算）

    def localize(self, detection_data: List[Tuple[Tuple[float, float], Dict]]) -> Dict:
        """
        统一定位算法（适用于全向+定向）

        策略：
        1. 先用两点交会计算有信号区域交集
        2. 如果有无信号点，应用约束缩小区域（定向源优化）
        3. 计算最小外接圆

        Args:
            detection_data: 检测数据 [(point, result), ...]

        Returns:
            {
                'center': (x, y),
                'diameter': float,
                'confidence': float,
                'method': 'wedge'
            }
        """
        # 分类检测点
        signal_points, nosignal_points = self._classify_points(detection_data)
        print(f"  → 有信号点: {len(signal_points)}个, 无信号点: {len(nosignal_points)}个")

        if len(signal_points) < 2:
            # 数据不足，使用单点估计
            print(f"  → 信号点不足(<2)，使用单点估计")
            return self._single_point_estimation(signal_points[0] if signal_points else ((0, 0), {}))

        # 步骤1：计算有信号扇形交集（两点交会）
        signal_region = self._compute_signal_intersection(signal_points)

        if signal_region is None or len(signal_region) == 0:
            # 扇形交集为空，回退到质心估计
            print(f"  → 扇形交集为空，回退到质心估计")
            return self._centroid_estimation(signal_points)

        # 步骤2：如果有无信号点，应用约束优化（定向源）
        if len(nosignal_points) > 2:
            # 估计发射方向
            emission_direction = self._estimate_emission_direction(signal_points, nosignal_points)
            print(f"  → 估计发射方向: {math.degrees(emission_direction):.1f}°")

            # 应用无信号点约束
            optimized_region = self._apply_nosignal_constraints(
                signal_region, nosignal_points, emission_direction
            )

            # 如果优化后区域变小（>20%缩减），使用优化结果
            if len(optimized_region) > 0 and len(optimized_region) < len(signal_region) * 0.8:
                signal_region = optimized_region
                print(f"  → 应用无信号约束，区域缩小 {len(signal_region)} 顶点")

        # 步骤3：计算最小外接圆
        center, diameter = self._compute_min_enclosing_circle(signal_region)

        # 步骤4：计算置信度
        confidence = self._compute_confidence(
            center, diameter, signal_points, nosignal_points
        )
        print(f"  → 最终结果: center=({center[0]:.1f}, {center[1]:.1f}), diameter={diameter:.1f}m, confidence={confidence:.2f}\n")

        return {
            'center': center,
            'diameter': diameter,
            'confidence': confidence,
            'method': 'wedge'
        }

    def _classify_points(self, detection_data):
        """分类检测点"""
        signal_points = []
        nosignal_points = []

        for point, result in detection_data:
            if result['type'] in ['direction', 'near']:
                azimuth = result.get('azimuth', 0.0)
                signal_points.append((point, azimuth))
            elif result['type'] == 'no_signal':
                nosignal_points.append(point)

        return signal_points, nosignal_points

    def _estimate_emission_direction(self, signal_points, nosignal_points) -> float:
        """
        估计发射方向

        使用质心法：干扰源应该在有信号点一侧，远离无信号点一侧
        """
        if len(nosignal_points) > 0:
            # 方法A：质心法
            signal_coords = [p[0] for p in signal_points]
            c_signal = self._compute_centroid(signal_coords)
            c_nosignal = self._compute_centroid(nosignal_points)

            dx = c_signal[0] - c_nosignal[0]
            dy = c_signal[1] - c_nosignal[1]

            direction = math.atan2(dy, dx)
        else:
            # 方法B：反向投影法（粗略估计）
            # 简化：取有信号点的平均示向度反方向
            azimuths = [az for _, az in signal_points]
            avg_azimuth = self._circular_mean(azimuths)
            direction = avg_azimuth + math.pi  # 反向

        return direction

    def _compute_signal_intersection(self, signal_points) -> List[Tuple[float, float]]:
        """
        计算有信号点的射线扇形交集（复用问题3算法）

        算法流程（与问题3 region_calculator.py 相同）：
        1. 构造边界射线（每个信号点2条：左右边界）
        2. 计算所有射线对的交点
        3. 筛选在所有扇形内的有效顶点
        4. 计算凸包

        Returns:
            交集区域的凸包顶点列表
        """
        print(f"  [DEBUG] _compute_signal_intersection: 有信号点数量={len(signal_points)}")

        if len(signal_points) < 2:
            print(f"  [DEBUG] 信号点<2，回退到单点估计")
            return self._fallback_intersection_estimate(signal_points)

        try:
            # 步骤1：构造边界射线
            rays = []
            detectors = []
            azimuths_rad = []

            for i, (point, azimuth) in enumerate(signal_points):
                detectors.append(np.array(point))
                azimuths_rad.append(azimuth)

                # 左边界射线
                theta_left = azimuth - self.error_angle
                direction_left = np.array([math.cos(theta_left), math.sin(theta_left)])
                rays.append({
                    'origin': np.array(point),
                    'direction': direction_left,
                    'type': 'left',
                    'detector_id': i
                })

                # 右边界射线
                theta_right = azimuth + self.error_angle
                direction_right = np.array([math.cos(theta_right), math.sin(theta_right)])
                rays.append({
                    'origin': np.array(point),
                    'direction': direction_right,
                    'type': 'right',
                    'detector_id': i
                })

            print(f"  [DEBUG] 构建射线: {len(rays)}条")

            # 步骤2：计算所有射线交点（保留所属检测点信息）
            candidates = []
            for i in range(len(rays)):
                for j in range(i + 1, len(rays)):
                    P, is_valid = ray_intersection(
                        rays[i]['origin'], rays[i]['direction'],
                        rays[j]['origin'], rays[j]['direction']
                    )
                    if is_valid and P is not None:
                        # 记录交点和产生它的两个检测点ID
                        detector_ids = set([rays[i]['detector_id'], rays[j]['detector_id']])
                        candidates.append({
                            'point': tuple(P),
                            'detector_ids': detector_ids
                        })

            print(f"  [DEBUG] 射线交点候选: {len(candidates)}个")

            # 步骤3：筛选在相关扇形内的有效顶点
            # 修正逻辑：交点只需要在产生它的那两个检测点的扇形内
            # 而不是要求在所有检测点的扇形内（那样对定向源来说几乎不可能）
            detectors_arr = np.array(detectors)
            azimuths_deg = np.array([math.degrees(az) for az in azimuths_rad])  # 转换为度数

            valid_vertices = []
            for candidate in candidates:
                point = np.array(candidate['point'])
                detector_ids = candidate['detector_ids']

                # 只检查相关的检测点
                is_valid = True
                for det_id in detector_ids:
                    if not point_in_sector(point, detectors_arr[det_id],
                                          azimuths_deg[det_id], self.error_angle_deg):
                        is_valid = False
                        break

                if is_valid:
                    valid_vertices.append(candidate['point'])

            print(f"  [DEBUG] 有效顶点（在所有扇形内）: {len(valid_vertices)}个")

            if len(valid_vertices) < 3:
                print(f"  [DEBUG] 有效顶点<3，回退到粗略估计")
                return self._fallback_intersection_estimate(signal_points)

            # 步骤4：计算凸包
            # 转换为NumPy数组（问题3的compute_convex_hull期望m×2的NumPy数组）
            valid_vertices_arr = np.array(valid_vertices)
            hull = compute_convex_hull(valid_vertices_arr)
            print(f"  [DEBUG] 凸包顶点: {len(hull)}个")
            if len(hull) > 0:
                print(f"    凸包示例顶点: {hull[:3]}")

            # 返回元组列表（保持内部接口一致）
            return [tuple(v) for v in hull]

        except Exception as e:
            print(f"[ERROR] _compute_signal_intersection failed: {e}")
            import traceback
            traceback.print_exc()
            # 回退：使用粗略估计
            return self._fallback_intersection_estimate(signal_points)

    def _apply_nosignal_constraints(self, signal_region, nosignal_points, emission_direction):
        """
        应用无信号点约束，排除不可能区域

        核心思想：
        - 无信号点说明干扰源不在该点朝向emission_direction的方向
        - 排除这些区域后，得到楔形区域
        """
        if len(nosignal_points) == 0:
            return signal_region

        # 简化实现：过滤掉在无信号点"前方"的区域顶点
        wedge_vertices = []

        for vertex in signal_region:
            # 检查vertex是否在任何无信号点的排除区域内
            in_exclusion = False

            for nosignal_point in nosignal_points:
                # 计算nosignal_point到vertex的方向
                dx = vertex[0] - nosignal_point[0]
                dy = vertex[1] - nosignal_point[1]
                direction_to_vertex = math.atan2(dy, dx)

                # 判断是否在排除方向（emission_direction ± 90°）
                angle_diff = abs(self._angle_difference(direction_to_vertex, emission_direction))
                if angle_diff < math.pi / 2:  # 90度内
                    in_exclusion = True
                    break

            if not in_exclusion:
                wedge_vertices.append(vertex)

        # 如果过滤后为空，返回原区域
        if len(wedge_vertices) == 0:
            return signal_region

        return wedge_vertices

    def _compute_min_enclosing_circle(self, vertices):
        """
        计算最小外接圆（复用问题3算法）

        使用旋转卡壳算法求直径，然后以直径为基础估算外接圆
        容错系数：1.8倍（与问题3一致）
        """
        print(f"  [DEBUG] _compute_min_enclosing_circle: 顶点数={len(vertices)}")
        if len(vertices) == 0:
            print(f"  [DEBUG] 顶点数为0，返回默认值")
            return (0.0, 0.0), 0.0

        try:
            # 转换为NumPy数组（问题3的compute_convex_hull期望m×2的NumPy数组）
            vertices_arr = np.array(vertices) if not isinstance(vertices, np.ndarray) else vertices

            # 计算凸包
            hull_points = compute_convex_hull(vertices_arr)
            print(f"  [DEBUG] 凸包顶点数={len(hull_points)}")

            if len(hull_points) < 2:
                # 只有1个点，直径为0
                center = tuple(hull_points[0]) if len(hull_points) > 0 else (0.0, 0.0)
                return center, 0.0

            # 使用旋转卡壳算法求直径
            # rotating_calipers返回 (D, V_p, V_q) 三个独立值
            diameter_value, V_p, V_q = rotating_calipers(hull_points)
            print(f"  [DEBUG] 旋转卡壳直径: {diameter_value:.1f}m")

            # 计算区域中心（直径端点的中点）
            center = ((V_p[0] + V_q[0]) / 2, (V_p[1] + V_q[1]) / 2)
            print(f"  [DEBUG] 区域中心: ({center[0]:.1f}, {center[1]:.1f})")

            # 容错：1.8倍直径（与问题3一致）
            diameter_with_tolerance = diameter_value * 1.8
            print(f"  [DEBUG] 容错后直径: {diameter_with_tolerance:.1f}m")

            return center, diameter_with_tolerance

        except Exception as e:
            print(f"[ERROR] _compute_min_enclosing_circle failed: {e}")
            import traceback
            traceback.print_exc()
            # 回退：使用质心和最远点
            center = self._compute_centroid(vertices)
            max_dist = max(self._distance(v, center) for v in vertices)
            diameter = 2 * max_dist * 1.8
            print(f"  [DEBUG] 回退方法: center={center}, diameter={diameter:.1f}m")
            return center, diameter

    def _compute_confidence(self, center, diameter, signal_points, nosignal_points) -> float:
        """
        计算置信度

        考虑因素：
        1. 不确定直径（越小越好）
        2. 检测点数量（越多越好）
        3. 有无信号点对比（定向源特征）
        """
        # 因素1：直径因子
        d_ref = 50.0
        f_diameter = math.exp(-diameter / d_ref)

        # 因素2：数据量因子
        n_signal = len(signal_points)
        n_nosignal = len(nosignal_points)
        f_data = min(1.0, (n_signal + 0.5 * n_nosignal) / 5.0)

        # 因素3：定向源特征（有无信号对比）
        if n_nosignal > 0:
            f_directional = min(1.0, n_nosignal / max(n_signal, 1))
        else:
            f_directional = 0.5

        # 综合置信度
        conf = f_diameter * f_data * (0.7 + 0.3 * f_directional)

        return min(1.0, conf)

    def _single_point_estimation(self, signal_data) -> Dict:
        """单点估计（数据不足时的回退策略）"""
        if isinstance(signal_data, tuple) and len(signal_data) == 2:
            point, result = signal_data
        else:
            point = (0.0, 0.0)
            result = {}

        # 粗略估计：在示向度方向1000米处
        azimuth = result.get('azimuth', 0.0)
        distance = 1000.0

        center_x = point[0] + distance * math.cos(azimuth)
        center_y = point[1] + distance * math.sin(azimuth)

        return {
            'center': (center_x, center_y),
            'diameter': 500.0,  # 大不确定度
            'confidence': 0.3,   # 低置信度
            'method': 'single_point'
        }

    def _centroid_estimation(self, signal_points) -> Dict:
        """质心估计（当扇形交集失败时）"""
        coords = [p[0] for p in signal_points]
        center = self._compute_centroid(coords)

        # 计算所有检测点到质心的最大距离
        max_dist = max(self._distance(p[0], center) for p in signal_points)

        return {
            'center': center,
            'diameter': max_dist,  # 保守估计
            'confidence': 0.4,
            'method': 'centroid'
        }

    def _fallback_intersection_estimate(self, signal_points) -> List[Tuple[float, float]]:
        """回退的交集估计（当几何算法失败时）"""
        # 简单策略：返回检测点周围的矩形区域
        coords = [p[0] for p in signal_points]
        x_vals = [p[0] for p in coords]
        y_vals = [p[1] for p in coords]

        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)

        return [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max)
        ]

    @staticmethod
    def _compute_centroid(points: List[Tuple[float, float]]) -> Tuple[float, float]:
        """计算质心"""
        if not points:
            return (0.0, 0.0)
        x_mean = sum(p[0] for p in points) / len(points)
        y_mean = sum(p[1] for p in points) / len(points)
        return (x_mean, y_mean)

    @staticmethod
    def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """计算两点距离"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    @staticmethod
    def _angle_difference(angle1: float, angle2: float) -> float:
        """计算两角度差（考虑周期性）"""
        diff = angle1 - angle2
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        return diff

    @staticmethod
    def _circular_mean(angles: List[float]) -> float:
        """计算角度的循环平均值"""
        if not angles:
            return 0.0

        sin_sum = sum(math.sin(a) for a in angles)
        cos_sum = sum(math.cos(a) for a in angles)

        return math.atan2(sin_sum, cos_sum)
