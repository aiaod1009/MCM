"""
生成8.4节固定搜索圆示意图 (Python版本)
对应论文8.4节的算法描述
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_fixed_search_circle(S1, theta1, d0, output_file=None):
    """
    绘制8.4节固定搜索圆示意图

    参数：
        S1: 第一检测点坐标 [x, y]
        theta1: 第一示向度（度）
        d0: 估计干扰源距离（米）
        output_file: 输出文件路径
    """
    # 固定参数
    r_fixed = 600  # 固定搜索半径（米）
    delta_phi = 1  # 角度采样间隔（度）

    # 计算估计干扰源位置
    theta1_rad = np.deg2rad(theta1)
    G_est = S1 + d0 * np.array([np.cos(theta1_rad), np.sin(theta1_rad)])

    # 生成搜索圆上的360个采样点
    angles = np.arange(0, 360, delta_phi)
    n_samples = len(angles)
    angles_rad = np.deg2rad(angles)
    sample_points = S1 + r_fixed * np.column_stack([np.cos(angles_rad), np.sin(angles_rad)])

    # 计算最优推荐点（垂直于第一示向线，逆时针90°）
    phi_optimal = theta1 + 90
    phi_optimal_rad = np.deg2rad(phi_optimal)
    S2_optimal = S1 + r_fixed * np.array([np.cos(phi_optimal_rad), np.sin(phi_optimal_rad)])

    # 计算交会角
    vec1 = G_est - S1
    vec2 = G_est - S2_optimal
    cos_alpha = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    alpha_optimal = np.rad2deg(np.arccos(np.clip(cos_alpha, -1, 1)))

    # 创建图形
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    # 1. 绘制搜索圆
    circle = Circle(S1, r_fixed, fill=False, edgecolor='black', linewidth=2, label='搜索圆 (r=600m)')
    ax.add_patch(circle)

    # 2. 绘制圆周上的360个采样点
    ax.plot(sample_points[:, 0], sample_points[:, 1], 'b.', markersize=2,
            label=f'采样点 (N={n_samples}, Δφ={delta_phi}°)')

    # 3. 绘制第一检测点
    ax.plot(S1[0], S1[1], 'ro', markersize=12, markerfacecolor='r',
            markeredgewidth=2, label='第一检测点 $S_1$')

    # 4. 绘制第一示向线
    line_length = d0 * 1.2
    x_line = [S1[0], S1[0] + line_length * np.cos(theta1_rad)]
    y_line = [S1[1], S1[1] + line_length * np.sin(theta1_rad)]
    ax.plot(x_line, y_line, 'k--', linewidth=1.5, label='第一示向线')

    # 5. 绘制估计干扰源位置
    ax.plot(G_est[0], G_est[1], 'bx', markersize=15, markeredgewidth=3,
            label='$G_{est}$ (估计干扰源)')

    # 6. 绘制最终推荐点
    ax.plot(S2_optimal[0], S2_optimal[1], 'mp', markersize=18,
            markerfacecolor='m', markeredgewidth=2, label='推荐点 $S_2^*$')

    # 7. 绘制从S2到G_est的连线（第二示向线）
    ax.plot([S2_optimal[0], G_est[0]], [S2_optimal[1], G_est[1]],
            'm--', linewidth=1.5, label='第二示向线')

    # 8. 标注交会角
    ax.text(G_est[0] + 50, G_est[1] + 50,
            f'α ≈ {alpha_optimal:.1f}°',
            fontsize=14, fontweight='bold', color='red',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='red'))

    # 9. 添加距离标注
    mid_point = (S1 + S2_optimal) / 2
    ax.text(mid_point[0], mid_point[1] - 50,
            f'||$S_2$-$S_1$|| = {r_fixed} m',
            fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # 10. 添加点标签
    ax.text(S1[0] - 80, S1[1] - 80, '$S_1$', fontsize=14, fontweight='bold')
    ax.text(S2_optimal[0] - 80, S2_optimal[1] + 80, '$S_2^*$', fontsize=14, fontweight='bold')
    ax.text(G_est[0] + 80, G_est[1], '$G_{est}$', fontsize=14, fontweight='bold')

    # 设置坐标轴
    ax.set_xlabel('东向距离 (米)', fontsize=12)
    ax.set_ylabel('北向距离 (米)', fontsize=12)
    ax.set_title(f'8.4节 固定搜索圆策略 (r={r_fixed}m, Δφ={delta_phi}°, N={n_samples})',
                fontsize=14, fontweight='bold')

    # 图例
    ax.legend(loc='best', fontsize=10)

    # 保存图片
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f'固定搜索圆示意图已保存：{output_file}')

    plt.tight_layout()
    return fig, ax


def main():
    """主函数"""
    print('=== 生成8.4节固定搜索圆示意图 ===')

    # 参数设置
    S1 = np.array([0.0, 0.0])  # 第一检测点
    theta1 = 45.0  # 第一示向度（度）
    d0 = 600.0  # 估计干扰源距离（米）

    print('参数设置：')
    print(f'  第一检测点 S1: ({S1[0]:.1f}, {S1[1]:.1f})')
    print(f'  第一示向度 θ1: {theta1:.1f}°')
    print(f'  估计干扰源距离 d0: {d0:.0f} m')
    print(f'  固定搜索半径: 600 m')
    print(f'  角度采样间隔: 1°')
    print(f'  采样点数量: 360')

    # 确保results目录存在
    if not os.path.exists('results'):
        os.makedirs('results')

    # 生成图形
    output_file = 'results/figure_8_4_fixed_search_circle_python.png'
    plot_fixed_search_circle(S1, theta1, d0, output_file)

    print(f'\n图片已保存至: {output_file}')
    print('=== 完成 ===')

    # 显示图形（可选）
    # plt.show()


if __name__ == '__main__':
    main()
