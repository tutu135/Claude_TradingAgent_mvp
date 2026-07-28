# 单股票投研证据链 Demo

这是一个个人、非商业、离线运行的工程验证 Demo。项目以中芯国际（`688981.SH`）的一份冻结公开资料快照为输入，验证一条投研分析链能否做到：**报告中的数字与重要判断，可沿证据链回溯到原始材料中的具体位置。**

它不是实时投研平台，不提供买卖建议、目标价、估值、仓位或投资评级。

## 研究范围

| 项目 | 内容 |
| --- | --- |
| 研究对象 | 中芯国际（`688981.SH`） |
| 信息截止时间（`as_of`） | `2026-05-15T23:59:59+08:00` |
| 核心观察期 | FY2023–2026 Q1 |
| 当前快照 | v3 `smic-a283e95e2c9e8068`，20 份材料 |
| 运行模式 | `FROZEN_REPLAY`：正式重放时不调用模型 |
| 报告用途 | `INTERNAL_DEMO_ONLY`，等待人工审阅 |

冻结的研究问题是：截至 `as_of`，中芯国际的经常性经营盈利能力发生了哪些可验证的变化？现有证据在多大程度上支持其已进入可持续改善阶段？

项目不预设结论：结果可以是支持、混合、反驳或证据不足。

## 这条链如何工作

```text
冻结研究材料
  → 结构化上下文（chunk）
  → 规整事实（fact）
  → 治理证据（evidence）
  → D1–D7 研究发现（finding）
  → 反方质询（challenge）
  → 内部报告（report）
```

每一层都有独立的 ID 与定位关系：

```text
material_id → chunk_id → fact_id → evidence_id → finding_id → challenge_id
```

材料被采集进快照，并不表示其已经可信。只有通过来源、内容、同源关系、冲突与用途治理的 `USABLE` 证据，才可以支撑研究发现。模型仅在离线判断阶段选择证据和表达方向；证据分由脚本反算，运行期读取冻结的判断输入并执行确定性校验。

## 当前交付物

- [最终内部报告](single-stock-demo-run/report.md)：固定十章节报告与证据表。
- [报告校验记录](single-stock-demo-run/report-validation.yaml)：数字绑定、溯源链与报告结构的校验结果。
- [运行门禁结果](single-stock-demo-run/run-gate.yaml)：治理状态和报告形态。
- [项目导览](docs/PROJECT-GUIDE.md)：完整的数据流、目录导航、实际运行结果和已知问题。
- [导师汇报版说明](docs/mentor-project-report.md)：面向非技术读者的项目概览。

当前黄金案例的最终结论以报告为准；它展示的是证据承载能力，不是投资结论。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `CONTEXT.md` | 领域术语与定义的权威词汇表 |
| `contracts/` | 阶段之间的文件契约与溯源关系 |
| `rules/` | 规整、检索、证据治理、分析与报告规则 |
| `scripts/` | 八个阶段的命令行实现与运行门禁 |
| `tests/` | 对阶段契约和关键边界的自动化测试 |
| `frozen-analysis-inputs/` | 已冻结的模型判断输入及其哈希清单 |
| `single-stock-demo-v3/` | 当前快照的元数据、材料清单与输入绑定 |
| `single-stock-demo-run/` | 可重建的运行目录；仅保留稳定的最终交付物 |
| `docs/adr/` | 关键架构取舍：冻结快照、采集/治理分离、冲突范围、分析分层、冻结重放 |
| `DEMO-KNOWN-ISSUES.md` | 已知限制与未修复问题登记册 |

历史快照 `single-stock-demo/` 与 `single-stock-demo-v2/` 保留为不可变历史输入，不是当前运行的材料来源。

## 安装与查看

运行环境为 Python 3.11。安装依赖：

```bash
python -m pip install -r requirements-dev.txt
```

然后可直接阅读已入库的最终报告与校验记录。阶段脚本位于 `scripts/`；完整七阶段重放顺序及参数以 [项目导览](docs/PROJECT-GUIDE.md) 和 `single-stock-research-orchestrator` 的工作指引为准。

## 可复现性与材料边界

本仓库提交了代码、规则、快照元数据、冻结判断输入、最终报告和稳定校验产物。为控制仓库体积并尊重第三方材料的使用边界，以下内容不会随 Git 分发：

- `single-stock-demo-v3/raw/`：原始 PDF、HTML 与文本材料；
- `single-stock-demo-v3/parsed/`：由原始材料生成的解析结果；
- 运行目录中的大体积中间产物；
- 本机缓存与临时文件。

因此，克隆仓库后可以审阅代码、规则、冻结绑定和最终产物；要执行完整重放，必须通过合规渠道取得**相同的冻结材料**并放入预期目录。不得以实时联网、后续资料或模型估计替代这些输入。

`frozen-analysis-inputs/frozen-inventory.yaml` 记录冻结判断输入的哈希，`.gitattributes` 将文本文件固定为 LF，以避免在不同操作系统中因换行差异破坏完整性校验。

## 已知限制

这是一个有意收窄范围的 Demo，当前已知限制包括：部分数值抽取可能存在语义错误；部分维度缺少可承重数值证据；真实材料尚未触发所有冲突和隔离分支。项目选择通过 `UNKNOWN`、gap 和报告警示保留这些限制，而不是用默认值、模型常识或新资料补齐。

详见 [DEMO-KNOWN-ISSUES.md](DEMO-KNOWN-ISSUES.md) 与 [产品范围说明](docs/product/demo-scope.md)。
