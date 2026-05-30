# 三维静态 CT 光源最优展布 SCI 实验总结草稿

记录日期：2026-05-30

## 1. 研究问题

本项目研究三维环形静态 CT 系统中的多点 X 射线光源最优展布问题。传统 CRLB / A-optimality 方法通常以参数估计方差为优化目标，适合评价全局平均重建精度或指定 ROI 方差。但在安检 CT 等任务中，核心目标往往不是全体体素平均最优，而是某些局部弱目标、偏心目标或先验未覆盖目标是否可检测。

因此，本研究提出并验证一种分层任务驱动设计思路：

```text
EIG 粗筛：基于可获得对象先验，保留信息获取能力较强的架构；
d' 精筛：基于具体检测任务，在高 EIG 候选中选择任务可探测性更好的架构。
```

该框架的核心价值不在于全面替代 CRLB，而在于补充 CRLB/A-optimality 对局部任务 detectability 描述不足的问题。尤其当 EIG 阶段对象先验不完整时，d' 阶段仍可以显式加入实际关心的任务目标，从而对先验缺失进行补偿。

## 2. 实验系统与参数

当前三维 quick-mode 实验使用多层环形点源与虚拟平板 detector tile。

| 参数 | 当前设置 |
|---|---:|
| 总源数 | `48` |
| 总光子预算 | `4.8e8` |
| 每源光子数 | `1e7` |
| 重建体积 | `1.0 x 1.0 x 1.0` |
| 体素数 | `32 x 32 x 32` |
| 探测器半径 | `1.5` |
| 探测器高度 | `1.6` |
| detector tile | `24 x 32` 或实验一 `32 x 48` |
| cone angle | `35 deg` |
| 重建 | ASTRA `SIRT3D_CUDA` quick MLE/MAP |
| 已知 ROI 中心 | `(0.25, -0.20, 0.15)` |

当前所有实验均为 quick-mode 方法链验证，不直接作为最终论文级数值。

## 3. 对比方法

| 方法 | 选择规则 |
|---|---|
| `Rule_triple_center` | 规则三层交错中心定向架构 |
| `CRLB_Aopt` | 在全部候选中选择低秩 A-optimality / CRLB 近似最小架构 |
| `EIG_only` | weighted EIG 最大架构 |
| `EIG_plus_dprime` | 先取 EIG top 10%，再按 maximin d' 精筛 |

当前代表架构为：

| 方法 | 架构 |
|---|---|
| `Rule_triple_center` | `triple_layer_staggered_center` |
| `CRLB_Aopt` | `cand_0216` |
| `EIG_only` | `cand_0216` |
| `EIG_plus_dprime` | `cand_0236` |

`CRLB_Aopt` 与 `EIG_only` 在当前 quick 候选空间中选到同一架构，说明全局 A-opt 近似和 weighted EIG 对高信息两层大 z-extent 架构有共同偏好；d' 精筛则进一步选择 `cand_0236`。

## 4. 实验一：规则基线比较

### 目的

在进入 EIG / d' 优化前，先比较可解释的规则几何：

1. 单层中心定向环；
2. 双层交错中心定向环；
3. 三层交错中心定向环；
4. 三层交错 ROI 定向环。

### 结果

| phantom | 最优全局 RMSE | 数值 | 最优 ROI RMSE | 数值 |
|---|---|---:|---|---:|
| `geometric_shapes` | `single_layer_center` | 0.00229263 | `single_layer_center` | 0.00653674 |
| `smooth_roi_target` | `triple_layer_staggered_center` | 0.00173601 | `single_layer_center` | 0.00615427 |

双层交错环出现明显 upper slab RMSE 升高：

```text
geometric_shapes upper RMSE = 0.00406564
smooth_roi_target upper RMSE = 0.00327414
```

### 结论

多层并不必然优于单层；三层结构对平滑背景略有帮助，但优势有限。全 ROI 定向没有带来 ROI RMSE 改善，说明朝向参数应作为连续搜索自由度，而不是固定为全中心或全 ROI。

## 5. 实验二：EIG 粗筛

### 目的

验证 EIG 是否能够在三维参数化候选架构中形成有意义排序，并删除低信息价值架构。

### 候选空间

参数化架构：

```text
Theta = {M_z, N_m, R_m, z_m, delta_m, alpha_m}
```

使用 Latin hypercube 采样 `240` 个候选，保留 top 10% 即 `24` 个候选。

### 结果

| 指标 | 数值 |
|---|---:|
| EIG 最小值 | 3.08294 |
| EIG 均值 | 3.27307 |
| EIG 中位数 | 3.26063 |
| EIG 最大值 | 3.57964 |
| top 10% 阈值 | 3.42751 |
| top 10% 均值 | 3.47198 |

层数偏好：

