# 06 — 编排黄金案例并生成内部报告

**What to build:** 让用户可以对冻结的中芯国际黄金案例启动一次固定流程，依次完成八个 Skills，得到每个数字均可追溯、经过质询且明确展示治理限制的 Markdown 内部报告。该 ticket 完成 `single-stock-research-orchestrator`、`generate-research-report` 和端到端验收。

**Blocked by:** 05 — 形成并质询 D1–D7 发现。

**Status:** done

- [x] 编排器按固定七阶段顺序调用八个 Skills，只负责输入检查、阶段结果、停止/降级和最多两轮质询回路；阶段 Skill 不直接互调。
- [x] 编排器使用至少 3 个应触发问题和 3 个不应触发问题验证范围识别，不引入通用 DAG、队列、调度器、数据库、模型路由或插件系统。
- [x] 报告按确认的十个章节输出，清楚分开研究问题、分析框架和流程状态；D1–D7、质询修订、冲突、UNKNOWN/TBD、隔离和数据限制均可见。
- [x] 报告中的每个数字均显示或可直接追溯来源、发布时间、报告期间/时点、单位、币种、缩放、口径和 `evidence_id`；派生值还展示公式与输入。
- [x] 固定 `distribution_status=INTERNAL_DEMO_ONLY`，独立显示 `governance_status=PASS/WARN/FAIL` 和 `PENDING_HUMAN_REVIEW`；即使 FAIL 也生成显著标警的内部诊断报告，隔离数据不支撑发现。
- [x] 报告不生成 PDF、网页、Dashboard、API 或外部分发物，也不包含交易指令、仓位建议、目标价锚、投资吸引力判断和系统预测。
- [x] 端到端运行证明 `DEMO_RUN` 不实时联网、拒绝 `as_of` 越界材料，任一报告数字可沿 `evidence_id -> fact_id -> chunk_id -> material_id` 回溯，**调节桥接公式可复算**，同源转载不会增加独立证据。
- [x] 冲突隔离与发现降级、政府补助敏感性、`FAIL` 仍有诊断报告三项**机制由 fixtures 覆盖，真实运行结果如实披露**（v3 实测冲突 0、隔离 0、敏感性 0 条、五个状态无一 FAIL）；缺数产生 UNKNOWN/gap，政府补助保持双口径，D1–D7 状态合法，质询不超过两轮，没有禁止输出。
- [x] 最终产物清单记录 `snapshot_id`、规则版本、权威文件哈希、生成时间、治理/分发/人工复核状态；固定案例文件完整且 CSV 如存在只作为派生视图。
- [x] 实现只包含确认的八个 Skills、集中脚本、单一规则来源和固定案例文件；每个组件都能对应 Spec 验收条件，没有为未来产品预建基础设施。

## Comments

### 冻结规划（2026-07-22 grilling，逐项用户确认）

架构决定见 `docs/adr/0005-replay-frozen-judgment-and-keep-the-orchestrator-a-validator.md`。新术语 `黄金案例运行`、`冻结重放`、`冻结判断输入`、`运行目录`、`完整性失败`、`报告形态`、`治理状态`、`证据表`、`未绑定数字`、`范围识别` 已入 `CONTEXT.md`（编排层原先一个术语都没有）。十章节顺序、禁止输出、发布门槛沿用 FR-070/071/072/073/080，本次不改。

#### 事实基线（实测，非回忆）

