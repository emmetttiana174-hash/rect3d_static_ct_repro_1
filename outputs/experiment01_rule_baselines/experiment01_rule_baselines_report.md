# 三维静态 CT 光源展布实验 1：规则基线比较

记录日期：2026-05-23

补充说明日期：2026-05-24

## 1. 实验目的

本实验是三维光源最优展布项目的第一组基线实验。它不试图直接找到最终最优架构，而是先比较若干可解释的规则几何：单层等角环、双层交错环、三层交错环以及 ROI 定向多层环。这样做的目的，是在进入 EIG 粗筛和 d' 精筛之前，先建立清楚的几何参照系。

这组实验重点回答四个问题：

1. 多层轴向布源是否明显优于单层环；
2. 层间交错是否值得作为后续候选架构的默认自由度；
3. ROI 定向是否会带来局部区域重建质量提升；
4. 后续 EIG / d' 优化应重点搜索哪些几何参数。

## 2. 实验设置

- 总源数：`48`，所有架构保持一致。
- 总光子预算：`4.8e+08`，每个源平均 `1e+07`。
- 探测器半径：`1.5`，探测器高度：`1.6`。
- 重建体积：`1.0 x 1.0 x 1.0`。
- 体素数：`32 x 32 x 32`。
- detector tile：`32 x 48`。
- cone angle：`35.0` degree。
- 重建算法：ASTRA `SIRT3D_CUDA`，迭代 `40` 次。
- ROI 中心：`(0.25, -0.2, 0.15)`。

## 3. 比较的四类规则架构

| 架构 | 含义 |
|---|---|
| `single_layer_center` | 所有源位于 z=0 单层环，圆周均匀分布，全部朝系统中心 |
| `double_layer_staggered_center` | 上下两层交错环，全部朝系统中心 |
| `triple_layer_staggered_center` | 三层交错环，全部朝系统中心 |
| `triple_layer_staggered_roi` | 三层交错环，全部朝指定 ROI 中心 |

## 4. 测试对象

| phantom | 含义 |
|---|---|
| `geometric_shapes` | 两个球体和一个立方体组成的简单几何对象 |
| `smooth_roi_target` | 平滑背景加一个偏心弱小 ROI 目标 |

## 5. 结果汇总

| phantom | architecture | layers | global RMSE | ROI RMSE | lower RMSE | middle RMSE | upper RMSE |
|---|---|---:|---:|---:|---:|---:|---:|
| geometric_shapes | `single_layer_center` | 1 | 0.00229263 | 0.00653674 | 0.00198305 | 0.00251141 | 0.00237157 |
| geometric_shapes | `double_layer_staggered_center` | 2 | 0.00302601 | 0.00689508 | 0.00198293 | 0.00260653 | 0.00406564 |
| geometric_shapes | `triple_layer_staggered_center` | 3 | 0.00237161 | 0.0066891 | 0.00208749 | 0.00261943 | 0.00240147 |
| geometric_shapes | `triple_layer_staggered_roi` | 3 | 0.00235102 | 0.00698571 | 0.00190179 | 0.00263067 | 0.00248422 |
| smooth_roi_target | `single_layer_center` | 1 | 0.00175436 | 0.00615427 | 0.0017834 | 0.00149099 | 0.00193701 |
| smooth_roi_target | `double_layer_staggered_center` | 2 | 0.00230148 | 0.00618583 | 0.00167688 | 0.0014369 | 0.00327414 |
| smooth_roi_target | `triple_layer_staggered_center` | 3 | 0.00173601 | 0.00626297 | 0.00178019 | 0.00142791 | 0.0019351 |
| smooth_roi_target | `triple_layer_staggered_roi` | 3 | 0.0018297 | 0.00647469 | 0.00173994 | 0.00146237 | 0.00218346 |

## 6. 初步观察

从全局 RMSE 看，两个 phantom 给出的趋势并不完全相同：

