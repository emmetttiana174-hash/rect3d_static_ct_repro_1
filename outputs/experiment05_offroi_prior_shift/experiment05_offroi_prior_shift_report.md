# 三维静态 CT 实验 5：非预设 ROI 检测与先验失配测试

记录日期：2026-05-29

## 1. 实验目的

二维 `rect2d_compare` 中最关键的证据不是 EIG+d' 全面优于 CRLB，而是在非预设 ROI 的 edge 任务和先验失配任务中，任务驱动准则能够体现出不同于全局/固定 ROI CRLB 的局部检测优势。本实验把这一思想迁移到三维环形静态 CT。

当前实验使用实验二和更新后的实验三已经确定的架构进行泊松 + MLE/MAP 闭环验证。需要说明的是，`offroi_edge_target` 已经被纳入实验三的 d' 精筛任务集合，但它没有被纳入 EIG 阶段的对象先验。因此，本实验考察的是：当 EIG 粗筛阶段的对象先验不完整时，后续 d' 精筛能否通过显式任务目标弥补这一缺失，并在三维非预设 ROI / 先验失配任务中体现价值。

这一设置符合当前方法的核心思想：EIG 负责利用已有对象先验保障整体信息获取能力；d' 负责根据实际关心的检测任务进行任务补偿和精筛。两者并不要求使用完全相同的先验信息。

## 2. 对比方法

| method | 含义 |
|---|---|
| `Rule_triple_center` | 实验一规则三层中心定向基线 |
| `CRLB_Aopt` | 当前 quick 低秩 A-optimality / CRLB 近似基线 |
| `EIG_only` | 实验二 weighted EIG top-1 架构 |
| `EIG_plus_dprime` | 实验三 d' maximin 精筛架构 |

## 3. 验证任务

| case | 含义 | 是否属于训练先验/显式 d' 任务 |
|---|---|---|
| `offroi_edge_target` | 位于训练 ROI 之外的三维边缘小目标 | 否 |
| `high_z_shift_target` | 位于较高 z 层、训练先验未覆盖的偏心目标 | 否 |
| `double_roi_offroi_target` | 指定 ROI 与非预设 ROI 同时存在的双目标对象，评价 off-ROI 区域 | 部分失配 |

每个方法、每个 case 使用 `6` 次独立泊松 realization。MAP 仍采用当前 quick 先验融合近似，结论只作为方法链验证。

## 4. MAP 验证结果

| method | case | recon | global RMSE | ROI RMSE | empirical d' |
|---|---|---|---:|---:|---:|
| `Rule_triple_center` | `offroi_edge_target` | `MAP` | 0.00144446 | 0.0050713 | 212.881 |
| `Rule_triple_center` | `high_z_shift_target` | `MAP` | 0.00141656 | 0.00473893 | 93.3556 |
| `Rule_triple_center` | `double_roi_offroi_target` | `MAP` | 0.00145191 | 0.00398257 | 131.008 |
| `CRLB_Aopt` | `offroi_edge_target` | `MAP` | 0.00747271 | 0.00499481 | 59.5871 |
| `CRLB_Aopt` | `high_z_shift_target` | `MAP` | 0.0081737 | 0.00481539 | 62.7401 |
| `CRLB_Aopt` | `double_roi_offroi_target` | `MAP` | 0.00656548 | 0.00407303 | 79.6603 |
| `EIG_only` | `offroi_edge_target` | `MAP` | 0.00638261 | 0.00502927 | 84.7766 |
| `EIG_only` | `high_z_shift_target` | `MAP` | 0.00620999 | 0.00477367 | 60.2177 |
| `EIG_only` | `double_roi_offroi_target` | `MAP` | 0.00787218 | 0.00403138 | 96.7068 |
| `EIG_plus_dprime` | `offroi_edge_target` | `MAP` | 0.00170157 | 0.00484655 | 148.891 |
| `EIG_plus_dprime` | `high_z_shift_target` | `MAP` | 0.00154985 | 0.00472607 | 143.33 |
| `EIG_plus_dprime` | `double_roi_offroi_target` | `MAP` | 0.00167929 | 0.00385944 | 107.707 |

## 5. MLE 验证结果

