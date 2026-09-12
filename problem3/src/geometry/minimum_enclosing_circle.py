"""
最小覆盖圆（Minimum Enclosing Circle, MEC）

采用 Welzl 随机增量算法，期望 O(n) 时间复杂度。

最小覆盖圆定义：
    对给定点集 P = {p_1, ..., p_n}，其最小覆盖圆为包含全部点的半径
    最小的圆，圆心与半径满足：

        c = argmin_c  max_{p in P} ||p - c||,
        R = min_c  max_{p in P} ||p - c||.

与"以某指定中心为圆心的覆盖半径"不同，MEC 的圆心与半径是同时
优化的，是定位区域最坏误差最小化的严格解，可直接作为：
    - 定位中心 c_j；
    - 覆盖半径 R_j；
    - 直接清除判据 R_j <= 20m；
    - 精修停止条件 R_j <= 20m。
"""

import numpy as np
import random


def _circle_from_two(p1: np.ndarray, p2: np.ndarray) -> tuple:
    """由两点构造以两点为直径端点的圆（最小覆盖这两点的圆）。"""
    c = (p1 + p2) / 2.0
    r = float(np.linalg.norm(p1 - p2)) / 2.0
    return c, r


def _circle_from_three(p1, p2, p3) -> tuple:
    """由三点构造其外接圆。"""
    # 平移 p1 到原点，简化计算
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    p3 = np.asarray(p3, dtype=float)

    ax, ay = p1
    bx, by = p2
    cx, cy = p3

    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        # 三点共线：退化为以最远两点为直径的圆
        pts = [p1, p2, p3]
        best = None
        for i in range(3):
            for j in range(i + 1, 3):
                c, r = _circle_from_two(pts[i], pts[j])
                if all(np.linalg.norm(p - c) <= r + 1e-9 for p in pts):
                    if best is None or r < best[1]:
                        best = (c, r)
        return best if best is not None else (p1, 0.0)

    ux = ((ax**2 + ay**2) * (by - cy)
          + (bx**2 + by**2) * (cy - ay)
          + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx)
          + (bx**2 + by**2) * (ax - cx)
          + (cx**2 + cy**2) * (bx - ax)) / d
    c = np.array([ux, uy])
    r = float(np.linalg.norm(p1 - c))
    return c, r


def _trivial_circle(boundary: list) -> tuple:
    """由边界点集（0~3 个点）构造其最小覆盖圆。"""
    if len(boundary) == 0:
        return np.array([0.0, 0.0]), 0.0
    if len(boundary) == 1:
        return np.asarray(boundary[0], dtype=float).copy(), 0.0
    if len(boundary) == 2:
        return _circle_from_two(boundary[0], boundary[1])
    # 3 个点：枚举两两构造的圆与三点外接圆，取覆盖全部且半径最小者
    p1, p2, p3 = boundary[0], boundary[1], boundary[2]
    candidates = []
    candidates.append(_circle_from_two(p1, p2))
    candidates.append(_circle_from_two(p1, p3))
    candidates.append(_circle_from_two(p2, p3))
    candidates.append(_circle_from_three(p1, p2, p3))

    pts = [p1, p2, p3]
    best_c, best_r = None, float('inf')
    for c, r in candidates:
        if all(np.linalg.norm(p - c) <= r + 1e-9 for p in pts):
            if r < best_r:
                best_c, best_r = c, r
    if best_c is None:
        # 兜底：取两点直径圆
        best_c, best_r = _circle_from_two(p1, p2)
    return best_c, best_r


def _welzl(points: list, boundary: list) -> tuple:
    """Welzl 随机增量递归。"""
    if not points or len(boundary) == 3:
        return _trivial_circle(boundary)

    idx = random.randrange(len(points))
    p = points[idx]
    points[idx], points[-1] = points[-1], points[idx]
    p = points.pop()

    c, r = _welzl(points, boundary)

    if np.linalg.norm(p - c) <= r + 1e-9:
        points.append(p)
        return c, r

    boundary.append(p)
    c, r = _welzl(points, boundary)
    boundary.pop()
    points.append(p)
    return c, r


def minimum_enclosing_circle(points) -> tuple:
    """
    计算点集的最小覆盖圆（MEC）。

    参数:
        points: 点集，形状 (n, 2) 的数组或列表。

    返回:
        (center, radius): center 为 (2,) 数组，radius 为 float。
    """
    pts = [np.asarray(p, dtype=float) for p in points]

    # 去重（Welzl 对重复点敏感）
    uniq = []
    for p in pts:
        if not any(np.linalg.norm(p - q) < 1e-9 for q in uniq):
            uniq.append(p)
    pts = uniq

    if len(pts) == 0:
        return np.array([0.0, 0.0]), 0.0

    # 拷贝，避免原地修改调用方数据
    working = [p.copy() for p in pts]
    c, r = _welzl(working, [])

    # 数值保护：半径不小于 0
    r = max(float(r), 0.0)
    return np.asarray(c, dtype=float), r


# 测试代码
if __name__ == '__main__':
    print("测试 minimum_enclosing_circle.py")
    print("=" * 60)

    # 测试1：正方形四顶点 → 圆心在中心，半径 = 半对角线
    print("测试1 - 正方形四顶点:")
    pts = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=float)
    c, r = minimum_enclosing_circle(pts)
    print(f"  圆心: ({c[0]:.3f}, {c[1]:.3f}), 半径: {r:.3f}")
    print(f"  期望: 圆心(1,1), 半径 {np.sqrt(2):.3f}")
    print()

    # 测试2：单点
    print("测试2 - 单点:")
    c, r = minimum_enclosing_circle(np.array([[3, 4]], dtype=float))
    print(f"  圆心: ({c[0]:.3f}, {c[1]:.3f}), 半径: {r:.3f} (期望 (3,4), 0)")
    print()

    # 测试3：两点
    print("测试3 - 两点:")
    c, r = minimum_enclosing_circle(np.array([[0, 0], [4, 0]], dtype=float))
    print(f"  圆心: ({c[0]:.3f}, {c[1]:.3f}), 半径: {r:.3f} (期望 (2,0), 2)")
    print()

    # 测试4：三点锐角三角形
    print("测试4 - 三点三角形:")
    pts = np.array([[0, 0], [3, 0], [0, 4]], dtype=float)
    c, r = minimum_enclosing_circle(pts)
    print(f"  圆心: ({c[0]:.3f}, {c[1]:.3f}), 半径: {r:.3f} (期望 (1.5,2), 2.5)")
    print()

    # 测试5：验证覆盖性（随机点集）
    print("测试5 - 随机点集覆盖性验证:")
    rng = np.random.default_rng(42)
    for trial in range(100):
        n = rng.integers(2, 20)
        pts = rng.uniform(-100, 100, size=(n, 2))
        c, r = minimum_enclosing_circle(pts)
        assert all(np.linalg.norm(p - c) <= r + 1e-6 for p in pts), \
            f"覆盖性失败 trial={trial}"
    print("  ✓ 100 组随机点集均满足覆盖性")
    print()

    print("=" * 60)
    print("测试完成！")
