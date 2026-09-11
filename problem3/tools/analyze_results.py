"""
结果分析工具

分析阶段1、阶段2、阶段3的结果，生成可视化报告
"""

import json
import os
import sys
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def analyze_phase1_result(result_file='../results/phase1_scan_result.json'):
    """分析阶段1结果"""
    print("\n" + "="*60)
    print("阶段1结果分析")
    print("="*60)

    if not os.path.exists(result_file):
        print(f"⚠️  结果文件不存在: {result_file}")
        return None

    with open(result_file, 'r') as f:
        result = json.load(f)

    active_channels = result['active_channels']
    scan_data = result['scan_data']

    print(f"\n发现频道数: {len(active_channels)}")
    print(f"频道列表: {active_channels}")

    print(f"\n各频道数据点数量:")
    for ch in active_channels:
        data_count = len(scan_data[str(ch)])
        print(f"  频道 {ch:2d}: {data_count} 个检测点")

    # 统计
    total_measurements = sum(len(scan_data[str(ch)]) for ch in active_channels)
    avg_measurements = total_measurements / len(active_channels) if active_channels else 0

    print(f"\n统计:")
    print(f"  总测量次数: {total_measurements}")
    print(f"  平均每频道: {avg_measurements:.1f} 个检测点")

    return result


def analyze_phase2_result(result_file='../results/phase2_targets.json'):
    """分析阶段2结果"""
    print("\n" + "="*60)
    print("阶段2结果分析")
    print("="*60)

    if not os.path.exists(result_file):
        print(f"⚠️  结果文件不存在: {result_file}")
        return None

    with open(result_file, 'r') as f:
        targets = json.load(f)

    print(f"\n定位目标数: {len(targets)}")

    print(f"\n目标详情:")
    two_point_count = 0
    single_point_count = 0

    for i, target in enumerate(targets, 1):
        method = target['method']
        if method == 'two_point':
            two_point_count += 1
            marker = "✓"
        else:
            single_point_count += 1
            marker = "⚠"

        print(f"  {i:2d}. {marker} 频道{target['channel_id']:2d}: "
              f"中心({target['center'][0]:7.1f}, {target['center'][1]:7.1f}), "
              f"D={target['diameter']:6.1f}m, conf={target['confidence']:.2f}, "
              f"{method}")

    # 统计
    diameters = [t['diameter'] for t in targets]
    confidences = [t['confidence'] for t in targets]

    print(f"\n统计:")
    print(f"  两点交会定位: {two_point_count}")
    print(f"  单点估计: {single_point_count}")
    print(f"  平均直径: {sum(diameters)/len(diameters):.1f}m")
    print(f"  平均置信度: {sum(confidences)/len(confidences):.2f}")
    print(f"  最小直径: {min(diameters):.1f}m")
    print(f"  最大直径: {max(diameters):.1f}m")

    return targets


def analyze_final_result(result_file='../results/final_results.json'):
    """分析最终结果"""
    print("\n" + "="*60)
    print("最终结果分析")
    print("="*60)

    if not os.path.exists(result_file):
        print(f"⚠️  结果文件不存在: {result_file}")
        return None

    with open(result_file, 'r') as f:
        result = json.load(f)

    print(f"\nrobot_id: {result['robot_id']}")
    print(f"时间戳: {result['timestamp']}")

    # 阶段1
    print(f"\n阶段1:")
    print(f"  发现频道数: {result['phase1']['total_channels']}")
    print(f"  频道列表: {result['phase1']['active_channels']}")

    # 阶段2
    print(f"\n阶段2:")
    print(f"  定位目标数: {result['phase2']['targets_count']}")

    # 阶段3
    phase3 = result['phase3']
    print(f"\n阶段3:")
    print(f"  成功清除: {phase3['cleared_count']}/{phase3['cleared_count'] + phase3['failed_count']}")
    print(f"  清除比例: {phase3['clearing_ratio']*100:.1f}%")
    print(f"  平均清除时间: {phase3['average_clear_time']:.1f}秒")
    print(f"  阶段3总时间: {phase3['total_time']:.1f}秒 ({phase3['total_time']/60:.1f}分钟)")

    # 总体
    summary = result['summary']
    print(f"\n总体:")
    print(f"  总虚拟时间: {summary['total_virtual_time']:.1f}秒 ({summary['total_virtual_time']/60:.1f}分钟)")
    print(f"  清除比例: {summary['clearing_ratio']*100:.1f}%")
    print(f"  任务状态: {'✓ 成功' if summary['success'] else '✗ 失败'}")

    # 评分估算
    print(f"\n性能评估:")
    clearing_ratio = summary['clearing_ratio']
    total_time_minutes = summary['total_virtual_time'] / 60

    # 时间评分（假设1小时为优秀，2小时为良好）
    if total_time_minutes <= 60:
        time_score = "⭐⭐⭐⭐⭐ (优秀)"
    elif total_time_minutes <= 90:
        time_score = "⭐⭐⭐⭐ (良好)"
    elif total_time_minutes <= 120:
        time_score = "⭐⭐⭐ (中等)"
    else:
        time_score = "⭐⭐ (需优化)"

    # 清除比例评分
    if clearing_ratio >= 1.0:
        clear_score = "⭐⭐⭐⭐⭐ (完美)"
    elif clearing_ratio >= 0.9:
        clear_score = "⭐⭐⭐⭐ (优秀)"
    elif clearing_ratio >= 0.8:
        clear_score = "⭐⭐⭐ (良好)"
    else:
        clear_score = "⭐⭐ (需改进)"

    print(f"  时间评分: {time_score}")
    print(f"  清除评分: {clear_score}")

    return result


def generate_report(output_file='../results/analysis_report.txt'):
    """生成完整分析报告"""
    print("\n" + "="*60)
    print("生成分析报告")
    print("="*60)

    import io
    import sys

    # 重定向输出到字符串
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    try:
        print("="*60)
        print("问题3 - 结果分析报告")
        print("="*60)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        analyze_phase1_result()
        analyze_phase2_result()
        analyze_final_result()

        print("\n" + "="*60)
        print("报告生成完成")
        print("="*60)

        # 获取输出内容
        output = buffer.getvalue()

    finally:
        # 恢复stdout
        sys.stdout = old_stdout

    # 打印到控制台
    print(output)

    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"\n报告已保存到: {output_file}")


def main():
    """主函数"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*20 + "结果分析工具" + " "*20 + "║")
    print("╚" + "="*58 + "╝")

    # 切换到脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 检查结果目录
    if not os.path.exists('../results'):
        print("\n⚠️  结果目录不存在，创建目录...")
        os.makedirs('../results')

    # 分析各阶段结果
    analyze_phase1_result()
    analyze_phase2_result()
    analyze_final_result()

    # 生成报告
    print("\n是否生成完整报告？(y/n): ", end='')
    choice = input().strip().lower()

    if choice == 'y':
        generate_report()

    print("\n" + "="*60)
    print("分析完成")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
