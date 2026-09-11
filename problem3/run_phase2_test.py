"""
阶段2测试运行脚本

独立运行脚本，测试阶段2定位功能
"""

import sys
import os
import numpy as np

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from phase2_localization import phase2_localization


def main():
    """主函数"""
    print("\n" + "="*60)
    print("阶段2：逐源交会定位 - 测试运行")
    print("="*60 + "\n")

    # 构造测试数据
    # 假设有3个干扰源
    scan_result = {
        'active_channels': [1, 2, 3],
        'scan_data': {
            # 频道1: 干扰源在(-500, -500)，3个检测点
            '1': [
                [[0.0, 0.0], 225.0],
                [[900.0, 0.0], 199.6],
                [[0.0, 900.0], 303.7]
            ],
            # 频道2: 干扰源在(500, -500)，2个检测点
            '2': [
                [[0.0, 0.0], 315.0],
                [[900.0, 0.0], 231.3]
            ],
            # 频道3: 干扰源位置未知，只有1个检测点
            '3': [
                [[0.0, 0.0], 90.0]
            ]
        }
    }

    print("输入数据:")
    print(f"  活跃频道: {scan_result['active_channels']}")
    for channel_id in scan_result['active_channels']:
        data = scan_result['scan_data'][str(channel_id)]
        print(f"  频道 {channel_id}: {len(data)} 个检测点")
    print()

    # 运行阶段2
    targets = phase2_localization(scan_result, enable_single_point=True, verbose=True)

    # 输出结果
    print("\n" + "="*60)
    print("测试结果统计")
    print("="*60 + "\n")

    if len(targets) == 0:
        print("⚠️  未定位到任何干扰源")
        return

    print(f"✓ 成功定位 {len(targets)} 个干扰源\n")

    # 统计
    two_point_count = sum(1 for t in targets if t.method == 'two_point')
    single_point_count = sum(1 for t in targets if t.method == 'single_point')

    print("定位方法统计:")
    print(f"  两点交会定位: {two_point_count} 个")
    print(f"  单点估计: {single_point_count} 个")
    print()

    # 详细信息
    print("详细结果:")
    print("-" * 60)
    for i, target in enumerate(targets, 1):
        status = "✓" if target.method == 'two_point' else "⚠"
        print(f"\n{i}. {status} 频道 {target.channel_id}")
        print(f"   定位方法: {target.method}")
        print(f"   中心坐标: ({target.center[0]:.2f}, {target.center[1]:.2f})")
        print(f"   区域直径: {target.diameter:.2f} 米")
        print(f"   置信度: {target.confidence:.2f}")
        if target.hull is not None and len(target.hull) > 0:
            print(f"   凸包顶点数: {len(target.hull)}")

    # 质量分析
    print("\n" + "-" * 60)
    print("质量分析:")

    if len(targets) > 0:
        avg_diameter = np.mean([t.diameter for t in targets])
        avg_confidence = np.mean([t.confidence for t in targets])

        print(f"  平均直径: {avg_diameter:.2f} 米")
        print(f"  平均置信度: {avg_confidence:.2f}")

        min_target = min(targets, key=lambda t: t.diameter)
        max_target = max(targets, key=lambda t: t.diameter)

        print(f"\n  最小直径: {min_target.diameter:.2f} 米 (频道 {min_target.channel_id})")
        print(f"  最大直径: {max_target.diameter:.2f} 米 (频道 {max_target.channel_id})")

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ 运行出错: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
