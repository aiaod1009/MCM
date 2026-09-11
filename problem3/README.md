# 问题3：自动搜索定位并清除全向干扰源

## 🎯 项目概述

本项目实现了机器狗自动搜索、定位并清除干扰源的完整算法，分为三个阶段：

1. **阶段1：枚举频道扫描** ✅ - 发现有源频道
2. **阶段2：逐源交会定位** ✅ - 计算干扰源位置
3. **阶段3：巡游清除** ⏳ - 移动清除干扰源

## 📁 项目结构

```
problem3/
├── src/                               # 源代码
│   ├── geometry/                      # 几何算法（从问题1移植）✅
│   │   ├── ray_intersection.py        # 射线交点计算
│   │   ├── point_in_sector.py         # 扇形判断
│   │   ├── convex_hull.py             # 凸包计算
│   │   ├── rotating_calipers.py       # 旋转卡壳算法
│   │   └── README.md                  # 几何算法文档
│   ├── localization/                  # 定位模块 ✅
│   │   ├── region_calculator.py       # 定位区域计算
│   │   ├── point_selector.py          # 检测点选择
│   │   ├── single_point_estimator.py  # 单点估计
│   │   └── README.md                  # 定位模块文档
│   ├── simulator_client.py            # 模拟器通信客户端 ✅
│   ├── phase1_frequency_scan.py       # 阶段1：频道扫描 ✅
│   ├── phase2_localization.py         # 阶段2：交会定位 ✅
│   └── target.py                      # Target类 ✅
├── tests/                             # 测试用例
│   ├── test_geometry_basic.py         # 几何算法测试 ✅
│   └── test_phase2.py                 # 阶段2综合测试 ✅
├── results/                           # 结果输出
├── run_phase2_test.py                 # 阶段2快速测试脚本 ✅
├── requirements.txt                   # Python依赖
├── 阶段2_实现完成报告.md              # 阶段2详细报告 ✅
├── 阶段2_快速使用指南.md              # 阶段2使用指南 ✅
└── README.md                          # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd problem3
pip install -r requirements.txt
```

依赖包：
- `numpy` - 数值计算
- `scipy` - 凸包计算
- `requests` - HTTP通信（阶段1）

### 2. 运行测试

```bash
# 测试几何算法
python tests/test_geometry_basic.py

# 测试阶段2定位
python tests/test_phase2.py

# 快速测试阶段2
python run_phase2_test.py
```

### 3. 使用阶段2定位

```python
import sys
sys.path.insert(0, 'src')

from phase2_localization import phase2_localization

# 准备阶段1的输出数据
scan_result = {
    'active_channels': [1, 2],
    'scan_data': {
        '1': [[[0.0, 0.0], 225.0], [[900.0, 0.0], 199.6]],
        '2': [[[0.0, 0.0], 315.0], [[900.0, 0.0], 231.3]]
    }
}

# 运行阶段2
targets = phase2_localization(scan_result)

# 使用结果
for target in targets:
    print(f"频道 {target.channel_id}: "
          f"中心({target.center[0]:.1f}, {target.center[1]:.1f}), "
          f"直径{target.diameter:.1f}m")
```

## 📊 当前状态

| 阶段 | 状态 | 完成时间 | 说明 |
|-----|------|---------|------|
| 阶段1：枚举频道扫描 | ✅ 完成 | 2026-09-11 | 混合扫描策略，已测试 |
| 阶段2：逐源交会定位 | ✅ 完成 | 2026-09-12 | 两点交会+单点估计 |
| 阶段3：巡游清除 | ✅ 完成 | 2026-09-12 | 路径规划+清除策略+精修+兜底 |

**整体状态：** ✅ 三阶段全部完成，准备就绪！

---

## 🚀 快速开始

### 完整运行（三阶段）

```bash
# 1. 启动模拟器（GUI程序）
# 2. 点击"开始测试"
# 3. 立即运行：

cd problem3/src
python main_problem3.py 202619020062
```

**注意：** 将 `202619020062` 替换为你的参赛队号

这将依次执行：
1. 阶段1：枚举频道扫描（约22分钟）
2. 阶段2：逐源交会定位（纯算法，<1秒）
3. 阶段3：巡游清除（约26-32分钟）

**总时间：** 约50-60分钟  
**清除比例：** 目标100%（通过兜底验证保证）

---

## 🧪 测试

### 完整测试（需要模拟器）

```bash
# 完整三阶段流程
cd problem3/src
python main_problem3.py 202619020062
```

### 分阶段测试

```bash
# 阶段1测试（需要模拟器）
python test_phase1.py 202619020062

# 阶段2测试（离线，使用测试数据）
python run_phase2_test.py

# 阶段3模块测试（离线）
python tests/test_phase3_modules.py
```

### 所有单元测试（离线）

```bash
# 几何算法测试
python tests/test_geometry_basic.py

# 阶段2定位测试
python tests/test_phase2.py

# 阶段3模块测试
python tests/test_phase3_modules.py
```

**预期：** 所有测试应显示 `✓ 所有测试通过！`