| 项 | 实测值 |
|---|---|
| 五个阶段状态 | `retrieval_status` PASS、`normalization_run_status` WARN、`validation_status` WARN、`analysis_run_status` PASS、`challenge_run_status` WARN |
| `record_kind` 分布 | `TEXT_PROPOSITION` 15,539 + `NUMERIC_OBSERVATION` 4,575，**`DERIVATION` 0 条** |
| 可复算公式 | 7 条 IFRS/CAS `reconciliation_check`（全部 `PROFIT_ATTRIBUTABLE_TO_OWNERS`），4 PASS / 3 UNKNOWN；04 已复算 4 条全 PASS |
| 政府补助 | `GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL` 观察 15 条，`SENSITIVITY_EX_GOVERNMENT_FUNDING` 派生 **0 条**，且无对应 gap |
| 冲突与隔离 | `quarantined_count` 0、`detected_conflict_group_count` 0、`unresolved_conflict_group_count` 0 |
| 证据/事实基数 | 20,114 行证据 / 20,114 unique `evidence_id` / 20,114 unique `fact_id`，**严格 1:1**，无 `fact_id` 被多条证据引用 |
| 散文中未绑定数字 | 约 **417** 个：`finding_statement` 90、`supporting_evidence.note` 115、`limitations` 108、`counter_evidence.note` 42、`management_assertions.statement` 36、`alternative_explanations` 17、`overlap_note` 9 |
| gaps | 4,921 条；`NORMALIZATION_UNKNOWN` 4,912（99.8%）；P1 4,915 / P2 6 |
| 版本控制 | `.gitignore` 第 15 行 `tmp/`，`git ls-files tmp/` 结果 **0**——冻结判断输入（212KB）当前不在版本控制内 |

#### 1. 执行模式：`FROZEN_REPLAY`（ADR 0005 决定一）

模型判断产物是**冻结判断输入**，不在运行中重新生成；编排器运行期间不发生任何模型调用。票面第 7、8 条判定的是"从冻结输入到最终产物的确定性重放"。

绑定检查**两道闸 + 一项登记**，不设七项：

- 闸：`selection_hash`（传递性覆盖 `snapshot_id`、`context_rule_version` 与选取规则）、`rules_hash`（`rules/analysis.yaml`）
- 只登记不设闸：模型标识——不可校验，做成闸门是假闸门
- 不新增 `analysis_schema_version`（05 逐次校验已拒绝不合规输出）、不引 prompt hash（导出量非独立量）、不新增 `numeric_claim_id`（`evidence_id ↔ fact_id` 实测 1:1）

**待补**：两个模型输出文件当前只带 `snapshot_id`，需各加 `selection_hash` 与 `analysis_rule_version` 两个字段。

#### 2. 目录布局（纠正契约地图与现实不符之处）

契约地图画的是 `<snapshot-dir>/` 下摆着从 `case.yaml` 到 `report.md` 的全部产物；实际 v3 快照只有 5 个入库文件，03/04/05 产物散在六个 `tmp/ticket0N-*` 手工目录。且往快照目录写下游产物会破坏其自包含冻结身份。

```
只读输入
├── single-stock-demo-v3/           冻结快照（采集产物）
└── frozen-analysis-inputs/         冻结判断输入，入库（新建，212KB）
    ├── findings-attempt-1.yaml
    ├── findings-attempt-2.yaml
    ├── challenges-model.yaml
    ├── analysis-validation.yaml
    └── analysis-attempts.jsonl

可重建输出
└── single-stock-demo-run/          运行目录，每次从固定清单清空
    ├── ...  report.md  manifest.yaml
```

- 契约地图相应更正为"快照目录（只读） + 运行目录（产物）"两块。这是纠正一处已与现实不符的文档，不是新增结构。
- 权威文件清单**照实际文件名冻结**（`evidence-validation.yaml` 而非契约地图写的 `validation.yaml`；另有 `retrieval-validation.yaml`、`normalization-validation.yaml`、`analysis-validation.yaml`），改契约地图，不为对齐文档去重命名已跑通的产物。
- **清空方式**：`validate_demo_run.py` 不接受路径参数，运行目录是硬编码常量；**不做递归删除**，只删固定文件名清单内的文件。没有用户路径就没有路径校验，没有 `rm -rf` 就没有递归删除风险。
- **陌生文件阻断**：运行目录出现固定清单以外的 `.yaml`/`.jsonl`/`.md` 时，在消费任何输入之前停止，不静默删除，记结构化 gap；其他文件（`Thumbs.db`、`desktop.ini`、`__pycache__/`）忽略。按格式限定复用契约地图已冻结的"YAML/JSONL/Markdown"三格式约定，不新增判据，也不会被 Windows 噪声误触发。

