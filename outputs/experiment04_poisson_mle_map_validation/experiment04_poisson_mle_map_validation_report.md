# 三维静态 CT 光源展布实验 4：泊松 + MLE/MAP 最终验证

记录日期：2026-05-29

## 1. 实验目的

实验一到实验三分别建立了规则几何基线、EIG 粗筛和 d' 任务精筛。但这些仍主要是设计准则层面的排序。实验四的作用，是在真实泊松 transmission 投影和重建流程下检查这些准则选出的架构是否仍然具有任务优势。

这组实验与参考 CRLB 方法中使用 MLE 验证 CRLB 可达性的作用类似：它不是再定义一个新的设计准则，而是用带噪投影和重建闭环检验前面选出的设计是否真正有效。

## 2. 对比架构

| method | architecture | layers | layer_zs | target |
|---|---|---:|---|---|
| `Rule_triple_center` | `Rule_triple_center_triple_layer_staggered_center` | 3 | `-0.45;0;0.45` | `(0.0, 0.0, 0.0)` |
| `CRLB_Aopt` | `CRLB_Aopt_cand_0216` | 2 | `-0.5762;0.5762` | `(0.2287, -0.183, 0.1372)` |
| `EIG_only` | `EIG_only_cand_0216` | 2 | `-0.5762;0.5762` | `(0.2287, -0.183, 0.1372)` |
| `EIG_plus_dprime` | `EIG_plus_dprime_cand_0236` | 2 | `-0.4103;0.4103` | `(0.0519, -0.0415, 0.0311)` |

`CRLB_Aopt` 是当前 quick 实现中的低秩 A-optimality 近似基线，用随机 probe 子空间估计全局方差准则，代表参考文献中 CRLB / A-optimality 思路。后续论文级实验可替换为更高秩或显式 Fisher 矩阵版本。

## 3. 验证对象与重建

| case | 含义 |
|---|---|
| `center_target` | 平滑背景 + 中心低对比小球目标 |
| `eccentric_roi_target` | 平滑背景 + 偏心 ROI 低对比小球目标 |

每个架构、每个 case 生成 `5` 次独立泊松投影。MLE 重建使用 ASTRA `SIRT3D_CUDA` 对泊松 log 数据重建；MAP 重建在 quick 阶段采用轻量先验融合近似，先验强度为 `0.18`。该 MAP 是用于流程验证的正则化近似，不等同于最终论文级严格 MAP 迭代。

## 4. MAP 验证结果

| method | case | recon | global RMSE | ROI RMSE | empirical d' |
|---|---|---|---:|---:|---:|
| `Rule_triple_center` | `center_target` | `MAP` | 0.00142963 | 0.00476923 | 197.393 |
| `Rule_triple_center` | `eccentric_roi_target` | `MAP` | 0.0014356 | 0.00494874 | 80.0772 |
| `CRLB_Aopt` | `center_target` | `MAP` | 0.00746133 | 0.00490208 | 271.433 |
| `CRLB_Aopt` | `eccentric_roi_target` | `MAP` | 0.00760841 | 0.00497747 | 189.596 |
| `EIG_only` | `center_target` | `MAP` | 0.00695009 | 0.00490755 | 121.173 |
| `EIG_only` | `eccentric_roi_target` | `MAP` | 0.00517104 | 0.00499695 | 111.525 |
| `EIG_plus_dprime` | `center_target` | `MAP` | 0.00169382 | 0.00472651 | 195.335 |
| `EIG_plus_dprime` | `eccentric_roi_target` | `MAP` | 0.00162012 | 0.00486161 | 160.311 |

## 5. MLE 验证结果

| method | case | recon | global RMSE | ROI RMSE | empirical d' |
|---|---|---|---:|---:|---:|
| `Rule_triple_center` | `center_target` | `MLE` | 0.00169946 | 0.00418391 | 197.392 |
| `Rule_triple_center` | `eccentric_roi_target` | `MLE` | 0.0017034 | 0.00433623 | 80.0772 |
| `CRLB_Aopt` | `center_target` | `MLE` | 0.0090899 | 0.00431483 | 271.433 |
| `CRLB_Aopt` | `eccentric_roi_target` | `MLE` | 0.0092687 | 0.00438082 | 189.596 |
| `EIG_only` | `center_target` | `MLE` | 0.00846598 | 0.00432136 | 121.173 |
| `EIG_only` | `eccentric_roi_target` | `MLE` | 0.00629206 | 0.00439588 | 111.525 |
| `EIG_plus_dprime` | `center_target` | `MLE` | 0.0020285 | 0.00413475 | 195.335 |
| `EIG_plus_dprime` | `eccentric_roi_target` | `MLE` | 0.0019348 | 0.00423545 | 160.311 |

## 6. 输出图像说明

`fig01_validation_metrics_map.png` 汇总 MAP 重建下的全局 RMSE、ROI RMSE 和经验 d'。读图时，全局 RMSE 和 ROI RMSE 越低越好，经验 d' 越高越好。该图用于判断 EIG+d' 是否在真实泊松重建后仍保持任务优势。

`fig02_reconstruction_validation_examples.png` 给出中心目标和偏心 ROI 目标在各架构下的代表性 MAP 重建切片及绝对误差图。它用于观察表格中的 RMSE 和 d' 差异是否能在重建图像中看到对应趋势。

## 7. 初步结论

在当前 quick MAP 验证中，偏心 ROI case 的最低 ROI RMSE 来自 `EIG_plus_dprime`，数值为 `0.00486161`；偏心 ROI case 的最高经验 d' 来自 `CRLB_Aopt`，数值为 `189.596`。

如果 EIG+d' 在 ROI RMSE 或经验 d' 上优于规则基线和 CRLB_Aopt，则说明任务精筛选出的架构在真实泊松重建条件下仍更贴近局部检测需求；如果全局 RMSE 与 CRLB_Aopt 接近而 ROI/d' 更优，则更符合本研究的核心论点：任务驱动设计不一定追求全局平均方差最小，而是追求目标任务更可探测。

当前实验仍是 quick 级闭环验证，主要用于验证流程和相对趋势。最终论文级结果应提高重复次数、体素分辨率、MAP 迭代严格性，并加入统计显著性检验。