# -*- coding: utf-8 -*-
"""
阶段2：分类定位（全向/定向判断 + 相应定位算法）
"""
import sys
import os
import numpy as np

# 添加问题3的路径
# 路径结构：problem4/src/phase2_classification_localization.py
# 目标路径：B题/问题3/MCM/problem3/src
current_file = os.path.abspath(__file__)  # .../problem4/src/phase2_classification_localization.py
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

from typing import List, Dict
from classification.source_classifier import SourceClassifier
from classification.wedge_localization import WedgeLocalizer

try:
    # 复用问题3的定位模块（全向源用）
    from phase2_localization import phase2_localization
    from target import Target
except ImportError as e:
    print(f"Warning: Cannot import from problem3: {e}")
    Target = None
    phase2_localization = None


class ClassificationLocalizer:
    """分类定位器（问题4专用）"""

    def __init__(self):
        self.classifier = SourceClassifier(
            nosignal_ratio_threshold=0.15,
            score_threshold=0.6
        )
        self.wedge_localizer = WedgeLocalizer(error_angle_deg=1.0)

    def localize_all(self, scan_result: Dict) -> List[Dict]:
        """
        对所有有源频道进行统一定位（不分类）

        策略：全部使用楔形定位（利用有信号+无信号约束）
              如果楔形失败，回退到两点交会

        Args:
            scan_result: {
                'active_channels': List[int],
                'scan_data': {channel_id: [(point, result), ...]}
            }

        Returns:
            List of Target objects
        """
        print("\n" + "="*60)
        print("阶段2：统一定位开始（不分类，全部楔形定位）")
        print("="*60)

        targets = []

        for channel_id in scan_result['active_channels']:
            print(f"\n--- 频道{channel_id} ---")

            detection_data = scan_result['scan_data'][channel_id]

            # 直接使用楔形定位（适用于全向+定向）
            try:
                target = self.wedge_localizer.localize(detection_data)
                target['method'] = 'wedge'
                print(f"✓ 楔形定位成功")
            except Exception as e:
                print(f"⚠ 楔形定位失败: {e}，尝试两点交会")
                # 回退：两点交会
                target = self._localize_omnidirectional(channel_id, detection_data)

            # 添加频道信息
            target['channel_id'] = channel_id
            target['source_type'] = 'unknown'  # 不再判断
            target['classification_confidence'] = 1.0

            print(f"定位结果：中心{target['center']}, 直径{target['diameter']:.1f}m, "
                  f"置信度{target['confidence']:.2f}, 方法={target['method']}")

            # 转换为Target对象
            if Target is not None:
                try:
                    detection_points_for_target = []
                    for point, result in detection_data:
                        azimuth = result.get('azimuth', 0.0)
                        detection_points_for_target.append((np.array(point), azimuth))

                    target_obj = Target(
                        channel_id=channel_id,
                        detection_points=detection_points_for_target,
                        center=np.array(target['center']),
                        diameter=target['diameter'],
                        confidence=target['confidence'],
                        method=target.get('method', 'wedge')
                    )
                    target_obj.source_type = 'unknown'
                    target_obj.classification_confidence = 1.0
                    targets.append(target_obj)
                except Exception as e:
                    print(f"Warning: Failed to create Target object: {e}")
                    targets.append(target)
            else:
                targets.append(target)

        print("\n" + "="*60)
        print(f"阶段2：统一定位完成，共定位{len(targets)}个干扰源")
        print("="*60)

        return targets

    def _localize_omnidirectional(self, channel_id: int, detection_data: List) -> Dict:
        """全向源定位（使用问题3的两点交会）"""
        if phase2_localization is None:
            # 回退：简单平均
            return self._fallback_localization(detection_data)

        try:
            # 构造问题3的scan_result格式
            scan_result_for_p3 = {
                'active_channels': [channel_id],
                'scan_data': {channel_id: detection_data}
            }

            # 调用问题3的定位函数
            targets = phase2_localization(scan_result_for_p3, verbose=False)

            if targets and len(targets) > 0:
                target = targets[0]
                return {
                    'center': target.center,
                    'diameter': target.diameter,
                    'confidence': target.confidence,
                    'method': 'two_point',
                    'detection_points': detection_data
                }
            else:
                return self._fallback_localization(detection_data)

        except Exception as e:
            print(f"Warning: Two-point localization failed: {e}")
            return self._fallback_localization(detection_data)

    def _localize_directional(self, channel_id: int, detection_data: List) -> Dict:
        """定向源定位（使用楔形交会）"""
        try:
            result = self.wedge_localizer.localize(detection_data)
            return result
        except Exception as e:
            print(f"Warning: Wedge localization failed: {e}")
            return self._fallback_localization(detection_data)

    def _fallback_localization(self, detection_data: List) -> Dict:
        """回退定位（当定位算法失败时）"""
        # 简单策略：使用有信号点的质心
        signal_points = [point for point, result in detection_data
                        if result['type'] in ['direction', 'near']]

        if not signal_points:
            return {
                'center': (0.0, 0.0),
                'diameter': 500.0,
                'confidence': 0.1,
                'method': 'fallback'
            }

        cx = sum(p[0] for p in signal_points) / len(signal_points)
        cy = sum(p[1] for p in signal_points) / len(signal_points)

        return {
            'center': (cx, cy),
            'diameter': 300.0,
            'confidence': 0.3,
            'method': 'fallback'
        }