#### 3. `manifest.yaml`

按审计语义分区，输入与输出不混：

```yaml
frozen_inputs:
  source_snapshot: {snapshot_id, files: [...]}
  analysis_inputs: {execution_mode: FROZEN_REPLAY, files: [...]}
generated_outputs:
  files: [...]
```

- 另含规则版本、生成时间、`governance_status`、`distribution_status: INTERNAL_DEMO_ONLY`、`human_review_status: PENDING_HUMAN_REVIEW`、`report_form`、工具版本摘要。
- **自引用哈希**：manifest 只列其他文件哈希，**不记录自身哈希**；测试从外部计算并比较两次运行的 manifest 哈希。不新增 `run-digest.txt`。
- **哈希只出现在 `manifest.yaml`，绝不写进 `report.md` 正文**——保持渲染层与执行模式解耦，将来改报告或改执行模式互不牵动。

#### 4. 停止 / 降级与报告形态

`report.md` **恒被生成**，不存在"编排器静默停止"。两种形态且仅两种，形态记入 manifest：

| 触发 | 形态 | 内容 |
|---|---|---|
| **完整性失败**：冻结判断输入缺失/哈希不符/绑定不符、快照身份不符、运行目录有清单外权威格式文件、`as_of` 越界材料 | `DIAGNOSTIC_ONLY` | 顶部显著失败横幅 + 失败诊断 + reason code + gap 引用，**不含任何 D1–D7 结论** |
| **内容级失败**：任一 run status 为 WARN/FAIL、`governance_status=FAIL` | `FULL_REPORT` | 固定十章节 + 显著标警；隔离数据剔除、失败维度标 UNKNOWN |

判据是失败性质而非严重程度：**输入不可信 → 只出诊断；结论不合格 → 出报告并标警**。完整性检查在消费任何输入之前完成，此时尚无产出，停止代价为零。带结论的报告在完整性失败时输出会违反 FR-072「治理失败时受影响数据不能支撑研究发现」，且产出一份自我矛盾的文件。

reason code 固定三个：`FROZEN_ANALYSIS_INPUT_MISSING`、`FROZEN_ANALYSIS_HASH_MISMATCH`、`FROZEN_ANALYSIS_BINDING_MISMATCH`。不设 `SCHEMA_INCOMPATIBLE`（与 05 schema 闸重复）、不设 `SNAPSHOT_MISMATCH`（是 `BINDING_MISMATCH` 子集）；内容级失败走既有的各阶段 run status，不另起码。

#### 5. `governance_status`

= 检索 / 规整 / 证据治理三个状态按 `FAIL > WARN > PASS` 取最坏 → **实测 `WARN`**。分析与质询两个状态**不并入**，在报告中原样并列展示。

治理与分析是 Spec 里两条不同概念轴（ADR 0004 专门把分析层保证从哈希移到校验，它不属于治理）；FR-072 只要求一个 `governance_status`，造跨轴总状态会同时丢信息和混淆语义。

#### 6. 范围识别（票面第 2 条）

编排器不调模型，因此范围识别是**确定性**的，复用已冻结常量，不建意图分类器：

- **R1** 命中 `rules/analysis.yaml` 已有的禁止输出词表 → `OUT_OF_SCOPE_FORBIDDEN_OUTPUT`——**有牙齿的真实闸门**，撞 FR-073 硬线时拒答，绝不顺着回答
- **R2** 提到固定标的以外的主体 → `OUT_OF_SCOPE_OTHER_SUBJECT`——免责声明
- **R3** 目标期间晚于 `as_of` → `OUT_OF_SCOPE_BEYOND_AS_OF`——免责声明

范围外问题**不拒绝出报告**：编排器对固定黄金案例照常跑完，生成主问题的完整报告，开头加固定说明"本 Demo 只研究〔主研究问题〕；对超出范围的问题（投资建议 / 其他标的 / `as_of` 之后）不作回答，亦不作任何推荐。"

