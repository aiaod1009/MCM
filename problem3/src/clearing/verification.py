"""
清除复核与补救（原"兜底验证扫描"）

—— 为什么不再需要"多点网格盲扫" ——
附件1 §2.3 / 附件2 §2.4 规定：/clear 是确定性操作——
只要指定位置 20 m 内存在该频道的未清除干扰源，就一定能精确定位并清除，
返回 "success"；否则返回 "no_target_in_range"。即

    一个频道是否已清除，完全由 /clear 的返回值决定。

因此"再派机器狗到若干固定点把频道扫一遍、看还有没有信号"这一做法是冗余的：
  · 对已返回 success 的频道是重复劳动；
  · 它给出的信息比 /clear 的返回值更弱（只能说明"某点还能收到信号"）；
  · 原来的 5 点布局（圆心 + 东南西北各 900 m）在几何上并不能覆盖全域：
    即使把 4 个方向点的半径调到最优的 1275 m，全域最远点距仍有 1273 m，
    大于源的最小有效接收半径 1000 m。所以"扫过 5 点"并不等价于"确认无遗漏"。

真正需要处理的只有两类频道，且都能直接从记账读出来（无需任何检测）：
  A. 阶段2给出了目标、但 clear_target 三次尝试仍失败的频道；
  B. 阶段1判定有源、但阶段2没能给出目标（例如全部数据点都是 "near"、
     取不到示向度）的频道。

补救清除沿用阶段1的原始测向数据：比 5 点扫描的角度更多、更贴近源
（这些点距源必然 ≤ 有效接收半径），交会几何条件更好。

本模块提供：
  · review_cleared()           —— 记账复核，零检测，输出待补救频道与测向数据
  · clear_remaining_sources()  —— 逐个补救清除（交会/单点/near点直清 + 螺旋）
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _to_point_angle(pairs):
    """把 [pos, theta] 序列规范化为 [(np.ndarray, float|None), ...]"""
    out = []
    for item in pairs or []:
        try:
            pos, theta = item[0], item[1]
        except (TypeError, IndexError):
            continue
        try:
            pt = np.asarray(pos, dtype=float)
        except (TypeError, ValueError):
            continue
        if pt.shape != (2,):
            continue
        if theta is None:
            out.append((pt, None))
        else:
            try:
                th = float(theta)
            except (TypeError, ValueError):
                out.append((pt, None))
                continue
            out.append((pt, th if np.isfinite(th) else None))
    return out


def review_cleared(active_channels, targets, cleared_targets, scan_data=None,
                   verbose=True) -> tuple:
    """
    清除复核（基于 /clear 返回值的记账复核，零检测）

    参数:
        active_channels: 阶段1判定"有源"的频道列表
        targets: 阶段2输出的目标列表
        cleared_targets: 阶段3中 /clear 返回 success 的目标列表
        scan_data: 阶段1原始扫描数据 {str(ch): [[[x, y], theta 或 None], ...]}
        verbose: 是否打印复核详情

    返回:
        (remaining_channels, channel_detections)
            remaining_channels: 未确认清除、需要补救的频道（升序）
            channel_detections: {ch: [(np.ndarray 检测点, 示向度或 None), ...]}

    正确性说明:
        阶段1的扫描环 r=1200 m 保证"任一全向源到最近扫描点 ≤ 830 m ≤ 1000 m"，
        且每个扫描点都对全部 20 个频道做检测，故 active_channels 必然包含
        题面区域内的全部干扰源。于是

            (每个 active 频道都已返回 success)  ⟺  (全部干扰源已清除)

        这正是"确保所有干扰源被清除"的充分条件，不需要再做任何扫描。
    """
    cleared_ids = {int(t.channel_id) for t in (cleared_targets or [])}
    target_by_ch = {int(t.channel_id): t for t in (targets or [])}
    scan_data = scan_data or {}

    remaining_channels = []
    channel_detections = {}

    for ch in sorted({int(c) for c in (active_channels or [])}):
        if ch in cleared_ids:
            continue  # /clear 返回 success ⇒ 必已清除（附件1 §2.3）

        remaining_channels.append(ch)

        # 测向数据的优先级：阶段1原始点（最多、最贴近源）→ 阶段2目标点 → 估计中心
        detections = _to_point_angle(scan_data.get(str(ch), []))
        if not detections and ch in target_by_ch:
            detections = _to_point_angle(
                getattr(target_by_ch[ch], 'detection_points', None))
        if not detections and ch in target_by_ch:
            detections = [(np.asarray(target_by_ch[ch].center, dtype=float), None)]

        channel_detections[ch] = detections

    if verbose:
        print(f"\n{'='*60}")
        print(f"清除复核（基于 /clear 返回值，零检测）")
        print(f"{'='*60}\n")
        print(f"阶段1有源频道: {sorted({int(c) for c in (active_channels or [])})}")
        print(f"已确认清除    : {sorted(cleared_ids)}  ← /clear 返回 success")
        if not remaining_channels:
            print(f"待补救频道    : 无")
            print(f"\n✓ 复核通过：全部有源频道均已返回 success，"
                  f"即全部干扰源已清除")
        else:
            print(f"待补救频道    : {remaining_channels}")
            for ch in remaining_channels:
                dets = channel_detections.get(ch, [])
                n_dir = sum(1 for _, a in dets if a is not None)
                n_near = sum(1 for _, a in dets if a is None)
                has_target = "有" if ch in target_by_ch else "无"
                print(f"   频道 {ch:2d}: 历史测向点 {n_dir} 个 / 近距离点 {n_near} 个"
                      f"（阶段2目标：{has_target}）")

    return remaining_channels, channel_detections


def clear_remaining_sources(robot, remaining_channels: list,
                            channel_detections: dict = None) -> list:
    """
    对"未确认清除"的频道执行补救清除

    参数:
        robot: 机器狗对象
        remaining_channels: 待补救频道列表（review_cleared 的输出）
        channel_detections: 历史测向数据 {ch: [(点, 示向度或None), ...]}

    返回:
        cleared_channels: 本次补救中"确实清除成功"的频道号列表

    策略（按可用信息由强到弱）:
        1. ≥2 个带示向度的检测点 → 两点交会重新定位；
        2. 恰好 1 个 → 单点估计；
        3. 无示向度但有 "near" 检测点 → 直接在 near 点清除
           （检测点距源 ≤5 m < 清除半径 20 m，必成功）；
        4. 什么信息都没有 → 回退到原点，按最大不确定度搜索。
        定位后先原地清除一次；失败则围绕估计中心做螺旋搜索（半径 ≤40 m）。

    说明:
        螺旋搜索半径可超过清除半径 20 m——清除是远程触发（与朝向无关），
        只要搜到 20 m 内即可命中，故 40 m 半径的螺旋对本问题有意义。
    """
    print(f"\n{'='*60}")
    print(f"补救清除（{len(remaining_channels)} 个待处理频道）")
    print(f"{'='*60}\n")

    cleared_channels = []

    for channel in remaining_channels:
        print(f"频道 {channel}:")

        detections = (channel_detections or {}).get(channel, []) or []
        direction_data = [(np.asarray(p, float), float(a))
                          for p, a in detections if a is not None]
        near_points = [np.asarray(p, float) for p, a in detections if a is None]

        estimated_position = None
        uncertainty = None

        # ---------- 策略 1：全部观测求交 ----------
        if len(direction_data) >= 2:
            try:
                from localization.region_calculator import compute_localization_region

                all_detectors = np.array([p for p, a in direction_data], dtype=float)
                all_azimuths = np.array([a for p, a in direction_data], dtype=float)

                region_info = compute_localization_region(
                    all_detectors, all_azimuths)
                estimated_position = np.asarray(region_info['center'], dtype=float)
                uncertainty = float(region_info['diameter'])

                print(f"  → 多点交会定位（{len(direction_data)} 个测向点全参与）")
                print(f"    定位中心: ({estimated_position[0]:.1f}, "
                      f"{estimated_position[1]:.1f})，区域直径 {uncertainty:.1f} m")
            except Exception as e:
                print(f"  ✗ 交会定位失败: {e}")
                estimated_position = None

        # ---------- 策略 2：单点估计 ----------
        if estimated_position is None and len(direction_data) == 1:
            from localization.single_point_estimator import single_point_estimation
            point, angle = direction_data[0]
            estimated_position, uncertainty = single_point_estimation(point, angle)
            estimated_position = np.asarray(estimated_position, dtype=float)
            print(f"  → 单点估计（唯一测向点）")
            print(f"    估计中心: ({estimated_position[0]:.1f}, "
                  f"{estimated_position[1]:.1f})，不确定度 {uncertainty:.1f} m")

        # ---------- 策略 3：无示向度 → 在 near 点直清 ----------
        if estimated_position is None and near_points:
            print(f"  → 无示向度，但有 {len(near_points)} 个\"距离过近\"检测点，"
                  f"直接在这些点尝试清除（点距源 ≤5 m < 清除半径 20 m）")
            hit = False
            for idx, p in enumerate(near_points, 1):
                result = robot.clear(tuple(p), channel)
                if result.get('code') == 0 and result.get('result') == 'success':
                    print(f"    ✓ 在历史 near 点{idx} "
                          f"({p[0]:.1f}, {p[1]:.1f}) 清除成功")
                    hit = True
                    break
            if hit:
                cleared_channels.append(channel)
                print()
                continue

            estimated_position = near_points[0].copy()
            uncertainty = 100.0

        # ---------- 策略 4：无任何信息 ----------
        if estimated_position is None:
            print(f"  → 无任何测向信息，回退到原点按大范围搜索")
            estimated_position = np.array([0.0, 0.0])
            uncertainty = 1800.0

        # ---------- 原地清除 ----------
        clear_result = robot.clear(tuple(estimated_position), channel)
        if clear_result.get('code') == 0 and clear_result.get('result') == 'success':
            print(f"  ✓ 直接清除成功")
            cleared_channels.append(channel)
            print()
            continue

        # ---------- 螺旋搜索 ----------
        print(f"  → 直接清除失败，启动螺旋搜索")
        from target import Target
        from clearing.refine_strategy import spiral_search

        temp_target = Target(
            channel_id=channel,
            detection_points=detections if detections else [(np.array([0.0, 0.0]), 0.0)],
            center=estimated_position,
            diameter=uncertainty * 2,
            confidence=0.4,
            method='recovery'
        )

        if uncertainty is None or uncertainty > 100:
            effective_radius = 40.0
        else:
            effective_radius = min(max(uncertainty, 20.0), 40.0)
        print(f"    螺旋搜索半径: {effective_radius:.1f} m")

        if spiral_search(robot, temp_target, search_radius=effective_radius, step=10):
            print(f"  ✓ 螺旋搜索成功清除")
            cleared_channels.append(channel)
        else:
            print(f"  ✗ 螺旋搜索失败，该频道仍未清除")

        print()

    print(f"补救结果: {len(cleared_channels)}/{len(remaining_channels)} 成功")

    return cleared_channels


# 测试代码
if __name__ == '__main__':
    print("测试 verification.py（清除复核与补救）")
    print("=" * 60)

    # 构造一个不依赖模拟器的记账复核用例：
    #   频道 1,2,3 有源；目标 1 清除成功，目标 2 清除失败，频道 3 阶段2无目标
    class _T:
        def __init__(self, ch, center=(0.0, 0.0), dps=None):
            self.channel_id = ch
            self.center = np.array(center, dtype=float)
            self.detection_points = dps or []

    t1 = _T(1, (100.0, 100.0))
    t2 = _T(2, (-200.0, 300.0), [(np.array([0.0, 0.0]), 123.7),
                                 (np.array([900.0, 0.0]), 160.2)])
    scan_data = {
        '1': [[[0.0, 0.0], 45.0], [[900.0, 0.0], 86.3]],
        '2': [[[0.0, 0.0], 123.7], [[900.0, 0.0], 160.2]],
        '3': [[[0.0, 0.0], None], [[0.0, 900.0], None]],   # 全是 near → 无示向度
    }

    remaining, dets = review_cleared(
        active_channels=[1, 2, 3],
        targets=[t1, t2],
        cleared_targets=[t1],
        scan_data=scan_data,
        verbose=True,
    )

    assert remaining == [2, 3], f"待补救频道应为 [2,3]，实际 {remaining}"
    assert len(dets[2]) == 2 and dets[2][0][1] is not None
    assert len(dets[3]) == 2 and all(a is None for _, a in dets[3])
    print("\n✓ 记账复核断言全部通过")

    print("\n接口说明验证完成！")
