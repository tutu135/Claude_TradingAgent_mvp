# 04 — 治理并核验证据

**What to build:** 让用户能够区分“已规整的候选事实”和“可用于分析的治理证据”，并清楚看到每项材料的来源等级、内容类型、同源关系、冲突处置、可用范围和确定性核验结果。该 ticket 完成 `govern-and-validate-research-evidence`。

**Blocked by:** 03 — 治理上下文并生成规整事实。

**Status:** done

- [ ] 对 `ACQUIRED_UNASSESSED` 材料及候选事实最终确定 T1–T4、六类 `claim_type`、同源/转载关系、冲突、隔离、允许用途和是否可支撑发现；采集状态本身不被回写。
- [ ] 信源等级只表示原始程度和可追溯性，管理层/第三方观点不会被改写为报告事实；来源使用说明和已知限制在此阶段评估，而不是用 `restriction_status=USABLE` 作为采集前提。
- [ ] `as_of` 越界或关键口径缺失的记录被隔离；无法满足证据资格的材料可以保留在快照中，但不能支撑研究发现。
- [ ] 同源转载和伪多源被归为同一来源组，不以转载数量投票；事实冲突严格按可比性、准入、同源去重、重述/审计/法定披露/信源等级顺序处理。
- [ ] 冲突值不会被平均或静默选择；无法解决的事实冲突标记 `CONFLICT_UNRESOLVED`，随时间变化的观点保留各版本。
- [ ] 每项治理证据可回溯 `fact_id -> chunk_id -> material_id`，并记录允许用途、冲突组、处置、隔离原因和 gap。
- [ ] 确定性核验覆盖哈希、`as_of`、定位、必需字段、单位/币种/期间、公式复算、同源组、冲突、隔离、ID 引用和 RAG 定位，并输出逐项原因及 PASS/WARN/FAIL。
- [ ] FAIL 不会终止内部诊断产物，但受影响数据不能进入可用证据集合；正常、警告和失败 fixtures 均能验证该约束。
- [ ] 信源、冲突和核验规则只有一个权威定义，Skill 与脚本引用同一版本，不复制规则或引入规则 DSL/插件机制。

## Comments

### 2026-07-21 规划结论（已与用户确认，实现按此执行）

术语见 `CONTEXT.md`（同源组、指标类、冲突组、证据状态、承重发现、定位链一致性）；冲突范围的取舍见 [ADR 0003](../../../docs/adr/0003-scope-conflict-detection-to-whitelisted-metric-facts.md)。

**覆盖面**：20,114 条规整事实全部生成治理证据，`fact_id : evidence_id` 为 1:1，`evidence_id` 由 `fact_id` 确定性派生；不因隔离或质量不足删除记录。冲突只在约 1,076 条带白名单 `metric_id` 的数值事实上检测，多条证据通过 `conflict_group_id` 关联，不复制行。

**信源等级**（`rules/source-governance.yaml` 内 20 行固定表，非算法）：HKEXnews ×4、CNINFO ×4、smics.com ×4 为 T1；SIA ×4 为 T2；上海证券报 2026Q1 全文为 T2，带 `tier_rationale: DESIGNATED_DISCLOSURE_MEDIA_FULL_TEXT_UNEDITED` 的窄例外，并与发行人 2026Q1 归入同一同源组；Alpha Spread 转录稿 ×2 为 T3，其中 `ALPHASPREAD_AI_SUMMARY` 记录降为 T4。

**内容类型**：材料类别规则优先于 `record_kind` 规则（转录稿内的数值记录同样走管理层判定，防止数字指引被判成 `REPORTED_FACT`）。转录稿内管理层发言按未来期指向或不确定性标记分为 `MANAGEMENT_GUIDANCE` / `MANAGEMENT_ASSERTION`，AI 摘要与主持人为 `THIRD_PARTY_VIEW`；其余数值为 `REPORTED_FACT`、派生记录为 `DERIVED_METRIC`；其余文本按材料类别定为 `REPORTED_FACT`（发行人法定披露）或 `THIRD_PARTY_VIEW`（SIA）。`ANALYTIC_INFERENCE` 在本阶段计数恒为 0。已知局限：发行人年报正文中的定性表述会被判为 `REPORTED_FACT`，接受该误差并登记 gap，不引入逐条模型判断。