- `geometric_shapes` 的全局 RMSE 最优架构为 `single_layer_center`，数值为 `0.00229263`。相比之下，`double_layer_staggered_center` 增大到 `0.00302601`，约差 `31.99%`；`triple_layer_staggered_center` 为 `0.00237161`，约差 `3.44%`；`triple_layer_staggered_roi` 为 `0.00235102`，约差 `2.55%`。
- `smooth_roi_target` 的全局 RMSE 最优架构为 `triple_layer_staggered_center`，数值为 `0.00173601`，相比 `single_layer_center` 的 `0.00175436` 只改善约 `1.05%`。这说明三层轴向覆盖对平滑背景对象有轻微收益，但优势很小。
- `double_layer_staggered_center` 在两个 phantom 中都不是稳定改进：在 `smooth_roi_target` 中全局 RMSE 为 `0.00230148`，比单层中心环差约 `31.19%`。

从 ROI RMSE 看，当前“所有源朝 ROI”的规则并没有带来局部误差收益：

- `geometric_shapes` 的 ROI RMSE 最优仍是 `single_layer_center`，数值为 `0.00653674`。
- `smooth_roi_target` 的 ROI RMSE 最优也是 `single_layer_center`，数值为 `0.00615427`。
- 对真正含有偏心 ROI 弱目标的 `smooth_roi_target`，`triple_layer_staggered_roi` 的 ROI RMSE 为 `0.00647469`，比单层中心环差约 `5.21%`。因此，当前结果不支持直接采用“全 ROI 定向”作为默认策略。

## 7. `fig03_axial_rmse.png` 如何理解

`fig03_axial_rmse.png` 是轴向重建质量比较图。它不是全局误差图，也不是 ROI 误差图，而是把整个三维重建体积沿 z 方向分成三个 slab 后分别计算 RMSE：

| 图中柱子 | 含义 |
|---|---|
| `lower` | 下部 z 区域的 RMSE |
| `middle` | 中间 z 区域的 RMSE |
| `upper` | 上部 z 区域的 RMSE |

这张图的目的，是观察不同光源层数和层高设置是否改善了轴向覆盖。三维静态 CT 与二维问题不同，单层环主要提供某个 z 平面附近的角度覆盖；多层环理论上应改善 z 方向覆盖，但也可能因为固定总源数后每层源数减少、投影角度分配改变、SIRT 迭代不足或当前 detector tile 设计不够匹配而导致某些轴向区域误差升高。

因此，读这张图时不要只看某一个柱子，而要看：

1. 单层环是否只在中间区域较好；
2. 多层环是否降低 lower / upper 区域误差；
3. 是否存在某一层或某一轴向区域误差异常升高；
4. ROI 定向是否改善 ROI 所在 z 附近的 slab。

当前数据中，`geometric_shapes` 的轴向误差为：

| architecture | lower RMSE | middle RMSE | upper RMSE |
|---|---:|---:|---:|
| `single_layer_center` | 0.00198305 | 0.00251141 | 0.00237157 |
| `double_layer_staggered_center` | 0.00198293 | 0.00260653 | 0.00406564 |
| `triple_layer_staggered_center` | 0.00208749 | 0.00261943 | 0.00240147 |
| `triple_layer_staggered_roi` | 0.00190179 | 0.00263067 | 0.00248422 |

对 `geometric_shapes` 来说，双层交错环的 upper RMSE 明显升高到 `0.00406564`，这是它全局 RMSE 变差的主要来源。三层交错环把 upper RMSE 拉回到 `0.00240147`，说明增加第三层确实缓解了双层架构的轴向不平衡，但它仍没有超过单层中心环的整体表现。ROI 定向三层环在 lower 区域最好，但 middle 和 upper 区域并不占优。

`smooth_roi_target` 的轴向误差为：

| architecture | lower RMSE | middle RMSE | upper RMSE |
|---|---:|---:|---:|
| `single_layer_center` | 0.00178340 | 0.00149099 | 0.00193701 |
| `double_layer_staggered_center` | 0.00167688 | 0.00143690 | 0.00327414 |
| `triple_layer_staggered_center` | 0.00178019 | 0.00142791 | 0.00193510 |
| `triple_layer_staggered_roi` | 0.00173994 | 0.00146237 | 0.00218346 |

