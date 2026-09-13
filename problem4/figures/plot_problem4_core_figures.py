#!/usr/bin/env python3
"""Generate the three core figures for the Problem 4 modelling report.

The drawings are deterministic theoretical schematics.  They do not read
hidden simulator locations, source types, or test logs.  The default values
match ``问题4_完整建模报告简明版.md`` and ``src/main_problem4_reliable.py``:

1. 25-point double-ring discovery coverage;
2. adaptive lateral re-measurement;
3. the 102-point two-lane fallback clearance cover.

Run from this directory, for example::

    D:\\anaconda3\\envs\\learning\\python.exe \\
        figures\\plot_problem4_core_figures.py --figure all

The old three-line/228-point strip in the earlier illustration brief is
available with ``--legacy-strip``.  It is retained only for compatibility;
the default figure follows the current report.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle, Wedge


# ---------------------------------------------------------------------------
# Publication style and shared constants
# ---------------------------------------------------------------------------

INK = "#20262E"
BLUE = "#21618C"
TEAL = "#007F82"
ORANGE = "#C96B32"
GREEN = "#2F7D59"
PURPLE = "#7554A3"
GRID = "#AEB8C2"
LIGHT_BLUE = "#DCEAF3"
LIGHT_ORANGE = "#F5E0D0"
LIGHT_GREEN = "#DDEDE4"

DOMAIN_RADIUS = 1800.0
RECEIVE_RADIUS = 1000.0
ANGLE_ERROR_DEG = 1.005
ANGLE_ERROR_RAD = math.radians(ANGLE_ERROR_DEG)
STRIP_LENGTH = 1500.0


def configure_publication_style() -> None:
    """Use editable vector text and a Chinese-capable sans-serif font."""

    # Register fonts explicitly so Chinese labels remain readable when the
    # script is run from a clean Matplotlib cache on Windows.
    candidate_paths = (
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    )
    font_names: list[str] = []
    for font_path in candidate_paths:
        if not font_path.exists():
            continue
        try:
            font_manager.fontManager.addfont(str(font_path))
            name = font_manager.FontProperties(fname=str(font_path)).get_name()
            if name not in font_names:
                font_names.append(name)
        except (OSError, RuntimeError):
            continue

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": font_names + ["Arial", "DejaVu Sans"],
            "font.size": 8.0,
            "axes.titlesize": 10.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.75,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )


def load_alignment_gate():
    """Load the Nature-figure Matplotlib alignment gate when available."""

    skill_script_dir = Path.home() / ".agents" / "skills" / "nature-figure" / "scripts"
    if str(skill_script_dir) not in sys.path:
        sys.path.insert(0, str(skill_script_dir))
    try:
        from audit_panel_alignment import require_matplotlib_panel_alignment

        return require_matplotlib_panel_alignment
    except ImportError as exc:  # pragma: no cover - depends on local skill install
        raise RuntimeError(
            "未找到论文插图版式检查器 audit_panel_alignment.py；"
            "请确认 nature-figure 技能已安装。"
        ) from exc


def save_publication_figure(
    fig: mpl.figure.Figure,
    stem: str,
    output_dir: Path,
    *,
    axes: Sequence[mpl.axes.Axes],
    panel_ids: Sequence[str],
    exclude_axes: Iterable[mpl.axes.Axes] = (),
    row_groups: Sequence[Sequence[str]] | None = None,
    column_groups: Sequence[Sequence[str]] | None = None,
    exemptions: Sequence[dict] = (),
) -> None:
    """Run the layout gate and export editable/vector and raster formats."""

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    require_matplotlib_panel_alignment = load_alignment_gate()
    require_matplotlib_panel_alignment(
        fig,
        axes=axes,
        panel_ids=panel_ids,
        exclude_axes=tuple(exclude_axes),
        row_groups=tuple(row_groups or ()),
        column_groups=tuple(column_groups or ()),
        exemptions=tuple(exemptions),
        json_out=output_dir / f"{stem}.alignment.json",
        overlay_svg=output_dir / f"{stem}.alignment.svg",
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        strict=True,
    )

    # Keep the three export calls explicit: this makes the source preflight
    # unambiguous and leaves editable text in both vector formats.
    fig.savefig(
        output_dir / f"{stem}.pdf",
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.04,
    )
    fig.savefig(
        output_dir / f"{stem}.svg",
        format="svg",
        bbox_inches="tight",
        pad_inches=0.04,
    )
    fig.savefig(
        output_dir / f"{stem}.png",
        format="png",
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.04,
    )
    tiff_path = output_dir / f"{stem}.tiff"
    # Pillow cannot overwrite some TIFF files created by an earlier run on
    # Windows.  These are generated artifacts, so replace that one file to
    # keep repeated script runs deterministic.
    try:
        if tiff_path.exists():
            tiff_path.unlink()
        fig.savefig(
            tiff_path,
            format="tiff",
            dpi=600,
            bbox_inches="tight",
            pad_inches=0.04,
        )
    except PermissionError:
        # A preview program may still hold the previous TIFF open.  Preserve
        # repeatability by writing a clearly named refreshed copy instead of
        # making PDF/SVG/PNG generation fail as a side effect.
        refreshed_tiff_path = output_dir / f"{stem}_refreshed.tiff"
        fig.savefig(
            refreshed_tiff_path,
            format="tiff",
            dpi=600,
            bbox_inches="tight",
            pad_inches=0.04,
        )
        print(f"提示：原 TIFF 正被占用，已写入 {refreshed_tiff_path.name}")
    plt.close(fig)


def unit(angle_deg: float) -> np.ndarray:
    angle = math.radians(angle_deg)
    return np.array([math.cos(angle), math.sin(angle)], dtype=float)


def add_arrow(
    ax: mpl.axes.Axes,
    start: Sequence[float],
    end: Sequence[float],
    *,
    color: str = INK,
    lw: float = 1.0,
    mutation_scale: float = 10.0,
    linestyle: str = "-",
    zorder: int = 6,
) -> FancyArrowPatch:
    arrow = FancyArrowPatch(
        tuple(start),
        tuple(end),
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=lw,
        linestyle=linestyle,
        color=color,
        shrinkA=0,
        shrinkB=0,
        zorder=zorder,
    )
    ax.add_patch(arrow)
    return arrow


def annotate_box(
    ax: mpl.axes.Axes,
    text: str,
    xy: tuple[float, float],
    *,
    fontsize: float = 7.5,
    color: str = INK,
    ha: str = "left",
    va: str = "top",
    zorder: int = 12,
    alpha: float = 0.94,
) -> None:
    ax.text(
        xy[0],
        xy[1],
        text,
        transform=ax.transData,
        ha=ha,
        va=va,
        fontsize=fontsize,
        color=color,
        linespacing=1.35,
        zorder=zorder,
    )


# ---------------------------------------------------------------------------
# Figure 1: 25-point double-ring discovery coverage
# ---------------------------------------------------------------------------


def double_ring_geometry() -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Return O, inner ring, outer ring, inner radius, and outer radius."""

    alpha = math.pi / 12.0
    outer_radius = 1801.0 / math.cos(alpha)
    inner_radius = 1801.0 / (2.0 * math.cos(alpha) ** 2)
    inner = np.array(
        [inner_radius * unit(30.0 * k) for k in range(12)], dtype=float
    )
    outer = np.array(
        [outer_radius * unit(15.0 + 30.0 * k) for k in range(12)], dtype=float
    )
    origin = np.zeros(2, dtype=float)
    assert len(inner) + len(outer) + 1 == 25
    return origin, inner, outer, inner_radius, outer_radius


