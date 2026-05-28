# 三维静态 CT 光源展布实验 4：泊松 + MLE/MAP 最终验证

记录日期：2026-05-28

## 1. 实验目的

实验一到实验三分别建立了规则几何基线、EIG 粗筛和 d' 任务精筛。但这些仍主要是设计准则层面的排序。实验四的作用，是在真实泊松 transmission 投影和重建流程下检查这些准则选出的架构是否仍然具有任务优势。

这组实验与参考 CRLB 方法中使用 MLE 验证 CRLB 可达性的作用类似：它不是再定义一个新的设计准则，而是用带噪投影和重建闭环检验前面选出的设计是否真正有效。

需要注意的是，本实验的目的不是证明 `EIG_plus_dprime` 在所有指标、所有任务上全面优于 CRLB / A-optimality。二维 `rect2d_compare` 对比实验已经表明，CRLB 类方法本身是合理且强有力的基线：当任务与其优化目标一致时，例如指定 ROI 方差或全局平均方差，它可能表现最好。本研究真正要验证的是：

```text
CRLB / A-optimality 的最优性依赖其评价目标；
全局或固定 ROI 方差最优，不一定等价于所有局部检测任务最优。
```

因此，实验四的正确读法应是：观察不同准则在真实泊松重建闭环下呈现怎样的任务偏好，而不是期待 EIG+d' 在全局 RMSE、ROI RMSE 和经验 d' 上同时全部第一。

## 2. 对比架构

| method | architecture | layers | layer_zs | target |
|---|---|---:|---|---|
| `Rule_triple_center` | `Rule_triple_center_triple_layer_staggered_center` | 3 | `-0.45;0;0.45` | `(0.0, 0.0, 0.0)` |
| `CRLB_Aopt` | `CRLB_Aopt_cand_0216` | 2 | `-0.5762;0.5762` | `(0.2287, -0.183, 0.1372)` |
| `EIG_only` | `EIG_only_cand_0216` | 2 | `-0.5762;0.5762` | `(0.2287, -0.183, 0.1372)` |
| `EIG_plus_dprime` | `EIG_plus_dprime_cand_0236` | 2 | `-0.4103;0.4103` | `(0.0519, -0.0415, 0.0311)` |

`CRLB_Aopt` 是当前 quick 实现中的低秩 A-optimality 近似基线，用随机 probe 子空间估计全局方差准则，代表参考文献中 CRLB / A-optimality 思路。后续论文级实验可替换为更高秩或显式 Fisher 矩阵版本。

当前 quick 结果中，`CRLB_Aopt` 与 `EIG_only` 都选到了 `cand_0216`。这并不表示两种准则在理论上等价，而是说明在当前低秩 probe、候选空间和先验设置下，A-optimality 近似基线与 weighted EIG top-1 对同一个两层大 z-extent 架构产生了共同偏好。这个现象本身也值得记录：强全局信息准则和 EIG 粗筛可能会在某些候选空间中收敛到相同架构，但 d' 精筛仍把最终候选改为 `cand_0236`。

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

更具体地说：

1. 在两个验证对象上，`EIG_plus_dprime` 的 MAP ROI RMSE 都是当前四类方法中最低的：
   - `center_target`: `0.00472651`
   - `eccentric_roi_target`: `0.00486161`
2. 在全局 RMSE 上，`Rule_triple_center` 仍然最优，说明规则三层中心环在当前 quick SIRT/MAP 设置下具有较强的全局平滑重建优势。
3. 在经验 d' 上，`CRLB_Aopt` 当前最高：
   - `center_target`: `271.433`
   - `eccentric_roi_target`: `189.596`
4. `EIG_plus_dprime` 在经验 d' 上没有超过 `CRLB_Aopt`，但在偏心 ROI case 中明显高于 `Rule_triple_center` 和 `EIG_only`：
   - `Rule_triple_center`: `80.0772`
   - `EIG_only`: `111.525`
   - `EIG_plus_dprime`: `160.311`
   - `CRLB_Aopt`: `189.596`

因此，当前 quick 闭环验证支持一个较谨慎的结论：`EIG_plus_dprime` 在真实泊松重建条件下表现出更好的 ROI 局部误差控制，尤其在偏心 ROI 目标上优于规则基线和 EIG-only；但当前 quick 经验 d' 最高者仍是 `CRLB_Aopt`，因此还不能宣称 EIG+d' 在所有任务 detectability 指标上已经全面优于 CRLB/A-optimality 基线。

这个结果并不否定实验三的设计准则结论，而是提示实验四的重建验证仍受当前 quick MLE/MAP 近似、重复次数、经验 d' 估计方差、通道模板和 CRLB probe 近似影响。后续论文级实验应增加泊松重复次数、使用严格 MAP 迭代和配对统计检验，进一步验证 `EIG_plus_dprime` 的任务 detectability 优势是否稳定。

结合二维 `rect2d_compare` 的经验，当前三维实验四更合理的阶段性解释是：

1. CRLB/A-optimality 不应被简单当作弱基线；它在某些任务和经验 d' 指标上可以非常强。
2. EIG+d' 的价值不在于“全面替代 CRLB”，而在于提供一种可以显式注入任务目标的分层设计路线。
3. 当前三维 quick 验证已经显示 `EIG_plus_dprime` 在 ROI RMSE 上具有优势，但经验 d' 仍需要更严格的重建模型和统计检验来确认。
4. 后续三维实验应像二维实验 B/D 那样加入更明确的“非预设 ROI”或“先验失配”任务，并分别报告各子任务结果，而不是只看场景平均或单一综合指标。

当前实验仍是 quick 级闭环验证，主要用于验证流程和相对趋势。最终论文级结果应提高重复次数、体素分辨率、MAP 迭代严格性，并加入统计显著性检验。