对 `smooth_roi_target` 来说，三层中心定向在 middle 和 upper 区域都最好或接近最好，因此获得最低全局 RMSE `0.00173601`。双层交错环虽然 lower 和 middle 较好，但 upper RMSE 升高到 `0.00327414`，导致整体表现变差。这说明当前双层高度和 detector tile 设置存在明显的上部轴向覆盖问题。

## 8. 基于当前输出数据的具体结论

### 8.1 多层是否明显优于单层

当前 quick 实验不能支持“多层一定优于单层”的结论。

在 `geometric_shapes` 中，单层中心环的全局 RMSE 为 `0.00229263`，优于双层交错环的 `0.00302601`、三层中心环的 `0.00237161` 和三层 ROI 定向环的 `0.00235102`。这说明对于当前简单几何对象，单层环已经能提供较好的中部覆盖，而多层分源后没有带来稳定收益。

在 `smooth_roi_target` 中，三层中心定向的全局 RMSE 为 `0.00173601`，略优于单层中心环的 `0.00175436`，提升幅度约为 1%。这说明三层结构对平滑背景对象的全局重建略有帮助，但优势很小，不能作为强结论。

### 8.2 层间交错是否值得保留

层间交错值得保留为后续候选自由度，但当前双层交错设置不应直接作为默认最优。

双层交错环在两个 phantom 中都出现 upper RMSE 异常偏高：

```text
geometric_shapes upper RMSE: 0.00406564
smooth_roi_target upper RMSE: 0.00327414
```

这说明当前双层 z 位置 `(-0.32, 0.32)` 和层间角偏移组合在上部区域覆盖不均衡。三层交错环显著缓解了这一点，因此后续搜索中应保留层间交错参数，但需要让 EIG / d' 自动选择层高和角偏移，而不是固定为当前规则值。

### 8.3 ROI 定向是否带来局部提升

当前结果不支持“ROI 定向一定带来 ROI RMSE 提升”。

在 `smooth_roi_target` 中，ROI RMSE 最低的是 `single_layer_center`，数值为 `0.00615427`；三层 ROI 定向反而为 `0.00647469`。这说明当前“所有源都朝 ROI”的策略过于激进，可能牺牲了整体角度覆盖，也没有在 SIRT 重建后的 ROI RMSE 上转化为收益。

这并不否定 ROI 定向自由度，而是说明后续不应只比较 `alpha=0` 和 `alpha=1` 两个极端。实验二中的 `orientation_alpha` 插值参数是必要的，后续 d' 精筛也应搜索中心定向到 ROI 定向之间的连续过渡。

### 8.4 后续优化应重点搜索哪些参数

根据实验一结果，后续 EIG / d' 优化应重点搜索：

1. `M_z`：层数，尤其是 2 层和 3 层之间的差异；
2. `z_m`：层高，当前双层高度导致 upper 区域误差升高；
3. `delta_m`：层间角偏移，当前固定交错不一定最优；
4. `alpha_m`：中心到 ROI 的朝向插值，不能只采用全中心或全 ROI 两个极端；
5. detector tile 尺寸和 cone angle：当前多层收益不稳定，可能与 detector patch 覆盖范围有关。

## 9. 阶段性结论

实验一的核心结论是：在当前 quick 级别 3D 设置下，规则架构之间确实存在可观测差异，但没有一个简单规则架构在所有指标上占优。

更具体地说：

1. 单层中心环在 `geometric_shapes` 上表现最好，说明单层并非天然不足；
2. 三层中心环在 `smooth_roi_target` 的全局 RMSE 上略优，说明轴向分层可能有价值；
3. 双层交错环存在明显 upper slab 误差升高，说明层高和角偏移必须被优化；
4. 全 ROI 定向没有降低 ROI RMSE，说明 ROI 定向应作为连续参数搜索，而不是直接采用极端规则；
5. 后续 EIG 粗筛的候选空间应包含层数、层高、角偏移和朝向插值，而不是只在固定规则架构之间选择。

当前实现采用 quick 级别 3D SIRT 重建，适合验证流程和相对趋势。后续论文级实验需要提高体素数、探测器采样和投影物理真实性，并引入三维 EIG 与 d' 设计准则。
