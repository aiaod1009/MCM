# 问题4论文核心插图

本目录提供问题4论文所需的三张核心几何图，统一由
`plot_problem4_core_figures.py` 生成。图中使用理论示意位置，不读取测试日志、隐藏源位置、源类型或发射方向。

## 三张正文图

| 图 | 输出文件名 | 对应内容 |
|---|---|---|
| 图1 | `fig_problem4_discovery_25pt` | 25点内外双环联合网格与未知朝向定向源发现覆盖 |
| 图2 | `fig_problem4_adaptive_side_probe` | 自适应侧向补测的几何关系与可行域收缩 |
| 图3 | `fig_problem4_strip_clearance_current_102pt` | 102点双线条带兜底清除及局部距离保证 |

图1已经按当前报告改为 **25点**：原点 1 点、内环 12 点、外环 12 点；没有继续使用需求总结中的 9×9=81 点旧网格。图3默认采用当前报告中的两条清除线 `y=±w/2`、`x=0,30,…,1500`，共102点。

## 运行方式

在本目录的上一级 `problem4` 目录执行：

```powershell
python figures\plot_problem4_core_figures.py --figure all
```

只生成单张图时，将 `all` 改为 `1`、`2` 或 `3`。脚本会在 `figures\output` 中生成 PDF、SVG、600 dpi PNG 和 TIFF，并同时生成版式对齐记录。

论文优先使用 PDF 或 SVG：

```text
fig_problem4_discovery_25pt.pdf
fig_problem4_adaptive_side_probe.pdf
fig_problem4_strip_clearance_current_102pt.pdf
```

## 旧版需求总结的兼容图

如果论文手仍需要与旧插图需求总结对应的“三线、20 m步长、228点”版本，可执行：

```powershell
python figures\plot_problem4_core_figures.py --figure 3 --legacy-strip
```

该命令会额外生成 `fig_problem4_strip_clearance_legacy_228pt`。它只用于兼容旧材料，当前报告正文应优先使用默认的102点图，避免把旧版参数写回正文。

## 建议图题

```latex
\caption{问题四内外联合网格及定向干扰源发现覆盖示意图}
```

```latex
\caption{问题四自适应侧向补测几何示意图}
```

```latex
\caption{问题四完整条带兜底清除及覆盖保证示意图}
```

图1的正文说明应引用当前25点三角形覆盖与“最长边小于1000 m”的证明；图3的正文说明应引用当前条带半宽
`w=1500 sin(1.005°)=26.309489 m`以及
`sqrt(15^2+(w/2)^2)=19.951123 m<20 m`的距离保证。