**冲突**：检测范围限定为**人工逐条核验的记录级 `fact_id` 白名单**（见 ADR 0003）。实现的第一步就是产出这份白名单：候选池为五核心指标（`REVENUE`、`GROSS_PROFIT`、`GROSS_MARGIN`、`PROFIT_FROM_OPERATIONS`、`PROFIT_ATTRIBUTABLE_TO_OWNERS`）× `period_type=FISCAL_YEAR` × `value_status=PRESENT`，共 **71 条**；逐条读 `source_span_text` 剔除附注编号、百分比串位等解析噪声后登记进 `rules/source-governance.yaml`。核验阶段必须断言每个白名单 `fact_id` 仍存在且 `normalized_value` 与登记值一致，否则 `FAIL`。

白名单内的记录按可比键 `entity_id, metric_id, period_start, period_end, period_type, accounting_standard, consolidation_scope, target_currency, target_unit, claim_type` 分组，全等才同组，组内数值有差异才算冲突。指标分 `AMOUNT`（需币种+单位）、`RATIO`（两者 `NOT_APPLICABLE`）、`PHYSICAL_COUNT`（需单位）三类，字段状态三态 `PRESENT`/`MISSING`/`NOT_APPLICABLE`。`audit_status` 不进分组键，只作裁决优先级输入；`AMBIGUOUS` 视同 `UNKNOWN`，不享受"经审计优先"，也不因此隔离。裁决按 FR-042 次序，不取平均、不静默选值；裁决成功时输出 `conflict_winner_evidence_id` 与 `conflict_resolution_rule_id`，未决为 `CONFLICT_UNRESOLVED`。

未检测记录**在证据输出中**一律带 `conflict_status`、`conflict_eligibility=EXCLUDED` 和一个粗原因码：文本命题 `NOT_APPLICABLE`+`TEXT_CONFLICT_OUT_OF_SCOPE`；数值事实 `NOT_EVALUATED`+`NOT_IN_CONFLICT_WHITELIST` / `MISSING_METRIC_ID` / `MISSING_COMPARABILITY_KEY`（缺失字段列入 `missing_fields`）。**不得留空字段**（满足"全量治理、分层深度"）。`NOISE_PERCENTAGE`/`NOISE_NOTE_NUMBER`/`NOISE_SHARE_COUNT`/`WRONG_PERIOD_H1`/`WRONG_PERIOD_Q3`/`NOT_MANUALLY_VERIFIED` 这类细分标签只放在人工核验工作表中作预分类依据，**不冻结进证据记录、也不写入 `rules`**（避免治理逻辑退化成事实清单）。

**白名单为快照级临时覆盖**：写入 `rules/source-governance.yaml` 独立段 `snapshot_conflict_eligibility_overrides`（含 `snapshot_id: smic-a283e95e2c9e8068`、`rationale: UPSTREAM_PERIOD_CLASSIFICATION_UNRELIABLE`、逐条 `verified_facts: [{fact_id, eligibility: INCLUDE, review_reason: MANUALLY_VERIFIED_FISCAL_YEAR}]`），**不混进信源表或指标规则**；只列 INCLUDE 项，其余默认不合格。核验对每条白名单记录比对**完整签名**（`fact_id, material_id, metric_id, period_start, period_end, period_type, accounting_standard, currency, unit, value, span_hash`），任一不一致即 **fail closed（`FAIL`）并要求重新人工确认**——只比 `fact_id`+value 不够，规整变动可能把同值错映射到别的指标/期间。

**上游缺口**：登记一条指向 Ticket 03 的缺陷缺口——03 把半年报/三季报的累计期数值错标为 `period_type=FISCAL_YEAR`，导致候选池污染。记录级白名单是 v3 的临时兼容措施，根因应由 normalize 阶段按材料报告期、表头与累计期间正确生成 period 字段修复；不阻塞 04，但保留明确上游引用，避免每换快照都要重新人工筛选几十条。