---

## ⚠️ 常见错误

### 错误1: ImportError

```
ImportError: cannot import name 'phase1_frequency_scan'
```

**原因：** 阶段1使用类而不是函数

**解决：** 使用 `from phase1_frequency_scan import FrequencyScan`

### 错误2: AttributeError

```
AttributeError: 'FrequencyScan' object has no attribute 'run_hybrid_scan'
```

**原因：** 方法名错误

**解决：** 使用 `scanner.hybrid_scan(scan_points)`

### 完整错误列表

请参考 `常见错误及解决方案.md` 文档。

---

## 📚 文档

- **快速上手：**
  - `问题3_快速启动指南.md` - 5分钟快速开始
  - `常见错误及解决方案.md` - 10种常见错误及解决
  
- **详细报告：**
  - `问题3_完整实现总结.md` - 完整项目总结
  - `阶段2_实现完成报告.md` - 阶段2详细报告
  - `阶段3_实现完成报告.md` - 阶段3详细报告
  
- **模块文档：**
  - `src/geometry/README.md` - 几何算法模块
  - `src/localization/README.md` - 定位模块
  
- **运维文档：**
  - `最终检查清单.md` - 运行前检查
  - `交付清单.md` - 完整交付清单
  
- **设计文档：**
  - `问题3_总体架构设计.md` - 总体设计
  - `问题3_阶段3_巡游清除路径优化.md` - 阶段3设计

#### 2. 启动模拟器

- 下载并运行无线电干扰源环境模拟器
- 确保模拟器运行在 `http://127.0.0.1:2026`
- 登录并选择"问题3演练测试"或"问题3正式测试"

#### 3. 运行测试

```bash
cd problem3
python test_phase1.py
```

#### 4. 输入参赛队号

程序会提示输入参赛队号（robot_id），输入后开始测试。

### 输出结果

#### 1. 控制台输出

实时显示扫描进度：
- 当前扫描点位置
- 每个频道的检测结果
- 有源频道列表
- 统计信息

#### 2. 结果文件

`results/phase1_result_<robot_id>.json`:
```json
{
  "active_channels": [1, 5, 7, 10, ...],
  "scan_data": {
    "1": [[[0.0, 0.0], 45.5], [[900.0, 0.0], 50.2], ...],
    "5": [[[0.0, 0.0], 120.3], ...]
  },
  "statistics": {
    "n_channels": 5,
    "n_detections": 55,
    "n_switches": 40,
    "scan_time": 60.5,
    "virtual_time": 1000.0
  }
}
```

#### 3. 日志文件

`logs/phase1_log_<robot_id>.json`:
完整的动作日志，包含每次操作的详细信息。

### 性能指标

**预期性能（假设5个有源频道）：**
- 检测次数：55次（20+20+5+5+5）
- 频道切换次数：40次
- 虚拟时间：≈1000秒（16.7分钟）
  - 切换时间：40秒
  - 检测时间：55×5 = 275秒
  - 移动时间：≈685秒

### 测试案例

#### 案例1：单个干扰源
- 干扰源：1个（频道3，位于(500, 500)）
- 预期结果：active_channels = [3]

#### 案例2：多个干扰源
- 干扰源：5个（频道1, 5, 10, 15, 20）
- 预期结果：active_channels = [1, 5, 10, 15, 20]

#### 案例3：边缘干扰源
- 干扰源：1个（频道7，位于(1700, 0)）
- 圆心检测不到，环点E1可以检测到
- 混合策略能正确发现

## 算法说明

### 混合扫描策略

```python
def hybrid_scan(scan_points):
    # 阶段1：圆心全扫（20个频道）
    C = scan_points[0]
    for ch in range(1, 21):
        result = measure(C, ch)
        if has_signal(result):
            active_channels.add(ch)
    
    # 阶段2：环点E1全扫（20个频道）
    E1 = scan_points[1]
    for ch in range(1, 21):
        result = measure(E1, ch)
        if has_signal(result):
            active_channels.add(ch)
    
    # 阶段3：其余环点只扫有源频道
    for point in scan_points[2:]:
        for ch in active_channels:
            result = measure(point, ch)
            # 记录数据
```

### 时间成本模型

**总时间 = 移动时间 + 切换时间 + 检测时间**

- **移动时间** = 距离 / 5 (m/s)
- **切换时间** = 1秒（当频道改变时）
- **检测时间** = 5秒（每次检测）

## 注意事项

1. **网络连接**：确保模拟器可访问
2. **参赛队号**：必须与模拟器登录信息一致
3. **测试模式**：演练测试可无限次，正式测试仅3次
4. **时间限制**：程序运行时间最长20分钟
5. **虚拟时间**：机器狗虚拟活动时间上限100小时

## 下一步

- [ ] 实现阶段2：逐源交会定位
- [ ] 实现阶段3：巡游清除
- [ ] 集成三个阶段
- [ ] 性能优化
- [ ] 正式测试

## 开发团队

- 总体架构设计：队长
- 阶段1实现：Claude Code
- 测试验证：待完成