def plot_discovery_25pt(output_dir: Path) -> None:
    origin, inner, outer, inner_radius, outer_radius = double_ring_geometry()

    # A deterministic schematic source near the boundary, inside the selected
    # triangle (I_0, I_1, E_0).  The weights make g a convex combination of
    # the three detector vertices, which is the geometric proof's key fact.
    cell = np.vstack((inner[0], inner[1], outer[0]))
    g = np.array([0.05, 0.05, 0.90]) @ cell
    u = unit(15.0)
    dot_products = (cell - g) @ u
    valid_index = int(np.argmax(dot_products))
    valid_vertex = cell[valid_index]
    distance_to_valid = float(np.linalg.norm(valid_vertex - g))

    fig, ax = plt.subplots(figsize=(7.2, 6.5))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-2200, 2200)
    ax.set_ylim(-2200, 2200)
    ax.set_xlabel(r"$x$/m")
    ax.set_ylabel(r"$y$/m")
    ax.set_title("问题四内外联合网格及定向干扰源发现覆盖示意图", pad=12)

    # Target domain and the outer dodecagon that contains it.
    ax.add_patch(
        Circle(
            origin,
            DOMAIN_RADIUS,
            facecolor=LIGHT_BLUE,
            edgecolor=BLUE,
            linewidth=1.1,
            alpha=0.33,
            zorder=1,
        )
    )
    outer_closed = np.vstack((outer, outer[0]))
    ax.plot(
        outer_closed[:, 0],
        outer_closed[:, 1],
        color=TEAL,
        linewidth=1.0,
        linestyle="-",
        zorder=2,
    )

    # Light triangulation edges: 12 central triangles and 24 annular ones.
    for k in range(12):
        kp = (k + 1) % 12
        ax.plot(
            [origin[0], inner[k, 0]],
            [origin[1], inner[k, 1]],
            color=GRID,
            linewidth=0.45,
            alpha=0.65,
            zorder=2,
        )
        ax.plot(
            [inner[k, 0], inner[kp, 0]],
            [inner[k, 1], inner[kp, 1]],
            color=GRID,
            linewidth=0.55,
            alpha=0.78,
            zorder=2,
        )
        ax.plot(
            [inner[k, 0], outer[k, 0]],
            [inner[k, 1], outer[k, 1]],
            color=GRID,
            linewidth=0.45,
            alpha=0.6,
            zorder=2,
        )
        ax.plot(
            [inner[kp, 0], outer[k, 0]],
            [inner[kp, 1], outer[k, 1]],
            color=GRID,
            linewidth=0.45,
            alpha=0.6,
            zorder=2,
        )
        ax.plot(
            [outer[k, 0], outer[kp, 0]],
            [outer[k, 1], outer[kp, 1]],
            color=GRID,
            linewidth=0.45,
            alpha=0.6,
            zorder=2,
        )

    # Unknown-orientation effective half-plane H(u): u^T(x-g) >= 0.
    normal = np.array([-u[1], u[0]])
    halfplane_length = 3000.0
    halfplane = np.vstack(
        (
            g - halfplane_length * normal,
            g + halfplane_length * normal,
            g + halfplane_length * normal + halfplane_length * u,
            g - halfplane_length * normal + halfplane_length * u,
        )
    )
    ax.add_patch(
        Polygon(
            halfplane,
            closed=True,
            facecolor=LIGHT_ORANGE,
            edgecolor="none",
            alpha=0.48,
            zorder=3,
        )
    )
    ax.plot(
        [g[0] - 1500 * normal[0], g[0] + 1500 * normal[0]],
        [g[1] - 1500 * normal[1], g[1] + 1500 * normal[1]],
        color=ORANGE,
        linewidth=0.9,
        linestyle="--",
        zorder=4,
    )

    # Detector points: O + 12 inner + 12 outer = 25.
    ax.scatter(
        inner[:, 0],
        inner[:, 1],
        s=32,
        facecolor=BLUE,
        edgecolor="white",
        linewidth=0.45,
        marker="o",
        label="内环 $I_k$（12点）",
        zorder=7,
    )
    ax.scatter(
        outer[:, 0],
        outer[:, 1],
        s=40,
        facecolor=TEAL,
        edgecolor="white",
        linewidth=0.45,
        marker="^",
        label="外环 $E_k$（12点）",
        zorder=7,
    )
    ax.scatter(
        [origin[0]],
        [origin[1]],
        s=40,
        facecolor=INK,
        edgecolor="white",
        linewidth=0.5,
        marker="o",
        label="中心点 $O$（1点）",
        zorder=8,
    )

    # Highlight one boundary triangle that contains g.
    ax.add_patch(
        Polygon(
            cell,
            closed=True,
            facecolor=ORANGE,
            edgecolor=ORANGE,
            linewidth=1.25,
            alpha=0.30,
            hatch="///",
            zorder=5,
        )
    )
    ax.scatter(
        [g[0]],
        [g[1]],
        s=62,
        facecolor=ORANGE,
        edgecolor="white",
        linewidth=0.9,
        marker="*",
        label="Source $g$（示例定向源）",
        zorder=10,
    )
    ax.scatter(
        [valid_vertex[0]],
        [valid_vertex[1]],
        s=74,
        facecolor="white",
        edgecolor=ORANGE,
        linewidth=1.35,
        marker="o",
        zorder=11,
    )

    # Label only the highlighted cell's vertices to keep the full figure clean.
    vertex_names = (r"$I_0$", r"$I_1$", r"$E_0$")
    label_offsets = ((125, -240), (-150, 220), (80, 250))
    for point, name, offset in zip(cell, vertex_names, label_offsets):
        ax.annotate(
            name,
            xy=point,
            xytext=(point[0] + offset[0], point[1] + offset[1]),
            fontsize=8.5,
            color=INK,
            zorder=12,
        )
    ax.annotate(
        r"$g$",
        xy=g,
        xytext=(1600, 220),
        fontsize=9,
        color=ORANGE,
        fontweight="bold",
        zorder=12,
    )

    # Direction vector and the guaranteed receiving vertex.
    add_arrow(ax, g, g + 380 * u, color=ORANGE, lw=1.25, mutation_scale=12)
    ax.text(
        2100,
        -1800,
        r"$u$（未知朝向，15°）",
        color=ORANGE,
        fontsize=8,
        ha="right",
        va="center",
        zorder=12,
    )
    ax.annotate(
        "",
        xy=valid_vertex,
        xytext=g,
        arrowprops={"arrowstyle": "<->", "color": ORANGE, "linewidth": 0.9},
        zorder=9,
    )
    ax.text(
        1900,
        1180,
        rf"$\|{vertex_names[valid_index]}-g\|={distance_to_valid:.1f}\,\mathrm{{m}}<1000\,\mathrm{{m}}$",
        fontsize=7.5,
        color=ORANGE,
        zorder=12,
    )

    condition_value = float(dot_products[valid_index])
    ax.text(
        1900,
        900,
        rf"$u^\mathrm{{T}}({vertex_names[valid_index]}-g)={condition_value:.1f}\geq0$",
        fontsize=7.5,
        color=ORANGE,
        zorder=12,
    )
    ax.text(
        1450,
        1650,
        r"有效发射半平面 $H(u):\,u^{\mathrm{T}}(x-g)\geq0$",
        color=ORANGE,
        fontsize=8,
        rotation=15,
        rotation_mode="anchor",
        ha="left",
        va="center",
        zorder=12,
    )

    ax.text(
        -2100,
        2150,
        r"目标圆域 $\Omega$: $\|x\|\leq1800\,\mathrm{m}$",
        fontsize=8,
        color=BLUE,
        ha="left",
        va="top",
        zorder=12,
    )
    ax.text(
        -2100,
        1980,
        r"$25=1+12+12$；外环内切圆半径 $1801\,\mathrm{m}$",
        fontsize=7.7,
        color=INK,
        ha="left",
        va="top",
        zorder=12,
    )
    annotate_box(
        ax,
        "\n".join(
            [
                r"选中三角形 $(I_0,I_1,E_0)$",
                r"三角形最长边 $r=965.2\,\mathrm{m}<1000\,\mathrm{m}$",
                r"$g$ 为三顶点凸组合，至少一个顶点满足半平面条件",
            ]
        ),
        (2250, -1580),
        fontsize=7.6,
    )
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 0.0),
        frameon=True,
        facecolor="white",
        edgecolor=GRID,
        framealpha=0.92,
        handlelength=1.6,
    )
    ax.grid(False)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.10, top=0.90)
    save_publication_figure(
        fig,
        "fig_problem4_discovery_25pt",
        output_dir,
        axes=(ax,),
        panel_ids=("a",),
    )