**运行统计**（写入 `evidence-validation.yaml`，不新增验收条目）：至少 `candidate_fact_count`、`eligible_fact_count`、`excluded_fact_count_by_reason`、`comparable_group_count`、`comparison_pair_count`、`detected_conflict_group_count`、`unresolved_conflict_group_count`。用以证明"零冲突"来自"有效比较后确无冲突"，而非"未运行"或"全被排除"。

候选池分布偏斜（IFRS 口径 2023/2024 `REVENUE` 缺失、`GROSS_MARGIN` 仅覆盖 CAS 2025），且期间错标使真实同期跨源冲突 ≈ 0。ticket 说明按如下严谨措辞（替换"预期为零"）：**Snapshot v3 的真实数据按人工核验的记录级资格白名单执行冲突检测；预期不产生跨源冲突组，但运行结果必须同时披露候选数、符合资格事实数、可比较组/记录对数量及各类排除原因，以证明零冲突并非检测未运行；冲突成立、无法裁决及 winner 字段等分支由合成 fixtures 验证。若最终 `comparison_pair_count=0`，描述为"未形成满足可比条件的跨源记录对，因此未产生冲突组"。**

**来源使用说明**：每条证据带 `source_use_note_status`，取 `RECORDED`（无限制记载）或 `RECORDED_WITH_LIMITATIONS`（材料写有已知限制）。它只作记录以满足 FR-043 的核验项，**不影响 `evidence_status`**，不引入 `PROHIBITED` 状态。

**同源组**：按"同一份原始披露"分组，**不按 URL、域名或平台分组**。因此 smics.com 三份季度业绩虽共用入口 URL 但属三份不同披露，各自独立成组；FY2025 的 IFRS 年报与 CAS 年报是两份独立法定披露，不同组；v3 中唯一的同源组是上海证券报 2026Q1 全文与发行人 2026Q1 披露。

**证据状态**：三值枚举，无 `can_support_bearing_finding` 布尔（与 `USABLE` 冗余）。按 `QUARANTINED > RESTRICTED > USABLE` 短路判定。`QUARANTINED`：材料 `as_of_eligible=false`、`content_locator` 无法解析或材料缺失、`normalization_status=BLOCKED`。`RESTRICTED`：`normalization_status=PARTIAL`、tier ∈ {T3,T4}、或 `CONFLICT_UNRESOLVED`（冲突各方仍需可在报告中展示，故不隔离）。其余 `USABLE`。

**核验**：FR-043 的 13 项全部实现为具名检查。RAG 项命名为 `locator_chain_consistency`，核对 ID 引用完整性与 `source_chunk_text_hash`，**不**重新验证定位准确性——该保证继承自 03 的检索验收，需在输出与文档中写明。公式复算只覆盖 03 已产出的 `DERIVATION` 与 IFRS/CAS 桥接，04 不新建公式。合法状态组合作为断言冻结。汇总：`FAIL` = 完整性/确定性问题（哈希不符、悬空 ID、必需字段缺失、重建哈希不一致、非法状态组合）；`WARN` = 存在 `QUARANTINED`/`CONFLICT_UNRESOLVED`/新 gap；否则 `PASS`。**预期真实运行结果为 `WARN`**。

**缺口**：3,499 条缺 `metric_id` 的数值事实合并为 **1 条**聚合 gap，正文含总量 `3499/4575` 与 top-N `source_metric_label` × 出现次数表；不按维度拆成上百条。`gap_id` 由稳定内容字段派生并去重；重建哈希比较排除时间戳与绝对路径。

**产物**：`rules/source-governance.yaml`（`rule_version: smic-v3-source-governance-v1`）、`scripts/govern_validate_research_evidence.py`（CLI 与 03 同形，并**必须包含 `--context-file`**，因为 `locator_chain_consistency` 要核对 `context.jsonl` 的 `source_chunk_text_hash`）、Skill `govern-and-validate-research-evidence`（约 25 行，只引用规则版本）。输出 `governed-evidence.jsonl`、`evidence-validation.yaml`、追加后的 `gaps.yaml` 到派生目录 `tmp/ticket04-final/`，不写回 v3。

**测试**：`tests/` 下三组手写小型合成 fixture（PASS/WARN/FAIL 各 5–10 条）+ 一个真实 v3 端到端测试，断言 `WARN` 与两次干净重建哈希一致。不复制快照做 fixture。
