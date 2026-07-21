---
status: accepted
date: 2026-07-21
decision-makers: user
---

# 冲突检测限定在人工核验的记录级白名单上

`govern-and-validate-research-evidence` 为 Snapshot v3 的全部 20,114 条规整事实各生成一条治理证据，信源等级、内容类型、同源组、证据状态和允许用途对全部记录赋值；但**冲突检测只在一份人工逐条核验过的记录级白名单上执行**，白名单以 `fact_id` 列举，登记于 `rules/source-governance.yaml`。其余记录不进入任何冲突组，并按原因确定性地区分状态：文本命题为 `NOT_APPLICABLE`（`TEXT_CONFLICT_OUT_OF_SCOPE`），未列入白名单的数值事实为 `NOT_EVALUATED`（`NOT_IN_CONFLICT_WHITELIST`、`MISSING_METRIC_ID` 或 `MISSING_COMPARABILITY_KEY`，并列出缺失字段）。

该决定来自在真实数据上的实测。按"全部带白名单 `metric_id` 的数值事实"检测，1,076 条中仅 275 条具备完整可比字段，形成 55 个冲突组，其中 43 组有多个成员、41 组数值不一致。抽样显示这 41 组几乎全是表格解析噪声：`REVENUE` 的 2023 财年组包含 `74`、`75` 这类附注编号，`OTHER_OPERATING_INCOME` 组混入百分比 `40.3`。这与 Ticket 03 放弃重述检测的原因相同——本期/上期/同比列共享文本 span，机械配对必然大量误报。若照此实施，`REVENUE`、`PROFIT_ATTRIBUTABLE_TO_OWNERS`、`GROSS_MARGIN` 会被判 `CONFLICT_UNRESOLVED` 进而降为 `RESTRICTED`，使 D1 盈利能力分析失去可承重证据——用误报打断黄金案例主线是最坏结果。

被否决的替代方案有三个。对 15,539 条文本命题也做冲突配对，需要语义相似度或模型判断，与确定性核验要求冲突，且文本观点按固定规则本就应保留各版本而非裁决。完全不做冲突检测虽诚实，但冲突处置是本 ticket 的核心验收，机制需要真实可跑。只按指标与期间类型规则收窄，仍会放进上述噪声行，无法消除误报。

白名单是**快照级临时覆盖**，放在 `rules/source-governance.yaml` 的独立段 `snapshot_conflict_eligibility_overrides`（绑定 `snapshot_id`、`rationale: UPSTREAM_PERIOD_CLASSIFICATION_UNRELIABLE`），不混入通用信源表或指标规则。其根因是上游缺陷：Ticket 03 把半年报/三季报的累计期数值错标为 `period_type=FISCAL_YEAR`，污染了候选池——这以一条指向 03 的上游缺口登记，白名单只作 v3 兼容措施，不替代上游修复。核验阶段对每条白名单记录比对完整签名（`fact_id, material_id, metric_id, period_start, period_end, period_type, accounting_standard, currency, unit, value, span_hash`），任一不一致即 fail closed 为 `FAIL`，防止规整变动后同值被错映射到别的指标或期间而 `fact_id` 仍存在。

代价明确并如实披露：白名单之外的数值事实即使互相矛盾也不会被检出，但每条仍带 `conflict_eligibility=EXCLUDED` 与粗原因码，不留空字段；候选池分布偏斜且期间错标使真实同期跨源冲突 ≈ 0。为避免"零"被误读，运行须输出 `candidate_fact_count`、`eligible_fact_count`、`excluded_fact_count_by_reason`、`comparable_group_count`、`comparison_pair_count`、`detected_conflict_group_count`、`unresolved_conflict_group_count`，以证明零冲突来自"有效比较后确无冲突"而非"未运行"或"全被排除"；`comparison_pair_count=0` 时描述为"未形成满足可比条件的跨源记录对"。冲突组的可比键固定为主体、指标、期间起止、期间类型、会计准则、合并范围、目标币种、目标单位和内容类型；比率类指标的币种与单位标记为本就不适用，不算缺失。裁决、`CONFLICT_UNRESOLVED` 与 winner 字段等分支由合成 fixtures 验证。
