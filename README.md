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

运行环境为 Python 3.11。克隆仓库后，在 PowerShell 中执行：

```powershell
git clone https://github.com/tutu135/Claude_TradingAgent_mvp.git
cd Claude_TradingAgent_mvp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

如果只是阅读项目，可直接查看已入库的最终报告与校验记录。若要执行完整的冻结重放，请继续阅读下一节。

## 受控完整重放

### 适用范围与材料边界

本仓库提交了代码、规则、快照元数据、冻结判断输入、最终报告和稳定校验产物。为控制仓库体积并尊重第三方材料的使用边界，以下内容不会随 Git 分发：

- `single-stock-demo-v3/raw/`：20 份原始 PDF、HTML 与文本材料；
- `single-stock-demo-v3/parsed/`：与原件一一对应的 20 份解析结果；
- 运行目录中的大体积中间产物；
- 本机缓存与临时文件。

完整重放只适用于两种情形：接收者已自行获得这些材料的合法使用权限，或材料提供者已确认拥有向接收者交付的权利。**私下转发不自动取得第三方材料的再分发权。**

材料一旦具备合法交付条件，提供方应交付 v3 快照中原样的 `raw/` 与 `parsed/` 两个目录。接收者应将其中的文件分别放到：

```text
single-stock-demo-v3/raw/
single-stock-demo-v3/parsed/
```

不要改名、编辑、重新下载或补入任何材料；不要把这些目录添加到 Git。`single-stock-demo-v3/snapshot-manifest.yaml` 记录了全部 40 个文件的 SHA-256，阶段 1 会校验文件完整性与哈希。历史 v1/v2 快照不是当前黄金案例的输入，不需要交付。

### 固定版本

完整重放必须使用提供方指定的仓库提交，而不是随后的 `main`。提供方应同时告知接收者提交 SHA；接收者在安装依赖后执行：

```powershell
git checkout <提供方给出的提交SHA>
```

`.gitattributes` 已将受管文本固定为 LF。不要用编辑器批量改写冻结输入的换行或编码，否则哈希校验会失败。

### 执行步骤

以下命令必须在仓库根目录执行，且顺序不可调整。`FROZEN_REPLAY` 不联网、不重新调用模型；分析与质询读取已纳入仓库并受哈希保护的冻结判断输入。

```powershell
$Run = "single-stock-demo-run"

# 0. 清空运行目录，校验冻结判断输入与绑定
python scripts/validate_demo_run.py preflight

# 1. 校验 v3 冻结材料，不下载、不刷新
python scripts/acquire_research_materials.py DEMO_RUN `
  --case-file single-stock-demo-v3/case.yaml `
  --snapshot-dir single-stock-demo-v3

# 2. 构建结构化上下文与固定查询召回结果
python scripts/govern_research_context.py `
  --snapshot-dir single-stock-demo-v3 `
  --rules-file rules/context-retrieval.yaml `
  --acceptance-file tests/fixtures/retrieval-acceptance-smic-v3.yaml `
  --output-dir $Run

# 3. 规整事实
python scripts/normalize_research_facts.py `
  --snapshot-dir single-stock-demo-v3 `
  --context-file "$Run/context.jsonl" `
  --retrieval-file "$Run/retrieval-validation.yaml" `
  --rules-file rules/accounting.yaml `
  --existing-gaps-file single-stock-demo-v3/gaps.yaml `
  --output-dir $Run

# 4. 证据治理与校验
python scripts/govern_validate_research_evidence.py `
  --snapshot-dir single-stock-demo-v3 `
  --facts-file "$Run/normalized-facts.jsonl" `
  --context-file "$Run/context.jsonl" `
  --rules-file rules/source-governance.yaml `
  --existing-gaps-file "$Run/gaps.yaml" `
  --output-dir $Run

