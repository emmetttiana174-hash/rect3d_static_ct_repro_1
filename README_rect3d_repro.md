# 三维静态 CT 光源最优展布复现实验项目

更新日期：2026-05-30

## 1. 项目定位

本项目用于复现和扩展三维环形静态 CT 光源最优展布实验。它承接二维项目 `rect2d_static_ct_repro` 中的 EIG+d' 与 CRLB/A-optimality 对比逻辑，将研究对象从二维四边探测器几何推进到三维多层环形源/探测器几何。

项目核心问题不是证明 EIG+d' 在所有指标上全面优于 CRLB，而是检验：

```text
CRLB / A-optimality 的最优性依赖其评价目标；
全局或固定 ROI 方差最优，不一定等价于所有局部检测任务最优；
EIG 粗筛 + d' 精筛可以把“对象先验”和“具体任务目标”解耦。
```

当前代码属于 quick-mode 方法链验证，适合用于理解实验逻辑、筛查方法趋势、准备后续 SCI 论文级实验。正式论文实验前还需要提高重建分辨率、泊松重复次数、MAP 严格性和统计显著性检验强度。

## 2. 路径与运行环境

项目根目录：

```text
D:\Astra-toolbox\astra-toolbox-2.4.1-python313-win-x64\astra-2.4.1\rect3d_static_ct_repro
```

推荐 Python：

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe
```

主要依赖：

- ASTRA Toolbox 2.4.1
- NumPy
- SciPy
- Pandas
- Matplotlib

当前几何与重建使用 ASTRA `cone_vec` 和 `SIRT3D_CUDA`。实验默认体素规模为 `32 x 32 x 32`，用于快速验证。

## 3. 代码结构

| 文件 | 作用 |
|---|---|
| `config.py` | 所有实验配置入口，包括几何尺寸、源数、EIG/d' 参数、输出目录 |
| `geometry_ring3d.py` | 三维多层环形光源几何、朝向插值、ASTRA `cone_vec` 生成 |
| `astra_backend3d.py` | ASTRA 3D forward projection、SIRT3D_CUDA 重建、泊松 transmission 数据 |
| `phantoms3d.py` | 三维几何 phantom、平滑背景、ROI mask、轴向 slab mask |
| `priors3d.py` | EIG 使用的三类对角高斯先验：背景、中心目标、偏心 ROI 目标 |
| `eig_screening3d.py` | Latin hypercube 候选采样与低秩 Laplace EIG 粗筛 |
| `dprime_screening3d.py` | 任务定义、低维 MAP-CHO d' 近似、maximin d' 精筛 |
| `validation3d.py` | 泊松 MLE/MAP quick 验证、CRLB/A-opt quick 基线、验证 case |
| `metrics3d.py` | 全局 RMSE、ROI RMSE、轴向 RMSE |
| `plotting3d.py` | 实验图像输出，包括几何、EIG 分布、d' 排名、重建图和任务标记图 |
| `experiments3d.py` | 五组实验的总编排与报告生成 |
| `run_experiment01_rule_baselines.py` | 实验一入口 |
| `run_experiment02_eig_screening.py` | 实验二入口 |
| `run_experiment03_dprime_fine_screening.py` | 实验三入口 |
| `run_experiment04_poisson_mle_map_validation.py` | 实验四入口 |
| `run_experiment05_offroi_prior_shift.py` | 实验五入口 |

## 4. 方法链

当前项目实现的三维 EIG+d' 分层设计路线为：

```text
参数化三维多层环候选架构
        ↓
EIG 粗筛：基于可获得对象先验，保留高信息候选
        ↓
d' 精筛：基于具体任务目标，在 EIG top 候选中选择任务最优架构
        ↓
泊松投影 + MLE/MAP quick 重建验证
        ↓