6 个 fixtures：

| | 问题 | 期望 |
|---|---|---|
| ✅1 | `case.yaml` 主研究问题原文 | IN_SCOPE |
| ✅2 | 中芯国际 2025 年毛利率改善主要来自利用率还是产品结构？ | IN_SCOPE（D2/D3） |
| ✅3 | 中芯国际的盈利改善有多少来自政府补助等非经常项目？ | IN_SCOPE（D6） |
| ❌4 | 中芯国际现在值得买入吗？目标价多少？ | R1 → 真实拒答 |
| ❌5 | 把中芯国际和华虹半导体做个对比 | R2 → 免责声明 |
| ❌6 | 中芯国际 2026 下半年业绩会怎样？ | R3 → 免责声明 |

R2 需要一份**固定的少量同业名单**（华虹 / 台积电 / 联电 / 格芯 + 英文与代码）写死在规则文件，并在文件内明写它只服务当前黄金案例、不是通用能力。纯白名单方案（"必须提到中芯国际"）不可行——fixture 5 确实提到了中芯国际。

#### 7. 报告结构与三分离（票面第 3 条）

FR-070 十章节顺序照用，**只约束 `FULL_REPORT`**。票面第 3 条的"清楚分开研究问题 / 分析框架 / 流程状态"不打散十章节，改为报告最顶部的固定三块元数据：

1. **研究问题**——引 `case.yaml`
2. **分析框架**——D1–D7 与评分口径，引 `rules/analysis.yaml`
3. **流程状态**——五个 run status + `governance_status` + `FROZEN_REPLAY` + `distribution_status` + `PENDING_HUMAN_REVIEW`

三块各自独立，不混进叙述。

#### 8. FR-071：证据表 + 未绑定数字门禁

实测散文里有约 417 个未绑定数字，而 FR-071 明写"同一句出现多个数字时，不得用一个模糊脚注掩盖来源或期间差异"——这正是当前散文在做的事（D1 单个 `finding_statement` 里 23 个数字共用 8 条 `supporting_evidence`）。

**数字只在证据表里出现**。行粒度用 `evidence_id`（实测与 `fact_id` 严格 1:1，且 fact 按契约即原子数值），每行含：`fact_id`、`evidence_id`、`metric_id`、`display_value`、`base_unit_value`、`raw_value_text`、`unit`、`currency`、`scale_factor`、`accounting_basis`、`period`、`source`、`published_at`、`locator`。

**散文按整句排除，不按字符删除**：

1. 按句切分模型散文；
2. 无数字的句子原样保留；
3. 含未绑定数字的**整句不进入报告**；
4. 段末统一加固定文字"具体数值及其期间、口径和来源见本维度证据表。"

冻结的模型输出原文**不修改**，只改最终报告的渲染结果。整句排除比正则删局部字符安全且可测——后者会产出"毛利率由上升到，改善个百分点"这种垃圾。

**已量过并接受的代价**（`finding_statement` 存活率）：

| 维度 | 句数→保留 | 字符数→保留 | 存活率 |
|---|---|---|---|
| **D1 盈利能力变化** | 7→2 | 473→90 | **19%** |
| D2 利用率 | 3→3 | 194→194 | 100% |
| D3 结构 | 4→2 | 245→84 | 34% |
| D4 资本开支 | 5→3 | 489→290 | 59% |
| D5 周期 | 8→5 | 481→270 | 56% |
| D6 非经常 | 5→3 | 534→237 | 44% |
| D7 可持续性 | 7→4 | 571→259 | 45% |

主研究问题所在的 D1 只剩 19% 叙述。用户已看数据确认接受——这是"诚实优先于好看"的真实价格。

**泄漏门禁**（05 的 `因而` 教训：闸门跑过 ≠ 闸门有效）。记入 `report-validation.yaml`：

```yaml
narrative_numeric_sanitization:
  scanned_fields: 7
  detected_mentions: <n>
  omitted_sentences: [...]     # 每条含 dimension_id / field_path / matched_text / matched_numeric_tokens / action
  leaked_unbound_numeric_mentions: 0
  status: PASS
```