| method | case | recon | global RMSE | ROI RMSE | empirical d' |
|---|---|---|---:|---:|---:|
| `Rule_triple_center` | `offroi_edge_target` | `MLE` | 0.00171339 | 0.00447627 | 212.881 |
| `Rule_triple_center` | `high_z_shift_target` | `MLE` | 0.00168368 | 0.0041506 | 93.3556 |
| `Rule_triple_center` | `double_roi_offroi_target` | `MLE` | 0.00171088 | 0.00352414 | 131.008 |
| `CRLB_Aopt` | `offroi_edge_target` | `MLE` | 0.00910333 | 0.0044288 | 59.5871 |
| `CRLB_Aopt` | `high_z_shift_target` | `MLE` | 0.00995933 | 0.00431401 | 62.7401 |
| `CRLB_Aopt` | `double_roi_offroi_target` | `MLE` | 0.00799253 | 0.00367097 | 79.6603 |
| `EIG_only` | `offroi_edge_target` | `MLE` | 0.00777209 | 0.00443875 | 84.7766 |
| `EIG_only` | `high_z_shift_target` | `MLE` | 0.00756273 | 0.00424413 | 60.2177 |
| `EIG_only` | `double_roi_offroi_target` | `MLE` | 0.009587 | 0.00364806 | 96.7068 |
| `EIG_plus_dprime` | `offroi_edge_target` | `MLE` | 0.00203633 | 0.00421999 | 148.891 |
| `EIG_plus_dprime` | `high_z_shift_target` | `MLE` | 0.00184982 | 0.00412316 | 143.33 |
| `EIG_plus_dprime` | `double_roi_offroi_target` | `MLE` | 0.0019976 | 0.0033772 | 107.707 |

## 6. 分任务观察

### double_roi_offroi_target

- MAP 全局 RMSE 最低：`Rule_triple_center`，数值 `0.00145191`。
- MAP ROI RMSE 最低：`EIG_plus_dprime`，数值 `0.00385944`。
- MAP empirical d' 最高：`Rule_triple_center`，数值 `131.008`。

### high_z_shift_target

- MAP 全局 RMSE 最低：`Rule_triple_center`，数值 `0.00141656`。
- MAP ROI RMSE 最低：`EIG_plus_dprime`，数值 `0.00472607`。
- MAP empirical d' 最高：`EIG_plus_dprime`，数值 `143.33`。

### offroi_edge_target

- MAP 全局 RMSE 最低：`Rule_triple_center`，数值 `0.00144446`。
- MAP ROI RMSE 最低：`EIG_plus_dprime`，数值 `0.00484655`。
- MAP empirical d' 最高：`Rule_triple_center`，数值 `212.881`。

## 7. 结果解释

当前实验结果呈现出三个清楚的现象。

第一，`EIG_plus_dprime` 在三个非预设 / 先验失配任务的 MAP ROI RMSE 上全部最优：

| case | Rule | CRLB_Aopt | EIG_only | EIG_plus_dprime |
|---|---:|---:|---:|---:|
| `offroi_edge_target` | 0.0050713 | 0.00499481 | 0.00502927 | **0.00484655** |
| `high_z_shift_target` | 0.00473893 | 0.00481539 | 0.00477367 | **0.00472607** |
| `double_roi_offroi_target` | 0.00398257 | 0.00407303 | 0.00403138 | **0.00385944** |

这说明，在当前三维 quick 闭环验证中，经过 d' 精筛得到的 `cand_0236` 确实更有利于非预设局部区域的重建误差控制。尤其是 `offroi_edge_target` 和 `double_roi_offroi_target` 中，评价 ROI 位于 EIG 先验没有显式建模的区域，`EIG_plus_dprime` 仍然取得最低 ROI RMSE，说明 d' 精筛对 EIG 先验缺失具有一定补偿作用。

第二，全局 RMSE 的最优方法始终是 `Rule_triple_center`：

| case | 全局 RMSE 最优方法 | 数值 |
|---|---|---:|
| `offroi_edge_target` | `Rule_triple_center` | 0.00144446 |
| `high_z_shift_target` | `Rule_triple_center` | 0.00141656 |
| `double_roi_offroi_target` | `Rule_triple_center` | 0.00145191 |

这说明规则三层中心定向环在当前 SIRT/MAP quick 设置下仍具有很强的全局平滑重建能力。该结果也再次说明，本研究不能表述为 EIG+d' 在所有指标上全面优于规则基线或 CRLB。不同设计准则对应不同性能目标：规则三层中心环更偏全局稳定重建，而 EIG+d' 更偏局部任务区域。

第三，经验 d' 的结果具有任务依赖性：