# ---------------------------------------------------------------------------
# Figure 2: adaptive lateral re-measurement geometry
# ---------------------------------------------------------------------------


def cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def clip_cross_halfplane(
    polygon: np.ndarray,
    line_point: np.ndarray,
    direction: np.ndarray,
    *,
    keep_positive: bool,
) -> np.ndarray:
    """Clip a convex polygon by a directed line half-plane."""

    if len(polygon) == 0:
        return polygon

    def signed(point: np.ndarray) -> float:
        value = cross2(direction, point - line_point)
        return value if keep_positive else -value

    result: list[np.ndarray] = []
    previous = polygon[-1]
    previous_value = signed(previous)
    previous_inside = previous_value >= -1e-9
    for current in polygon:
        current_value = signed(current)
        current_inside = current_value >= -1e-9
        if current_inside != previous_inside:
            denominator = previous_value - current_value
            if abs(denominator) > 1e-12:
                fraction = previous_value / denominator
                result.append(previous + fraction * (current - previous))
        if current_inside:
            result.append(current)
        previous = current
        previous_value = current_value
        previous_inside = current_inside
    return np.array(result, dtype=float) if result else np.empty((0, 2), dtype=float)


def clip_bearing_wedge(
    polygon: np.ndarray,
    observer: np.ndarray,
    target: np.ndarray,
    half_angle_deg: float = ANGLE_ERROR_DEG,
) -> np.ndarray:
    direction_angle = math.atan2(target[1] - observer[1], target[0] - observer[0])
    lower = np.array(
        [math.cos(direction_angle - math.radians(half_angle_deg)),
         math.sin(direction_angle - math.radians(half_angle_deg))]
    )
    upper = np.array(
        [math.cos(direction_angle + math.radians(half_angle_deg)),
         math.sin(direction_angle + math.radians(half_angle_deg))]
    )
    # The target lies to the left of the lower ray and to the right of the
    # upper ray, so both half-plane operations retain the target.
    clipped = clip_cross_halfplane(polygon, observer, lower, keep_positive=True)
    return clip_cross_halfplane(clipped, observer, upper, keep_positive=False)


