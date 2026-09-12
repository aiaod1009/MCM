# 快速参考卡片

## 🚀 启动命令

```bash
cd problem3/src
python main_problem3.py 202619020062 --case-code <测试案例编码>
```

## ⚙️ 切换策略

编辑 `src/main_problem3.py` 第122行：

```python
# 当前：混合策略（推荐）——9 点（圆心 + 8 环点，r=1200 m）全部 20 频道全扫
scanner.run(strategy='hybrid')

# 可选：
# scanner.run(strategy='naive')  # 全点全扫（与 hybrid 同为完备扫描）
# scanner.run(strategy='smart')  # 仅 3 个全扫点（快，但放弃不漏检保证，仅供试跑）
```

## 📊 策略对比

| 策略 | 全扫点 | 是否保证不漏检 | 说明 |
|------|--------|---------------|------|
| **hybrid** ⚖️ | 9 个 | ✅ 是 | 正式测试采用 |
| **naive** | 9 个 | ✅ 是 | 统计口径更啰嗦，用于对照 |
| **smart** 🚀 | 3 个 | ❌ 否 | 仅快速试跑 |

> 三种策略共用同一组 9 个扫描点，区别只在"几个点做全频道扫描"。
> 只有 9 点全部全扫，才能把"覆盖性几何保证"转化为"任一源至少检出一次"，
> 从而让阶段3的记账复核成为可靠的 100% 判据。

## 🧪 测试命令

```bash
# 完整流程
cd src && python main_problem3.py 202619020062

# 离线端到端回归（不需要模拟器）
python tests/test_offline_pipeline.py

# 补救路径单元测试
python tests/test_recovery.py

# 阶段1
python test_phase1.py 202619020062

# 阶段2（离线）
python run_phase2_test.py
```

## 🔧 常见问题速查

### 连接失败
- 检查模拟器是否启动
- 确认点击"开始测试"
- 验证 robot_id 正确

### 阶段1覆盖不全
- 说明用了 `smart`（只 3 点全扫），改用 `hybrid` 即可保证不漏检
- 不要指望阶段3补救——记账复核只能发现"阶段1已经发现过"的频道

### 清除率 < 100%
- 确认阶段1用的是 `hybrid`（9 点全扫）
- 查看阶段3输出的"待补救频道"列表，逐个核对补救结果

## 📦 输出文件

```
results/
├── phase1_scan_result.json   # 扫描结果
├── phase2_targets.json        # 定位目标
├── final_results.json         # 最终结果
├── action_log_*.json          # 行为日志（附件1 4.6 要求）
└── action_table_*.csv         # 指令序列表（附件1 表2 格式）
```

## 🎯 关键提示

1. **清除半径20米** - 题目限制；`/clear` 返回 `success` 即该频道已清除
2. **阶段1用 hybrid** - 全 9 点全扫，保证不漏检（这是 100% 的基础）
3. **清除复核零开销** - 记账复核不产生任何检测，比"5 点网格盲扫"更快更可靠
