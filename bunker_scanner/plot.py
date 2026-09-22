"""Saving renders: bare images for inspection, annotated maps for evidence."""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.image import imsave

MARKER = "#ff3b30"
ACCENT = "#00d1ff"
TRENCH = "#ffd400"


def save_raw(path: pathlib.Path, array: np.ndarray) -> pathlib.Path:
    """One pixel per cell, no axes or annotation — what the render actually is."""
    path.parent.mkdir(parents=True, exist_ok=True)
    imsave(path, array, cmap="gray", vmin=0.0, vmax=1.0, origin="upper")
    return path


def _scalebar(ax, extent):
    span = extent[1] - extent[0]
    length = 100.0 if span <= 1200 else round(span / 8 / 100) * 100 or 100.0
    x0 = extent[0] + span * 0.05
    y0 = extent[2] + (extent[3] - extent[2]) * 0.05
    ax.plot([x0, x0 + length], [y0, y0], color=ACCENT, linewidth=3)
    ax.text(x0, y0 + span * 0.012, f"{length:.0f} m", color=ACCENT, fontsize=9)


def draw(ax, array, extent, title=None, points=(), lines=(), scalebar=True, labels=True):
    ax.imshow(array, cmap="gray", vmin=0, vmax=1, extent=extent, origin="upper")
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    for coords, colour in lines:
        ax.plot([c[0] for c in coords], [c[1] for c in coords], linewidth=1.6, color=colour)
    for point in points:
        ax.plot(point[0], point[1], marker="o", markersize=15, markerfacecolor="none",
                markeredgecolor=MARKER, markeredgewidth=1.4)
        if labels and len(point) > 2 and point[2]:
            ax.annotate(point[2], (point[0], point[1]), textcoords="offset points",
                        xytext=(10, 6), color=MARKER, fontsize=7)
    if scalebar:
        _scalebar(ax, extent)
    if title:
        ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])


def save_map(path: pathlib.Path, array, extent, title=None, points=(), lines=(),
             labels=True, size=9.0) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(size, size), dpi=140)
    draw(ax, array, extent, title, points, lines, labels=labels)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_comparison(path: pathlib.Path, array, extent, plain_title, overlay_title,
                    points=(), lines=(), labels=True) -> pathlib.Path:
    """Plain render beside the annotated one, so the evidence can be judged unprompted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(20, 10.4), dpi=150)
    draw(axes[0], array, extent, plain_title)
    draw(axes[1], array, extent, overlay_title, points, lines, scalebar=False, labels=labels)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