def plot_adaptive_side_probe(output_dir: Path) -> None:
    s = np.array([0.0, 0.0])
    target = np.array([900.0, 420.0])
    target_angle = math.atan2(target[1], target[0])
    radii = (115.0, 1420.0)
    ray_minus = np.array(
        [math.cos(target_angle - ANGLE_ERROR_RAD), math.sin(target_angle - ANGLE_ERROR_RAD)]
    )
    ray_plus = np.array(
        [math.cos(target_angle + ANGLE_ERROR_RAD), math.sin(target_angle + ANGLE_ERROR_RAD)]
    )
    # Initial conservative feasible polygon P: a finite display window of the
    # two-sided angular wedge supplied by the first valid measurement.
    P = np.array(
        [radii[0] * ray_minus, radii[1] * ray_minus,
         radii[1] * ray_plus, radii[0] * ray_plus],
        dtype=float,
    )
    c = P.mean(axis=0)
    rho = float(np.max(np.linalg.norm(P - c, axis=1)))
    e = (c - s) / np.linalg.norm(c - s)
    e_perp = np.array([-e[1], e[0]])
    b = min(250.0, max(30.0, rho / 2.0))
    q_plus = c - b * e + b * e_perp
    q_minus = c - b * e - b * e_perp

    refined = clip_bearing_wedge(P, q_plus, target)
    refined = clip_bearing_wedge(refined, q_minus, target)
    if len(refined) < 3:
        raise RuntimeError("侧向补测示意区域为空，请检查示意参数。")

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-180, 1020)
    ax.set_ylim(-430, 720)
    ax.set_xlabel(r"$x$/m")
    ax.set_ylabel(r"$y$/m")
    fig.suptitle("问题四自适应侧向补测几何示意图", fontsize=10, y=1.06)

    # Initial feasible region and its conservative cover circle.
    P_closed = np.vstack((P, P[0]))
    ax.add_patch(
        Polygon(
            P,
            closed=True,
            facecolor=LIGHT_BLUE,
            edgecolor=BLUE,
            linewidth=1.15,
            alpha=0.62,
            zorder=2,
        )
    )
    ax.plot(P_closed[:, 0], P_closed[:, 1], color=BLUE, linewidth=1.15, zorder=3)
    ax.add_patch(
        Circle(
            c,
            rho,
            facecolor="none",
            edgecolor=GRID,
            linewidth=0.9,
            linestyle="--",
            alpha=0.95,
            zorder=1,
        )
    )

    # Refined intersection after the two lateral observations.
    refined_closed = np.vstack((refined, refined[0]))
    ax.add_patch(
        Polygon(
            refined,
            closed=True,
            facecolor=LIGHT_GREEN,
            edgecolor=GREEN,
            linewidth=1.4,
            alpha=0.86,
            zorder=5,
        )
    )
    ax.plot(refined_closed[:, 0], refined_closed[:, 1], color=GREEN, linewidth=1.4, zorder=6)

    # Original bearing cone from s.
    far = 1150.0
    ax.plot(
        [s[0], far * ray_minus[0]],
        [s[1], far * ray_minus[1]],
        color=BLUE,
        linewidth=0.85,
        linestyle="--",
        zorder=4,
    )
    ax.plot(
        [s[0], far * ray_plus[0]],
        [s[1], far * ray_plus[1]],
        color=BLUE,
        linewidth=0.85,
        linestyle="--",
        zorder=4,
    )

    # Side-probe bearing wedges aimed at the schematic source.
    for q, color in ((q_plus, ORANGE), (q_minus, PURPLE)):
        q_angle = math.degrees(math.atan2(target[1] - q[1], target[0] - q[0]))
        ax.add_patch(
            Wedge(
                q,
                430.0,
                q_angle - ANGLE_ERROR_DEG,
                q_angle + ANGLE_ERROR_DEG,
                facecolor=color,
                edgecolor=color,
                linewidth=0.65,
                alpha=0.14,
                zorder=4,
            )
        )
        add_arrow(
            ax,
            q,
            q + 0.92 * (target - q),
            color=color,
            lw=0.95,
            mutation_scale=10,
            linestyle="--",
            zorder=7,
        )

    # Key points and the construction of e/e_perp.
    ax.scatter([s[0]], [s[1]], s=48, color=INK, marker="o", zorder=10)
    ax.scatter([c[0]], [c[1]], s=48, color=ORANGE, marker="o", zorder=10)
    ax.scatter([q_plus[0]], [q_plus[1]], s=54, color=ORANGE, marker="D", zorder=10)
    ax.scatter([q_minus[0]], [q_minus[1]], s=54, color=PURPLE, marker="D", zorder=10)
    ax.scatter([target[0]], [target[1]], s=66, color=INK, edgecolor="white", marker="*", zorder=11)

    add_arrow(ax, s, s + 0.62 * (c - s), color=INK, lw=1.05, mutation_scale=11, linestyle="--")
    add_arrow(ax, c - 120 * e_perp, c + 120 * e_perp, color=ORANGE, lw=1.0, mutation_scale=10)
    ax.text(760, 650, r"$e_\perp=(-e_y,e_x)$", fontsize=8, color=ORANGE, ha="left", va="bottom")

    ax.text(-105, -80, r"$s$", fontsize=9, fontweight="bold", color=INK)
    ax.text(c[0] + 32, c[1] - 40, r"$c$", fontsize=9, fontweight="bold", color=ORANGE)
    ax.text(q_plus[0] + 35, q_plus[1] + 45, r"$q_+$", fontsize=9, fontweight="bold", color=ORANGE)
    ax.text(q_minus[0] + 24, q_minus[1] - 58, r"$q_-$", fontsize=9, fontweight="bold", color=PURPLE)
    ax.text(995, 620, r"$g$（示意真实源）", fontsize=8.5, color=INK, ha="right")
    ax.text(100, -410, r"虚线圆：以 $c$ 为圆心的保守覆盖圆，半径为 $\rho$", fontsize=7.8, color=GRID)
    ax.annotate(
        "",
        xy=(c[0] + rho * 0.22, c[1] + rho * 0.15),
        xytext=c,
        arrowprops={"arrowstyle": "<->", "color": GRID, "linewidth": 0.8},
        zorder=4,
    )

    fig.text(
        0.035,
        0.99,
        "\n".join(
            [
                r"首次观测形成保守区域 $P$",
                r"方向单位向量：$e=(c-s)/\|c-s\|$",
                r"侧向点：$q_\pm=c-be\pm be_\perp$",
                rf"$b=\min(250,\max(30,\rho/2))={b:.1f}\,\mathrm{{m}}$",
                r"新约束交会得到更小的 $P'$",
            ]
        ),
        fontsize=7.6,
        color=INK,
        ha="left",
        va="top",
        linespacing=1.35,
    )
    ax.text(
        730,
        -375,
        r"蓝色：初始 $P$；绿色：加入 $q_+,q_-$ 观测后的 $P'$",
        fontsize=7.8,
        color=GREEN,
        ha="center",
        va="bottom",
    )
    ax.grid(False)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.11, top=0.80)
    save_publication_figure(
        fig,
        "fig_problem4_adaptive_side_probe",
        output_dir,
        axes=(ax,),
        panel_ids=("a",),
    )