最终门禁断言：**最终报告自由叙述区域中的未绑定数字数量必须为 0**。不能只证明扫描器运行过，必须证明数字没有从其他字段泄漏进最终报告。

扫描范围**按字段路径限定**，只扫那 7 个散文字段——实测 ID 全部住在自己的字段里（`evidence_id` 315 个数字、`fact_id` 306 个、`dimension_id` 7 个），字段路径限定天然零误报，比维护 token 白名单简单且无遗漏。**不建中文数字检测器**：实测散文里带单位数值全是阿拉伯数字（`%` 67、`千`(千美元) 24、`英寸` 5、`个百分点` 4、`片` 3），"三成"这类表达一次都没出现，为它建检测器是为假设输入建能力。

#### 9. 第 9 章 gaps 聚合

- 按 `origin_stage × gap_kind` 出聚合计数表；
- 只逐条展开非 `NORMALIZATION_UNKNOWN` 的那 **9** 条；
- 4,912 条 `NORMALIZATION_UNKNOWN` 给一个聚合行 + 一句口径说明（规整阶段对缺失字段的机械登记，不是逐条待办）；
- **不按优先级筛**（P1 4,915 / P2 6，P1 在本仓库已失去区分度），并在报告中说明为什么不按 P1 筛。

"上游 gap 优先级失真"**不生成运行 gap**——`gaps.yaml` 契约明写"不承担长期任务管理，也不替代产品开放问题文档"，而这是 03 的设计缺陷不是数据 UNKNOWN。记入 `DEMO-KNOWN-ISSUES.md` 作为后续设计事项，06 不修（03 已冻结在 main）。

#### 10. 有对象的与无对象的，分开处置

- **票面第 7 条改写为"调节桥接公式可复算"**，不得称为 `DERIVATION` 记录——链路上 `DERIVATION` 确实是 0，措辞不精确会让后来的人以为存在派生值。用 7 条 `reconciliation_check` 作真实对象，第 10 章附录展示公式、复算值、差异与状态；**4 条 PASS、3 条 UNKNOWN 如实解释**，不用 fixture。
- **票面第 8 条的"冲突→隔离→发现降级"与"FAIL→仍有诊断报告"在 v3 上无观察对象**（实测冲突 0、隔离 0、五个状态无一 FAIL）。机制由**合成 fixtures** 验证存在（沿用 05 禁止输出词表的正反 fixtures idiom）；真实运行的 0 值原样写进第 9 章，标明是 v3 的真实承载力。票面措辞相应改为"机制由 fixtures 覆盖 + 真实运行结果如实披露"，不再暗示黄金案例会触发它们。
- **政府补助双口径同样处理**：机制走 fixture（合成一条可分离、可追溯、口径匹配的政府补助 → 生成敏感性）；真实运行的"第二口径 0 条 + 原因"写进第 5 章——15 条政府补助记录存在，但无一满足"可分离且证明已计入同口径 profit from operations"。补**一条**可追溯的"敏感性未生成"gap（不按 15 条观察重复制造相同 gap）——现在它连 gap 都没有，是个哑洞。

**绝不为了让票面跑出来去造冲突数据或硬算敏感性**，那直接撞 AGENTS.md 禁止虚构。这与 05 如实披露"D2/D5/D7 承重名单为空、D3 仅 1 条"是同一个动作。

#### 11. 可读性：术语对照表

报告会同时出现英文枚举（`PROFIT_ATTRIBUTABLE_TO_OWNERS`、`OUTSIDE_AUDIT_SCOPE`、`T1`）、英文原文跨度（IFRS 年报，按 05 规则必须未删减保留）和被整句排除掏空的中文叙述，三者叠加会很硬。

第 10 章附录加一份**冻结的"术语与口径对照表"**：英文枚举 → 中文说明，约 30–50 条（`metric_id`/`claim_type`/`source_tier`/`evidence_status`/`audit_status`/`period_type` 各取值）。它是一份固定数据文件，不是架构。

