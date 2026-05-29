"""Plotting helpers for 3D static CT experiments."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def save_geometry_plot(sources_by_arch: list[object], cfg: object, path: Path) -> None:
    """Save x-y and z-angle source geometry overview."""

    fig, axes = plt.subplots(2, len(sources_by_arch), figsize=(4.0 * len(sources_by_arch), 7.0), constrained_layout=True)
    axes = np.asarray(axes).reshape(2, len(sources_by_arch))
    for col, srcs in enumerate(sources_by_arch):
        ax = axes[0, col]
        ax.scatter(srcs.positions[:, 0], srcs.positions[:, 1], s=18)
        ax.scatter([0], [0], c="k", s=20)
        ax.scatter([cfg.roi_center[0]], [cfg.roi_center[1]], c="tab:red", s=35)
        ax.set_aspect("equal")
        ax.set_title(srcs.architecture)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True, alpha=0.25)
        ax2 = axes[1, col]
        angles = np.degrees(np.arctan2(srcs.positions[:, 1], srcs.positions[:, 0]))
        ax2.scatter(angles, srcs.positions[:, 2], s=18)
        ax2.axhline(0.0, c="k", lw=0.8)
        ax2.set_xlabel("azimuth angle (deg)")
        ax2.set_ylabel("z")
        ax2.grid(True, alpha=0.25)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_metric_bars(rows: list[dict], path: Path) -> None:
    """Save global/ROI RMSE bars for each architecture and phantom."""

    labels = [f"{r['architecture']}\n{r['phantom']}" for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(max(9, 0.75 * len(rows)), 4.8), constrained_layout=True)
    width = 0.36
    ax.bar(x - width / 2, [r["rmse_global"] for r in rows], width, label="global RMSE")
    ax.bar(x + width / 2, [r["rmse_roi"] for r in rows], width, label="ROI RMSE")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("RMSE")
    ax.set_title("3D rule-baseline reconstruction errors")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_axial_metric_bars(rows: list[dict], path: Path) -> None:
    """Save axial slab RMSE comparison."""

    labels = [f"{r['architecture']}\n{r['phantom']}" for r in rows]
    x = np.arange(len(rows))
    width = 0.25
    fig, ax = plt.subplots(figsize=(max(9, 0.75 * len(rows)), 4.8), constrained_layout=True)
    ax.bar(x - width, [r["rmse_axial_lower"] for r in rows], width, label="lower")
    ax.bar(x, [r["rmse_axial_middle"] for r in rows], width, label="middle")
    ax.bar(x + width, [r["rmse_axial_upper"] for r in rows], width, label="upper")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("axial slab RMSE")
    ax.set_title("Axial reconstruction quality")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_reconstruction_slices(truth: np.ndarray, recon_rows: list[dict], cfg: object, path: Path) -> None:
    """Save central and ROI-near slices for truth/recon pairs."""

    z_mid = cfg.nz // 2
    z_roi = int(np.clip(np.floor((cfg.roi_center[2] + cfg.volume_height / 2.0) / cfg.volume_height * cfg.nz), 0, cfg.nz - 1))
    names = ["truth"] + [r["architecture"] for r in recon_rows]
    imgs_mid = [truth[z_mid]] + [r["recon"][z_mid] for r in recon_rows]
    imgs_roi = [truth[z_roi]] + [r["recon"][z_roi] for r in recon_rows]
    vmax = max(float(np.max(img)) for img in imgs_mid + imgs_roi)
    fig, axes = plt.subplots(2, len(names), figsize=(3.0 * len(names), 6.0), constrained_layout=True)
    for c, name in enumerate(names):
        axes[0, c].imshow(imgs_mid[c], cmap="gray", vmin=0.0, vmax=vmax)
        axes[0, c].set_title(name)
        axes[0, c].set_axis_off()
        axes[1, c].imshow(imgs_roi[c], cmap="gray", vmin=0.0, vmax=vmax)
        axes[1, c].set_axis_off()
    axes[0, 0].set_ylabel("middle z")
    axes[1, 0].set_ylabel("ROI z")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_eig_distribution(rows: list[dict], top_count: int, path: Path) -> None:
    """Save sorted EIG distribution colored by layer count."""

    sorted_rows = sorted(rows, key=lambda r: r["eig_weighted"], reverse=True)
    y = [r["eig_weighted"] for r in sorted_rows]
    layers = [int(r["layer_count"]) for r in sorted_rows]
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    sc = ax.scatter(np.arange(len(y)), y, c=layers, cmap="viridis", s=16)
    ax.axvline(top_count - 0.5, color="tab:red", ls="--", lw=1.2, label=f"top {top_count}")
    ax.set_xlabel("candidate rank by weighted EIG")
    ax.set_ylabel("weighted approximate EIG")
    ax.set_title("3D EIG coarse-screening distribution")
    ax.grid(True, alpha=0.3)
    fig.colorbar(sc, ax=ax, label="layer count")
    ax.legend()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_top_parameter_distributions(rows: list[dict], top_rows: list[dict], path: Path) -> None:
    """Compare all-candidate and EIG-top parameter distributions."""

    params = [
        ("layer_count", "layers"),
        ("radius", "radius"),
        ("z_extent", "z extent"),
        ("angular_offset_fraction", "offset fraction"),
        ("orientation_alpha", "orientation alpha"),
    ]
    fig, axes = plt.subplots(1, len(params), figsize=(4.0 * len(params), 4.2), constrained_layout=True)
    for ax, (key, label) in zip(axes, params, strict=True):
        all_vals = np.asarray([r[key] for r in rows], dtype=float)
        top_vals = np.asarray([r[key] for r in top_rows], dtype=float)
        bins = np.arange(0.5, 5.5, 1.0) if key == "layer_count" else 16
        ax.hist(all_vals, bins=bins, alpha=0.45, label="all")
        ax.hist(top_vals, bins=bins, alpha=0.75, label="EIG top")
        ax.set_title(label)
        ax.grid(True, axis="y", alpha=0.25)
    axes[-1].legend(fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_eig_vs_dprime_plot(rows: list[dict], path: Path) -> None:
    """Save EIG rank versus task-driven d-prime utility comparison."""

    eig_rank = np.asarray([r["eig_rank_within_top"] for r in rows], dtype=float)
    d_rank = np.asarray([r["dprime_rank"] for r in rows], dtype=float)
    utility = np.asarray([r["task_utility_min_dprime"] for r in rows], dtype=float)
    layers = np.asarray([r["layer_count"] for r in rows], dtype=float)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), constrained_layout=True)
    sc = axes[0].scatter(eig_rank, d_rank, c=layers, cmap="viridis", s=42)
    axes[0].plot([1, max(eig_rank)], [1, max(eig_rank)], color="0.55", ls="--", lw=1.0)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("EIG rank within top candidates")
    axes[0].set_ylabel("d-prime maximin rank")
    axes[0].set_title("EIG rank vs task rank")
    axes[0].grid(True, alpha=0.3)
    fig.colorbar(sc, ax=axes[0], label="layer count")

    order = np.argsort(eig_rank)
    axes[1].bar(np.arange(len(rows)), utility[order])
    axes[1].set_xlabel("candidates sorted by EIG rank")
    axes[1].set_ylabel("min task d-prime")
    axes[1].set_title("Task utility after EIG screening")
    axes[1].grid(True, axis="y", alpha=0.3)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_dprime_task_bars(rows: list[dict], task_names: list[str], path: Path, top_n: int = 12) -> None:
    """Save per-task d-prime bars for the best fine-screened candidates."""

    subset = rows[: min(top_n, len(rows))]
    labels = [r["candidate_id"] for r in subset]
    x = np.arange(len(subset))
    width = 0.8 / max(len(task_names), 1)
    fig, ax = plt.subplots(figsize=(max(9, 0.7 * len(subset)), 5.0), constrained_layout=True)
    for i, task in enumerate(task_names):
        vals = [r[f"dprime_{task}"] for r in subset]
        ax.bar(x + (i - (len(task_names) - 1) / 2.0) * width, vals, width, label=task)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("d-prime")
    ax.set_title("Task d-prime values for fine-screened candidates")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_validation_metric_bars(rows: list[dict], path: Path) -> None:
    """Save RMSE and empirical d-prime validation bars."""

    map_rows = [r for r in rows if r["reconstruction"] == "MAP"]
    labels = [f"{r['method']}\n{r['case']}" for r in map_rows]
    x = np.arange(len(map_rows))
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.8), constrained_layout=True)
    for ax, key, title in [
        (axes[0], "rmse_global_mean", "Global RMSE (MAP)"),
        (axes[1], "rmse_roi_mean", "ROI RMSE (MAP)"),
        (axes[2], "empirical_dprime", "Empirical d-prime (MAP)"),
    ]:
        ax.bar(x, [r[key] for r in map_rows])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.3)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_validation_reconstruction_grid(examples: list[dict], cfg: object, path: Path) -> None:
    """Save representative H1 reconstruction slices for validation architectures."""

    methods = list(dict.fromkeys(ex["method"] for ex in examples))
    cases = list(dict.fromkeys(ex["case"] for ex in examples))
    fig, axes = plt.subplots(len(cases) * 2, len(methods) + 1, figsize=(3.0 * (len(methods) + 1), 4.8 * len(cases)), constrained_layout=True)
    axes = np.asarray(axes).reshape(len(cases) * 2, len(methods) + 1)
    for ci, case in enumerate(cases):
        case_examples = [ex for ex in examples if ex["case"] == case]
        truth = case_examples[0]["truth"]
        z = cfg.nz // 2 if "center" in case else int(np.clip(np.floor((cfg.roi_center[2] + cfg.volume_height / 2.0) / cfg.volume_height * cfg.nz), 0, cfg.nz - 1))
        imgs = [truth[z]]
        for method in methods:
            ex = next(e for e in case_examples if e["method"] == method)
            imgs.append(ex["MAP"][z])
        vmax = max(float(np.max(img)) for img in imgs)
        row = ci * 2
        for col, img in enumerate(imgs):
            axes[row, col].imshow(img, cmap="gray", vmin=0.0, vmax=vmax)
            axes[row, col].set_axis_off()
            axes[row, col].set_title("truth" if col == 0 else methods[col - 1], fontsize=9)
        for col, img in enumerate(imgs):
            err = np.abs(img - imgs[0]) if col > 0 else np.zeros_like(img)
            axes[row + 1, col].imshow(err, cmap="magma")
            axes[row + 1, col].set_axis_off()
        axes[row, 0].set_ylabel(f"{case}\nMAP", fontsize=9)
        axes[row + 1, 0].set_ylabel("abs error", fontsize=9)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_selected_architectures_with_tasks(
    sources_by_method: list[tuple[str, object]],
    task_points: list[dict],
    path: Path,
) -> None:
    """Save selected source geometries with task locations marked."""

    n = len(sources_by_method)
    fig, axes = plt.subplots(2, n, figsize=(4.4 * n, 9.6), constrained_layout=False)
    axes = np.asarray(axes).reshape(2, n)
    colors = {
        "center": "black",
        "known_roi": "tab:red",
        "offroi": "tab:purple",
        "high_z": "tab:green",
        "material": "tab:orange",
    }
    markers = {
        "center": "x",
        "known_roi": "o",
        "offroi": "D",
        "high_z": "^",
        "material": "s",
    }
    for col, (method, srcs) in enumerate(sources_by_method):
        ax = axes[0, col]
        ax.scatter(srcs.positions[:, 0], srcs.positions[:, 1], s=16, c="tab:blue", alpha=0.78, label="sources")
        for task in task_points:
            x, y, z = task["point"]
            kind = task.get("kind", "center")
            ax.scatter([x], [y], c=colors.get(kind, "0.2"), marker=markers.get(kind, "o"), s=70, label=task["label"])
        ax.set_title(method)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.25)

        ax2 = axes[1, col]
        angles = np.degrees(np.arctan2(srcs.positions[:, 1], srcs.positions[:, 0]))
        ax2.scatter(angles, srcs.positions[:, 2], s=16, c="tab:blue", alpha=0.78)
        for task in task_points:
            x, y, z = task["point"]
            angle = np.degrees(np.arctan2(y, x))
            kind = task.get("kind", "center")
            ax2.scatter([angle], [z], c=colors.get(kind, "0.2"), marker=markers.get(kind, "o"), s=70)
        ax2.set_xlabel("azimuth angle (deg)")
        ax2.set_ylabel("z")
        ax2.grid(True, alpha=0.25)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles, strict=False))
    fig.subplots_adjust(left=0.055, right=0.985, top=0.90, bottom=0.18, wspace=0.24, hspace=0.30)
    fig.legend(
        by_label.values(),
        by_label.keys(),
        loc="lower center",
        bbox_to_anchor=(0.5, 0.035),
        ncol=min(6, len(by_label)),
        fontsize=9,
        frameon=True,
    )
    fig.savefig(path, dpi=180)
    plt.close(fig)