# ---------------------------------------------------------------------------
# Figure 3: complete strip fallback and local proof
# ---------------------------------------------------------------------------


def strip_parameters(legacy: bool) -> tuple[np.ndarray, np.ndarray, float, float, str]:
    half_width = STRIP_LENGTH * math.sin(ANGLE_ERROR_RAD)
    if legacy:
        line_offsets = np.array([-20.0, 0.0, 20.0])
        x_values = np.arange(0.0, STRIP_LENGTH + 0.001, 20.0)
        max_distance = math.sqrt(10.0**2 + 10.0**2)
        mode = "legacy"
    else:
        line_offsets = np.array([-half_width / 2.0, half_width / 2.0])
        x_values = np.arange(0.0, STRIP_LENGTH + 0.001, 30.0)
        max_distance = math.sqrt(15.0**2 + (half_width / 2.0) ** 2)
        mode = "current"
    return line_offsets, x_values, half_width, max_distance, mode


def draw_lawnmower_path(
    ax: mpl.axes.Axes,
    line_offsets: np.ndarray,
    x_values: np.ndarray,
    *,
    color: str = ORANGE,
) -> None:
    rows: list[np.ndarray] = []
    for row, y in enumerate(line_offsets):
        xs = x_values if row % 2 == 0 else x_values[::-1]
        rows.append(np.column_stack((xs, np.full_like(xs, y))))
    path = np.vstack(
        [row if index == 0 else np.vstack((np.array([rows[index - 1][-1]]), row)) for index, row in enumerate(rows)]
    )
    # The concatenation above includes each row's points and the connector;
    # drawing in short arrows preserves the intended serial sweep.
    for start, end in zip(path[:-1], path[1:]):
        segment = end - start
        segment_length = float(np.linalg.norm(segment))
        if segment_length == 0:
            continue
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=color,
            linewidth=0.65,
            alpha=0.52,
            zorder=4,
        )
    # A small number of arrows gives direction without covering every point.
    stride = max(1, len(path) // 8)
    for index in range(0, len(path) - 1, stride):
        add_arrow(
            ax,
            path[index],
            path[min(index + 1, len(path) - 1)],
            color=color,
            lw=0.85,
            mutation_scale=8,
            zorder=7,
        )


def plot_strip_clearance(output_dir: Path, *, legacy: bool = False) -> None:
    line_offsets, x_values, half_width, max_distance, mode = strip_parameters(legacy)
    point_count = int(len(line_offsets) * len(x_values))

    if legacy:
        example_g = np.array([930.0, 10.0])
        example_q = np.array([920.0, 0.0])
        x_bound = 10.0
        y_bound = 10.0
        stem = "fig_problem4_strip_clearance_legacy_228pt"
        mode_label = "旧版需求参数：3条线、228点"
    else:
        example_g = np.array([945.0, 0.0])
        example_q = np.array([930.0, line_offsets[1]])
        x_bound = 15.0
        y_bound = half_width / 2.0
        stem = "fig_problem4_strip_clearance_current_102pt"
        mode_label = "现行报告参数：2条线、102点"

    fig = plt.figure(figsize=(7.2, 2.95))
    grid_spec = fig.add_gridspec(1, 2, width_ratios=(2.25, 1.0), wspace=0.30)
    ax = fig.add_subplot(grid_spec[0, 0])
    inset = fig.add_subplot(grid_spec[0, 1])
    ax.set_xlim(-80, 1600)
    ax.set_ylim(-62, 62)
    ax.set_xlabel(r"局部纵向坐标 $x$/m")
    ax.set_ylabel(r"局部横向坐标 $y$/m")
    ax.set_title("(a) 完整条带与折返路径", fontsize=8.8, pad=3)
    fig.suptitle("问题四完整条带兜底清除及覆盖保证示意图", fontsize=10, y=0.995)

    ax.add_patch(
        Rectangle(
            (0.0, -half_width),
            STRIP_LENGTH,
            2.0 * half_width,
            facecolor=LIGHT_BLUE,
            edgecolor="none",
            alpha=0.82,
            zorder=1,
        )
    )
    for sign, label in ((1.0, rf"$y={half_width:.1f}$"), (-1.0, rf"$y=-{half_width:.1f}$")):
        y = sign * half_width
        ax.plot(
            [0.0, STRIP_LENGTH],
            [y, y],
            color=BLUE,
            linewidth=0.9,
            linestyle="--",
            zorder=2,
        )
        ax.text(
            STRIP_LENGTH + 18,
            y,
            label,
            color=BLUE,
            fontsize=7.6,
            va="center",
            ha="left",
        )

    # Candidate clearance points and the serial lawnmower path.
    for row, y in enumerate(line_offsets):
        ax.plot(
            x_values,
            np.full_like(x_values, y),
            linestyle="none",
            marker="o",
            markersize=2.45,
            markerfacecolor=ORANGE if row % 2 == 0 else PURPLE,
            markeredgecolor="white",
            markeredgewidth=0.25,
            alpha=0.95,
            zorder=6,
        )
    draw_lawnmower_path(ax, line_offsets, x_values)
    ax.plot(
        [0.0, STRIP_LENGTH],
        [0.0, 0.0],
        color=GRID,
        linewidth=0.55,
        linestyle=":",
        zorder=2,
    )
    add_arrow(ax, (0.0, 0.0), (250.0, 0.0), color=INK, lw=1.0, mutation_scale=10, zorder=8)
    ax.scatter([0.0], [0.0], s=45, color=INK, marker="o", zorder=10)
    ax.text(-65, -50, r"$S$（首条有效示向度位置）", fontsize=7.8, color=INK, ha="left")
    ax.text(320, -38, "初始示向度方向（局部 $x$ 轴）", fontsize=7.8, color=INK, ha="left", va="bottom")

    # Highlight the local region used by the inset.
    ax.add_patch(
        Rectangle(
            (example_g[0] - 65, example_g[1] - 28),
            130,
            56,
            facecolor="none",
            edgecolor=GREEN,
            linewidth=1.0,
            linestyle="-.",
            zorder=8,
        )
    )
    ax.scatter([example_g[0]], [example_g[1]], s=38, color=INK, marker="*", zorder=9)
    ax.text(
        1575,
        -56,
        f"{mode_label}；候选清除点共 {point_count} 个",
        fontsize=7.8,
        color=INK,
        ha="right",
        va="bottom",
    )

    # Local zoom is shown as a deliberately unequal-width companion panel:
    # the main panel carries the long strip, while panel (b) carries the
    # distance proof at readable scale.
    inset.set_xlim(example_g[0] - 75, example_g[0] + 75)
    inset.set_ylim(example_g[1] - 42, example_g[1] + 42)
    # Keep the companion panel aligned with the main panel's top and bottom
    # edges.  The two component arrows and the numerical bound carry the
    # metric proof, so the zoom panel can use an automatic display aspect.
    inset.set_aspect("auto")
    inset.set_xlabel(r"$x$/m", fontsize=6.7, labelpad=1)
    inset.set_ylabel(r"$y$/m", fontsize=6.7, labelpad=1)
    inset.tick_params(labelsize=6.0, width=0.45, length=2)
    inset.set_title("(b) 局部放大与距离证明", fontsize=7.5, pad=3)
    inset.add_patch(
        Rectangle(
            (example_g[0] - 75, -half_width),
            150,
            2.0 * half_width,
            facecolor=LIGHT_BLUE,
            edgecolor="none",
            alpha=0.75,
            zorder=1,
        )
    )
    for row, y in enumerate(line_offsets):
        local_mask = (x_values >= example_g[0] - 75) & (x_values <= example_g[0] + 75)
        inset.plot(
            x_values[local_mask],
            np.full(np.count_nonzero(local_mask), y),
            linestyle="none",
            marker="o",
            markersize=4.0,
            markerfacecolor=ORANGE if row % 2 == 0 else PURPLE,
            markeredgecolor="white",
            markeredgewidth=0.3,
            zorder=5,
        )
    inset.scatter([example_g[0]], [example_g[1]], s=62, color=INK, marker="*", zorder=8)
    inset.scatter([example_q[0]], [example_q[1]], s=34, color=GREEN, marker="o", zorder=8)
    inset.plot(
        [example_g[0], example_q[0]],
        [example_g[1], example_q[1]],
        color=GREEN,
        linewidth=0.9,
        zorder=7,
    )
    # Orthogonal components make the covering inequality visible.
    inset.plot(
        [example_g[0], example_q[0]],
        [example_g[1], example_g[1]],
        color=GREEN,
        linewidth=0.7,
        linestyle="--",
        zorder=6,
    )
    inset.plot(
        [example_q[0], example_q[0]],
        [example_g[1], example_q[1]],
        color=GREEN,
        linewidth=0.7,
        linestyle="--",
        zorder=6,
    )
    inset.text(
        example_g[0] - 70,
        example_g[1] + (39 if not legacy else 35),
        rf"$\Delta x\leq{x_bound:g}\,\mathrm{{m}}$；$\Delta y\leq{y_bound:.2f}\,\mathrm{{m}}$",
        fontsize=6.35,
        color=GREEN,
        ha="left",
        va="top",
    )
    inset.text(
        example_g[0] + 50,
        example_g[1] + (32 if not legacy else 38),
        r"$g$",
        fontsize=7.8,
        color=INK,
        fontweight="bold",
    )
    inset.text(
        example_q[0] + 15,
        example_q[1] + (16 if not legacy else 28),
        r"$Q$",
        fontsize=7.5,
        color=GREEN,
        fontweight="bold",
    )
    inset.text(
        example_g[0] - 69,
        example_g[1] - 37,
        rf"$d(g,Q)\leq{max_distance:.3f}\,\mathrm{{m}}<20\,\mathrm{{m}}$",
        fontsize=6.65,
        color=GREEN,
        ha="left",
        va="bottom",
    )
    for spine in inset.spines.values():
        spine.set_linewidth(0.65)
        spine.set_edgecolor(GREEN)

    annotate_box(
        ax,
        "\n".join(
            [
                rf"$w=1500\sin(1.005^\circ)={half_width:.3f}\,\mathrm{{m}}$",
                r"三条线：$y=-20,0,20$；步长 $20\,\mathrm{m}$"
                if legacy
                else r"两条线：$y=\pm w/2$；步长 $30\,\mathrm{m}$",
                rf"最坏距离上界 $<{20}\,\mathrm{{m}}$",
            ]
        ),
        (30, 55),
        fontsize=7.5,
    )
    ax.grid(False)
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.17, top=0.86)
    save_publication_figure(
        fig,
        stem,
        output_dir,
        axes=(ax, inset),
        panel_ids=("main", "inset"),
        row_groups=(["main", "inset"],),
        exemptions=(
            {
                "panels": ["main", "inset"],
                "checks": ["panel-width"],
                "reason": "主图需要承载1500 m长条带，局部放大 panel 需要保持距离标注可读，因此采用有意的不等宽布局。",
            },
        ),
    )


# ---------------------------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成问题4三张核心论文插图")
    parser.add_argument(
        "--figure",
        choices=("1", "2", "3", "all"),
        default="all",
        help="生成图1、图2、图3，或全部生成（默认：all）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="输出目录（默认：figures/output）",
    )
    parser.add_argument(
        "--legacy-strip",
        action="store_true",
        help="图3同时生成旧版三线228点兼容图；默认只生成当前102点双线图。",
    )
    return parser


def main() -> None:
    configure_publication_style()
    args = build_parser().parse_args()
    figures = {args.figure} if args.figure != "all" else {"1", "2", "3"}

    if "1" in figures:
        plot_discovery_25pt(args.output_dir)
    if "2" in figures:
        plot_adaptive_side_probe(args.output_dir)
    if "3" in figures:
        plot_strip_clearance(args.output_dir, legacy=False)
        if args.legacy_strip:
            plot_strip_clearance(args.output_dir, legacy=True)

    print(f"已生成图形文件：{args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
