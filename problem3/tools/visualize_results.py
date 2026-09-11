"""
结果可视化工具

读取阶段1和阶段2的结果，生成ASCII可视化图
"""

import json
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def load_results():
    """加载结果文件"""
    results = {}

    # 阶段1结果
    phase1_file = '../results/phase1_scan_result.json'
    if os.path.exists(phase1_file):
        with open(phase1_file, 'r') as f:
            results['phase1'] = json.load(f)

    # 阶段2结果
    phase2_file = '../results/phase2_targets.json'
    if os.path.exists(phase2_file):
        with open(phase2_file, 'r') as f:
            results['phase2'] = json.load(f)

    return results


def create_ascii_map(scan_points, targets, width=80, height=40):
    """
    创建ASCII地图

    参数:
        scan_points: 扫描点列表
        targets: 目标列表
        width: 地图宽度（字符）
        height: 地图高度（字符）

    返回:
        ascii_map: ASCII字符串
    """
    # 创建空白地图
    map_grid = [[' ' for _ in range(width)] for _ in range(height)]

    # 确定坐标范围
    all_x = [p[0] for p in scan_points]
    all_y = [p[1] for p in scan_points]

    if targets:
        all_x.extend([t['center'][0] for t in targets])
        all_y.extend([t['center'][1] for t in targets])

    min_x, max_x = min(all_x) - 200, max(all_x) + 200
    min_y, max_y = min(all_y) - 200, max(all_y) + 200

    # 坐标转换函数
    def to_map_coords(x, y):
        map_x = int((x - min_x) / (max_x - min_x) * (width - 1))
        map_y = int((max_y - y) / (max_y - min_y) * (height - 1))  # Y轴翻转
        map_x = max(0, min(width - 1, map_x))
        map_y = max(0, min(height - 1, map_y))
        return map_x, map_y

    # 绘制扫描点（圆心和环点）
    for point in scan_points:
        mx, my = to_map_coords(point[0], point[1])
        if 0 <= mx < width and 0 <= my < height:
            if point[0] == 0 and point[1] == 0:
                map_grid[my][mx] = 'C'  # 圆心
            else:
                map_grid[my][mx] = 'E'  # 环点

    # 绘制目标
    if targets:
        for i, target in enumerate(targets):
            cx, cy = target['center']
            mx, my = to_map_coords(cx, cy)
            if 0 <= mx < width and 0 <= my < height:
                # 使用频道号标记（如果<10）或'*'
                if target['channel_id'] < 10:
                    map_grid[my][mx] = str(target['channel_id'])
                else:
                    map_grid[my][mx] = '*'

    # 绘制坐标轴
    # X轴
    y_axis = int((max_y) / (max_y - min_y) * (height - 1))
    if 0 <= y_axis < height:
        for x in range(width):
            if map_grid[y_axis][x] == ' ':
                map_grid[y_axis][x] = '-'

    # Y轴
    x_axis = int((0 - min_x) / (max_x - min_x) * (width - 1))
    if 0 <= x_axis < width:
        for y in range(height):
            if map_grid[y][x_axis] == ' ':
                map_grid[y][x_axis] = '|'

    # 原点
    ox, oy = to_map_coords(0, 0)
    if 0 <= ox < width and 0 <= oy < height:
        map_grid[oy][ox] = '+'

    # 转换为字符串
    ascii_map = '\n'.join([''.join(row) for row in map_grid])

    return ascii_map, (min_x, max_x, min_y, max_y)


def visualize_results():
    """可视化结果"""
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*30 + "结果可视化" + " "*30 + "║")
    print("╚" + "="*78 + "╝\n")

    # 切换到脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 加载结果
    results = load_results()

    if 'phase1' not in results:
        print("⚠️  未找到阶段1结果文件")
        return

    phase1 = results['phase1']
    phase2 = results.get('phase2', [])

    # 提取扫描点
    scan_points = []
    scan_points.append([0, 0])  # 圆心

    # 从扫描数据中提取环点
    for ch_data in phase1['scan_data'].values():
        for point, _ in ch_data:
            if point not in scan_points:
                scan_points.append(point)

    print(f"扫描点数量: {len(scan_points)}")
    print(f"发现频道: {len(phase1['active_channels'])}")
    if phase2:
        print(f"定位目标: {len(phase2)}")

    # 创建ASCII地图
    print("\n" + "="*80)
    print("目标区域地图")
    print("="*80)
    print("\n图例:")
    print("  C = 圆心 (0, 0)")
    print("  E = 环点 (扫描位置)")
    print("  1-9 = 干扰源 (频道号)")
    print("  * = 干扰源 (频道号≥10)")
    print("  + = 原点")
    print("  | = Y轴")
    print("  - = X轴")
    print()

    ascii_map, bounds = create_ascii_map(scan_points, phase2)
    print(ascii_map)

    print(f"\n坐标范围:")
    print(f"  X: [{bounds[0]:.0f}, {bounds[1]:.0f}]")
    print(f"  Y: [{bounds[2]:.0f}, {bounds[3]:.0f}]")

    # 显示目标详情
    if phase2:
        print("\n" + "="*80)
        print("目标详情")
        print("="*80)
        print(f"\n{'频道':<6} {'中心坐标':<20} {'直径(m)':<10} {'置信度':<8} {'方法':<12}")
        print("-" * 80)

        for target in phase2:
            ch = target['channel_id']
            cx, cy = target['center']
            d = target['diameter']
            conf = target['confidence']
            method = target['method']

            print(f"{ch:<6} ({cx:7.1f}, {cy:7.1f})    {d:7.1f}     {conf:.2f}      {method:<12}")

    print("\n" + "="*80)


def save_visualization(output_file='../results/visualization.txt'):
    """保存可视化到文件"""
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    try:
        visualize_results()
        output = buffer.getvalue()
    finally:
        sys.stdout = old_stdout

    # 打印到控制台
    print(output)

    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"\n可视化已保存到: {output_file}")


if __name__ == '__main__':
    visualize_results()

    print("\n是否保存可视化到文件？(y/n): ", end='')
    choice = input().strip().lower()

    if choice == 'y':
        save_visualization()