| layer_count | 全部候选比例 | EIG top 10% 比例 |
|---:|---:|---:|
| 1 | 0.25 | 0 |
| 2 | 0.25 | 0.583 |
| 3 | 0.25 | 0.292 |
| 4 | 0.25 | 0.125 |

参数均值变化：

| 参数 | 全部均值 | EIG top 均值 |
|---|---:|---:|
| `radius` | 1.4750 | 1.3024 |
| `z_extent` | 0.2844 | 0.4628 |
| `angular_offset_fraction` | 0.5000 | 0.4378 |
| `orientation_alpha` | 0.5000 | 0.4866 |

### 结论

EIG 粗筛不是最终任务指标，但它能有效排除单层低信息候选，并明显偏好多层、大轴向覆盖和较小半径架构。这说明 EIG 适合作为三维光源搜索的第一层粗筛准则。

## 6. 实验三：d' 精筛

### 目的

在 EIG top 10% 候选中，用任务可探测性进一步精筛，证明 EIG 最优不一定是任务最优。

### 任务集合

| task | 含义 |
|---|---|
| `center_small_target` | 中心小目标检测 |
| `eccentric_roi_target` | 已知偏心 ROI 小目标检测 |
| `offroi_edge_target` | EIG 先验未包含的非预设 ROI 边缘目标 |
| `material_contrast` | 局部材料/低对比判别 |

精筛准则：

```text
U_task(Theta) = min_t d_t'^2(Theta)
```

### 结果

EIG top-1：

```text
cand_0216
EIG = 3.57964
d' rank = 22
min d' = 132.186
```

d' maximin 最优：

```text
cand_0236
EIG rank = 7
min d' = 138.407
```

`cand_0236` 分任务 d'：

| 任务 | d' |
|---|---:|
| `center_small_target` | 146.320 |
| `eccentric_roi_target` | 138.407 |
| `offroi_edge_target` | 146.122 |
| `material_contrast` | 222.357 |

### 结论

EIG 最优架构并不是任务最优架构。加入 EIG 先验未包含的 off-ROI 任务后，d' 精筛仍选择 `cand_0236`，且该架构在 off-ROI 任务上保持较高理论 d'。这支持“EIG 先验保障整体信息，d' 任务精筛补偿先验缺失”的分层设计思想。

## 7. 实验四：泊松 + MLE/MAP 闭环验证

### 目的

检验设计准则筛出的架构在真实泊松投影和 quick MLE/MAP 重建后是否仍体现任务差异。

### 验证任务

| case | 含义 |
|---|---|
| `center_target` | 中心低对比小目标 |
| `eccentric_roi_target` | 已知偏心 ROI 低对比小目标 |

### MAP 结果

| method | case | global RMSE | ROI RMSE | empirical d' |
|---|---|---:|---:|---:|
| `Rule_triple_center` | `center_target` | 0.001430 | 0.004769 | 197.393 |
| `CRLB_Aopt` | `center_target` | 0.007461 | 0.004902 | 271.433 |
| `EIG_only` | `center_target` | 0.006950 | 0.004908 | 121.173 |
| `EIG_plus_dprime` | `center_target` | 0.001694 | **0.004727** | 195.335 |
| `Rule_triple_center` | `eccentric_roi_target` | 0.001436 | 0.004949 | 80.077 |
| `CRLB_Aopt` | `eccentric_roi_target` | 0.007608 | 0.004977 | 189.596 |
| `EIG_only` | `eccentric_roi_target` | 0.005171 | 0.004997 | 111.525 |
| `EIG_plus_dprime` | `eccentric_roi_target` | 0.001620 | **0.004862** | 160.311 |

### 结论

`EIG_plus_dprime` 在两个已知任务的 ROI RMSE 上均最优；`Rule_triple_center` 全局 RMSE 最优；`CRLB_Aopt` empirical d' 最高。因此实验四支持局部误差优势，但不能表述为 EIG+d' 全面优于 CRLB。

## 8. 实验五：非预设 ROI 与先验失配验证

### 目的

对应二维实验中的 edge task 和 prior-shift 测试，检验当 EIG 对象先验不完整时，d' 精筛是否能通过显式任务目标补偿先验缺失。

### 验证任务

| case | 含义 |
|---|---|
| `offroi_edge_target` | 训练 ROI 之外的三维边缘目标 |
| `high_z_shift_target` | 高 z 轴向偏心目标 |
| `double_roi_offroi_target` | 已知 ROI 与 off-ROI 双目标对象 |

### MAP 结果

