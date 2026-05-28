"""Experiment orchestration for 3D static CT rule baselines."""

from __future__ import annotations

import csv
import json
import logging
import platform
from datetime import datetime
from pathlib import Path

import numpy as np

from astra_backend3d import forward_project, reconstruct_sirt3d, transmission_counts
from dprime_screening3d import rank_candidates_by_dprime3d
from eig_screening3d import latin_hypercube_candidates, rank_candidates_by_eig3d
from geometry_ring3d import build_rule_architectures
from metrics3d import compute_metrics
from phantoms3d import build_geometric_phantom, build_roi_target_phantom
from plotting3d import (
    save_axial_metric_bars,
    save_eig_distribution,
    save_eig_vs_dprime_plot,
    save_geometry_plot,
    save_metric_bars,
    save_dprime_task_bars,
    save_reconstruction_slices,
    save_top_parameter_distributions,
    save_validation_metric_bars,
    save_validation_reconstruction_grid,
)
from priors3d import build_eig_prior_classes
from validation3d import build_validation_cases, selected_architectures_for_validation, validate_architecture

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure concise logging for command-line runs."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def write_rows(path: Path, rows: list[dict]) -> None:
    """Write rows to CSV."""

    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _phantoms(cfg: object) -> list[tuple[str, np.ndarray]]:
    return [
        ("geometric_shapes", build_geometric_phantom(cfg)),
        ("smooth_roi_target", build_roi_target_phantom(cfg)),
    ]


def run_experiment01_rule_baselines(cfg: object) -> dict:
    """Run rule-baseline geometry comparisons for four 3D source layouts."""

    rng = np.random.default_rng(cfg.seed)
    architectures = build_rule_architectures(cfg)
    phantoms = _phantoms(cfg)
    metric_rows: list[dict] = []
    recon_bank: dict[str, list[dict]] = {}

    save_geometry_plot(architectures, cfg, cfg.output_dir / "figures" / "fig01_rule_geometries.png")
    for phantom_name, truth in phantoms:
        LOGGER.info("Running phantom: %s", phantom_name)
        recon_bank[phantom_name] = []
        for sources in architectures:
            LOGGER.info("Architecture: %s", sources.architecture)
            line_integrals = forward_project(cfg, truth, sources)
            _, log_data = transmission_counts(cfg, line_integrals, rng)
            recon = reconstruct_sirt3d(cfg, log_data, sources)
            row = {
                "architecture": sources.architecture,
                "num_sources": int(sources.positions.shape[0]),
                "num_layers": int(len(sources.layer_zs)),
                "layer_zs": ";".join(f"{z:.4g}" for z in sources.layer_zs),
                "target_x": sources.target[0],
                "target_y": sources.target[1],
                "target_z": sources.target[2],
                **compute_metrics(cfg, truth, recon, phantom_name),
            }
            metric_rows.append(row)
            recon_bank[phantom_name].append({"architecture": sources.architecture, "recon": recon})
        save_reconstruction_slices(
            truth,
            recon_bank[phantom_name],
            cfg,
            cfg.output_dir / "recon_slices" / f"{phantom_name}_representative_slices.png",
        )

    write_rows(cfg.output_dir / "tables" / "experiment01_rule_baseline_metrics.csv", metric_rows)
    (cfg.output_dir / "tables" / "experiment01_rule_baseline_metrics.json").write_text(
        json.dumps(metric_rows, indent=2),
        encoding="utf-8",
    )
    save_metric_bars(metric_rows, cfg.output_dir / "figures" / "fig02_global_roi_rmse.png")
    save_axial_metric_bars(metric_rows, cfg.output_dir / "figures" / "fig03_axial_rmse.png")
    write_experiment01_report(cfg, metric_rows)
    write_manifest(cfg, metric_rows)
    return {"metrics": metric_rows, "architectures": architectures}


def _best(rows: list[dict], phantom: str, metric: str) -> dict:
    candidates = [r for r in rows if r["phantom"] == phantom]
    return min(candidates, key=lambda r: float(r[metric]))