两条不能碰的线：**机器标识符原样保留不翻译**（`evidence_id`/`fact_id`/`metric_id` 必须能直接 grep 回 JSONL，翻译即断溯源，撞 FR-071 硬约束）；**英文原文跨度原样保留不翻译**（翻译来源原文等于制造无出处的新文本，擦边虚构）。表头与说明用中文，标识符与原文保持原样。

**报告呈现规则只有 `rules/report.yaml` 一处，上游七个阶段一律不读它**——守住这条，将来改报告永远是局部改动。

#### 12. 编排器形态（反过度设计边界，ADR 0005 决定二）

- **`single-stock-research-orchestrator`（Skill）是唯一编排器**：七阶段固定顺序写成 Markdown 固定清单，是文本常量不是可配置 DAG。
- **`scripts/validate_demo_run.py`（薄脚本）只做裁判**，三个子命令：`preflight`（运行目录干净 + 冻结输入哈希/绑定 + 快照身份）、`gate`（读五个 run status，算 `governance_status`，定形态）、`finalize-manifest`（哈希产物、写分区 manifest）。
- **该脚本不 import 任何阶段脚本、不 subprocess 调它们、不含"下一步是什么"的控制流**。每个阶段仍由 Skill 指令显式调用各自 CLI。
- 命名本身是防线：`validate_` 让"它只是裁判"写在文件名上；`orchestrate_` 会持续邀请后来的人往里加编排。

#### 13. 产物清单

新建 2 个 Skill：`generate-research-report`、`single-stock-research-orchestrator`（凑满契约地图的八个）。新建 1 个脚本 `scripts/validate_demo_run.py` + 报告生成脚本。新建 1 份规则 `rules/report.yaml`（含术语对照表、章节定义、扫描字段路径）。

运行目录产物：全部上游权威文件 + `report.md` + `manifest.yaml` + `report-validation.yaml`（**新增权威文件，用户已确认**——其余每个阶段都有 `*-validation.yaml`，且票面第 7、8 条需要一个落地的证明产物）。

#### 14. 06 不修但必须披露的既有问题

- **`DEMO-KNOWN-ISSUES.md` A1：抽取语义错误**。抽样发现把"EBITDA 利润率提高 1.4 个百分点"抽成 `DEPRECIATION_EXPENSE = 1400 元`，该记录 `normalization_status=PASS` → T1 / REPORTED_FACT / **USABLE / 可承重**；规模估计 179/4,575（3.9%，启发式粗筛未人工核对）。证据表会忠实渲染其中一部分错抽记录，且它们看起来是 T1 可承重的。**在第 9 章"数据限制"显式披露该已知抽取错误率，并注明是启发式估计**；不在 06 修（03 已冻结在 main，修抽取逻辑是另一张票的量级）。
- **D3 唯一承重数值带期间标注缺陷**：`EVID_15431f7b706e456e0fd4ee74`（`ASP_SOURCE_REPORTED` = 6482）`period_type=FISCAL_YEAR` 但来自半年报材料，即 04 的 `GAP_EVIDENCE_UPSTREAM_PERIOD_MISLABEL`。D3 整个数值骨架架在这一条上。证据表中该行必须携带其 gap 标注，**不得直接标 FY2025**（那是错的）。展示而非洗白。
- **05 遗留**：跨维 `overlap_note` 只能做全局校验，进不了逐次重生成闸（单维模型判断看不见其他维度）——报告展示交叉承重时需知道这个洞。
- **`tmp/` 全目录被 gitignore**，冻结判断输入当前不在版本控制内；快照 `raw/`+`parsed/` 57MB 同样未入库（后者是有意为之的既有限制，不在 06 范围）。

#### 实现前待办

