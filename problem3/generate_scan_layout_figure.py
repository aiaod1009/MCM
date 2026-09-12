import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 创建图形
fig, ax = plt.subplots(figsize=(10, 10))

# 1. 绘制目标区域（正方形）
square = plt.Rectangle((-900, -900), 1800, 1800,
                       fill=False, edgecolor='black', linewidth=2)
ax.add_patch(square)

# 2. 绘制扫描圆（虚线）
circle = plt.Circle((0, 0), 900, fill=False,
                    edgecolor='gray', linestyle='--', linewidth=1.5)
ax.add_patch(circle)

# 3. 中心扫描点
ax.plot(0, 0, 'ro', markersize=12, label='中心扫描点', zorder=5)
ax.text(0, -80, 'O(0,0)', ha='center', va='top', fontsize=11, fontweight='bold')

# 4. 8个外围扫描点
r = 900
angles = np.array([0, 45, 90, 135, 180, 225, 270, 315])
labels = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8']

for i, (angle, label) in enumerate(zip(angles, labels)):
    theta = np.radians(angle)
    x = r * np.cos(theta)
    y = r * np.sin(theta)

    # 绘制扫描点
    ax.plot(x, y, 'bs', markersize=10, zorder=5)

    # 标注点名
    offset = 100
    text_x = x + offset * np.cos(theta)
    text_y = y + offset * np.sin(theta)
    ax.text(text_x, text_y, label, ha='center', va='center',
            fontsize=10, fontweight='bold')

# 5. 绘制半径标注线（从O到E1）
ax.plot([0, 900], [0, 0], 'k-', linewidth=1, alpha=0.5)
ax.text(450, 50, r'$r_s=900\,\mathrm{m}$', ha='center',
        fontsize=10, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# 6. 添加区域标注
ax.text(0, 950, '目标区域 (1800m×1800m)', ha='center',
        fontsize=12, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))

# 7. 设置坐标轴
ax.set_xlim(-1100, 1100)
ax.set_ylim(-1100, 1100)
ax.set_xlabel('x (m)', fontsize=12)
ax.set_ylabel('y (m)', fontsize=12)
ax.set_aspect('equal')
ax.grid(True, alpha=0.3, linestyle=':')
ax.axhline(0, color='k', linewidth=0.5)
ax.axvline(0, color='k', linewidth=0.5)

# 8. 设置刻度
ticks = [-900, -450, 0, 450, 900]
ax.set_xticks(ticks)
ax.set_yticks(ticks)

# 9. 添加图例
ax.legend(loc='upper right', fontsize=10)

# 10. 添加标题
plt.title('九点扫描布局与区域覆盖示意图', fontsize=14, fontweight='bold', pad=20)

# 保存图形
plt.tight_layout()
plt.savefig('E:/problem/problem3/problem3_scan_layout.png', dpi=300, bbox_inches='tight')
print("图形已保存至: E:/problem/problem3/problem3_scan_layout.png")

plt.show()
