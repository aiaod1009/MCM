"""
Target类 - 干扰源目标

表示一个已定位的干扰源，包含定位信息和置信度
"""

import numpy as np
from typing import List, Tuple, Optional
import sys
import os

# 添加localization模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


class Target:
    """
    干扰源目标

    属性:
        channel_id: 频道ID
        detection_points: 检测点列表 [(S, theta), ...]
        center: 定位中心坐标 [x, y]
        diameter: 定位区域直径（米）
        confidence: 置信度 (0.0-1.0)
        method: 定位方法 ('two_point', 'single_point', 'dynamic')
        hull: 凸包顶点（可选，两点交会定位时有）
        cleared: 是否已清除
    """

    def __init__(
        self,
        channel_id: int,
        detection_points: List[Tuple[np.ndarray, float]],
        region_info: Optional[dict] = None,
        center: Optional[np.ndarray] = None,
        diameter: Optional[float] = None,
        confidence: Optional[float] = None,
        method: str = ''
    ):
        """
        初始化Target对象

        参数:
            channel_id: 频道ID
            detection_points: 检测点列表 [(S, theta), ...]
            region_info: 定位区域信息（两点交会定位）
                {
                    'hull': 凸包顶点,
                    'diameter': 直径,
                    'center': 中心坐标
                }
            center: 定位中心（单点估计）
            diameter: 区域直径（单点估计为不确定度×2）
            confidence: 置信度（手动指定时）
            method: 定位方法
        """
        self.channel_id = channel_id
        self.detection_points = detection_points
        self.method = method
        self.cleared = False

        if region_info is not None:
            # 两点交会定位
            self.hull = region_info['hull']
            self.center = region_info['center']
            self.diameter = region_info['diameter']
            self.confidence = self._compute_confidence_from_region()
        else:
            # 单点估计
            self.hull = None
            self.center = center if center is not None else np.array([0.0, 0.0])
            self.diameter = diameter if diameter is not None else 0.0
            self.confidence = confidence if confidence is not None else 0.5

    def _compute_confidence_from_region(self) -> float:
        """
        基于区域特性计算置信度

        评分因素:
            - 直径评分（权重0.5）：直径越小越好
            - 交会角评分（权重0.3）：越接近90°越好
            - 基线评分（权重0.2）：800-1000米最佳

        返回:
            confidence: 置信度 (0.0-1.0)
        """
        if len(self.detection_points) != 2:
            return 0.3

        S1, theta1 = self.detection_points[0]
        S2, theta2 = self.detection_points[1]

        # 1. 直径评分（权重0.5）
        # 直径<20米: 1.0
        # 直径20-120米: 线性衰减
        # 直径>120米: 0.2
        if self.diameter <= 20:
            diameter_score = 1.0
        elif self.diameter <= 120:
            diameter_score = 1.0 - (self.diameter - 20) / 100
        else:
            diameter_score = 0.2

        # 2. 交会角评分（权重0.3）
        from localization.point_selector import compute_intersection_angle
        alpha = compute_intersection_angle(S1, theta1, S2, theta2)
        angle_score = 1.0 - abs(alpha - 90) / 90

        # 3. 基线评分（权重0.2）
        baseline = np.linalg.norm(S2 - S1)
        if 800 <= baseline <= 1000:
            baseline_score = 1.0
        elif baseline < 800:
            baseline_score = baseline / 800
        else:
            baseline_score = min(1000 / baseline, 1.0)

        confidence = (0.5 * diameter_score +
                     0.3 * angle_score +
                     0.2 * baseline_score)

        return confidence

    def __repr__(self) -> str:
        """字符串表示"""
        return (f"Target(CH{self.channel_id}, "
                f"center=({self.center[0]:.1f}, {self.center[1]:.1f}), "
                f"diameter={self.diameter:.1f}m, "
                f"conf={self.confidence:.2f}, "
                f"method={self.method})")

    def __str__(self) -> str:
        """更详细的字符串表示"""
        lines = [
            f"Target - 频道 {self.channel_id}",
            f"  定位方法: {self.method}",
            f"  中心坐标: ({self.center[0]:.2f}, {self.center[1]:.2f})",
            f"  区域直径: {self.diameter:.2f} 米",
            f"  置信度: {self.confidence:.2f}",
            f"  检测点数: {len(self.detection_points)}",
        ]

        if self.hull is not None and len(self.hull) > 0:
            lines.append(f"  凸包顶点数: {len(self.hull)}")

        if self.cleared:
            lines.append(f"  状态: ✓ 已清除")
        else:
            lines.append(f"  状态: ⏳ 待清除")

        return "\n".join(lines)

    def distance_to(self, position: np.ndarray) -> float:
        """
        计算到指定位置的距离

        参数:
            position: 位置坐标 [x, y]

        返回:
            distance: 欧氏距离（米）
        """
        return np.linalg.norm(self.center - position)

    def to_dict(self) -> dict:
        """
        转换为字典（用于JSON序列化）

        返回:
            data: 字典表示
        """
        return {
            'channel_id': int(self.channel_id),
            'center': self.center.tolist(),
            'diameter': float(self.diameter),
            'confidence': float(self.confidence),
            'method': self.method,
            'cleared': self.cleared,
            'detection_points': [
                {
                    'position': S.tolist(),
                    'azimuth': float(theta)
                }
                for S, theta in self.detection_points
            ],
            'hull': self.hull.tolist() if self.hull is not None else None
        }


