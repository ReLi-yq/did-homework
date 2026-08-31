# 迭代反思（2 轮）

> 迭代 = 观察输出 → 记录问题 → 修订设计 → 重新运行 → 对比。本文件记录作业过程中真实发生的问题与改进。

## 第一轮：初版的问题与修订

### 我观察到的关键问题

1. **课堂脚本聚类标准误为 NaN**：`scripts/analyze_did.py` 的模型同时包含 `soe`、`export_share`，
   这两个变量企业层面不随时间变化，与企业固定效应完全共线 → 设计矩阵秩亏（SingularMatrixWarning）
   → statsmodels 0.15 聚类标准误计算为 **NaN**，无法判断显著性。
2. **R1 事件研究实现反复报错**：先 `.astype("category")`（NumPy 数组不支持该类型）；
   再用含负号的列名 `ry-4`（被公式解析器当作减号运算符）；最后 `C(ry)+C(year)` 在同步处理下共线，
   联合 F 检验返回 NaN。
3. **环境混乱**：`linearmodels` 被装进课堂项目的 `.venv`，而 did-homework 的 `.venv` 是独立环境，
   import 多次失败；激活状态跟随终端走，导致"明明激活了却装错地方"。

### 我做的修订

1. 写干净主回归脚本 `estimate_main_did.py`：移除被企业 FE 吸收的 time-invariant 变量
   （`soe`、`export_share`），聚类标准误恢复正常（0.0047），且 `digital` 系数不变（0.1209）。
2. 重写 R1：手动构造**不含负号**的相对年份虚拟变量（`pre4/pre3/pre2/post0...`）+ Wald 联合检验，
   避开公式解析与共线问题。
3. 用 did-homework 的 `.venv\Scripts\python.exe` **显式**安装 linearmodels，绕开激活状态混乱。

### 证据

- `output/main_did_results.csv`：SE = 0.0047（正常，修复 NaN）；digital = 0.1209 与 Stata 一致。
- `R1_pre_joint_p` = 0.69（平行趋势通过）；`robustness_table_r1_r7.csv` 全部 `[OK]`。
- git log：`efae6b3 feat: 复现主回归并修复聚类标准误`。

## 第二轮：Skill 与 Agent 的迭代

### 我观察到的关键问题

1. **Skill 层面**：用"裸 Prompt"驱动检验时没有内置检查清单——容易漏检查共线/SE、没固定随机种子、
   没强制把 Prompt 与结果存为 Markdown；且硬编码变量名（`digital`、`log_tfp`、`firm_id`），
   换一个研究主题就失效。
2. **Agent 层面**：初版容易"只堆数字"（列一张系数表 + 是否显著），
   说不清"这对数字化转型研究意味着什么"，没指出残余威胁，也没给论文写作建议。

### 我做的修订

1. **Skill**：写成完整六模块 `SKILL.md`（触发条件/背景知识/工作步骤/检查清单/边界条件/验证方式），
   用 `{outcome}/{treatment}/{id}/{time}` 占位符，要求"先读 README/数据自动识别变量"，
   末尾加"如何迁移"一节论证一般适用性。
2. **Agent**：设计六步流程 `eval-did-robustness`（S1 读结果 → S2 判定 → S3 稳定性 → S4 残余威胁
   → S5 主题解读 → S6 写作建议），并强制输出边界声明、缺输入停下询问。

### 证据

- `.claude/skills/robustness-check/SKILL.md`（六模块 + 迁移）；`audit-log.md` 中"Skill vs 裸 Prompt"对比。
- `output/eval_robustness_report.md`：含稳健性判定表、结论稳定性、**残余威胁**、**主题解读**、
  **写作建议（能说/不能说）**、边界声明。
- 对比：裸 Prompt 版本（Part A 初版）漏检查清单 vs Skill 版本（内置共线/SE/落盘检查），
  差异本质是"制度内置" vs "每次提醒"。

## 一般适用性论证

- **换一个研究主题（如"最低工资对就业""医保对健康"），我的 Skill/Agent 需要改哪里？**
  - 数据路径、结果/处理/个体/时间变量名——由 AI 先读 README/数据自动识别；
  - 处理时间是否交错——影响事件研究写法；
  - 聚类层级、固定效应组合——按研究设计调整。
- **不需要改哪里？**
  - Skill 的工作步骤（识别→复现→逐项检验→留痕→汇总）、检查清单（共线、SE、平行趋势、越界表述）、
    边界与验证方式；
  - Agent 的六步流程（S1–S6）、输出模板、边界与验证方式。
- **结论**：我的设计是"可迁移的制度"（框架通用、变量/数据自适应），而非"本项目的定制脚本"。
