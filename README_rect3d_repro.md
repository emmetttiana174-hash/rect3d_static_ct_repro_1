# ASTRA 三维静态 CT 光源最优展布工程

本目录用于三维静态 CT 光源最优展布复现实验和后续 EIG + d' 方法开发。

当前第一阶段实现：

```text
实验 1：规则基线比较
```

该实验比较四类可解释规则架构：

1. 单层等角环，全部朝中心；
2. 双层交错环，全部朝中心；
3. 三层交错环，全部朝中心；
4. 三层交错环，全部朝 ROI 中心。

运行命令：

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment01_rule_baselines.py
```

输出目录：

```text
outputs/experiment01_rule_baselines/
```

主要输出：

```text
tables/experiment01_rule_baseline_metrics.csv
tables/experiment01_rule_baseline_metrics.json
figures/fig01_rule_geometries.png
figures/fig02_global_roi_rmse.png
figures/fig03_axial_rmse.png
recon_slices/geometric_shapes_representative_slices.png
recon_slices/smooth_roi_target_representative_slices.png
experiment01_rule_baselines_report.md
manifest.json
```

当前实现说明：

- ASTRA 几何使用 `cone_vec`；
- 每个源对应一个朝向系统中心或 ROI 的虚拟平板 detector tile；
- 重建使用 ASTRA `SIRT3D_CUDA`；
- 第一阶段以 quick mode 验证几何趋势和工程闭环为主。

## 实验 2：EIG 粗筛实验

该实验在参数化三维多层环架构族中采样候选，并使用 Laplace EIG 的低秩随机探针近似进行粗筛排序。

运行命令：

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment02_eig_screening.py
```

输出目录：

```text
outputs/experiment02_eig_screening/
```

主要输出：

```text
tables/experiment02_all_candidate_eig.csv
tables/experiment02_top_candidate_eig.csv
figures/fig01_eig_distribution.png
figures/fig02_top_parameter_distributions.png
experiment02_eig_screening_report.md
manifest.json
```

当前 quick 实现说明：

- 候选架构参数包括层数、半径、层高、层间角偏移和中心/ROI 朝向插值。
- 对象先验包括平滑背景、中心弱目标和偏心 ROI 弱目标。
- 三维完整 FIM 的 logdet 不直接显式构造，而是在固定随机低维 probe 子空间中近似 `0.5 logdet(I + Sigma^(1/2) F Sigma^(1/2))`。
