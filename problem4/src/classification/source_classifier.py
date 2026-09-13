# -*- coding: utf-8 -*-
"""
全向/定向干扰源分类判断模块
"""
import math
import numpy as np
from typing import List, Tuple, Dict

class SourceClassifier:
    """全向/定向干扰源分类器"""

    def __init__(self, nosignal_ratio_threshold=0.15, score_threshold=0.6):
        """
        Args:
            nosignal_ratio_threshold: 无信号比例阈值（低于此值视为全向源）
            score_threshold: 综合得分阈值（高于此值视为定向源）
        """
        self.nosignal_ratio_threshold = nosignal_ratio_threshold
        self.score_threshold = score_threshold

    def classify(self, detection_data: List[Tuple[Tuple[float, float], Dict]]) -> Tuple[str, float]:
        """
        判断干扰源类型（终极简化版）

        核心判断依据：
        1. 无信号点比例（最重要）
        2. 检测点的空间分布（辅助）

        Args:
            detection_data: 检测数据列表 [(point, result), ...]

        Returns:
            (type, confidence)
        """
        # 数据分类
        signal_points, nosignal_points = self._classify_points(detection_data)

        n_signal = len(signal_points)
        n_nosignal = len(nosignal_points)
        n_total = n_signal + n_nosignal

        # 数据不足判断
        if n_total < 3:
            return 'omnidirectional', 0.5

        if n_signal == 0:
            return 'omnidirectional', 0.3  # 完全检测不到，保守按全向

        # === 核心判断：无信号点比例 ===
        nosignal_ratio = n_nosignal / n_total

        # 严格阈值
        if nosignal_ratio >= 0.35:
            # 超过35%无信号 → 极可能是定向源
            confidence = 0.6 + nosignal_ratio * 0.4  # 0.74-1.0
            return 'directional', confidence

        elif nosignal_ratio <= 0.10:
            # 少于10%无信号 → 极可能是全向源
            confidence = 0.9 - nosignal_ratio * 5  # 0.4-0.9
            return 'omnidirectional', confidence

        else:
            # 10%-35%之间：需要辅助判断
            score_spatial = self._spatial_separation_test(signal_points, nosignal_points)

            # 综合评分
            score_nosignal = (nosignal_ratio - 0.10) / 0.25  # 归一化到[0,1]
            combined_score = 0.7 * score_nosignal + 0.3 * score_spatial

            if combined_score > 0.55:
                return 'directional', 0.6 + combined_score * 0.3
            else:
                return 'omnidirectional', 0.6 + (1 - combined_score) * 0.3

    def _geometric_consistency_test(self, signal_data: List[Tuple[Tuple[float, float], Dict]]) -> float:
        """
        几何一致性检验（新增）

        核心思想：
        - 全向源：从各个检测点的示向度射线应该交于同一点
        - 定向源：射线不一定交于同一点（因为发射方向有限制）

        方法：
        1. 计算任意两条射线的交点
        2. 如果所有交点都集中在一个小区域 → 全向源（一致性高）
        3. 如果交点分散 → 定向源（一致性低）

        Returns:
            score ∈ [0, 1]
            0 = 不一致（定向源特征）
            1 = 高度一致（全向源特征）
        """
        if len(signal_data) < 2:
            return 1.0  # 数据不足，默认一致

        # 计算所有射线对的交点
        intersections = []

        for i in range(len(signal_data)):
            for j in range(i+1, len(signal_data)):
                point_i, result_i = signal_data[i]
                point_j, result_j = signal_data[j]

                azimuth_i = result_i.get('azimuth', 0.0)
                azimuth_j = result_j.get('azimuth', 0.0)

                # 计算射线交点
                intersection = self._ray_intersection(
                    point_i, azimuth_i,
                    point_j, azimuth_j
                )

                if intersection is not None:
                    intersections.append(intersection)

        if len(intersections) < 2:
            return 0.5  # 交点太少，无法判断

        # 计算交点的集中度（标准差）
        x_coords = [p[0] for p in intersections]
        y_coords = [p[1] for p in intersections]

        x_mean = sum(x_coords) / len(x_coords)
        y_mean = sum(y_coords) / len(y_coords)

        # 计算平均距离（作为离散度）
        distances = [
            math.sqrt((x - x_mean)**2 + (y - y_mean)**2)
            for x, y in intersections
        ]
        avg_distance = sum(distances) / len(distances)

        # 评分：交点越集中（avg_distance越小）→ 一致性越高
        if avg_distance < 50:
            return 1.0  # 高度一致（全向源）
        elif avg_distance > 200:
            return 0.0  # 不一致（定向源）
        else:
            return 1.0 - (avg_distance - 50) / 150

    def _ray_intersection(self, point1, azimuth1, point2, azimuth2):
        """
        计算两条射线的交点

        Returns:
            (x, y) 或 None（如果射线平行或不相交）
        """
        # 射线方向向量
        dx1 = math.cos(azimuth1)
        dy1 = math.sin(azimuth1)
        dx2 = math.cos(azimuth2)
        dy2 = math.sin(azimuth2)

        # 行列式
        det = dx1 * dy2 - dy1 * dx2

        if abs(det) < 1e-6:
            return None  # 平行

        # 参数方程求交点
        x1, y1 = point1
        x2, y2 = point2

        t1 = ((x2 - x1) * dy2 - (y2 - y1) * dx2) / det

        # 检查t1是否为正（射线方向）
        if t1 < 0:
            return None

        # 计算交点
        x = x1 + t1 * dx1
        y = y1 + t1 * dy1

        # 检查交点是否在合理范围内（避免极远交点）
        if abs(x) > 5000 or abs(y) > 5000:
            return None

        return (x, y)

    def _classify_points(self, detection_data):
        """
        分类检测点

        Returns:
            signal_points: 有信号点列表 [(x, y), ...]
            nosignal_points: 无信号点列表 [(x, y), ...]
        """
        signal_points = []
        nosignal_points = []

        for point, result in detection_data:
            if result['type'] in ['direction', 'near']:
                signal_points.append(point)
            elif result['type'] == 'no_signal':
                nosignal_points.append(point)

        return signal_points, nosignal_points


    def _spatial_separation_test(self, signal_points: List[Tuple[float, float]],
                                  nosignal_points: List[Tuple[float, float]]) -> float:
        """
        空间分离检验

        核心思想：
        - 定向源：有信号点和无信号点在空间上分离明显
        - 全向源：有信号点和无信号点混杂

        Returns:
            score ∈ [0, 1]
            0 = 全向源特征（混杂）
            1 = 定向源特征（分离明显）
        """
        if len(signal_points) == 0 or len(nosignal_points) == 0:
            return 0.0

        # 计算质心
        c_signal = self._compute_centroid(signal_points)
        c_nosignal = self._compute_centroid(nosignal_points)

        # 质心距离
        centroid_distance = self._distance(c_signal, c_nosignal)

        # 计算每个簇的半径
        r_signal = self._compute_average_distance(signal_points, c_signal)
        r_nosignal = self._compute_average_distance(nosignal_points, c_nosignal)

        if r_signal + r_nosignal == 0:
            return 0.0

        # 分离度
        separation = centroid_distance / (r_signal + r_nosignal)

        # 评分
        if separation > 1.5:
            score = 1.0
        elif separation < 0.5:
            score = 0.0
        else:
            score = (separation - 0.5) / (1.5 - 0.5)

        return score

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

    def _compute_average_distance(self, points: List[Tuple[float, float]],
                                   center: Tuple[float, float]) -> float:
        """计算点集到中心的平均距离"""
        if not points:
            return 0.0
        distances = [self._distance(p, center) for p in points]
        return sum(distances) / len(distances)