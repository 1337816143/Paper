# Q方法合成计算：阅读、运行与核对

网页已经包含完整结果，可以直接追踪20条原创陈述、10份合成排序，不需要先安装软件。它不是Cheng的327份原始Q-sorts，也没有受访者访谈。

## Python：同一份输入，两套明确情景

把 `q_pipeline.py` 和 `q_synthetic.csv` 放在同一目录。使用Python3和NumPy2.3.5；如需安装依赖，使用官方PyPI：

```text
python -m pip install numpy==2.3.5
python q_pipeline.py --scenario baseline --output q_results.json
python q_pipeline.py --scenario reverse-p03 --output q_reverse_results.json
python q_pipeline.py --test
```

第一条分析保留原合成CSV；第二条仅将P03分数改成 `6−原分数`，再重算整条链。每人的2/4/8/4/2槽位保持不变。输出JSON包含原分数、10×10人物相关、特征值/载荷、旋转、标记、权重、20×2的z和典型排序、可靠性假设及两因子差异比较。

文件前两列是陈述ID和原创陈述文本；其后每一列是一人的20个排序位置。不要将输入转成“人作行”后仍直接使用同一工具接口。页面人物/陈述选择器只追踪结果中的对象；手动转轴是几何预览，不重新生成varimax模型。

## 代码怎样对应步骤

1. `read_data`检查陈述/人物身份、完整性与网格
2. `analyze`构造人物相关矩阵，提取两个PCA方向，并调用`varimax`
3. `automatic_flags`同时检查绝对载荷门槛和严格平方优势
4. `postprocess`使用带符号权重，逐条得到总和、z、factor array及两因子比较
5. `rank_to_grid`按平均名次与声明的索引规则分配离散分数，保留精确同分的影响

固定两因子是教学选择，第三特征值仍大于1；不能称为自动因子数选择。未旋转轴与最终旋转因子各有明确符号/顺序约定，以避免不同计算环境把同一轴整体翻转后误读为新结果。

## R参考与真正的软件对照

`qmethod_reference.R`和CSV也放在一起。参考环境明确固定为R4.4.3、qmethod1.8.4、psych2.5.6；这是本站的对照环境，不是已经查明的作者环境。作者主文报告R4.4.0，其确切包版本、全部选项仍未知。

脚本同时导出两个模式：

- `matched`：Kaiser归一化，显式相对收敛参数eps=1e-12，供数值一致性门槛使用
- `native-default`：保留eps=1e-5，单独展示默认停止设置可能引起的差别，不作为失败后的替代通关门槛

正确安装这些版本后可运行：

```text
Rscript qmethod_reference.R --output-dir q-r-reference
```

它会生成各阶段CSV、原始/规范化后的RDS对象、版本及`sessionInfo`记录。出现这些文件本身不等于已经验证一致；完整仓库的 `tests/q/compare_r_reference.py` 才按事先声明的容差、因子符号/列顺序对齐、精确标记/排名/数组和区分类别进行比较。

完整自动对照流程、经SHA256核验的官方CRAN源包、固定数值容差见仓库 `tests/q/reference-manifest.json` 与下载的 `q_method_sources.json`。比较器缺少真实R导出时会失败；不得生成假的R结果或扩大容差来掩盖差异。实际通过状态应以对应发布commit的CI报告为准。

## 已发表表格与本例不要混用

网页的Farmer_1类别均值取自论文Table5已发表factor scores；它们不是本站S01–S20，也不是农户原始记录。Table2类别成员→Table5分值→类别和/均值可以逐项核算。2026-10-05已核对官方SI pp.3–5及TableS3 p.14：按固定网格的类别可达上下界作0–100缩放，72个已发表类别值均在印刷精度下匹配。SI权重最大值归一到10是共同正缩放；在SD>0且同一SD口径下不改变z。现有toy输入、代码和数值不改，作者327人原始复现仍未完成。官方SI：https://ars.els-cdn.com/content/image/1-s2.0-S0308521X24003378-mmc1.pdf

本文的载荷、z、网格分数、类别均值和计算权重均不能自动转成农场优化目标权重、人口比例或采纳概率。实际观点命名还要结合访谈，不能为合成人物编造动机。


## 5.5.9：官方SI的两条可核对支路

1. 既有20×10原创合成排序：页面第5步展开“最大权重归一到10”，可切换人、陈述、因子和反向情景，查看原w与W、Total、均值、SD和z。共同有限正倍数、同一集合/SD口径且SD>0时z不变；不修改原数值管线。
2. 已发表数值事实：`q_published_tables.json`转录主文Table5和SI TableS3的数字；这不是合成受访者数据，更不是原始327份排序。运行`python q_si_categories.py --json`查看18×4完整推导；`--test`核对72格和严格>50边界，不需第三方包。

这两条支路不能拼接成作者完整研究复现。SI PDF不随公开资源新增发布；原公式通过出版商链接访问。旧20节文字/锚点保留，s16/s19前有历史状态提示，新增s20–s22承担当前来源校正。