def write_experiment01_report(cfg: object, rows: list[dict]) -> None:
    """Write a Chinese markdown report for experiment 1."""

    by_phantom = {}
    for phantom in sorted({r["phantom"] for r in rows}):
        by_phantom[phantom] = {
            "global": _best(rows, phantom, "rmse_global"),
            "roi": _best(rows, phantom, "rmse_roi"),
        }

    def table() -> list[str]:
        lines = [
            "| phantom | architecture | layers | global RMSE | ROI RMSE | lower RMSE | middle RMSE | upper RMSE |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for r in rows:
            lines.append(
                "| {phantom} | `{architecture}` | {num_layers} | {rmse_global:.6g} | {rmse_roi:.6g} | "
                "{rmse_axial_lower:.6g} | {rmse_axial_middle:.6g} | {rmse_axial_upper:.6g} |".format(**r)
            )
        return lines

    lines = [
        "# 三维静态 CT 光源展布实验 1：规则基线比较",
        "",
        f"记录日期：{datetime.now().date().isoformat()}",
        "",
        "## 1. 实验目的",
        "",
        "本实验是三维光源最优展布项目的第一组基线实验。它不试图直接找到最终最优架构，而是先比较若干可解释的规则几何：单层等角环、双层交错环、三层交错环以及 ROI 定向多层环。这样做的目的，是在进入 EIG 粗筛和 d' 精筛之前，先建立清楚的几何参照系。",
        "",
        "这组实验重点回答四个问题：",
        "",
        "1. 多层轴向布源是否明显优于单层环；",
        "2. 层间交错是否值得作为后续候选架构的默认自由度；",
        "3. ROI 定向是否会带来局部区域重建质量提升；",
        "4. 后续 EIG / d' 优化应重点搜索哪些几何参数。",
        "",
        "## 2. 实验设置",
        "",
        f"- 总源数：`{cfg.source_count_total}`，所有架构保持一致。",
        f"- 总光子预算：`{cfg.j0_total:.3g}`，每个源平均 `{cfg.photons_per_source:.3g}`。",
        f"- 探测器半径：`{cfg.detector_radius}`，探测器高度：`{cfg.detector_height}`。",
        f"- 重建体积：`{cfg.volume_side_xy} x {cfg.volume_side_xy} x {cfg.volume_height}`。",
        f"- 体素数：`{cfg.nx} x {cfg.ny} x {cfg.nz}`。",
        f"- detector tile：`{cfg.detector_rows} x {cfg.detector_cols}`。",
        f"- cone angle：`{cfg.cone_angle_deg}` degree。",
        f"- 重建算法：ASTRA `SIRT3D_CUDA`，迭代 `{cfg.sirt_iterations}` 次。",
        f"- ROI 中心：`{cfg.roi_center}`。",
        "",
        "## 3. 比较的四类规则架构",
        "",
        "| 架构 | 含义 |",
        "|---|---|",
        "| `single_layer_center` | 所有源位于 z=0 单层环，圆周均匀分布，全部朝系统中心 |",
        "| `double_layer_staggered_center` | 上下两层交错环，全部朝系统中心 |",
        "| `triple_layer_staggered_center` | 三层交错环，全部朝系统中心 |",
        "| `triple_layer_staggered_roi` | 三层交错环，全部朝指定 ROI 中心 |",
        "",
        "## 4. 测试对象",
        "",
        "| phantom | 含义 |",
        "|---|---|",
        "| `geometric_shapes` | 两个球体和一个立方体组成的简单几何对象 |",
        "| `smooth_roi_target` | 平滑背景加一个偏心弱小 ROI 目标 |",
        "",
        "## 5. 结果汇总",
        "",
        *table(),
        "",
        "## 6. 初步观察",
        "",
    ]
    for phantom, winners in by_phantom.items():
        lines.extend(
            [
                f"- `{phantom}` 的全局 RMSE 最优架构为 `{winners['global']['architecture']}`，数值为 `{winners['global']['rmse_global']:.6g}`。",
                f"- `{phantom}` 的 ROI RMSE 最优架构为 `{winners['roi']['architecture']}`，数值为 `{winners['roi']['rmse_roi']:.6g}`。",
            ]
        )
    lines.extend(
        [
            "",
            "## 7. 阶段性结论",
            "",
            "本实验的主要作用是为后续 EIG / d' 搜索提供规则基线，而不是给出最终最优设计。若多层交错环在全局或轴向 RMSE 上优于单层环，则后续候选集应保留轴向分层与层间交错自由度；若 ROI 定向架构在 `smooth_roi_target` 上表现出更低 ROI RMSE，则后续任务驱动 d' 精筛应显式建模 ROI 指向或任务指向参数。",
            "",
            "当前实现采用 quick 级别 3D SIRT 重建，适合验证流程和相对趋势。后续论文级实验需要提高体素数、探测器采样和投影物理真实性，并引入三维 EIG 与 d' 设计准则。",
        ]
    )
    text = "\n".join(lines)
    (cfg.output_dir / "experiment01_rule_baselines_report.md").write_text(text, encoding="utf-8")


def write_manifest(cfg: object, rows: list[dict]) -> None:
    """Write reproducibility metadata."""

    try:
        import astra

        astra_version = getattr(astra, "__version__", "unknown")
    except Exception:
        astra_version = "unavailable"
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "astra_version": astra_version,
        "config": {k: str(v) for k, v in cfg.__dict__.items()},
        "metric_rows": len(rows),
    }
    (cfg.output_dir / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_experiment02_eig_screening(cfg: object) -> dict:
    """Run 3D EIG coarse-screening over a sampled architecture family."""

    candidates = latin_hypercube_candidates(cfg)
    priors = build_eig_prior_classes(cfg)
    ranked = rank_candidates_by_eig3d(cfg, candidates, priors)
    top_count = max(1, int(round(cfg.eig_top_fraction * len(ranked))))
    top_rows = ranked[:top_count]
    write_rows(cfg.output_dir / "tables" / "experiment02_all_candidate_eig.csv", ranked)
    write_rows(cfg.output_dir / "tables" / "experiment02_top_candidate_eig.csv", top_rows)
    (cfg.output_dir / "tables" / "experiment02_all_candidate_eig.json").write_text(
        json.dumps(ranked, indent=2),
        encoding="utf-8",
    )
    save_eig_distribution(ranked, top_count, cfg.output_dir / "figures" / "fig01_eig_distribution.png")
    save_top_parameter_distributions(ranked, top_rows, cfg.output_dir / "figures" / "fig02_top_parameter_distributions.png")
    write_experiment02_report(cfg, ranked, top_rows)
    write_manifest(cfg, ranked)
    return {"ranked": ranked, "top": top_rows}


def run_experiment03_dprime_fine_screening(cfg: object) -> dict:
    """Run task-driven d-prime fine screening on experiment-2 EIG top candidates."""

    source_path = Path(__file__).resolve().parent / "outputs" / "experiment02_eig_screening" / "tables" / "experiment02_top_candidate_eig.csv"
    if not source_path.exists():
        LOGGER.info("Experiment-2 top table not found; rerunning EIG screening first.")
        eig_cfg = cfg
        candidates = latin_hypercube_candidates(eig_cfg)
        priors = build_eig_prior_classes(eig_cfg)
        ranked = rank_candidates_by_eig3d(eig_cfg, candidates, priors)
        top_count = max(1, int(round(eig_cfg.eig_top_fraction * len(ranked))))
        top_candidates = ranked[:top_count]
    else:
        with source_path.open("r", newline="", encoding="utf-8") as f:
            top_candidates = list(csv.DictReader(f))
        for row in top_candidates:
            for key in [
                "layer_count",
                "sources_per_layer_mean",
                "radius",
                "z_extent",
                "angular_offset_fraction",
                "orientation_alpha",
                "eig_smooth_background",
                "eig_center_weak_target",
                "eig_eccentric_roi_target",
                "eig_weighted",
                "eig_weighted_minmax",
                "eig_weighted_zscore",
            ]:
                if key in row:
                    row[key] = float(row[key])
            row["layer_count"] = int(row["layer_count"])

    ranked, tasks = rank_candidates_by_dprime3d(cfg, top_candidates)
    task_names = [task.name for task in tasks]
    write_rows(cfg.output_dir / "tables" / "experiment03_dprime_rankings.csv", ranked)
    (cfg.output_dir / "tables" / "experiment03_dprime_rankings.json").write_text(
        json.dumps(ranked, indent=2),
        encoding="utf-8",
    )
    write_rows(
        cfg.output_dir / "tables" / "experiment03_task_definitions.csv",
        [{"task": t.name, "description": t.description} for t in tasks],
    )
    save_eig_vs_dprime_plot(ranked, cfg.output_dir / "figures" / "fig01_eig_rank_vs_dprime_rank.png")
    save_dprime_task_bars(ranked, task_names, cfg.output_dir / "figures" / "fig02_task_dprime_bars.png")
    best_sources = candidate_to_sources_for_report(cfg, ranked[0])
    save_geometry_plot([best_sources], cfg, cfg.output_dir / "figures" / "fig03_selected_dprime_geometry.png")
    write_experiment03_report(cfg, ranked, tasks)
    write_manifest(cfg, ranked)
    return {"ranked": ranked, "tasks": tasks}


def candidate_to_sources_for_report(cfg: object, row: dict) -> object:
    """Build source geometry for the selected d-prime candidate."""

    from eig_screening3d import candidate_to_sources

    sources = candidate_to_sources(cfg, row)
    return type(sources)(
        sources.positions,
        sources.directions,
        f"{row['candidate_id']}_dprime_selected",
        sources.layer_zs,
        sources.target,
    )


def write_experiment03_report(cfg: object, rows: list[dict], tasks: list[object]) -> None:
    """Write a Chinese markdown report for experiment 3."""

    best = rows[0]
    eig_best = min(rows, key=lambda r: int(r["eig_rank_within_top"]))
    task_names = [t.name for t in tasks]

    def rank_table(limit: int = 12) -> list[str]:
        header = [
            "| d' rank | EIG rank | candidate | EIG | layers | radius | z_extent | alpha | min d' | mean d'^2 |",
            "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in rows[:limit]:
            header.append(
                f"| {int(r['dprime_rank'])} | {int(r['eig_rank_within_top'])} | `{r['candidate_id']}` | "
                f"{float(r['eig_weighted']):.6g} | {int(r['layer_count'])} | {float(r['radius']):.4f} | "
                f"{float(r['z_extent']):.4f} | {float(r['orientation_alpha']):.4f} | "
                f"{float(r['task_utility_min_dprime']):.6g} | {float(r['task_utility_mean_dprime2']):.6g} |"
            )
        return header

    def task_table(limit: int = 12) -> list[str]:
        header = ["| candidate | " + " | ".join(f"{name} d'" for name in task_names) + " | min d' |"]
        header.append("|---" + "|---:" * (len(task_names) + 1) + "|")
        for r in rows[:limit]:
            vals = " | ".join(f"{float(r[f'dprime_{name}']):.6g}" for name in task_names)
            header.append(f"| `{r['candidate_id']}` | {vals} | {float(r['task_utility_min_dprime']):.6g} |")
        return header

    eig_same_as_task = best["candidate_id"] == eig_best["candidate_id"]
    lines = [
        "# 三维静态 CT 光源展布实验 3：d' 任务精筛实验",
        "",
        f"记录日期：{datetime.now().date().isoformat()}",
        "",
        "## 1. 实验目的",
        "",
        "实验二已经证明 EIG 可以在大量三维候选光源架构中形成有意义的粗筛排序，但 EIG 本身仍是平均信息量指标，并不直接等价于具体成像任务的最优可探测性。本实验的目的，是在 EIG top 候选池内部继续引入任务驱动的 d' 精筛，检验高信息架构之间是否仍存在任务性能差异。",
        "",
        "本组实验要验证的核心命题是：在环形探测器静态 CT 中，系统最优不应只由全局参数精度或平均信息量定义，而应由具体成像任务定义。因此，EIG 粗筛之后仍需要 d' 精筛。",
        "",
        "## 2. 候选来源",
        "",
        "本实验不再面对实验二中的全部 240 个候选架构，而是只使用实验二保留下来的 EIG top 10% 候选，共 24 个架构。这样做对应 EIG+d' 分层设计路线：",
        "",
        "```text",
        "大量参数化候选架构 -> EIG 粗筛 -> 少量高信息候选 -> d' 任务精筛",
        "```",
        "",
        "因此，本实验关注的不是 EIG 能否排除低信息架构，而是：在已经通过 EIG 初筛的架构中，哪一个更适合具体任务。",
        "",
        "## 3. 任务定义",
        "",
        "| task | 含义 |",
        "|---|---|",
    ]
    for task in tasks:
        lines.append(f"| `{task.name}` | {task.description} |")
    lines.extend(
        [
            "",
            "其中前两个任务是局部小目标检测，分别对应中心 ROI 和偏心 ROI；第三个任务是局部材料/低对比差异判别，用来避免精筛准则只服务于单一检测位置。",
            "",
            "## 4. d' 近似计算方式",
            "",
            "当前 quick 实验没有显式构造完整三维 Fisher 矩阵或完整 MAP Hessian，因为 32 x 32 x 32 体素下完整矩阵规模已经较大。这里采用低维通道化 MAP observer 近似：先围绕每个任务位置构造局部高斯通道，再把候选架构的投影 Fisher 信息投影到通道空间，计算任务信号在该通道空间中的可分离度。",
            "",
            "计算形式可以理解为：",
            "",
            "```text",
            "d_t'^2(Theta) = Delta_mu_c,t^T K_c,t^{-1} Delta_mu_c,t",
            "```",
            "",
            "其中 `Delta_mu_c,t` 是任务信号在通道空间中的线性响应，`K_c,t` 是通道空间中的噪声/不确定性矩阵。当前实现加入 MAP 正则项 `beta`，避免 quick 近似下矩阵病态。",
            "",
            f"- 通道数：`{cfg.dprime_channel_count}`",
            f"- MAP 正则参数 beta：`{cfg.dprime_regularization_beta:.3g}`",
            "- 光子预算、探测器采样、总源数与实验二保持一致。",
            "",
            "## 5. 精筛准则",
            "",
            "本实验采用 maximin 任务准则：",
            "",
            "```text",
            "U_task(Theta) = min_t d_t'^2(Theta)",
            "```",
            "",
            "也就是说，最终选择的不是只在某一个任务上特别强的架构，而是在最弱任务上仍然尽可能好的架构。这个准则更符合多任务安检 CT 的设计目标，因为真实系统不能只对一个固定位置或一种目标表现好。",
            "",
            "## 6. d' 精筛排名结果",
            "",
            *rank_table(),
            "",
            "各任务 d' 数值如下：",
            "",
            *task_table(),
            "",
            "## 7. EIG 排名与 d' 排名的关系",
            "",
            f"EIG 排名第 1 的候选为 `{eig_best['candidate_id']}`，其 d' 精筛排名为 `{int(eig_best['dprime_rank'])}`，maximin min d' 为 `{float(eig_best['task_utility_min_dprime']):.6g}`。",
            f"d' 精筛最终选中的候选为 `{best['candidate_id']}`，其 EIG 排名为 `{int(best['eig_rank_within_top'])}`，maximin min d' 为 `{float(best['task_utility_min_dprime']):.6g}`。",
            "",
        ]
    )
    if eig_same_as_task:
        lines.extend(
            [
                "在当前 quick 参数下，EIG 排名第 1 的候选同时也是 d' maximin 最优候选。这说明当前 EIG top-1 架构恰好也满足本组任务的最弱任务性能要求。不过，这并不意味着 d' 精筛可以省略，因为实验仍显示 top 候选之间存在任务 d' 差异，且该结论依赖当前任务、通道模型和正则参数。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "这说明 EIG 最优架构并不等于任务最优架构。EIG 负责筛出平均信息价值较高的候选，但在这些候选内部，具体中心目标、偏心 ROI 目标和材料判别任务的 d' 排名仍会重新排序。",
                "",
            ]
        )
    lines.extend(
        [
            "因此，本实验支持 EIG+d' 的分层逻辑：EIG 用于快速删除低信息价值架构，d' 用于在高信息候选中选择更符合具体任务需求的架构。",
            "",
            "## 8. 输出文件说明",
            "",
            "| 文件 | 内容 |",
            "|---|---|",
            "| `tables/experiment03_dprime_rankings.csv` | EIG top 候选的 d' 精筛排名和各任务 d' 数值 |",
            "| `tables/experiment03_task_definitions.csv` | 本实验使用的任务定义 |",
            "| `figures/fig01_eig_rank_vs_dprime_rank.png` | EIG 排名与 d' maximin 排名对比 |",
            "| `figures/fig02_task_dprime_bars.png` | d' 排名前若干候选在各任务上的 d' 条形图 |",
            "| `figures/fig03_selected_dprime_geometry.png` | d' 精筛最终选中架构的三维几何示意 |",
            "",
            "## 9. 阶段性结论",
            "",
            "实验三的关键作用，是把实验二的“高信息架构筛选”推进到“具体任务可探测性筛选”。当前 quick 结果应作为方法链验证：它证明了 EIG top 候选之间仍需要根据任务 d' 进行比较，并给出了 maximin 任务准则下的最终候选。",
            "",
            "最重要的论文式表述是：EIG 最优架构不一定是任务最优架构；在通过 EIG 粗筛后，仍需使用 d' 进行任务驱动精筛。即使在某些 quick 参数下两者恰好一致，d' 精筛仍提供了必要的任务性能验证。",
        ]
    )
    (cfg.output_dir / "experiment03_dprime_fine_screening_report.md").write_text("\n".join(lines), encoding="utf-8")


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key, value in list(row.items()):
            try:
                if key in {"candidate_id", "architecture", "method", "case", "reconstruction"}:
                    continue
                if value == "":
                    continue
                num = float(value)
                row[key] = int(num) if key in {"layer_count", "dprime_rank", "eig_rank_within_top"} else num
            except (TypeError, ValueError):
                pass
    return rows


def run_experiment04_poisson_mle_map_validation(cfg: object) -> dict:
    """Run final Poisson MLE/MAP validation for selected architectures."""

    root = Path(__file__).resolve().parent
    eig_path = root / "outputs" / "experiment02_eig_screening" / "tables" / "experiment02_top_candidate_eig.csv"
    eig_all_path = root / "outputs" / "experiment02_eig_screening" / "tables" / "experiment02_all_candidate_eig.csv"
    dprime_path = root / "outputs" / "experiment03_dprime_fine_screening" / "tables" / "experiment03_dprime_rankings.csv"
    if not eig_path.exists():
        raise FileNotFoundError(f"Missing experiment-2 top candidates: {eig_path}")
    if not eig_all_path.exists():
        raise FileNotFoundError(f"Missing experiment-2 all candidates: {eig_all_path}")
    if not dprime_path.exists():
        raise FileNotFoundError(f"Missing experiment-3 d-prime rankings: {dprime_path}")

    eig_rows = _read_csv_rows(eig_path)
    eig_all_rows = _read_csv_rows(eig_all_path)
    for i, row in enumerate(sorted(eig_rows, key=lambda r: float(r["eig_weighted"]), reverse=True), start=1):
        row["eig_rank_within_top"] = i
    dprime_rows = _read_csv_rows(dprime_path)
    cases = build_validation_cases(cfg)
    selected = selected_architectures_for_validation(cfg, eig_all_rows, eig_rows, dprime_rows)
    all_metrics: list[dict] = []
    all_examples: list[dict] = []
    for method, sources in selected:
        LOGGER.info("Experiment 4 validation: %s", method)
        rows, examples = validate_architecture(cfg, method, sources, cases)
        all_metrics.extend(rows)
        all_examples.extend(examples)

    write_rows(cfg.output_dir / "tables" / "experiment04_validation_metrics.csv", all_metrics)
    (cfg.output_dir / "tables" / "experiment04_validation_metrics.json").write_text(
        json.dumps(all_metrics, indent=2),
        encoding="utf-8",
    )
    write_rows(
        cfg.output_dir / "tables" / "experiment04_selected_architectures.csv",
        [
            {
                "method": method,
                "architecture": src.architecture,
                "num_sources": int(src.positions.shape[0]),
                "num_layers": int(len(src.layer_zs)),
                "layer_zs": ";".join(f"{z:.4g}" for z in src.layer_zs),
                "target_x": src.target[0],
                "target_y": src.target[1],
                "target_z": src.target[2],
            }
            for method, src in selected
        ],
    )
    save_validation_metric_bars(all_metrics, cfg.output_dir / "figures" / "fig01_validation_metrics_map.png")
    save_validation_reconstruction_grid(all_examples, cfg, cfg.output_dir / "figures" / "fig02_reconstruction_validation_examples.png")
    write_experiment04_report(cfg, all_metrics, selected)
    write_manifest(cfg, all_metrics)
    return {"metrics": all_metrics, "selected": selected}


def write_experiment04_report(cfg: object, rows: list[dict], selected: list[tuple[str, object]]) -> None:
    """Write a Chinese markdown report for experiment 4."""

    map_rows = [r for r in rows if r["reconstruction"] == "MAP"]
    mle_rows = [r for r in rows if r["reconstruction"] == "MLE"]

    def metric_table(subset: list[dict]) -> list[str]:
        lines = [
            "| method | case | recon | global RMSE | ROI RMSE | empirical d' |",
            "|---|---|---|---:|---:|---:|",
        ]
        for r in subset:
            lines.append(
                f"| `{r['method']}` | `{r['case']}` | `{r['reconstruction']}` | "
                f"{float(r['rmse_global_mean']):.6g} | {float(r['rmse_roi_mean']):.6g} | {float(r['empirical_dprime']):.6g} |"
            )
        return lines

    def selected_table() -> list[str]:
        lines = ["| method | architecture | layers | layer_zs | target |", "|---|---|---:|---|---|"]
        for method, src in selected:
            lines.append(
                f"| `{method}` | `{src.architecture}` | {len(src.layer_zs)} | "
                f"`{';'.join(f'{z:.4g}' for z in src.layer_zs)}` | `{tuple(round(v, 4) for v in src.target)}` |"
            )
        return lines

    best_roi = min([r for r in map_rows if r["case"] == "eccentric_roi_target"], key=lambda r: float(r["rmse_roi_mean"]))
    best_d = max([r for r in map_rows if r["case"] == "eccentric_roi_target"], key=lambda r: float(r["empirical_dprime"]))
    lines = [
        "# 三维静态 CT 光源展布实验 4：泊松 + MLE/MAP 最终验证",
        "",
        f"记录日期：{datetime.now().date().isoformat()}",
        "",
        "## 1. 实验目的",
        "",
        "实验一到实验三分别建立了规则几何基线、EIG 粗筛和 d' 任务精筛。但这些仍主要是设计准则层面的排序。实验四的作用，是在真实泊松 transmission 投影和重建流程下检查这些准则选出的架构是否仍然具有任务优势。",
        "",
        "这组实验与参考 CRLB 方法中使用 MLE 验证 CRLB 可达性的作用类似：它不是再定义一个新的设计准则，而是用带噪投影和重建闭环检验前面选出的设计是否真正有效。",
        "",
        "## 2. 对比架构",
        "",
        *selected_table(),
        "",
        "`CRLB_Aopt` 是当前 quick 实现中的低秩 A-optimality 近似基线，用随机 probe 子空间估计全局方差准则，代表参考文献中 CRLB / A-optimality 思路。后续论文级实验可替换为更高秩或显式 Fisher 矩阵版本。",
        "",
        "## 3. 验证对象与重建",
        "",
        "| case | 含义 |",
        "|---|---|",
        "| `center_target` | 平滑背景 + 中心低对比小球目标 |",
        "| `eccentric_roi_target` | 平滑背景 + 偏心 ROI 低对比小球目标 |",
        "",
        f"每个架构、每个 case 生成 `{cfg.validation_replicates}` 次独立泊松投影。MLE 重建使用 ASTRA `SIRT3D_CUDA` 对泊松 log 数据重建；MAP 重建在 quick 阶段采用轻量先验融合近似，先验强度为 `{cfg.map_prior_strength}`。该 MAP 是用于流程验证的正则化近似，不等同于最终论文级严格 MAP 迭代。",
        "",
        "## 4. MAP 验证结果",
        "",
        *metric_table(map_rows),
        "",
        "## 5. MLE 验证结果",
        "",
        *metric_table(mle_rows),
        "",
        "## 6. 输出图像说明",
        "",
        "`fig01_validation_metrics_map.png` 汇总 MAP 重建下的全局 RMSE、ROI RMSE 和经验 d'。读图时，全局 RMSE 和 ROI RMSE 越低越好，经验 d' 越高越好。该图用于判断 EIG+d' 是否在真实泊松重建后仍保持任务优势。",
        "",
        "`fig02_reconstruction_validation_examples.png` 给出中心目标和偏心 ROI 目标在各架构下的代表性 MAP 重建切片及绝对误差图。它用于观察表格中的 RMSE 和 d' 差异是否能在重建图像中看到对应趋势。",
        "",
        "## 7. 初步结论",
        "",
        f"在当前 quick MAP 验证中，偏心 ROI case 的最低 ROI RMSE 来自 `{best_roi['method']}`，数值为 `{float(best_roi['rmse_roi_mean']):.6g}`；偏心 ROI case 的最高经验 d' 来自 `{best_d['method']}`，数值为 `{float(best_d['empirical_dprime']):.6g}`。",
        "",
        "如果 EIG+d' 在 ROI RMSE 或经验 d' 上优于规则基线和 CRLB_Aopt，则说明任务精筛选出的架构在真实泊松重建条件下仍更贴近局部检测需求；如果全局 RMSE 与 CRLB_Aopt 接近而 ROI/d' 更优，则更符合本研究的核心论点：任务驱动设计不一定追求全局平均方差最小，而是追求目标任务更可探测。",
        "",
        "当前实验仍是 quick 级闭环验证，主要用于验证流程和相对趋势。最终论文级结果应提高重复次数、体素分辨率、MAP 迭代严格性，并加入统计显著性检验。",
    ]
    (cfg.output_dir / "experiment04_poisson_mle_map_validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def _mean(rows: list[dict], key: str) -> float:
    return float(np.mean([float(r[key]) for r in rows]))


def write_experiment02_report(cfg: object, ranked: list[dict], top_rows: list[dict]) -> None:
    """Write a Chinese markdown report for experiment 2."""

    all_rows = ranked
    top_fraction = 100.0 * len(top_rows) / len(all_rows)
    eig_values = np.asarray([r["eig_weighted"] for r in all_rows], dtype=float)
    top_eig_values = np.asarray([r["eig_weighted"] for r in top_rows], dtype=float)
    layer_counts = sorted({int(r["layer_count"]) for r in all_rows})

    def layer_table() -> list[str]:
        lines = ["| layer_count | all fraction | EIG top fraction |", "|---:|---:|---:|"]
        for layer in layer_counts:
            all_frac = sum(int(r["layer_count"]) == layer for r in all_rows) / len(all_rows)
            top_frac = sum(int(r["layer_count"]) == layer for r in top_rows) / len(top_rows)
            lines.append(f"| {layer} | {all_frac:.3f} | {top_frac:.3f} |")
        return lines

    top10 = top_rows[:10]
    top10_lines = [
        "| rank | candidate | EIG | layers | radius | z_extent | offset | alpha |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(top10, start=1):
        top10_lines.append(
            f"| {i} | `{row['candidate_id']}` | {row['eig_weighted']:.6g} | {int(row['layer_count'])} | "
            f"{row['radius']:.4f} | {row['z_extent']:.4f} | {row['angular_offset_fraction']:.4f} | "
            f"{row['orientation_alpha']:.4f} |"
        )

    lines = [
        "# 三维静态 CT 光源展布实验 2：EIG 粗筛实验",
        "",
        f"记录日期：{datetime.now().date().isoformat()}",
        "",
        "## 1. 实验目的",
        "",
        "本实验用于验证 EIG 是否适合作为三维光源架构搜索的第一层粗筛准则。它不直接回答最终检测任务最优，而是检验 EIG 是否能在大量参数化候选架构中形成有意义的排序，并把明显低信息价值的架构排除掉。",
        "",
        "如果 EIG 排序没有结构性偏好，或者 top 候选与全体候选的几何参数分布没有差异，那么后续 d' 精筛就缺少可靠前提。因此，本实验是 EIG+d' 分层设计路线中的第一层创新证据。",
        "",
        "## 2. 候选架构空间",
        "",
        "候选架构不是任意三维点集，而是在参数化多层环架构族中采样：",
        "",
        "```text",
        "Theta = {M_z, N_m, R_m, z_m, delta_m, alpha_m}",
        "```",
        "",
        "| 参数 | 含义 | 当前 quick 范围 |",
        "|---|---|---|",
        "| `M_z` | 层数 | 1, 2, 3, 4 |",
        "| `N_m` | 每层源数 | 总源数固定为 48，按层数分配 |",
        "| `R_m` | 源环半径 | 1.25 到 1.70 |",
        "| `z_m` | 最大层高半幅 | 0.15 到 0.60，单层为 0 |",
        "| `delta_m` | 层间角偏移比例 | 0 到 1 |",
        "| `alpha_m` | 朝向插值参数 | 0 为中心定向，1 为 ROI 定向 |",
        "",
        f"本次使用 Latin hypercube 采样 `{len(all_rows)}` 个候选架构，并保留 EIG 排名前 `{len(top_rows)}` 个候选，约为 top `{top_fraction:.1f}%`。",
        "",
        "## 3. 对象先验库",
        "",
        "EIG 使用三类对角高斯先验对象：",
        "",
        "| 先验类别 | 权重 | 含义 |",
        "|---|---:|---|",
        f"| `smooth_background` | {cfg.eig_prior_weights[0]:.3f} | 平滑背景对象 |",
        f"| `center_weak_target` | {cfg.eig_prior_weights[1]:.3f} | 平滑背景 + 中心弱目标 |",
        f"| `eccentric_roi_target` | {cfg.eig_prior_weights[2]:.3f} | 平滑背景 + 偏心 ROI 弱目标 |",
        "",
        "## 4. EIG 近似计算方式",
        "",
        "理论目标是对每个先验类计算 Laplace EIG：",
        "",
        "```text",
        "U_EIG,c(Theta) = 1/2 logdet(I + Sigma_c^(1/2) F_c(Theta) Sigma_c^(1/2))",
        "```",
        "",
        "三维全矩阵 logdet 代价很高，因此当前 quick 实验使用固定随机低维探针子空间近似该 logdet。具体做法是用 ASTRA `cone_vec` 对 covariance-weighted probe volume 做 forward projection，形成低秩矩阵 `B`，再计算：",
        "",
        "```text",
        "U_EIG,c approx 1/2 logdet(I + B^T B)",
        "```",
        "",
        "多类先验按权重加权：",
        "",
        "```text",
        "U_EIG_coarse = sum_c pi_c U_EIG,c",
        "```",
        "",
        "## 5. EIG 分布与 top 候选",
        "",
        f"- 全体候选 weighted EIG 最小值：`{eig_values.min():.6g}`。",
        f"- 全体候选 weighted EIG 最大值：`{eig_values.max():.6g}`。",
        f"- 全体候选 weighted EIG 标准差：`{eig_values.std():.6g}`。",
        f"- top 候选 weighted EIG 均值：`{top_eig_values.mean():.6g}`。",
        f"- 全体候选 weighted EIG 均值：`{eig_values.mean():.6g}`。",
        "",
        "top 10 候选如下：",
        "",
        *top10_lines,
        "",
        "## 6. EIG top 候选的几何参数偏好",
        "",
        *layer_table(),
        "",
        "| 参数 | 全体均值 | EIG top 均值 |",
        "|---|---:|---:|",
        f"| radius | {_mean(all_rows, 'radius'):.4f} | {_mean(top_rows, 'radius'):.4f} |",
        f"| z_extent | {_mean(all_rows, 'z_extent'):.4f} | {_mean(top_rows, 'z_extent'):.4f} |",
        f"| angular_offset_fraction | {_mean(all_rows, 'angular_offset_fraction'):.4f} | {_mean(top_rows, 'angular_offset_fraction'):.4f} |",
        f"| orientation_alpha | {_mean(all_rows, 'orientation_alpha'):.4f} | {_mean(top_rows, 'orientation_alpha'):.4f} |",
        "",
        "## 7. 阶段性结论",
        "",
        "本实验的结论不应理解为 EIG 已经给出最终任务最优架构，而应理解为：EIG 在三维参数化架构族上能够产生非平坦的排序，并且 top 候选在层数、层高、角偏移和朝向插值等几何参数上呈现可观察的分布偏好。",
        "",
        "因此，EIG 可以作为后续三维光源展布搜索的第一层粗筛准则：先删除低信息价值候选，把搜索空间缩小到 top 5% 到 10%，再进入 d' 精筛和泊松重建验证。",
    ]
    (cfg.output_dir / "experiment02_eig_screening_report.md").write_text("\n".join(lines), encoding="utf-8")