与规则基线、CRLB/A-optimality 基线、EIG-only 对比
```

EIG 阶段使用对象先验：

| 先验 | 含义 |
|---|---|
| `smooth_background` | 平滑背景对象 |
| `center_weak_target` | 平滑背景 + 中心弱目标 |
| `eccentric_roi_target` | 平滑背景 + 已知偏心 ROI 弱目标 |

d' 阶段使用任务集合：

| 任务 | 含义 |
|---|---|
| `center_small_target` | 中心低对比小球检测 |
| `eccentric_roi_target` | 已知偏心 ROI 低对比小球检测 |
| `offroi_edge_target` | EIG 先验未包含的非预设 ROI 边缘目标 |
| `material_contrast` | 局部材料/低对比判别 |

这里的关键设计思想是：EIG 粗筛只依赖可获得的对象先验；d' 精筛可以根据实际任务目标补充 EIG 先验未覆盖的检测任务。二者解耦，使框架对先验缺失具有一定容错性。

## 5. 对比方法定义

| 方法 | 当前实现 |
|---|---|
| `Rule_triple_center` | 实验一规则三层交错中心定向架构 |
| `CRLB_Aopt` | 在全部 240 个候选中用低秩 A-optimality / CRLB 近似筛选出的架构 |
| `EIG_only` | 实验二 weighted EIG top-1 架构 |
| `EIG_plus_dprime` | 实验三 EIG top 候选中按 maximin d' 精筛出的架构 |

当前 quick 结果中：

```text
CRLB_Aopt       -> cand_0216
EIG_only        -> cand_0216
EIG_plus_dprime -> cand_0236
```

这说明在当前候选空间和低秩近似下，CRLB/A-opt 与 EIG-only 对同一高信息架构产生了共同偏好，但 d' 精筛将最终选择改为 `cand_0236`。

## 6. 实验与运行命令

### 实验一：规则基线比较

目的：比较单层、双层交错、三层交错、ROI 定向三层等规则架构，建立三维几何参照系。

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment01_rule_baselines.py
```

输出：

```text
outputs/experiment01_rule_baselines/
```

关键文件：

- `experiment01_rule_baselines_report.md`
- `tables/experiment01_rule_baseline_metrics.csv`
- `figures/fig01_rule_geometries.png`
- `figures/fig02_global_roi_rmse.png`
- `figures/fig03_axial_rmse.png`
- `recon_slices/geometric_shapes_representative_slices.png`
- `recon_slices/smooth_roi_target_representative_slices.png`

### 实验二：EIG 粗筛

目的：验证 weighted EIG 能否在参数化三维候选空间中形成有意义排序，并缩小搜索空间。

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment02_eig_screening.py
```

输出：

```text
outputs/experiment02_eig_screening/
```

关键文件：

- `experiment02_eig_screening_report.md`
- `tables/experiment02_all_candidate_eig.csv`
- `tables/experiment02_top_candidate_eig.csv`
- `figures/fig01_eig_distribution.png`
- `figures/fig02_top_parameter_distributions.png`

### 实验三：d' 任务精筛

目的：在 EIG top 10% 候选中，用任务 d' maximin 准则选择最终任务驱动架构。

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment03_dprime_fine_screening.py
```

输出：

```text
outputs/experiment03_dprime_fine_screening/
```

关键文件：

- `experiment03_dprime_fine_screening_report.md`
- `tables/experiment03_dprime_rankings.csv`
- `tables/experiment03_task_definitions.csv`
- `figures/fig01_eig_rank_vs_dprime_rank.png`
- `figures/fig02_task_dprime_bars.png`
- `figures/fig03_selected_dprime_geometry.png`

### 实验四：泊松 + MLE/MAP 闭环验证