# 测试代码
if __name__ == '__main__':
    print("测试 target.py")
    print("=" * 60)

    # 测试1：两点交会定位的Target
    print("测试1 - 两点交会定位的Target:")

    from localization.region_calculator import compute_localization_region

    S1 = np.array([0.0, 0.0])
    theta1 = 197.56
    S2 = np.array([900.0, 0.0])
    theta2 = 229.45

    region_info = compute_localization_region(S1, theta1, S2, theta2, error=1.0)

    target = Target(
        channel_id=1,
        detection_points=[(S1, theta1), (S2, theta2)],
        region_info=region_info,
        method='two_point'
    )

    print(target)
    print()

    # 测试2：单点估计的Target
    print("测试2 - 单点估计的Target:")

    from localization.single_point_estimator import single_point_estimation

    S = np.array([900.0, 0.0])
    theta = 304.24

    position, uncertainty = single_point_estimation(S, theta)

    target = Target(
        channel_id=10,
        detection_points=[(S, theta)],
        center=position,
        diameter=uncertainty * 2,
        confidence=0.3,
        method='single_point'
    )

    print(target)
    print()

    # 测试3：Target列表排序
    print("测试3 - Target列表排序（按直径）:")

    targets = []

    # 创建3个Target
    for i, (d, c) in enumerate([(10.5, 0.85), (45.2, 0.62), (8.3, 0.91)], 1):
        t = Target(
            channel_id=i,
            detection_points=[(np.array([0.0, 0.0]), 0.0)],
            center=np.array([100.0, 100.0]),
            diameter=d,
            confidence=c,
            method='test'
        )
        targets.append(t)

    print("  排序前:")
    for t in targets:
        print(f"    {t}")

    # 按直径排序
    targets.sort(key=lambda t: t.diameter)

    print("\n  排序后（直径从小到大）:")
    for t in targets:
        print(f"    {t}")

    print()

    # 测试4：距离计算
    print("测试4 - 距离计算:")

    target = Target(
        channel_id=1,
        detection_points=[(np.array([0.0, 0.0]), 0.0)],
        center=np.array([300.0, 400.0]),
        diameter=10.0,
        confidence=0.8,
        method='test'
    )

    test_positions = [
        np.array([0.0, 0.0]),
        np.array([300.0, 400.0]),
        np.array([600.0, 800.0]),
    ]

    print(f"  Target中心: {target.center}")
    for pos in test_positions:
        dist = target.distance_to(pos)
        print(f"  距离到 {pos}: {dist:.2f} 米")

    print()

    # 测试5：JSON序列化
    print("测试5 - JSON序列化:")

    target = Target(
        channel_id=1,
        detection_points=[(S1, theta1), (S2, theta2)],
        region_info=region_info,
        method='two_point'
    )

    data = target.to_dict()

    import json
    json_str = json.dumps(data, indent=2)
    print("  JSON表示:")
    print(json_str)

    print()
    print("=" * 60)
    print("测试完成！")
