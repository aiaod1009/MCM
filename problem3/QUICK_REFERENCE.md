# 快速参考卡片

## 🚀 启动命令

```bash
cd problem3/src
python main_problem3.py 202619020062
```

## ⚙️ 切换策略

编辑 `src/main_problem3.py` 第68行：

```python
# 当前：智能快速（推荐）
scanner.run(strategy='smart')

# 可选：
# scanner.run(strategy='hybrid')  # 更保守
# scanner.run(strategy='naive')   # 全扫描
```

## 📊 策略对比

| 策略 | 时间 | 阶段1覆盖 | 特点 |
|------|------|-----------|------|
| **smart** | ~40分钟 | 60-70% | 最快，配合兜底 ⭐⭐⭐ |
| **hybrid** | ~50分钟 | 80-90% | 平衡 ⭐⭐ |
| **naive** | ~45分钟 | 95-100% | 保守 ⭐ |

## 🧪 测试命令

```bash
# 完整流程
cd src && python main_problem3.py 202619020062

# 阶段1
python test_phase1.py 202619020062

# 阶段2（离线）
python run_phase2_test.py

# 单元测试
python tests/test_geometry_basic.py
python tests/test_phase2.py
python tests/test_phase3_modules.py
```

## 🔧 常见问题速查

### 连接失败
- 检查模拟器是否启动
- 确认点击"开始测试"
- 验证 robot_id 正确

### 阶段1覆盖不全（11/15）
- 正常现象！阶段3兜底会补救
- 或切换到 `hybrid` 策略

### 清除率 < 100%
- 检查是否执行兜底验证
- 确认螺旋搜索半径 ≤ 20米

## 📦 输出文件

```
results/
├── phase1_scan_result.json   # 扫描结果
├── phase2_targets.json        # 定位目标
└── final_results.json         # 最终结果
```

## 🎯 关键提示

1. **清除半径20米** - 题目限制
2. **兜底验证必须** - 保证100%
3. **Smart策略推荐** - 总时间最优