目的：对规则基线、CRLB_Aopt、EIG-only 和 EIG+d' 进行中心目标与已知 ROI 目标的泊松投影与 quick MLE/MAP 验证。

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment04_poisson_mle_map_validation.py
```

输出：

```text
outputs/experiment04_poisson_mle_map_validation/
```

关键文件：

- `experiment04_poisson_mle_map_validation_report.md`
- `tables/experiment04_validation_metrics.csv`
- `tables/experiment04_selected_architectures.csv`
- `figures/fig01_validation_metrics_map.png`
- `figures/fig02_reconstruction_validation_examples.png`
- `figures/fig03_selected_architectures_with_tasks.png`

### 实验五：非预设 ROI 与先验失配验证

目的：对应二维实验中的 edge task 和 prior-shift 测试，验证 EIG+d' 在 EIG 先验不完整时的任务补偿能力。

```powershell
D:\Astra-toolbox\.venv\Scripts\python.exe run_experiment05_offroi_prior_shift.py
```

输出：

```text
outputs/experiment05_offroi_prior_shift/
```

关键文件：

- `experiment05_offroi_prior_shift_report.md`
- `tables/experiment05_offroi_prior_shift_metrics.csv`
- `tables/experiment05_selected_architectures.csv`
- `figures/fig01_offroi_prior_shift_metrics_map.png`
- `figures/fig02_offroi_prior_shift_recon_examples.png`
- `figures/fig03_selected_architectures_with_tasks.png`

## 7. 当前关键结果

### 实验一

- `geometric_shapes` 中，单层中心环全局 RMSE 最低：`0.00229263`。
- `smooth_roi_target` 中，三层中心环全局 RMSE 略低：`0.00173601`。
- 双层交错环在两个 phantom 中均出现 upper slab RMSE 升高。
- 全 ROI 定向没有改善 ROI RMSE，说明 ROI 朝向应作为连续参数搜索，而不是固定极端策略。

### 实验二

- 候选数：`240`
- EIG top 10%：`24`
- 全体 EIG 均值：`3.27307`
- top 10% EIG 均值：`3.47198`
- top 10% 中没有单层架构。
- top 候选偏好多层、大 `z_extent` 和较小源环半径。

### 实验三

EIG top-1：

```text
cand_0216, EIG = 3.57964
```

d' maximin 最优：

```text
cand_0236, EIG rank = 7, min d' = 138.407
```

`cand_0236` 的任务 d'：

```text
center_small_target     = 146.320
eccentric_roi_target    = 138.407
offroi_edge_target      = 146.122
material_contrast       = 222.357
```

结论：EIG 最优架构不等于任务最优架构；加入 EIG 先验未包含的 off-ROI 任务后，d' 精筛仍选择 `cand_0236`，说明该架构对非预设任务不脆弱。

### 实验四

MAP 验证中：

- `EIG_plus_dprime` 在 center 和 known ROI case 的 ROI RMSE 均最低。
- `Rule_triple_center` 在全局 RMSE 上最低。
- `CRLB_Aopt` 在 empirical d' 上最高。

因此，实验四不能表述为 EIG+d' 全面优于 CRLB，而应表述为：EIG+d' 在局部 ROI 误差控制上更优，CRLB/A-opt 在当前经验 d' 指标上仍是强基线。

### 实验五

MAP ROI RMSE：

| case | EIG_plus_dprime |
|---|---:|
| `offroi_edge_target` | 0.00484655 |
| `high_z_shift_target` | 0.00472607 |
| `double_roi_offroi_target` | 0.00385944 |

`EIG_plus_dprime` 在三个非预设 / 先验失配 case 的 MAP ROI RMSE 上全部最优。

Empirical d'：

- `high_z_shift_target` 中 `EIG_plus_dprime` 最高：`143.33`。
- `offroi_edge_target` 中 `EIG_plus_dprime` 高于 `CRLB_Aopt` 和 `EIG_only`，但低于 `Rule_triple_center`。
- `double_roi_offroi_target` 中 `Rule_triple_center` 的 empirical d' 最高。

结论：EIG+d' 在 EIG 先验不完整时体现出稳定局部 ROI RMSE 优势，并在 high-z 先验失配任务中取得最高 detectability，但并非在所有指标上全面最优。

## 8. 当前限制

当前实验属于 quick-mode 研究验证，主要限制包括：

- 体素分辨率较低：`32 x 32 x 32`；
- 探测器采样较少；
- CRLB/A-opt 使用低秩 probe 近似；
- EIG 使用低秩 probe Laplace 近似；
- d' 使用低维通道化 MAP-CHO 近似；
- MAP 验证为轻量先验融合近似，不是严格迭代 MAP；
- 泊松重复次数较少；
- 尚未进行 paired bootstrap / permutation 显著性检验；
- empirical d' 对模板和重建近似较敏感。

## 9. 后续 SCI 实验建议

进入正式 SCI 实验前，建议优先完成：

1. 提高体素数和探测器采样；
2. 增加候选数和 EIG top-k 稳健性分析；
3. 提高 CRLB/A-opt 近似秩，或实现更严格的 Fisher/CRLB 估计；
4. 使用严格 MAP 或稳定线性化 MAP 验证；
5. 增加泊松 realization 数量；
6. 增加 paired bootstrap 和 paired permutation test；
7. 分任务报告 matched d'、ROI RMSE 和全局 RMSE；
8. 不使用“全面优于 CRLB”的叙述，而采用任务相关优势表述。