| method | case | global RMSE | ROI RMSE | empirical d' |
|---|---|---:|---:|---:|
| `Rule_triple_center` | `offroi_edge_target` | 0.001444 | 0.005071 | 212.881 |
| `CRLB_Aopt` | `offroi_edge_target` | 0.007473 | 0.004995 | 59.587 |
| `EIG_only` | `offroi_edge_target` | 0.006383 | 0.005029 | 84.777 |
| `EIG_plus_dprime` | `offroi_edge_target` | 0.001702 | **0.004847** | 148.891 |
| `Rule_triple_center` | `high_z_shift_target` | 0.001417 | 0.004739 | 93.356 |
| `CRLB_Aopt` | `high_z_shift_target` | 0.008174 | 0.004815 | 62.740 |
| `EIG_only` | `high_z_shift_target` | 0.006210 | 0.004774 | 60.218 |
| `EIG_plus_dprime` | `high_z_shift_target` | 0.001550 | **0.004726** | **143.330** |
| `Rule_triple_center` | `double_roi_offroi_target` | 0.001452 | 0.003983 | 131.008 |
| `CRLB_Aopt` | `double_roi_offroi_target` | 0.006565 | 0.004073 | 79.660 |
| `EIG_only` | `double_roi_offroi_target` | 0.007872 | 0.004031 | 96.707 |
| `EIG_plus_dprime` | `double_roi_offroi_target` | 0.001679 | **0.003859** | 107.707 |

### 结论

`EIG_plus_dprime` 在三个非预设 / 先验失配任务的 ROI RMSE 上全部最优，并在 `high_z_shift_target` 上取得最高 empirical d'。在 `offroi_edge_target` 中，`EIG_plus_dprime` 的 empirical d' 明显高于 `CRLB_Aopt` 和 `EIG_only`，但低于规则三层中心环。该结果说明 d' 精筛可以补偿 EIG 先验缺失并改善局部任务区域，但 empirical d' 仍具有任务依赖性。

## 9. 综合讨论

### 9.1 CRLB/A-optimality 的角色

CRLB/A-optimality 不应被描述为弱基线。当前三维 quick 实验中，`CRLB_Aopt` 在实验四 empirical d' 上最强，说明它仍然能选择出高信息、高可分离度架构。但 CRLB/A-opt 的目标是全局方差或其低秩近似，不一定与所有局部 ROI 误差或任务 maximin detectability 一致。

### 9.2 EIG 粗筛的作用

EIG 粗筛有效缩小搜索空间。它排除了所有单层架构，并偏好具有较大轴向覆盖的多层架构。实验三显示 EIG top-1 不是任务最优，说明 EIG 不能替代 d'，但它能提供合理的高信息候选池。

### 9.3 d' 精筛的作用

d' 精筛将最终架构从 `cand_0216` 改为 `cand_0236`。`cand_0236` 在四个任务上保持较高且均衡的理论 d'，尤其在 EIG 先验没有包含的 `offroi_edge_target` 上仍达到 `146.122`。这支持任务驱动精筛的必要性。

### 9.4 泊松验证的意义

实验四和实验五表明，EIG+d' 的优势主要体现在局部 ROI RMSE，而不是所有 empirical d' 指标。对于 SCI 论文，应避免“全面优于 CRLB”的表述，改为：

```text
EIG+d' 在非预设 ROI 与先验失配任务中表现出稳定的局部 ROI 误差优势，并在部分任务上提升经验可探测性；CRLB/A-optimality 仍是强全局信息基线。
```

## 10. 当前可用于论文初稿的核心结论

1. 三维规则基线实验表明，多层和朝向参数对轴向覆盖与局部重建质量有明显影响，不能依赖单一规则架构作为最终设计。
2. EIG 粗筛能够在 240 个参数化候选中形成有结构的排序，并将搜索空间缩小到高信息多层候选。
3. EIG top-1 不等于任务最优，d' 精筛是必要步骤。
4. 在 EIG 先验未覆盖 off-ROI 目标时，d' 精筛仍能通过显式任务目标选择对该任务有利的架构，体现先验缺失容错性。
5. 泊松 + quick MLE/MAP 验证显示，EIG+d' 在已知 ROI、off-ROI 和 prior-shift 任务的局部 ROI RMSE 上具有稳定优势。
6. empirical d' 结果并非全面支持 EIG+d' 最优，说明正式论文实验需要更严格 observer、MAP 和统计检验。
7. 本研究的准确表述不是“EIG+d' 全面优于 CRLB”，而是“EIG+d' 能补充 CRLB/A-optimality 在局部任务驱动设计中的不足”。

## 11. SCI 正式实验建议

正式实验建议在当前 quick 框架基础上升级：

- 提高体素数，例如 `48^3` 或 `64^3`；
- 增加 detector tile 采样；
- 增加候选架构数到 500-1000；
- 提高 EIG probe rank 和 CRLB/A-opt probe rank；
- 使用严格 MAP 或稳定线性化 MAP；
- 将泊松重复次数提高到至少 30-100；
- 采用 paired bootstrap 和 paired permutation test；
- 分别报告 center、known ROI、off-ROI、high-z、double-target 的 matched d'；
- 将 AUC 作为辅助指标，重点使用 matched d'、ROI RMSE、统计显著性；
- 保留 `Rule_triple_center`，因为它在全局 RMSE 和部分 empirical d' 上是强基线。