# 5. 确定性选择候选集，并消费冻结的模型判断、反算证据分
python scripts/analyze_and_score_research_findings.py select `
  --snapshot-dir single-stock-demo-v3 `
  --context-file "$Run/context.jsonl" `
  --facts-file "$Run/normalized-facts.jsonl" `
  --evidence-file "$Run/governed-evidence.jsonl" `
  --rules-file rules/analysis.yaml `
  --existing-gaps-file "$Run/gaps.yaml" `
  --output-dir $Run

python scripts/analyze_and_score_research_findings.py finalize `
  --analysis-inputs "$Run/analysis-inputs.jsonl" `
  --model-findings frozen-analysis-inputs/findings-attempt-1.yaml `
  --model-findings frozen-analysis-inputs/findings-attempt-2.yaml `
  --rules-file rules/analysis.yaml `
  --existing-gaps-file "$Run/gaps.yaml" `
  --output-dir $Run

# 6. 执行冻结的反方质询与定向复核
python scripts/challenge_research_findings.py `
  --findings-file "$Run/findings.yaml" `
  --analysis-inputs "$Run/analysis-inputs.jsonl" `
  --model-challenges frozen-analysis-inputs/challenges-model.yaml `
  --rules-file rules/analysis.yaml `
  --existing-gaps-file "$Run/gaps.yaml" `
  --output-dir $Run

# 7. 汇总门禁、渲染报告、封存清单
python scripts/validate_demo_run.py gate
python scripts/generate_research_report.py
python scripts/validate_demo_run.py finalize-manifest
```

### 失败处理

如果第 0 步 `preflight` 非零退出，立即停止第 1–6 步。不要尝试修改冻结输入或跳过校验；只执行以下三个收尾命令，以生成不含任何研究结论的 `DIAGNOSTIC_ONLY` 诊断报告：

```powershell
python scripts/validate_demo_run.py gate
python scripts/generate_research_report.py
python scripts/validate_demo_run.py finalize-manifest
```

常见原因是：冻结判断输入的哈希或绑定不匹配、v3 快照身份错误，或运行目录出现非清单内的受管格式文件。第 1 步失败则通常表示私下交付的 `raw/` 或 `parsed/` 文件缺失、改名或字节不一致；应重新核对 `single-stock-demo-v3/snapshot-manifest.yaml`，而不是重新联网获取材料。

### 结果核对

一次成功的当前黄金案例重放应满足：

- `single-stock-demo-run/run-integrity.yaml`：`integrity_status: PASS`；
- `single-stock-demo-run/run-gate.yaml`：`report_form: FULL_REPORT`、`governance_status: WARN`；其中规整、证据治理与质询的 `WARN` 是已登记限制，不是本次重放失败；
- `single-stock-demo-run/report-validation.yaml`：`report_validation_status: PASS`、`leaked_unbound_numeric_mentions: 0`、`traceability.unresolved: []`；
- `single-stock-demo-run/report.md`：生成完整十章节内部报告。

要验证确定性重放，可保存第一次的报告哈希、再次从第 0 步完整执行，然后比较两次哈希：

```powershell
Get-FileHash "$Run/report.md" -Algorithm SHA256
Get-FileHash "$Run/report-validation.yaml" -Algorithm SHA256
```

两次的 `report.md` 与 `report-validation.yaml` 应一致。`manifest.yaml` 中的 `generated_at` 会随运行时间变化，不应直接要求其文件哈希完全相同；其余记录的输入/输出哈希与状态应一致。

## 已知限制

这是一个有意收窄范围的 Demo，当前已知限制包括：部分数值抽取可能存在语义错误；部分维度缺少可承重数值证据；真实材料尚未触发所有冲突和隔离分支。项目选择通过 `UNKNOWN`、gap 和报告警示保留这些限制，而不是用默认值、模型常识或新资料补齐。

详见 [DEMO-KNOWN-ISSUES.md](DEMO-KNOWN-ISSUES.md) 与 [产品范围说明](docs/product/demo-scope.md)。
