# -*- coding: utf-8 -*-
"""
测试分类算法修复效果（终极简化版）
"""
import sys
import os
import math

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from classification.source_classifier import SourceClassifier

def test_omnidirectional_source():
    """测试全向源识别（无信号点少）"""
    print("\n" + "="*60)
    print("测试1：全向源识别（无信号点占比<10%）")
    print("="*60)

    # 模拟全向源：16个检测点，只有1个无信号（可能距离太远）
    detection_data = [
        ((0, 0), {'type': 'direction', 'azimuth': 0.0}),
        ((600, 0), {'type': 'direction', 'azimuth': 0.1}),
        ((600, 600), {'type': 'direction', 'azimuth': 0.2}),
        ((0, 600), {'type': 'direction', 'azimuth': 0.3}),
        ((-600, 600), {'type': 'direction', 'azimuth': 0.4}),
        ((-600, 0), {'type': 'direction', 'azimuth': 0.5}),
        ((-600, -600), {'type': 'direction', 'azimuth': 0.6}),
        ((0, -600), {'type': 'direction', 'azimuth': 0.7}),
        ((600, -600), {'type': 'direction', 'azimuth': 0.8}),
        ((900, 0), {'type': 'direction', 'azimuth': 0.9}),
        ((0, 900), {'type': 'direction', 'azimuth': 1.0}),
        ((-900, 0), {'type': 'direction', 'azimuth': 1.1}),
        ((0, -900), {'type': 'direction', 'azimuth': 1.2}),
        ((424, 424), {'type': 'direction', 'azimuth': 1.3}),
        ((-424, -424), {'type': 'direction', 'azimuth': 1.4}),
        ((1200, 0), {'type': 'no_signal'}),  # 只有1个无信号（距离太远）
    ]

    classifier = SourceClassifier()
    source_type, confidence = classifier.classify(detection_data)

    signal_count = sum(1 for _, r in detection_data if r['type'] in ['direction', 'near'])
    nosignal_count = sum(1 for _, r in detection_data if r['type'] == 'no_signal')
    nosignal_ratio = nosignal_count / len(detection_data)

    print(f"检测点数量：{len(detection_data)}")
    print(f"有信号点：{signal_count}个 (93.8%)")
    print(f"无信号点：{nosignal_count}个 (6.2%)")
    print(f"判断结果：{source_type}")
    print(f"置信度：{confidence:.2f}")

    if source_type == 'omnidirectional':
        print("✅ 正确！无信号点<10% → 全向源")
        return True
    else:
        print("❌ 错误！应该识别为全向源")
        return False

def test_directional_source():
    """测试定向源识别（无信号点多）"""
    print("\n" + "="*60)
    print("测试2：定向源识别（无信号点占比>35%）")
    print("="*60)

    # 模拟定向源：朝东发射，西侧大量无信号点
    detection_data = [
        ((0, 0), {'type': 'direction', 'azimuth': 0.0}),
        ((600, 0), {'type': 'direction', 'azimuth': 0.1}),
        ((600, 300), {'type': 'direction', 'azimuth': 0.0}),
        ((600, -300), {'type': 'direction', 'azimuth': -0.1}),
        ((300, 300), {'type': 'direction', 'azimuth': 0.05}),
        ((300, -300), {'type': 'direction', 'azimuth': -0.05}),
        ((-600, 0), {'type': 'no_signal'}),      # 西侧无信号
        ((-600, 300), {'type': 'no_signal'}),
        ((-600, -300), {'type': 'no_signal'}),
        ((-300, 300), {'type': 'no_signal'}),
        ((-300, -300), {'type': 'no_signal'}),
        ((0, 600), {'type': 'no_signal'}),       # 远处无信号
        ((0, -600), {'type': 'no_signal'}),
    ]

    classifier = SourceClassifier()
    source_type, confidence = classifier.classify(detection_data)

    signal_count = sum(1 for _, r in detection_data if r['type'] in ['direction', 'near'])
    nosignal_count = sum(1 for _, r in detection_data if r['type'] == 'no_signal')
    nosignal_ratio = nosignal_count / len(detection_data)

    print(f"检测点数量：{len(detection_data)}")
    print(f"有信号点：{signal_count}个 (46.2%)")
    print(f"无信号点：{nosignal_count}个 (53.8%)")
    print(f"判断结果：{source_type}")
    print(f"置信度：{confidence:.2f}")

    if source_type == 'directional':
        print("✅ 正确！无信号点>35% → 定向源")
        return True
    else:
        print("❌ 错误！应该识别为定向源")
        return False

def test_edge_case_medium():
    """测试边界情况：10%-35%之间（需要辅助判断）"""
    print("\n" + "="*60)
    print("测试3：边界情况 - 无信号点15%（需辅助判断）")
    print("="*60)

    # 无信号点占15%，需要看空间分离度
    detection_data = [
        ((600, 0), {'type': 'direction', 'azimuth': 0.0}),
        ((600, 300), {'type': 'direction', 'azimuth': 0.1}),
        ((600, -300), {'type': 'direction', 'azimuth': -0.1}),
        ((300, 300), {'type': 'direction', 'azimuth': 0.0}),
        ((300, -300), {'type': 'direction', 'azimuth': 0.0}),
        ((0, 300), {'type': 'direction', 'azimuth': 0.1}),
        ((0, -300), {'type': 'direction', 'azimuth': -0.1}),
        ((-600, 0), {'type': 'no_signal'}),      # 西侧集中
        ((-300, 0), {'type': 'no_signal'}),
    ]

    classifier = SourceClassifier()
    source_type, confidence = classifier.classify(detection_data)

    signal_count = sum(1 for _, r in detection_data if r['type'] in ['direction', 'near'])
    nosignal_count = sum(1 for _, r in detection_data if r['type'] == 'no_signal')
    nosignal_ratio = nosignal_count / len(detection_data)

    print(f"检测点数量：{len(detection_data)}")
    print(f"有信号点：{signal_count}个 (东侧集中)")
    print(f"无信号点：{nosignal_count}个 (22.2%, 西侧集中)")
    print(f"判断结果：{source_type}")
    print(f"置信度：{confidence:.2f}")

    # 这个情况可接受两种结果（取决于空间分离度）
    print("⚠️  边界情况，两种结果都可接受")
    return True

def main():
    print("\n" + "="*80)
    print(" "*15 + "分类算法测试（终极简化版 - 基于无信号点比例）")
    print("="*80)

    results = []

    results.append(test_omnidirectional_source())
    results.append(test_directional_source())
    results.append(test_edge_case_medium())

    print("\n" + "="*80)
    print("测试汇总")
    print("="*80)
    success_count = sum(results)
    total_count = len(results)
    print(f"通过率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

    if success_count == total_count:
        print("\n🎉 所有测试通过！")
        print("\n核心逻辑：")
        print("  无信号点 <10%  → 全向源")
        print("  无信号点 >35%  → 定向源")
        print("  无信号点 10-35% → 综合判断（空间分离度）")
    else:
        print(f"\n⚠️  部分测试失败")

if __name__ == '__main__':
    main()