| case | empirical d' 最优方法 | 数值 | EIG_plus_dprime 数值 |
|---|---|---:|---:|
| `offroi_edge_target` | `Rule_triple_center` | 212.881 | 148.891 |
| `high_z_shift_target` | `EIG_plus_dprime` | 143.33 | **143.33** |
| `double_roi_offroi_target` | `Rule_triple_center` | 131.008 | 107.707 |

其中 `high_z_shift_target` 是最接近“先验缺失 + 轴向覆盖挑战”的任务，`EIG_plus_dprime` 在该任务上同时取得最低 ROI RMSE 和最高 empirical d'。这说明当新任务主要考验三维轴向覆盖和局部任务适配时，加入 off-ROI 任务后的 d' 精筛可以有效改善 detectability。

在 `offroi_edge_target` 中，`EIG_plus_dprime` 的 empirical d' 虽低于规则三层中心环，但明显高于 `CRLB_Aopt` 和 `EIG_only`：

```text
Rule_triple_center: 212.881
CRLB_Aopt:          59.5871
EIG_only:           84.7766
EIG_plus_dprime:    148.891
```

这说明 d' 精筛相较于 EIG-only 和 CRLB/A-opt 基线确实改善了非预设 ROI 任务的 detectability，但当前规则三层中心环在该特定 off-ROI edge 模板上的经验分数仍最高。

在 `double_roi_offroi_target` 中，`EIG_plus_dprime` 的 ROI RMSE 最低，但 empirical d' 低于规则三层中心环。这表明双目标场景下，当前 scalar template score 的经验 d' 与 ROI RMSE 并不完全一致；规则三层中心环可能在模板响应的均值分离上更强，而 EIG+d' 在局部误差控制上更优。

综合来看，实验五给出的不是“EIG+d' 全面胜出”的结论，而是一个更符合当前研究逻辑的结果：EIG+d' 在 EIG 先验不完整的情况下，通过 d' 任务精筛获得了稳定的局部 ROI RMSE 优势，并在 high-z 先验失配任务上取得最高 detectability；但 empirical d' 仍受任务位置、模板定义和重建模型影响，部分任务中规则三层中心环仍然更强。

## 8. 输出文件

| 文件 | 内容 |
|---|---|
| `tables/experiment05_offroi_prior_shift_metrics.csv` | 非预设 ROI 与先验失配任务的 MLE/MAP 指标 |
| `tables/experiment05_selected_architectures.csv` | 四类方法对应架构 |
| `figures/fig01_offroi_prior_shift_metrics_map.png` | MAP 下 RMSE 与经验 d' 对比 |
| `figures/fig02_offroi_prior_shift_recon_examples.png` | 代表性 MAP 重建切片与误差图 |

## 9. 阶段性结论

实验五是三维版本中对应二维 `edge task` 和先验失配测试的闭环 quick 验证。基于当前实际数据，可以得到以下阶段性结论：

1. `EIG_plus_dprime` 在三个非预设 / 先验失配任务的 MAP ROI RMSE 上全部最优，说明 d' 精筛后的架构 `cand_0236` 对局部任务区域具有稳定优势。
2. 在 `high_z_shift_target` 中，`EIG_plus_dprime` 同时取得最低 ROI RMSE 和最高 empirical d'，说明该方法在三维轴向先验失配任务中体现出明确价值。
3. 在 `offroi_edge_target` 中，`EIG_plus_dprime` 的 empirical d' 明显高于 `CRLB_Aopt` 和 `EIG_only`，但低于 `Rule_triple_center`，说明任务驱动精筛相较信息准则基线有改善，但仍未在所有任务上超过规则几何基线。
4. 在 `double_roi_offroi_target` 中，`EIG_plus_dprime` 局部 ROI RMSE 最优，但 empirical d' 不是最高，说明当前经验 d' 模板与局部误差指标并不完全等价，后续需要更严格的 observer 和统计检验。

因此，当前实验支持的论文式表述应为：

```text
在三维静态 CT 非预设 ROI 与先验失配验证中，EIG+d' 分层准则在局部 ROI RMSE 上表现出稳定优势，并在高 z 先验失配任务中获得最高经验可探测性。结果说明，当 EIG 阶段对象先验不完整时，d' 精筛能够通过显式任务目标对架构选择进行补偿。但该优势并非在所有指标上全面成立，规则三层中心环在部分经验 d' 任务中仍然更强。
```
