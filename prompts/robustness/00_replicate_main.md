# 复现主回归（四要素 Prompt）

> 对应Part A 2.2：用四要素 Prompt 复现主回归，确认与 `output/stata_did_results.csv` 一致。

## Prompt（四要素）

**主回归设定（渲染版）**：

$$
\log TFP_{it} = \alpha_i + \lambda_t + \tau\, Digital_{it} + X_{it}'\beta + \varepsilon_{it}
$$

其中 $\alpha_i$ 为企业固定效应，$\lambda_t$ 为年份固定效应，$X_{it}$ 为控制变量向量（资本密集度、出口占比、所有制），标准误聚类到企业层面。

> 以下是完整四要素 Prompt（供 AI 阅读的纯文本）：

```Markdown
【目标】用 data/raw/digital_transformation_firm_panel.csv 复现 DID 主回归：
$$
\log TFP_{it} = \alpha_i + \lambda_t + \tau\, Digital_{it} + X_{it}'\beta + \varepsilon_{it}
$$
标准误聚类到企业层面（firm_id）。估计系数应报告 digital 的系数、聚类标准误、t 值、p 值与样本量。

【边界】这是合成数据演示，结果不能解释为真实因果证据；不要虚构文献；只读 data/，不修改任何数据文件。

【验证】输出应包含 output/main_did_results.csv，digital 系数符号为正、量级约 0.1；
聚类标准误应为有限正数（不得为 NaN）；若与 output/stata_did_results.csv（digital=0.1209, SE≈0.0047）差异较大请说明原因。

【汇报】汇报：digital 系数、聚类标准误、t 值、p 值、样本量，以及你的观察：
- 系数是否与课堂 Stata 主结果一致？
- 标准误是否正常（解决课堂脚本 analyze_did.py 中 SE 为 NaN 的问题）？
```

## 为什么需要"干净脚本"（问题与修复）

- **设定公式中 $X_{it}$ 完整包含三个控制变量（资本密集度、出口占比、所有制）**，
  与企业固定效应模型公式保持一致；但由于 `export_share`、`soe` 企业层面不随时间变化，
  会被企业固定效应完全吸收（不识别），实际估计中不单独放入，不影响 `digital` 的估计。
- 课堂脚本 `scripts/analyze_did.py` 的模型同时包含 `soe`、`export_share`，
  但这两个变量**企业层面不随时间变化**，会被企业固定效应完全吸收 → 设计矩阵秩亏
  （SingularMatrixWarning），且聚类标准误在 statsmodels 0.15 下计算为 **NaN**。
- 修复：主回归模型移除被企业固定效应吸收的 time-invariant 变量（`soe`、`export_share`），
  仅保留随时间变化的处理变量与协变量。这不改变 `digital` 的估计，但能给出正常的聚类标准误。

## 运行

```bash
python scripts/estimate_main_did.py
```

## 结果摘要

- DID 系数：digital = 0.1209（聚类标准误 ≈ 0.0047，t ≈ 25.6，p < 0.001，N = 3240）
- 与 `output/stata_did_results.csv`（digital = 0.1209，SE = 0.0047）**一致**。

## 我的观察

- 复现成功：系数与显著性完全吻合课堂 Stata 主结果。
- 修复了课堂脚本"聚类标准误 NaN"的缺陷（原因是 time-invariant 变量与企业固定效应共线）。