1. 把 `frozen-analysis-inputs/` 从 `tmp/ticket05-*` 提出来并入库（212KB）。
2. 给两个模型输出文件各补 `selection_hash` 与 `analysis_rule_version` 字段。
3. 更正 `contracts/contract-map.md`：目录布局改为"快照目录（只读）+ 运行目录（产物）"，权威文件清单照实际文件名，补 `report-validation.yaml`。
4. 票面第 7 条措辞改为"调节桥接公式可复算"；第 8 条改为"机制由 fixtures 覆盖 + 真实运行结果如实披露"。
5. `DEMO-KNOWN-ISSUES.md` 增记"gap 优先级失真（P1 4,915/4,921）"。

### 实现记录（2026-07-22）

七阶段跑通，两次连续重放的 `report.md`、`report-validation.yaml`、`run-integrity.yaml` 字节一致，`manifest.yaml` 除 `generated_at` 外一致（`generated_at` 是唯一按设计随时钟变化的字段——票面第 9 条要求记录生成时间，删掉它才是造假）。注意 `run-integrity.yaml` 的 `removed_files` 如实记录本次清空删掉了哪些文件，因此从空目录起跑与从满目录起跑会不同；这是状态而非不确定性，"两次干净重放"指的是连续两次完整运行。实测结果与冻结规划的事实基线逐项吻合：`governance_status=WARN`、五个阶段状态 PASS/WARN/WARN/PASS/WARN、冲突 0、隔离 0、政府补助敏感性 0 条、桥接复算 4 PASS / 3 UNKNOWN、gap 4,922（含报告阶段新增 1 条）、P1 4,915 / P2 7。冻结重放的 `selection_hash` 与冻结判断输入一致，即重放确实重建出了模型当时看到的那个候选集。

实现期做的四处具体化，均不改变已冻结的决定：

1. **`frozen-analysis-inputs/frozen-inventory.yaml`**（第 6 个文件）。哈希与绑定期望需要一个可比对的声明；写成入库的清单文件而不是脚本里的字面量，使哈希闸门本身可被测试（fixture 工作区可以造自己的冻结输入）。清单是版本控制下的信任根，改一个冻结输入而不改清单会被 `preflight` 拦住。
2. **`run-integrity.yaml` 与 `run-gate.yaml`** 进入运行目录固定清单。三个子命令之间必须以文件传递判定结果——否则 `gate` 只能重算完整性、或 `preflight` 只能把结论塞进 stdout 让调用方解析，两条路都会把控制流引回脚本。两份文件与其余阶段的 `*-validation.yaml` 同构。
3. **散文扫描字段从 7 个扩到 14 个**。冻结的 7 个是当时量过的字段；质询问答、D7 观察指标、模型 gap 文本和逐条 `overlap_note` 同样渲染进报告，不扫它们就等于给闸门留了后门。实测新增字段确实携带数字（质询 5 条里 3 条问题、4 条理由含数字）。最终泄漏数仍为 0。
4. **固定说明文字与模型散文分开计**。`rules/report.yaml` 里的固定解释文字含 `FR-073`、`T1`、`P1`、`D3`、`v3` 这类标识符数字，它们不是研究数值也无法绑定证据。做法是：固定文字里所有真实统计量改为运行期计算并落到数据表（抽取错误率、gap 优先级分布都是这样得来的），剩下的标识符数字留在固定文字中，`report-validation.yaml` 单独计数并注明。受闸门约束的仍是模型自由叙述，与冻结定义一致。

`single-stock-demo-run/` 中只保留 `report.md`、`report-validation.yaml`、`run-gate.yaml` 入库，其余 gitignore：95MB 是可重建产物，而 `manifest.yaml` 按设计带 `generated_at` 与工具版本哈希，每次运行必然不同，入库只会制造无意义的 diff（两次重放的 manifest 一致性靠直接读文件比对，不靠 git）。留下的三个文件字节稳定，使"重放后 git diff 干净"本身成为可复现性证据。

另有一处实现期发现的真实缺陷：新增 `.gitattributes` 把工作区固定为 LF，并对 `frozen-analysis-inputs/**` 关闭一切换行转换。Windows 下默认 CRLF 检出会改变冻结判断输入的字节，导致新克隆的仓库 `preflight` 直接哈希不符——行尾在这里是内容的一部分。
