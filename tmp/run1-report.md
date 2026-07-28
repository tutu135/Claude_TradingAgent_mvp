# 中芯国际单股票投研 Demo 内部报告

> 本报告为内部演示产物，`distribution_status=INTERNAL_DEMO_ONLY`，`human_review_status=PENDING_HUMAN_REVIEW`，不构成任何投资建议。

## 研究问题

> 截至 {as_of}，中芯国际的经常性经营盈利能力发生了哪些可验证的变化，现有证据在多大程度上支持其已进入可持续改善阶段？

| case_origin | company | security | as_of | 来源 |
|---|---|---|---|---|
| model_generated | 中芯国际集成电路制造有限公司 | 688981.SH | 2026-05-15T23:59:59+08:00 | single-stock-demo-v3/case.yaml |

**范围识别**（确定性规则，不使用模型判断）

| id | 问题 | label | action |
|---|---|---|---|
| Q1 | 截至 {as_of}，中芯国际的经常性经营盈利能力发生了哪些可验证的变化，现有证据在多大程度上支持其已进入可持续改善阶段？ | IN_SCOPE | ANSWER |
| Q2 | 中芯国际 2025 年毛利率改善主要来自利用率还是产品结构？ | IN_SCOPE | ANSWER |
| Q3 | 中芯国际的盈利改善有多少来自政府补助等非经常项目？ | IN_SCOPE | ANSWER |
| Q4 | （命中禁止输出词表，问题原文不复述） | OUT_OF_SCOPE_FORBIDDEN_OUTPUT | REFUSE |
| Q5 | 把中芯国际和华虹半导体做个对比 | OUT_OF_SCOPE_OTHER_SUBJECT | DISCLAIM |
| Q6 | 中芯国际 2026 下半年业绩会怎样？ | OUT_OF_SCOPE_BEYOND_AS_OF | DISCLAIM |

本 Demo 只研究〔主研究问题〕；对超出范围的问题（投资建议 / 其他标的 / as_of 之后） 不作回答，亦不作任何推荐。

该问题要求的是投资动作或投资吸引力判断。本 Demo 按 FR-073 不输出此类内容，此处不作回答， 也不以任何形式暗示；问题原文因命中禁止输出词表，不在报告中复述。

## 分析框架

| dimension_id | bearing_metric_whitelist | finding | evidence_score |
|---|---|---|---|
| D1_PROFITABILITY_CHANGE | GROSS_MARGIN, GROSS_PROFIT, PROFIT_FROM_OPERATIONS, PROFIT_ATTRIBUTABLE_TO_OWNERS, REVENUE, COST_OF_SALES | MIXED | 3 |
| D2_UTILIZATION_EFFECT | — | MIXED | 2 |
| D3_MIX_EFFECT | ASP_SOURCE_REPORTED | MIXED | 2 |
| D4_CAPEX_CONVERSION | CAPITAL_EXPENDITURE_INCURRED, DEPRECIATION_EXPENSE | MIXED | 3 |
| D5_CYCLE_EXPLANATION | — | UNKNOWN | 2 |
| D6_NONCORE_EXPLANATION | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL, OTHER_OPERATING_INCOME | MIXED | 3 |
| D7_SUSTAINABILITY_EVIDENCE | — | UNKNOWN | 2 |

来源：`rules/analysis.yaml`。评分口径见第十章术语对照表。

## 流程状态

| 项 | 值 |
|---|---|
| retrieval_status | PASS |
| normalization_run_status | WARN |
| validation_status | WARN |
| analysis_run_status | PASS |
| challenge_run_status | WARN |
| governance_status | WARN |
| execution_mode | FROZEN_REPLAY |
| report_form | FULL_REPORT |
| distribution_status | INTERNAL_DEMO_ONLY |
| human_review_status | PENDING_HUMAN_REVIEW |

governance_status 只由检索、规整与证据治理三个状态按最坏值合成；分析与质询状态属于另一条概念轴，不并入其中，在上表中原样并列展示。

## 一、案例、as_of、快照、治理状态与分发状态

| 项 | 值 |
|---|---|
| snapshot_id | smic-a283e95e2c9e8068 |
| as_of | 2026-05-15T23:59:59+08:00 |
| governance_status | WARN |
| distribution_status | INTERNAL_DEMO_ONLY |
| human_review_status | PENDING_HUMAN_REVIEW |
| execution_mode | FROZEN_REPLAY |
| analysis_rule_version | smic-v3-analysis-v1 |
| context_rule_version | smic-v3-context-retrieval-v3 |
| report_rule_version | smic-v3-report-v1 |
| overall_score | NOT_APPLICABLE |

## 二、数据覆盖与来源覆盖

| required_coverage | 已取得材料数 |
|---|---|
| company_security_master | 6 |
| annual_materials_fy2023 | 2 |
| annual_materials_fy2024 | 2 |
| annual_materials_fy2025 | 2 |
| quarterly_materials_2025_q2 | 3 |
| quarterly_materials_2025_q3 | 2 |
| quarterly_materials_2025_q4 | 3 |
| quarterly_materials_2026_q1 | 4 |
| capacity | 14 |
| utilization | 13 |
| shipments | 13 |
| average_selling_price | 6 |
| process_application_mix | 13 |
| capital_expenditure | 14 |
| government_grants | 13 |
| other_operating_income | 13 |
| ifrs_cas_reconciliation | 9 |
| industry_cycle | 4 |
| comparability_events | 10 |
| smnc_49_transaction | 1 |
| nsi_transaction | 2 |

| 统计项 | 值 |
|---|---|
| 材料数 | 20 |
| 同源组数 | 19 |
| 证据总数 | 20114 |
| evidence_status=RESTRICTED | 4912 |
| evidence_status=USABLE | 15202 |
| source_tier=T1 | 19544 |
| source_tier=T2 | 203 |
| source_tier=T3 | 278 |
| source_tier=T4 | 89 |
| record_kind=NUMERIC_OBSERVATION | 4575 |
| record_kind=TEXT_PROPOSITION | 15539 |

同源转载不增加独立证据：同一次原始披露的多个入口共享一个 source_group_id，证据分只按独立同源组计。

## 三、报告口径与规整口径下的盈利能力变化（D1）

#### D1_PROFITABILITY_CHANGE — MIXED

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| MIXED | 3 | STRONG | MODEL_JUDGMENT | 2 | COST_OF_SALES, GROSS_MARGIN, GROSS_PROFIT, PROFIT_ATTRIBUTABLE_TO_OWNERS, PROFIT_FROM_OPERATIONS, REVENUE | — |

在统一为 IFRS 美元口径后，候选证据可验证到两层并存的变化。在收入于同一期间持续增长的背景下，年度口径的盈利能力改善与最近几个季度的边际回落同时成立，整体判定为 MIXED。具体数值及其期间、口径和来源见本维度证据表。

*supporting_evidence*

- `EVID_3b988db2f6b5049f66b6227a` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

毛利率同样可被利用率维度或产品结构维度引用，但那些维度需要的是利用率百分比与结构占比的独立证据；此处只把毛利率本身作为盈利能力结果指标的水平变化来读，不解释其构成，与利用率/结构维度不共用同一结论，不构成重复计分。

- `EVID_f28af2b9e69c01c2b43fd0de` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

毛利绝对额也可能在周期维度中作为景气位置的旁证，但周期维度关心的是同业与需求侧节奏；此处仅用其确认公司自身年度盈利规模的量级变化，与周期判断不共用同一结论，不构成重复计分。

- `EVID_38ba63715dd51c6304b026ab` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

经营利润也可被非经常性损益维度引用，但该维度需要的是其他收益/损失与政府补助等单项证据；此处只取经营利润总额的年度变化，未拆分其中的非经常项，二者读取的层级不同，不构成重复计分。

- `EVID_16327139f06b3e53b66585fe` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

净利率含非经营项，可能同时进入非经常性损益维度；此处仅将其作为「年度综合盈利率是否同向变化」的交叉验证，非经常项的归属留给该维度，故非重复计分。

- `EVID_a3f92a279254fc09ad1ea142` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

单季毛利率也可能在可持续性维度中被引用为波动性素材；此处仅用其确定季度序列的起点数值，波动是否可持续的判断不在本条内完成，故非重复计分。

- `EVID_6827b1e1cf99ee76189e5f2e` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

该季度毛利率回落同时可被资本开支/折旧维度引用（折旧上升期），但那需要独立的折旧与在建产能证据；此处只记录盈利率水平的下移事实，不做成因归属，故非重复计分。

- `EVID_d6efa2d8f71dc14d7c9c89c1` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

该点位也与产品结构维度相关（公司自述涉及结构与均价变化），但结构维度需要结构占比与均价的独立证据；此处仅使用毛利率数值本身刻画最新水平，故非重复计分。

- `EVID_49b0a2d636a94a70f10566a8` role=CONTEXT
该项标注 bearing=NO，仅用于说明毛利以下的费用结构存在同期变动，不用于确定盈利能力变化的方向。具体数值及其期间、口径和来源见本维度证据表。

该费用项更适合归入研发投入或可持续性维度；本维度仅作背景引用且不承重，不参与方向判断，故不构成重复计分。

*counter_evidence*

- `EVID_a9e7bdcf575cdf9e5cbd1445` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_ce52d35fc78952c0fa924568` role=—
具体数值及其期间、口径和来源见本维度证据表。

*alternative_explanations*

年度毛利率上行与出货量、产能利用率的同期变化并存，年度改善可能主要反映产能与出货的规模条件变化，而非单位产品盈利能力的独立提升；候选集中缺少可用的利用率与出货量数值证据来分离两者。

季度毛利率的起伏可能与产品组合和平均售价的季节性变化同时出现，在仅有五个季度的窗口内难以与趋势性变化区分。

折旧在高投入期上升与毛利率回落在时间上重叠，最近两个季度的边际走弱可能属于成本结构的阶段性特征，而非盈利能力的结构性削弱。

具体数值及其期间、口径和来源见本维度证据表。

*limitations*

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

候选集未提供 IFRS 与 CAS 之间盈利指标的定量桥接，仅有文字性的差异说明，跨准则口径的可比性未在本维度内验证。

*gaps*

缺少按产品线、技术节点或应用领域拆分的毛利率数值证据，无法在同一口径下对盈利能力变化做结构分解。

缺少连续季度的折旧与摊销数值证据，无法量化其在毛利率变动中的占比。

缺少可用的季度产能利用率与出货量数值记录（相关内容仅以文字形式出现），无法与毛利率序列做同口径对照。

具体数值及其期间、口径和来源见本维度证据表。

*management_assertions*（来源观点，claim_type 见证据表）

- `EVID_e4b206094f5890f4cf04ffc1`
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_20847c93979c92b6d9eb5597`
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_43289a6874cc99aca0fa341c`
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_759908b984d49c1fedb7c038`
具体数值及其期间、口径和来源见本维度证据表。

**D1_PROFITABILITY_CHANGE 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_0030ec95b60bda21e9f04b2f | EVID_d6efa2d8f71dc14d7c9c89c1 | GROSS_MARGIN | 20.1 | — | 20.1% | PERCENT | USD | 1 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2026-01-01~2026-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.4 WEBCAST CHUNK_fd51b55ab05bfc90ed31a5cf | REPORTED_FACT | — |
| FACT_42d2a396ea65b8defbb32f97 | EVID_a3f92a279254fc09ad1ea142 | GROSS_MARGIN | 22.5 | — | 22.5% | PERCENT | USD | 1 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-01-01~2025-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended June 30, 2025 (MATERIAL_SMIC_2025_Q2_RESULTS) | 2025-08-07T23:59:59+08:00 | p.4 WEBCAST CHUNK_5755a6499a6563603daf0f63 | REPORTED_FACT | — |
| FACT_abf6710b0e1277ff41c622a7 | EVID_6827b1e1cf99ee76189e5f2e | GROSS_MARGIN | 19.2 | — | 19.2% | PERCENT | USD | 1 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.4 WEBCAST CHUNK_6673c3dbcdee031ba7c06d6d | REPORTED_FACT | — |
| FACT_da479aca4adbccefeddd352d | EVID_49b0a2d636a94a70f10566a8 | RESEARCH_AND_DEVELOPMENT_EXPENSE | 187.1 | 187100000.0 | $187.1 million | MONEY | USD | 1000000 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2026-01-01~2026-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.6 1Q26 4Q25 1Q25 CHUNK_d6f6db576be5052fed536071 | REPORTED_FACT | — |

**D1_PROFITABILITY_CHANGE 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_024c51c443e8855a0714279b | EVID_38ba63715dd51c6304b026ab | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.105 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_15924eb7530fdb9bbfe7a703 | Profit from operations 1,109,937 473,900 | — |
| FACT_1d9b94ee5cb6062a7bff54d4 | EVID_a9e7bdcf575cdf9e5cbd1445 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.4 WEBCAST CHUNK_6673c3dbcdee031ba7c06d6d | Gross profit 478,121 522,811 -8.5% 499,011 -4.2% | — |
| FACT_4e41ee6d5e010a0f03a1b4f2 | EVID_759908b984d49c1fedb7c038 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | gross margin is expected to be in the range of 18% to 20%. | — |
| FACT_782a7a42b7bfeb280dc74181 | EVID_20847c93979c92b6d9eb5597 | REPORTED_FACT | T1 | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.4 WEBCAST CHUNK_6673c3dbcdee031ba7c06d6d |  Gross margin was 19.2% in 4Q25, compared to 22.0% in 3Q25, due to the increase in depreciation. | — |
| FACT_851d0d49a10ed9c41496cbae | EVID_ce52d35fc78952c0fa924568 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.4 WEBCAST CHUNK_fd51b55ab05bfc90ed31a5cf | Profit from operations 247,792 298,620 -17.0% 309,571 -20.0% | — |
| FACT_9ab89a8bfa5e1839a71fe8cf | EVID_e4b206094f5890f4cf04ffc1 | REPORTED_FACT | T1 | SINGLE_QUARTER 2026-01-01~2026-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.4 WEBCAST CHUNK_fd51b55ab05bfc90ed31a5cf |  Gross margin was 20.1% in 1Q26, compared to 19.2% in 4Q25, due to the product mix change and | — |
| FACT_bbdf6a2dd887a56b9ba99292 | EVID_f28af2b9e69c01c2b43fd0de | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.28 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_15b589c565ba839c26891647 | Gross profit 1,956,599 1,447,968 35.1 | — |
| FACT_e19e7b7e58cbc7cf7918dbf2 | EVID_16327139f06b3e53b66585fe | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.16 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_ea64802875034d5bf4858151 | Net margin 10.6% 9.1% Increased by 1.5 17.8% | — |
| FACT_e69584ac5c086eb4eba2b005 | EVID_3b988db2f6b5049f66b6227a | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.16 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_ea64802875034d5bf4858151 | Gross margin 21.0% 18.0% Increased by 3.0 19.3% | — |
| FACT_f2901c346e1957c1172b69ae | EVID_43289a6874cc99aca0fa341c | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.28 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_15b589c565ba839c26891647 | to the increase in wafer shipment, the increase in capacity utilisation rate and the product mix change for this year. | — |

## 四、D2–D4：利用率、结构和资本开支驱动

#### D2_UTILIZATION_EFFECT — MIXED

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| MIXED | 2 | ADEQUATE | MODEL_JUDGMENT | 2 | — | CH_002 |

候选证据集中不存在可承重的产能利用率数值记录，本维度只能依据公司自身披露的文本表述。定向复核发现，中国企业会计准则口径年报与国际财务报告准则口径年报的相关表述来自同一年度的同一次原始披露，两者互相印证不构成独立多来源。在此口径下，利用率在公司的成本与毛利说明中被列为与盈利能力变化同时出现的因素之一，但证据集内没有独立于公司自身表述的记录，方向由 SUPPORTED 下调为 MIXED。

*supporting_evidence*

- `EVID_b1c888ce8a1e8062eafc586e` role=PRIMARY_SUPPORT
中国会计准则口径年报的毛利变动原因说明中，当年产能利用率下降列为首项，与晶圆销售数量减少及产品组合变动并列，属于公司自身把利用率纳入盈利解释项的直接文本。

同一句也提到产品组合与销售数量，这些部分可在结构与周期维度承重；本维度只取其中的利用率分句，其余分句留给对应维度，不构成重复计分。

- `EVID_4524a43ea22b3d39a75acad1` role=PRIMARY_SUPPORT
同一份年报的营业成本变动原因说明中同样列出当年产能利用率下降，与产品组合变动和折旧增加并列，指向固定成本吸收侧的成本口径而非毛利口径。

句中的折旧部分可在资本开支维度承重；本维度只使用利用率分句，且与毛利口径的证据分属成本端与利润端两个不同披露位置，不构成重复计分。

- `EVID_c515b1039aecf047ebcc1197` role=PRIMARY_SUPPORT
国际财务报告准则口径年报在销售成本说明中给出与中国会计准则口径一致的并列表述，两套准则的独立披露互相印证同一文本事实。

该句同时涉及产品组合与折旧，可在结构与资本开支维度承重；此处只作为跨准则口径一致性的利用率证据使用，不重复用于其他维度的方向判断。

- `EVID_1c3dc864090cac8f4c9a9b23` role=PRIMARY_SUPPORT
国际财务报告准则口径年报在毛利说明中列出产能利用率下降、晶圆出货下降与产品组合变动三项并列因素，构成下行阶段的利用率与盈利同向记录。

出货量与产品组合部分归属周期与结构维度承重；本维度仅取利用率分句，与成本端证据分属不同披露段落，不构成重复计分。

- `EVID_3154aa1a93149fb86a04d72c` role=PRIMARY_SUPPORT
年报在风险与经营段落中陈述公司通过优化产品组合、提升利用率、精进工艺制程来增强整体盈利能力，表明利用率在公司自述的盈利机制清单中占据位置。

产品组合部分可在结构维度承重，工艺制程部分可在可持续性维度承重；本维度只援引其中的利用率一项作为机制存在性的文本依据，不构成重复计分。

- `EVID_ac341415e94d16e43f70b315` role=PRIMARY_SUPPORT
较晚年度的致股东的信中记载产能利用率同比提升，与前述下行年度的利用率下降形成方向相反的两个阶段，本维度的方向在跨周期上保持一致。

同段落还提到折旧与代工地位，可在资本开支与可持续性维度承重；本维度只取利用率提升这一分句，毛利率部分另以上下文角色引用，不构成重复计分。

- `EVID_921e1d21d4acaffbf75b5190` role=CONTEXT
同一封致股东的信中，毛利率同比提升与折旧大幅增长写在与利用率提升相邻的语句中，仅用于呈现两者在同一披露段落内的并存关系，不由其承担本维度方向。

- `EVID_391db1c31ad31d10c4481811` role=CONTEXT
单季资本开支数值仅用于说明公司处于持续产能建设阶段这一背景，不是利用率或产能指标，不得作为利用率的替代量，不承担本维度方向。

*counter_evidence*

- `EVID_6e847621bd3a5e7b8471a1d6` role=—
年报陈述在持续高投入过程中毛利率承受较高折旧压力，说明盈利能力变化存在与利用率并行的另一条披露渠道，削弱把变化单独归入利用率的解释力。

- `EVID_e7103d2a15cefb9eaf2c7f2a` role=—
年报陈述当年集团处于高投入期、折旧较上年增加，与利用率的表述同期并存，构成对利用率单一解释的直接制衡。

- `EVID_3639b4225c2c0e412050cf02` role=—
季报文本显示利用率在相邻季度间存在回落与波动，而候选集内没有与之配对的同期毛利率文本，季度层面的同向关系无法在本证据集内核验。

*alternative_explanations*

折旧与高投入阶段的固定成本上升，在公司披露中与利用率并列出现，可独立解释盈利能力变化的一部分。

产品组合变动在成本与毛利两处说明中均与利用率并列，可能承担相当比例的解释。

晶圆出货数量与平均售价变化在年报中被单独列示，属于与利用率不同的量价渠道。

政府补助、汇兑与利息等非经营项目在同期报表中变动明显，可影响利润口径而与产能吸收无关。

*limitations*

本维度的承重指标白名单为空，候选数值记录仅有资本开支、营业收入与营业利润，均不是利用率或产能指标，无任何数值证据承担方向。

利用率与盈利指标的并列表述来自公司自身的原因说明，属于公司口径的归因，未经独立验证。

证据集中的文本命题是按结构切分的分句，部分语义依赖被切走的上下文，单句可读性受限。

同一披露段落内的并存关系不等同于机制强度，本证据集不支持对贡献度或弹性作任何量化陈述。

中国会计准则口径与国际财务报告准则口径、年报与季报的期间与币种口径不一致，跨口径比较仅能作定性使用。

经质询确认：CAS 与 IFRS 两个口径的年报表述属同一次原始披露的两种呈报，构成伪多源，不能作为独立来源一致性的依据。

*gaps*

缺少可承重的利用率数值记录，无法构成利用率与毛利率的成对时间序列。

缺少折旧占营业成本比重的口径，无法核验固定成本吸收这一具体机制。

缺少公司对利用率、产品组合、折旧三项各自贡献度的拆分披露。

缺少季度层面利用率与毛利率的同期配对披露，季度粒度的同向关系无法核验。

**D2_UTILIZATION_EFFECT 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_e7648614374c0447bd4f3a51 | EVID_391db1c31ad31d10c4481811 | CAPITAL_EXPENDITURE_INCURRED | 1415.5 | 1415500000.0 | $1,415.5 million | MONEY | USD | 1000000 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-04-01~2025-06-30 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended June 30, 2025 (MATERIAL_SMIC_2025_Q2_RESULTS) | 2025-08-07T23:59:59+08:00 | p.5 WEBCAST CHUNK_2530f5dd3150f863931a3bd3 | REPORTED_FACT | — |

**D2_UTILIZATION_EFFECT 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_22b9ac0e65017fdf5637ea3e | EVID_e7103d2a15cefb9eaf2c7f2a | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_fe7226e4050a537918998c43 | In addition, the Group was in high investment period, and depreciation increased accordingly compared with 2022. | — |
| FACT_59161a36335978070219da32 | EVID_ac341415e94d16e43f70b315 | REPORTED_FACT | T1 | UNKNOWN | CNINFO / SMIC 2025 A Share Annual Report (MATERIAL_SMIC_2025_A_SHARE_ANNUAL_REPORT_CNINFO) | 2026-03-27T23:59:59+08:00 | p.6 A股 指 本公司在上交所科创板发行的普通股 CHUNK_047f7c0644533f5f8da9a760 | 固全球纯晶圆代工企业第二位置；产能利用率增至 93.5%，同比增长 8 个百分点；在折旧大幅增 | — |
| FACT_7700597229822810afcb120e | EVID_6e847621bd3a5e7b8471a1d6 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.37 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_8498c6b6d07561225cd7f841 | During the process of continuous high investments, the Company’s gross margin is under the pressure of high depreciation, | — |
| FACT_7dc73dc2ac88899123aa2d62 | EVID_921e1d21d4acaffbf75b5190 | REPORTED_FACT | T1 | UNKNOWN | CNINFO / SMIC 2025 A Share Annual Report (MATERIAL_SMIC_2025_A_SHARE_ANNUAL_REPORT_CNINFO) | 2026-03-27T23:59:59+08:00 | p.6 A股 指 本公司在上交所科创板发行的普通股 CHUNK_047f7c0644533f5f8da9a760 | 长的情况下，毛利率增至 22%，同比增加 3 个百分点。同时，公司实质性推进中芯北方少数股权 | — |
| FACT_aaf06bdf0e8e768f7380322a | EVID_4524a43ea22b3d39a75acad1 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.25 截至本报告发布日，公司较大的未决诉讼及仲裁包括：2020年5月7日，PDF SOLUTIONS, INC. CHUNK_91b66d24c60b7930fd79e362 | (2) 营业成本变动原因说明：主要是由于本年产能利用率下降、产品组合变动和折旧增加所致。 | — |
| FACT_c3c4d4d6b58a5002625b3edc | EVID_3639b4225c2c0e412050cf02 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.5 1Q26 4Q25 1Q25 CHUNK_94ea2e5744eeb2e4c5371ea0 | Utilization rate(2) 93.1% 95.7% 89.6% | — |
| FACT_c73fc50f7bfa5d90b6276fa2 | EVID_1c3dc864090cac8f4c9a9b23 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_fe7226e4050a537918998c43 | to the decrease of capacity utilization rate, the decrease of wafer shipment and product mix change during this year. | — |
| FACT_d95fd4952f0a60e39d094340 | EVID_3154aa1a93149fb86a04d72c | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2024 Annual Report (MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX) | 2025-04-09T23:59:59+08:00 | p.25 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_ce6dbe8257c5ac3eacc1c89d | The Company enhances its overall profitability by optimizing product mix, improving utilization rate, and refining process | — |
| FACT_fa29dcfa363cf7f3709b00c4 | EVID_c515b1039aecf047ebcc1197 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_fe7226e4050a537918998c43 | to the decrease of capacity utilization rate, the product mix change and the increase in depreciation. | — |
| FACT_fbadfef7e1807b434e6e41b0 | EVID_b1c888ce8a1e8062eafc586e | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.25 截至本报告发布日，公司较大的未决诉讼及仲裁包括：2020年5月7日，PDF SOLUTIONS, INC. CHUNK_91b66d24c60b7930fd79e362 | (3) 毛利变动原因说明：主要是由于本年产能利用率下降、晶圆销售数量减少及产品组合变动所 | — |

#### D3_MIX_EFFECT — MIXED

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| MIXED | 2 | ADEQUATE | MODEL_JUDGMENT | 2 | ASP_SOURCE_REPORTED | CH_003 |

公司关于「产品结构变化」的说明已全部移入管理层表述，不再作为支撑证据。在剩余可承重证据下，结构变化与售价、成本或毛利之间的关系只能表述为同期并存，方向维持 MIXED。具体数值及其期间、口径和来源见本维度证据表。

*supporting_evidence*

- `EVID_15431f7b706e456e0fd4ee74` role=PRIMARY_SUPPORT
它确认「售价」这一被问变量在证据集中确有可追溯的口径与数值，但为单点年度值，无上期可比数、无按制程或应用的拆分。具体数值及其期间、口径和来源见本维度证据表。

同一售价数据在盈利能力维度也可能被引用。此处的用途不同：本维度只把它作为「售价口径存在且被披露」的锚点，用于界定结构讨论所指向的价格变量，不用它论证利润率水平或其可持续性，不构成重复计分。

- `EVID_508ec4593d8212410c49cb84` role=CONTEXT
应用结构在报告期内存在可观测的位移。该数值在本集中标为不可承重，仅作背景。具体数值及其期间、口径和来源见本维度证据表。

应用占比亦可作为非主业或周期维度的背景。此处仅用于确认「结构确实发生变化」这一前提事实，不参与任何强度判断。

- `EVID_78340e489763db9663aa3022` role=CONTEXT
与消费电子占比上升方向相反，两者共同刻画应用结构位移的幅度。仅作背景。具体数值及其期间、口径和来源见本维度证据表。

与上一条同源，属同一张应用结构表。此处只作背景，不单独计入证据强度。

- `EVID_87d902958326c93773422130` role=CONTEXT
制程尺寸结构在同期基本持平，与应用结构的明显位移形成对照，提示「制程结构变化」一侧在本证据集内缺乏可观测位移。具体数值及其期间、口径和来源见本维度证据表。

尺寸结构数据在资本开支维度也可能被引用（产能投向）。此处仅用于说明本维度问题中「制程结构」一侧证据不足，用途不同。

*counter_evidence*

- `EVID_20847c93979c92b6d9eb5597` role=—
该期毛利率下降的说明中并未列入产品结构变化，只列折旧一项，结构并非各期毛利变动说明的稳定组成项。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_6e847621bd3a5e7b8471a1d6` role=—
公司披露的这句话把折旧单独点名为毛利承压来源，构成与结构解释并行的替代路径。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_f943e43f546a2e5fa8c716e3` role=—
同一季度中，结构变化出现在收入增长的说明里，而同期毛利率下降的说明中未提结构；两处表述指向不一致，削弱了「结构—毛利」的单一方向读法。具体数值及其期间、口径和来源见本维度证据表。

*alternative_explanations*

折旧规模上升：多期说明中折旧被单独或并列列为成本与毛利变动来源，在不涉及结构变化的情况下即可解释毛利率波动。

具体数值及其期间、口径和来源见本维度证据表。

会计口径与币种差异：唯一承重的售价观测为 CAS 口径人民币年度值，而毛利率与成本观测多为 IFRS 口径美元季度值，口径差异本身即可产生表观上的不一致。

行业与需求端因素：年报行业段落提到存储需求挤压其他应用供给、终端价格与需求变化等外部条件，这些条件在结构解释之外亦与售价和成本相关。

*limitations*

其余数值均标记 bearing=NO，只能以 CONTEXT 角色引用，量化骨架实际上是单点数据，无同口径上期可比值。具体数值及其期间、口径和来源见本维度证据表。

结论主要依赖文本命题而非数值证据；文本中「product mix change」始终与出货量、产能利用率、折旧并列出现，证据集内不存在把结构效应单独量化或分离的披露。

集内所有条目均为公司自身披露（年报与季度业绩公告），不含独立第三方对结构与售价关系的核验材料。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

经质询确认：公司自身的「产品结构变化」归因语句在证据集内没有独立佐证，已保留为管理层表述而非验证后的原因。

*gaps*

缺少按制程节点或按应用划分的售价、单位成本或毛利率拆分数据。

缺少可比期的 ASP 观测（同口径上期值），售价变化幅度无法计算。

缺少把结构效应与出货量、产能利用率、折旧分离的量化归因披露（如结构、价格、量的分解表）。

缺少独立第三方对制程与应用结构变化及其价格影响的核验材料。

*management_assertions*（来源观点，claim_type 见证据表）

- `EVID_e4b206094f5890f4cf04ffc1`
公司在该次披露中把产品结构变化列为毛利率或平均售价变动的说明之一；本阶段保留为公司具名表述，不作独立确认。

- `EVID_c2538a34f11c5131292d1fe8`
公司在该次披露中把产品结构变化列为毛利率或平均售价变动的说明之一；本阶段保留为公司具名表述，不作独立确认。

- `EVID_43289a6874cc99aca0fa341c`
公司在该次披露中把产品结构变化列为毛利率或平均售价变动的说明之一；本阶段保留为公司具名表述，不作独立确认。

- `EVID_1c3dc864090cac8f4c9a9b23`
公司在该次披露中把产品结构变化列为毛利率或平均售价变动的说明之一；本阶段保留为公司具名表述，不作独立确认。

**D3_MIX_EFFECT 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_4c74c9aa4f32c09e536c9436 | EVID_15431f7b706e456e0fd4ee74 | ASP_SOURCE_REPORTED | 6482 | 6482000 | 6,482 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/AMBIGUOUS/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.22 已通过环境管理系统（ISO 14001）、职业安全卫生管理系统（ISO 45001）的验证，并建立营运 CHUNK_42f10a406fae2fe45ce1defd | REPORTED_FACT | — |

**D3_MIX_EFFECT 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_7700597229822810afcb120e | EVID_6e847621bd3a5e7b8471a1d6 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.37 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_8498c6b6d07561225cd7f841 | During the process of continuous high investments, the Company’s gross margin is under the pressure of high depreciation, | — |
| FACT_782a7a42b7bfeb280dc74181 | EVID_20847c93979c92b6d9eb5597 | REPORTED_FACT | T1 | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.4 WEBCAST CHUNK_6673c3dbcdee031ba7c06d6d |  Gross margin was 19.2% in 4Q25, compared to 22.0% in 3Q25, due to the increase in depreciation. | — |
| FACT_92b8c517a6aa621cec3587e9 | EVID_87d902958326c93773422130 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_147513b98011d2d61311c7f2 | 12’’ wafers 77.1% 77.3% | — |
| FACT_9ab89a8bfa5e1839a71fe8cf | EVID_e4b206094f5890f4cf04ffc1 | REPORTED_FACT | T1 | SINGLE_QUARTER 2026-01-01~2026-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.4 WEBCAST CHUNK_fd51b55ab05bfc90ed31a5cf |  Gross margin was 20.1% in 1Q26, compared to 19.2% in 4Q25, due to the product mix change and | — |
| FACT_bdc5b86707712d5a81ac081f | EVID_c2538a34f11c5131292d1fe8 | REPORTED_FACT | T1 | SINGLE_QUARTER 2026-01-01~2026-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.4 WEBCAST CHUNK_fd51b55ab05bfc90ed31a5cf | the increase of average selling price in 1Q26. | — |
| FACT_bec5de889c5d1dd8ebee9580 | EVID_f943e43f546a2e5fa8c716e3 | REPORTED_FACT | T1 | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.4 WEBCAST CHUNK_6673c3dbcdee031ba7c06d6d | growth was mainly due to the increase in wafer shipment and product mix change in 4Q25. | — |
| FACT_c73fc50f7bfa5d90b6276fa2 | EVID_1c3dc864090cac8f4c9a9b23 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_fe7226e4050a537918998c43 | to the decrease of capacity utilization rate, the decrease of wafer shipment and product mix change during this year. | — |
| FACT_cbaf1cd15153701d8c96c7a6 | EVID_508ec4593d8212410c49cb84 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_147513b98011d2d61311c7f2 | Consumer Electronics 43.2% 37.8% | — |
| FACT_f2901c346e1957c1172b69ae | EVID_43289a6874cc99aca0fa341c | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.28 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_15b589c565ba839c26891647 | to the increase in wafer shipment, the increase in capacity utilisation rate and the product mix change for this year. | — |
| FACT_ff95a0200b19d3dce27e588e | EVID_78340e489763db9663aa3022 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.29 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_147513b98011d2d61311c7f2 | Smartphone 23.1% 27.8% | — |

#### D4_CAPEX_CONVERSION — MIXED

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| MIXED | 3 | STRONG | MODEL_JUDGMENT | 1 | CAPITAL_EXPENDITURE_INCURRED, DEPRECIATION_EXPENSE | — |

上述量价与产能指标与持续的资本开支在同一期间并行出现，可以说明支出规模与可观察产能、出货、收入呈现同向变动， 但候选集内没有任何单位产能投资额、新增产能爬坡节奏、分厂/分制程收入归属或增量投资回报的口径，无法将收入与产能的变化归因于特定期间的资本开支。折旧压力一侧更弱：候选集中标注为承重指标的折旧记录全部来自同一半年度来源组却被标为整个财年，且同时存在百分比与金额、正值与负值混排的记录， 数值互不自洽，不能据以刻画折旧对利润的实际压力。综合来看，"支出与可观察产能、出货、收入同向"这一半可由证据支持， "折旧压力如何"这一半在本候选集内不可回答，故整体判定为 MIXED。具体数值及其期间、口径和来源见本维度证据表。

*supporting_evidence*

- `EVID_b6ca12760465cf1f85ac2132` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

此处仅把它当作"投入规模"的时间序列输入，用来与产能、出货口径做同期对照，不重复承担盈利结论的权重，故非重复计数。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_64b7b6e55bf09b1bd6d6a983` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

本处只用其季度环比水平变化刻画投入节奏， 不用于推断毛利率或利用率结论，避免在两个维度同时充当承重结论的依据。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_506c9008573e9b29806e0917` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

在本维度它仅回答"支出是否持续"， 而不回答"支出是否改善盈利"，两处使用的结论指向不同，不构成双重计数。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_39fad64e2bfafa430372af35` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

此处用于刻画投入的期间波动，属于本维度问题的直接对象， 而周期维度关注的是需求侧节奏，两者的承重对象不同，故非重复使用。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_e74c8dc24d64d1c54207c161` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

产能指标同时属于利用率维度；此处仅作为背景对照，不承担本维度方向。

- `EVID_b3be960651e4a865e67edf78` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

与利用率、产能扩张维度共享，此处仅为背景，不承重。

- `EVID_eb92a4da2d3d97b5b80eb6bf` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

收入增速属于成长与盈利维度的承重口径，此处仅作同期并列的背景观察，不用其推断投入回报。

- `EVID_73fb997b13c8db486f7293ce` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

该表述也可服务于战略与可持续性维度；此处仅用作支出用途的定性背景，不作为产能或收入结果的依据。

*counter_evidence*

- `EVID_3639b4225c2c0e412050cf02` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_f4043f182aabc51a9d04505c` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_3f86d2cc1b762cdd4d777208` role=—
年报风险章节列示资产减值风险条目，提示重资产投入在资产端存在潜在减值敞口。

*alternative_explanations*

收入与出货的同期上行可能主要来自下游需求与产品结构变化，而非本期资本开支所形成的新增产能。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

收入增长与产能扩张同期出现，也可能同时受行业本地化替代等外部环境因素影响，候选集不含可区分这两者的口径。

*limitations*

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

资本开支为美元 IFRS 口径，折旧记录为人民币 CAS 口径，候选集内没有可用于跨口径对照的桥接记录。

*gaps*

缺少可用的折旧费用绝对额与折旧率时间序列，无法回答问题中"折旧压力"的一半。

缺少单位新增产能对应的资本开支口径，无法衡量投入效率。

缺少分厂、分制程或分节点的收入与产能归属数据，无法把产能增量与收入增量对应起来。

缺少在建工程转固、固定资产原值与净值的期间明细，无法观察支出向可折旧资产的落地节奏。

**D4_CAPEX_CONVERSION 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_72cd7213f8abbab8f390e4c1 | EVID_b6ca12760465cf1f85ac2132 | CAPITAL_EXPENDITURE_INCURRED | 1885.1 | 1885100000.0 | $1,885.1 million | MONEY | USD | 1000000 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-04-01~2025-06-30 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended June 30, 2025 (MATERIAL_SMIC_2025_Q2_RESULTS) | 2025-08-07T23:59:59+08:00 | p.5 WEBCAST CHUNK_2530f5dd3150f863931a3bd3 | REPORTED_FACT | — |
| FACT_8936d88d35f037bbb23164bd | EVID_64b7b6e55bf09b1bd6d6a983 | CAPITAL_EXPENDITURE_INCURRED | 2394.2 | 2394200000.0 | $2,394.2 million | MONEY | USD | 1000000 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-07-01~2025-09-30 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended September 30, 2025 (MATERIAL_SMIC_2025_Q3_RESULTS) | 2025-11-13T17:49:59+08:00 | p.5 WEBCAST CHUNK_8a6728d872d8c5a02efea27a | REPORTED_FACT | — |
| FACT_95f02ef2ce7a6ec2213217a6 | EVID_506c9008573e9b29806e0917 | CAPITAL_EXPENDITURE_INCURRED | 2407.5 | 2407500000.0 | $2,407.5 million | MONEY | USD | 1000000 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.5 4Q25 3Q25 4Q24 CHUNK_d39510d857cc96651cbdf1ea | REPORTED_FACT | — |
| FACT_d5837996a073342df0392242 | EVID_39fad64e2bfafa430372af35 | CAPITAL_EXPENDITURE_INCURRED | 1562.8 | 1562800000.0 | $1,562.8 million | MONEY | USD | 1000000 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2026-01-01~2026-03-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.5 1Q26 4Q25 1Q25 CHUNK_640905b37fb37f2823d8b528 | REPORTED_FACT | — |

**D4_CAPEX_CONVERSION 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_17069a179073a6a29c4feed7 | EVID_e74c8dc24d64d1c54207c161 | REPORTED_FACT | T1 | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.5 4Q25 3Q25 4Q24 CHUNK_d39510d857cc96651cbdf1ea |  Monthly capacity increased to 1,058,750 standard logic 8-inch equivalent wafers in 4Q25 from | — |
| FACT_65856c1c25671ab2a05edac4 | EVID_73fb997b13c8db486f7293ce | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.31 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_35e230c4e370ee57d12bc7bf | Most of the capital expenditure in the Reporting Period are used for capacity expansion. | — |
| FACT_7080375444417ebb46bf9497 | EVID_f4043f182aabc51a9d04505c | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.5 1Q26 4Q25 1Q25 CHUNK_94ea2e5744eeb2e4c5371ea0 | Wafer shipments(1) 2,509,137 2,514,970 -0.2% 2,292,153 9.5% | — |
| FACT_8068bc23d8b4a510e7c4ca87 | EVID_3f86d2cc1b762cdd4d777208 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.26 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_78c3137a8f8e87171382ea9f | The risk of impairment on assets | — |
| FACT_c3c4d4d6b58a5002625b3edc | EVID_3639b4225c2c0e412050cf02 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.5 1Q26 4Q25 1Q25 CHUNK_94ea2e5744eeb2e4c5371ea0 | Utilization rate(2) 93.1% 95.7% 89.6% | — |
| FACT_caac62f4e583c266ae2709a7 | EVID_b3be960651e4a865e67edf78 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | capacity was 1,059 thousand standard logic 8-inch equivalent wafers by the end of the year, increased | — |
| FACT_ec0c0f8bfd11c7cee85c0a87 | EVID_eb92a4da2d3d97b5b80eb6bf | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | revenue in 2025 increased by 16.2% year-over-year to $9,327 million, and gross margin increased by | — |

## 五、D5–D6：行业周期、政府补助和其他替代解释

#### D5_CYCLE_EXPLANATION — UNKNOWN

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| UNKNOWN | 2 | ADEQUATE | MODEL_JUDGMENT | 1 | — | — |

候选证据集中没有任何可用的数值观测，承重指标白名单为空，本维度的全部内容只能建立在文字命题之上。但候选集中不存在任何毛利率、单价、产能利用率或盈利能力的可用量化观测，也没有把周期变量与盈利变动分离开来的口径说明。与此同时，年报文本还明确提到在持续高投入过程中毛利率承受很高的折旧压力，这是一条与周期无关、同样作用于盈利能力的表述。综合来看，现有材料只能说明行业供需、价格与库存周期 与公司经营方向的描述在时间上一致，无法说明周期能解释盈利能力变化中的多少部分，也无法排除折旧、产品组合与成本结构等并行因素。故本维度结论为 UNKNOWN。具体数值及其期间、口径和来源见本维度证据表。

*supporting_evidence*

- `EVID_15a40887766c5686a185424c` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

同一事实也可在盈利能力（D 系列中的利润率）维度中作为背景出现；此处仅用于确立"周期方向"这一自变量的存在，不用于解释利润率水平本身，故不构成重复计分。

- `EVID_7f39841c745ba9ed70472acb` role=PRIMARY_SUPPORT
文本表述半导体行业经历结构性供需调整，直接对应本维度问题中的"供需"部分。

供需描述也可能被产能利用率维度引用；此处只作为行业侧供需状态的文字刻画，不用于推断公司自身产能利用水平，二者取用角度不同。

- `EVID_75b2adc0f19f81f46584457a` role=PRIMARY_SUPPORT
文本表述集成电路库存仍处于高位，对应本维度问题中的"库存周期"部分。

库存表述也可能与非经常性或可持续性维度相关；此处仅用于描述行业库存状态，不用于评价公司存货计价或减值，故不构成重复计分。

- `EVID_1f1570b0e2365bc83cdbd1ea` role=PRIMARY_SUPPORT
文本表述半导体库存消化速度慢于产业链各环节的生产与采购速度，补充了库存周期的相对速度信息。

该表述属于行业链条层面的库存节奏，与公司自身存货科目无关，不会与非核心或可持续性维度的公司层面存货证据重叠。

- `EVID_9c0f69c1e76737a377b54293` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

需求复苏描述亦可服务于可持续性维度；此处仅用于刻画周期内部的方向切换，不用于对未来盈利延续性作判断。

- `EVID_9ac85d42c839ece6141f7e4d` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_acbfa8e8c3cfec4d7a0f4541` role=CONTEXT
文本表述中长期行业整体仍兼具周期性，说明周期属性是行业的常态特征，而非某一年的孤立现象。

- `EVID_e86d1ef128bda41d33f8fef6` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

*counter_evidence*

- `EVID_6e847621bd3a5e7b8471a1d6` role=—
年报文本表述在持续高投入过程中毛利率承受很高的折旧压力，说明盈利能力同时受到与行业周期无关的固定成本因素影响，削弱了把盈利变化单独归于周期的可能。

- `EVID_71541cf2991d52d9673bc9c0` role=—
文本表述公司以持续盈利为目标、严格控制成本并提高效率，属于与周期并行的内部成本管理因素，同样可能作用于盈利结果。

- `EVID_d19afcec2124af5c19d2da7d` role=—
文本表述从整体市场看需求复苏强度不足，说明周期信号本身在期内是混合的，不足以支撑一个单向的周期解释。

*alternative_explanations*

折旧与固定资产投入节奏：候选文本明确提到高投入阶段的折旧压力，盈利能力变化可能主要与产能建设节奏相关，而非行业周期。

产品与应用结构变化：文本提到各细分应用领域的复苏节奏存在差异，产品组合与应用结构的变动是与周期并列的另一条解释路径。

成本控制与效率管理：文本提到公司严格控制成本、提高效率，内部经营举措可能与周期同时作用于盈利结果。

地缘与产业链在地化因素：文本提到区域化、在地化产能建设与地缘政治挑战，这些结构性因素与传统供需周期并不等价。

*limitations*

本维度候选集内没有任何可用数值观测，承重指标白名单为空，全部结论只能建立在文字命题之上。

没有毛利率、平均单价、产能利用率等盈利能力相关的可用量化观测，无法度量周期与盈利之间的任何对应关系。

文字命题只能给出方向性描述与时间上的并存关系，无法支持任何分解或归因结论。

候选文本主要来自公司年报的行业概述章节，缺少独立第三方的行业价格与库存序列作为交叉核对。

同一期间的文本内部存在方向不一致的表述（下行与复苏迹象并存），进一步限制了结论的确定性。

*gaps*

缺少按期间可比的毛利率与平均销售单价观测，无法建立盈利能力的量化基线。

缺少产能利用率的可用数值序列，无法刻画供需状态在公司层面的传导。

缺少独立的行业价格指数与渠道库存数据，无法对年报文本中的周期描述作外部验证。

缺少把折旧、产品结构与周期因素分开列示的口径说明，无法进行任何分解分析。

**D5_CYCLE_EXPLANATION 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

**D5_CYCLE_EXPLANATION 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_07dd9d3bee5dbba7688b2b17 | EVID_7f39841c745ba9ed70472acb | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.21 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_461d3ea418efa90a335ba1bc | The semiconductor industry experienced structural supply and | — |
| FACT_1626f2745f88ae86fa62c933 | EVID_d19afcec2124af5c19d2da7d | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.37 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_8498c6b6d07561225cd7f841 | However, from the perspective of the overall market, the demand recovery is not strong | — |
| FACT_1962c06abfbed14fe0f9bf96 | EVID_e86d1ef128bda41d33f8fef6 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.14 IP支持、光掩模制造等一站式配套服务，并促进集成电路产业链的上下游协同，与产业链中各环 CHUNK_0a039d068339d69bb23c095f | 库存消化仍为 2023 年半导体行业主旋律。中长期看，全球半导体行业兼具周期性和成长性，短期 | — |
| FACT_2de147af452a89c66c846a50 | EVID_acbfa8e8c3cfec4d7a0f4541 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.20 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_81d56871b4272bbb8893862b | In the medium to long term, the overall industry maintains its cyclicality | — |
| FACT_403db0117eea218feb0ad93d | EVID_9c0f69c1e76737a377b54293 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.20 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_81d56871b4272bbb8893862b | In the second half of 2023, the end market demand showed signs of recovery, while the overall supply | — |
| FACT_4494afc0366905e7714d4de3 | EVID_75b2adc0f19f81f46584457a | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.21 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_461d3ea418efa90a335ba1bc | And the IC inventory was still at the high level. | — |
| FACT_7700597229822810afcb120e | EVID_6e847621bd3a5e7b8471a1d6 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.37 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_8498c6b6d07561225cd7f841 | During the process of continuous high investments, the Company’s gross margin is under the pressure of high depreciation, | — |
| FACT_7ca9a7bfe1257381b13a7cde | EVID_15a40887766c5686a185424c | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.20 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_81d56871b4272bbb8893862b | In 2023, the semiconductor industry went into a downward cycle due to global economic weakness, soft market demand | — |
| FACT_a228e185d1528c0370081f99 | EVID_9ac85d42c839ece6141f7e4d | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2024 Annual Report (MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX) | 2025-04-09T23:59:59+08:00 | p.20 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_a3f233b769b926bad10d7df4 | In 2024, the global semiconductor industry showed signs of recovery. | — |
| FACT_b394c7e69e083f22d7ffc3fb | EVID_1f1570b0e2365bc83cdbd1ea | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.21 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_461d3ea418efa90a335ba1bc | semiconductor inventory digestion was slower than that of the production and procurement on all links of the industry | — |
| FACT_d4c359334de1c29d2cb43ffb | EVID_71541cf2991d52d9673bc9c0 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2023 Annual Report (MATERIAL_SMIC_2023_ANNUAL_REPORT_IFRS_HKEX) | 2024-04-09T23:59:59+08:00 | p.37 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_8498c6b6d07561225cd7f841 | and the Company will always target sustained profitability, strictly control costs and improve efficiency. | — |

#### D6_NONCORE_EXPLANATION — MIXED

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| MIXED | 3 | STRONG | MODEL_JUDGMENT | 1 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL, OTHER_OPERATING_INCOME | — |

候选证据可以证明政府补助与其他营业收入在中芯国际的利润构成中体量可观且逐年波动，但不足以量化它们对盈利能力变化的解释比例。与此同时，年报披露该期间息税折旧摊销前利润及其利润率的变化主要与晶圆出货量、产能利用率与产品结构相关， 补助并未被公司列为盈利能力变化的主要说明口径。候选集合内缺少可复算的毛利率或净利率分解， 也缺少将补助金额与利润率变动逐期对应的桥接数据，在此前提下只能确认非核心因素在规模上重要且波动明显， 无法给出其解释盈利能力变化的确定份额，结论为部分支持。具体数值及其期间、口径和来源见本维度证据表。

*supporting_evidence*

- `EVID_0d549953e11009b614bdee9d` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

- `EVID_97d41328fbf5d641da666274` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

- `EVID_00021b95b7341434185a4255` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

此处只用于刻画非核心项目的年度波动路径， 未重复用于评价利润或资本开支水平。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_42bc010cf9031d1137d6ad44` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

本维度使用它是为了定位非核心收入的规模与其在报表中的落点，不重复评价盈利能力水平。具体数值及其期间、口径和来源见本维度证据表。

- `EVID_6dc910188f51d398a252dfc8` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_5f5e3a69713e087b033996e6` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_c7990a96f80f5f982e258933` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_b98a7e786ac2a8e90fb59b1b` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

*counter_evidence*

- `EVID_82053569393d872bbf3d0c0d` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_b44990fde51e27f29bd8aacb` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_2407ff7913bbf5adec678577` role=—
具体数值及其期间、口径和来源见本维度证据表。

*alternative_explanations*

出货量、产能利用率与产品结构的变化可在不依赖政府补助的情况下与同期盈利能力变化并存。

折旧与摊销规模的持续扩大与毛利率变化同期出现，可能是比非核心项目更重要的解释路径。

非经常性损益中还包含公允价值变动损益、资产处置损益与联营企业相关项目，其合计波动幅度大于补助本身。

递延收益按设备使用年限或里程碑分期释放，确认节奏与实际收到金额并不同步，年度间落差可能来自会计确认时点而非经营变化。

*limitations*

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

中国企业会计准则口径以千元列示、国际财务报告准则口径以千美元列示，候选集合内没有可复算的汇率或桥接关系，跨口径数值只能并列观察。

候选集合内没有毛利率或净利率的逐期分解，也没有把补助金额换算为利润率贡献点数的可复算公式。

具体数值及其期间、口径和来源见本维度证据表。

*gaps*

缺少与盈利能力指标同频的季度政府补助确认序列，无法把补助波动与季度利润率变化逐期对齐。

缺少递延收益余额的分期释放计划，无法判断未来期间非核心收入的确认节奏。

缺少剔除政府补助后的经营利润口径披露，无法直接观察扣除非核心因素后的盈利能力路径。

**D6_NONCORE_EXPLANATION 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_55b5130d21b9b2e013460469 | EVID_0d549953e11009b614bdee9d | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1677347 | 1677347000 | 1,677,347 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2023-01-01~2023-12-31 | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.233 与PDF SOLUTIONS,INC.的合同纠纷仲裁 CHUNK_1690c8b2f51869c7bc31802f | REPORTED_FACT | — |
| FACT_7767b79f68b2e80d80662853 | EVID_42bc010cf9031d1137d6ad44 | OTHER_OPERATING_INCOME | 2577275 | 2577275000 | 2,577,275 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2023-01-01~2023-12-31 | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.29 A.公司主要销售客户情况 CHUNK_9c46bceb1cba96b9b098224b | REPORTED_FACT | — |
| FACT_cf753829b162ef8180c699df | EVID_00021b95b7341434185a4255 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1582524 | 1582524000 | 1,582,524 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 A Share Annual Report (MATERIAL_SMIC_2025_A_SHARE_ANNUAL_REPORT_CNINFO) | 2026-03-27T23:59:59+08:00 | p.231 中国信息通信 何书平 2018 年 8 月 91420100MA4 人民币300 信息通信 CHUNK_d9f3073fdca0fd6d96cd3eea | REPORTED_FACT | — |
| FACT_f78cc67bd6b884715913abd9 | EVID_97d41328fbf5d641da666274 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1333945 | 1333945000 | 1,333,945 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2024-01-01~2024-12-31 | HKEXnews / SMIC 2024 A Share Annual Report (MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2025-03-27T23:59:59+08:00 | p.221 与PDF的合同纠纷仲裁 CHUNK_0ffe0c93997624d6aecb4f9e | REPORTED_FACT | — |

**D6_NONCORE_EXPLANATION 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_05373d5adb650d12476d2853 | EVID_5f5e3a69713e087b033996e6 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.17 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_300fa12fa7fb91f7f22ca504 | Total	109,575	123,818	436,563 | — |
| FACT_4c2f5382dec3610817ce5e35 | EVID_6dc910188f51d398a252dfc8 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.17 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_a8d8b7ee15f556a29c8b654f | Government funding 222,637 187,686 236,425 | — |
| FACT_5f62647a93bc93c3a10be0ba | EVID_2407ff7913bbf5adec678577 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2024 Annual Report (MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX) | 2025-04-09T23:59:59+08:00 | p.17 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_725c0bc97940fb7aa4d21150 | The decrease of EBITDA margin was mainly due to EBITDA growth rate for this year lower than revenue growth rate. | — |
| FACT_64bca05b4fa7511e564217ff | EVID_b98a7e786ac2a8e90fb59b1b | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.146 NOTES TO THE CONSOLIDATED FINANCIAL STATEMENTS CHUNK_a9c3cbfe017f17fd93fffd0a | Group receives government funding of US$193.0 million (2024: US$261.8 million) and recognised US$199.6 million | — |
| FACT_6dfc40a26ee318a380e9f205 | EVID_82053569393d872bbf3d0c0d | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.17 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_300fa12fa7fb91f7f22ca504 | The increase in EBITDA and EBITDA margin for this year were mainly due to the increase in wafer shipment, the increase | — |
| FACT_723d3583835d18c3bb800cf7 | EVID_c7990a96f80f5f982e258933 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.17 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_a8d8b7ee15f556a29c8b654f | Profit for the year 988,944 729,993 | — |
| FACT_f9ee1198848f9e3b432b6fe6 | EVID_b44990fde51e27f29bd8aacb | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2024 Annual Report (MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX) | 2025-04-09T23:59:59+08:00 | p.17 SECTION 3 CORPORATE PROFILE AND PRINCIPAL FINANCIAL INDICATORS CHUNK_725c0bc97940fb7aa4d21150 | The increase in EBITDA was mainly due to the increase in wafer shipment and the product mix change during this year. | — |

### 政府补助双口径

**报告口径**：来源披露的、已计入损益的政府资金记录。

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_073e5cdc3df008074dd343c0 | EVID_f982d6663d726a8ef0382da2 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1931143 | 1931143000 | 1,931,143 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | UNKNOWN | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.12 A股 上交所科创板 中芯国际 688981 不适用 CHUNK_481effeacf8ae7dbcae42b74 | REPORTED_FACT | GAP_NORMALIZE_8cb493fd7d6d7675 |
| FACT_09c05b5b2cbf15c8d9069b48 | EVID_329549e63dfe07e21a1bbb53 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 517163 | 517163000 | 517,163 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.136 及期货条例第XV章）股份、相关股份及债权证且须按照香港证券及期货条例第XV章第7及第8 CHUNK_bba7287760d6ca789714b5be | REPORTED_FACT | — |
| FACT_146c5811e718c63a2a32d856 | EVID_991f22695017e71f91b5c707 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1272642 | 1272642000 | 1,272,642 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | UNKNOWN | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.12 A股 上交所科创板 中芯国际 688981 不适用 CHUNK_481effeacf8ae7dbcae42b74 | REPORTED_FACT | GAP_NORMALIZE_45099e0461ec7e5b |
| FACT_1e6095f5eae592d62251d590 | EVID_9ad5737500adeb457cbdced0 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 182045 | 182045000 | 182,045 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Third Quarter A Share Report (MATERIAL_SMIC_2025_Q3_A_SHARE_REPORT_CNINFO) | 2025-11-14T23:59:59+08:00 | p.6 DOCUMENT_BODY CHUNK_4c02021fb44dc6fcc398a119 | REPORTED_FACT | — |
| FACT_27e5affb877ea102048f92b0 | EVID_9cf50310803db512b4ea169c | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 722975 | 722975000 | 722,975 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.136 及期货条例第XV章）股份、相关股份及债权证且须按照香港证券及期货条例第XV章第7及第8 CHUNK_bba7287760d6ca789714b5be | REPORTED_FACT | — |
| FACT_28d4ae07a983e8c7be6f10e3 | EVID_18023647762adf13b9d9c35d | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1677347 | 1677347000 | 1,677,347 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2023-01-01~2023-12-31 | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.233 与PDF SOLUTIONS,INC.的合同纠纷仲裁 CHUNK_1690c8b2f51869c7bc31802f | REPORTED_FACT | — |
| FACT_4d7c61c83c5da993530ee776 | EVID_c651c7aaaec125dcbdd03132 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1677347 | 1677347000 | 1,677,347 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | UNKNOWN | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.12 A股 上交所科创板 中芯国际 688981 不适用 CHUNK_481effeacf8ae7dbcae42b74 | REPORTED_FACT | GAP_NORMALIZE_be0466bf847a8d28 |
| FACT_55b5130d21b9b2e013460469 | EVID_0d549953e11009b614bdee9d | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1677347 | 1677347000 | 1,677,347 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2023-01-01~2023-12-31 | HKEXnews / SMIC 2023 A Share Annual Report (MATERIAL_SMIC_2023_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2024-03-28T23:59:59+08:00 | p.233 与PDF SOLUTIONS,INC.的合同纠纷仲裁 CHUNK_1690c8b2f51869c7bc31802f | REPORTED_FACT | — |
| FACT_8ea35a2006d28f0033fad0cf | EVID_de819659b6f969e25d85fb82 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 477768 | 477768000 | 477,768 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/AMBIGUOUS/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.151 与PDF SOLUTIONS,INC.的合同纠纷仲裁 CHUNK_77749d3b4f11611f3c415834 | REPORTED_FACT | — |
| FACT_99317225dac92e4a516cdaae | EVID_6b2a64fce4803b010bfb8e64 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 517163 | 517163000 | 517,163 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.136 及期货条例第XV章）股份、相关股份及债权证且须按照香港证券及期货条例第XV章第7及第8 CHUNK_bba7287760d6ca789714b5be | REPORTED_FACT | — |
| FACT_cbca644e06c4cad89a4aece2 | EVID_652ae1728c5fc4ef8a51e918 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 722975 | 722975000 | 722,975 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.136 及期货条例第XV章）股份、相关股份及债权证且须按照香港证券及期货条例第XV章第7及第8 CHUNK_bba7287760d6ca789714b5be | REPORTED_FACT | — |
| FACT_cf753829b162ef8180c699df | EVID_00021b95b7341434185a4255 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1582524 | 1582524000 | 1,582,524 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 A Share Annual Report (MATERIAL_SMIC_2025_A_SHARE_ANNUAL_REPORT_CNINFO) | 2026-03-27T23:59:59+08:00 | p.231 中国信息通信 何书平 2018 年 8 月 91420100MA4 人民币300 信息通信 CHUNK_d9f3073fdca0fd6d96cd3eea | REPORTED_FACT | — |
| FACT_e12d5bb8cf4b4e785c1810b2 | EVID_5f050d52a8b8f3287929a9c3 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 659813 | 659813000 | 659,813 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Third Quarter A Share Report (MATERIAL_SMIC_2025_Q3_A_SHARE_REPORT_CNINFO) | 2025-11-14T23:59:59+08:00 | p.6 DOCUMENT_BODY CHUNK_4c02021fb44dc6fcc398a119 | REPORTED_FACT | — |
| FACT_f47040bfa71e5d2d630243c1 | EVID_e676a479f740d59eeaa60697 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 477768 | 477768000 | 477,768 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/AMBIGUOUS/SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | CNINFO / SMIC 2025 Semi-Annual A Share Report (MATERIAL_SMIC_2025_H1_A_SHARE_REPORT_CNINFO) | 2025-08-29T23:59:59+08:00 | p.9 A股 上交所科创板 中芯国际 688981 不适用 CHUNK_5beaaafdcf1ed4b936d1ca6b | REPORTED_FACT | — |
| FACT_f78cc67bd6b884715913abd9 | EVID_97d41328fbf5d641da666274 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 1333945 | 1333945000 | 1,333,945 | MONEY | CNY | 1000 | CAS/CONSOLIDATED/REVIEWED/SOURCE_REPORTED | FISCAL_YEAR 2024-01-01~2024-12-31 | HKEXnews / SMIC 2024 A Share Annual Report (MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS) | 2025-03-27T23:59:59+08:00 | p.221 与PDF的合同纠纷仲裁 CHUNK_0ffe0c93997624d6aecb4f9e | REPORTED_FACT | — |

| 口径 | 记录数 |
|---|---|
| GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL（报告口径） | 15 |
| SENSITIVITY_EX_GOVERNMENT_FUNDING（敏感性口径） | 0 |

第二口径没有任何记录。政府资金记录存在，但无一满足「金额可分离、可追溯，且能证明已计入同期间同口径 profit from operations」的全部条件，因此固定公式不被触发，敏感性值保持 UNKNOWN。这里不硬算一个数：按会计规则，不可分离的金额被扣减出来的利润不是任何一种真实口径。该缺口已登记为 `GAP_REPORT_GOVERNMENT_FUNDING_SENSITIVITY_ABSENT`。

## 六、D7：可持续性支持、降级与证伪条件

#### D7_SUSTAINABILITY_EVIDENCE — UNKNOWN

| finding | evidence_score | evidence_score_label | finding_reason_code | generation_attempts | bearing_metric_whitelist | revised_from_challenge_ids |
|---|---|---|---|---|---|---|
| UNKNOWN | 2 | ADEQUATE | MODEL_JUDGMENT | 1 | — | CH_005 |

但必须说明：本维度的承重指标白名单为空，上述收入、销售成本、毛利与毛利率均属结果性指标，用结果证明结果本身可持续属于循环论证， 故它们在本判断中仅作为背景信息引用，不承担支撑重量。与此同时公司在风险章节反复提示业绩波动、毛利率波动、资产减值与持续大额资本开支压力。快照中存在经营活动现金流记录，但本维度冻结的检索族 未将其取回，故无法在本证据集内做现金流与利润的交叉验证。综合而言，改善事实可跨期、跨结果指标观察到，但「有经营机制支持且可持续」这一 命题在当前证据集内未获得可承重的独立验证，故判定为 MIXED。具体数值及其期间、口径和来源见本维度证据表。

*supporting_evidence*

- `EVID_7f523f5b558ecd8b586991d9` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

同一句在 D 系其他维度（如竞争力或经营质量类维度）也可能被引用，但那里承担的是「公司是否具备经营抓手」的描述性作用；本维度只用它检验 「改善是否有被披露的机制解释」，且已明确其为通用表述、未附拆分数据，不作为可持续性的独立证明，故不构成重复计量。

- `EVID_3154aa1a93149fb86a04d72c` role=PRIMARY_SUPPORT
具体数值及其期间、口径和来源见本维度证据表。

与上一条同源但属不同年度文件，在本维度的作用是「跨期一致性检验」而非再次证明机制有效；其他维度若引用，引用的是机制内容本身， 两者用途不同，不构成重复计量。

- `EVID_bfa338a32e5774667b036775` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_2a7313c13e2e5c8906a767bf` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_f90533faff49aad01a87a752` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_eb92a4da2d3d97b5b80eb6bf` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_92274e4288006aaeb477ca74` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_af629896441719c1cc08a092` role=CONTEXT
具体数值及其期间、口径和来源见本维度证据表。

*counter_evidence*

- `EVID_6827b1e1cf99ee76189e5f2e` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_0a7d6f7545b73e221846761d` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_280a312fa4d2242c710058e1` role=—
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_c520e297f760b3b478bd5501` role=—
具体数值及其期间、口径和来源见本维度证据表。

*alternative_explanations*

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

毛利率变化可能与产能利用率的高位运行同步，而高利用率本身可能是需求侧短期状态，不必然对应长期机制。

会计口径与期间划分（IFRS 单季数据、快照内同一期间存在多条口径不同的销售成本记录）也可能影响跨期比较的表观改善幅度。

*limitations*

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

候选文本大量为年报风险章节与业务模式章节的切片，句子被截断，语义完整性有限，不宜据以做因果推断。

前瞻性指引材料只能作为具名公司陈述记录，不能用于支撑或反驳本维度结论。

*gaps*

经营活动现金流记录存在于快照中，但本维度冻结的检索族未将其取回，无法在本证据集内完成利润与现金流的交叉验证。

缺少费用结构（研发费用、销售管理费用）与折旧摊销的期间数据，无法检验毛利改善是否被下游成本项抵消。

缺少产品结构、晶圆平均单价、各技术节点收入占比等分项数据，无法核验「优化产品组合」这一机制表述。

缺少客户集中度与订单/在手订单的量化披露，无法判断需求侧支撑的稳定性。

*management_assertions*（来源观点，claim_type 见证据表）

- `EVID_759908b984d49c1fedb7c038`
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_608ec900f29e9941221ebc20`
具体数值及其期间、口径和来源见本维度证据表。

- `EVID_a2a9122327152a79c0162dfd`
公司管理层表示，基于客户需求与在手订单，对本年度整体业务较上季度更为乐观。

- `EVID_937ccb9a137eb428b0ba681e`
具体数值及其期间、口径和来源见本维度证据表。

*watch_indicators*

若后续季度实际毛利率持续低于公司已披露的指引区间下限，则结果指标改善的跨期连续性被削弱，本维度结论应向 NOT_SUPPORTED 方向下调；若实际值稳定处于或高于区间上限，则维持现有 MIXED 判断而不自动上调，机制层面的缺口并未随之补齐。

产能利用率与毛利率在同一期间同向变动时，说明结果指标高度依赖负荷水平；若利用率明显回落而毛利率同步走弱，则「有经营机制支持」的解释 进一步减弱，结论应下调。

该数据在本维度证据集内缺失；一旦取得，若利润改善期间经营活动现金流未同向改善，则盈利改善的质量存疑，本维度结论应下调；若两者同向且幅度相称，则可支持向 SUPPORTED 方向修正。

若后续年报仍仅重复「优化产品组合、提高产能利用率、精进工艺」的通用表述而无可核验拆分，则机制层面的证据缺口保持不变， 本维度不应上调；若出现分项披露且与毛利变动方向一致，则可支持上调。

若后续期间出现减值计提或折旧压力披露扩大， 同时毛利率走弱，则可持续性判断应下调。具体数值及其期间、口径和来源见本维度证据表。

| indicator | threshold | threshold_basis | basis_evidence_id | proposed_threshold |
|---|---|---|---|---|
| 季度毛利率（公司季度业绩公告披露口径） | 18% | SOURCE_DISCLOSED_THRESHOLD | EVID_759908b984d49c1fedb7c038 | — |
| 年化/季度产能利用率（公司业绩公告披露口径） | UNKNOWN | UNKNOWN | — | — |
| 经营活动产生的现金流量净额与净利润的期间对照（年报/季报现金流量表） | UNKNOWN | UNKNOWN | — | — |
| 年报披露的盈利机制表述是否附带分项数据（产品组合、单价、单位成本拆分） | UNKNOWN | UNKNOWN | — | — |
| 资本开支规模与固定资产减值/存货跌价相关披露 | UNKNOWN | UNKNOWN | — | — |

**D7_SUSTAINABILITY_EVIDENCE 数值证据表**（本维度所有数字的唯一出处）

| fact_id | evidence_id | metric_id | display_value | base_unit_value | raw_value_text | unit | currency | scale_factor | accounting_basis | period | source | published_at | locator | claim_type | gap_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_abf6710b0e1277ff41c622a7 | EVID_6827b1e1cf99ee76189e5f2e | GROSS_MARGIN | 19.2 | — | 19.2% | PERCENT | USD | 1 | IFRS/CONSOLIDATED/UNAUDITED/SOURCE_REPORTED | SINGLE_QUARTER 2025-10-01~2025-12-31 | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.4 WEBCAST CHUNK_6673c3dbcdee031ba7c06d6d | REPORTED_FACT | — |

**D7_SUSTAINABILITY_EVIDENCE 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）

| fact_id | evidence_id | claim_type | source_tier | period | source | published_at | locator | source_span_text | gap_ids |
|---|---|---|---|---|---|---|---|---|---|
| FACT_0adade094aa3cde28e201350 | EVID_608ec900f29e9941221ebc20 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_6fde9a260cfadddcc82a7d5f |  Gross margin to range from 20% to 22%. | — |
| FACT_1ca21d31f2764eb6c8221503 | EVID_af629896441719c1cc08a092 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2024 Annual Report (MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX) | 2025-04-09T23:59:59+08:00 | p.19 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_7c48ff2719ff17dbd3afce54 | During the reporting period, the Group recorded revenue of US$8,029.9 million, representing a year-on-year increase of | — |
| FACT_2c264530d1cf4aae5770844d | EVID_7f523f5b558ecd8b586991d9 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.25 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_aae6d0ad0f6c2b629e39f643 | The Company enhances its overall profitability by optimizing product mix, improving utilisation rate, and refining process | — |
| FACT_4e41ee6d5e010a0f03a1b4f2 | EVID_759908b984d49c1fedb7c038 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | gross margin is expected to be in the range of 18% to 20%. | — |
| FACT_5461cf1785ac35634275dfcd | EVID_a2a9122327152a79c0162dfd | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended March 31, 2026 (MATERIAL_SMIC_2026_Q1_RESULTS) | 2026-05-14T18:17:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_6fde9a260cfadddcc82a7d5f | Based on customer demand and order in hand, we are more optimistic about our overall business for | — |
| FACT_6e8d0a614e78d2e41a6adf46 | EVID_bfa338a32e5774667b036775 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | margin was 19.2% and the capacity utilization rate remained at 95.7%. | — |
| FACT_822490933e86819059cf72a0 | EVID_92274e4288006aaeb477ca74 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | 3.0 percentage points to 21.0%. | — |
| FACT_843bc45fe90db646bb7be975 | EVID_0a7d6f7545b73e221846761d | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.25 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_aae6d0ad0f6c2b629e39f643 | The risk of performance fluctuations | — |
| FACT_b6bc8455fe572bd14bcb888e | EVID_280a312fa4d2242c710058e1 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.25 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_aae6d0ad0f6c2b629e39f643 | and R&D expenses, may cause the Company to be exposed to the risks of fluctuations in sales revenue, gross margin, | — |
| FACT_d2aa8768f9a44e5838db4cff | EVID_c520e297f760b3b478bd5501 | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2025 Annual Report (MATERIAL_SMIC_2025_ANNUAL_REPORT_IFRS_HKEX) | 2026-04-08T23:59:59+08:00 | p.25 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_aae6d0ad0f6c2b629e39f643 | performance stability, operating efficiency and sustained profitability may be adversely affected. | — |
| FACT_d95fd4952f0a60e39d094340 | EVID_3154aa1a93149fb86a04d72c | REPORTED_FACT | T1 | UNKNOWN | HKEXnews / SMIC 2024 Annual Report (MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX) | 2025-04-09T23:59:59+08:00 | p.25 SECTION 4 MANAGEMENT DISCUSSION AND ANALYSIS CHUNK_ce6dbe8257c5ac3eacc1c89d | The Company enhances its overall profitability by optimizing product mix, improving utilization rate, and refining process | — |
| FACT_dae341852c47383bdd090a51 | EVID_f90533faff49aad01a87a752 | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | year to 93.5%. | — |
| FACT_df36c5999362a4da0f3b4a1f | EVID_2a7313c13e2e5c8906a767bf | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | 9.7 million wafers, and annualized capacity utilization rate increased by 8 percentage points year-over- | — |
| FACT_ec0c0f8bfd11c7cee85c0a87 | EVID_eb92a4da2d3d97b5b80eb6bf | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | revenue in 2025 increased by 16.2% year-over-year to $9,327 million, and gross margin increased by | — |
| FACT_fbc5576368ee9d4b071147b2 | EVID_937ccb9a137eb428b0ba681e | REPORTED_FACT | T1 | UNKNOWN | Semiconductor Manufacturing International Corporation / SMIC Reports Unaudited Results for the Three Months Ended December 31, 2025 (MATERIAL_SMIC_2025_Q4_RESULTS) | 2026-02-10T17:12:59+08:00 | p.2 SEMICONDUCTOR MANUFACTURING INTERNATIONAL CORPORATION CHUNK_ada0367884505128f1bfbbc7 | expenditure is expected to be roughly flat compared to that of 2025. | — |

## 七、D1–D7 发现和证据分向量

| dimension_id | finding | evidence_score | evidence_score_label | support_count | numeric_support_count | independent_source_groups | bearing_cross_period_metrics | finding_reason_code |
|---|---|---|---|---|---|---|---|---|
| D1_PROFITABILITY_CHANGE | MIXED | 3 | STRONG | 8 | 4 | 4 | GROSS_MARGIN | MODEL_JUDGMENT |
| D2_UTILIZATION_EFFECT | MIXED | 2 | ADEQUATE | 8 | 1 | 5 | — | MODEL_JUDGMENT |
| D3_MIX_EFFECT | MIXED | 2 | ADEQUATE | 4 | 1 | 2 | — | MODEL_JUDGMENT |
| D4_CAPEX_CONVERSION | MIXED | 3 | STRONG | 8 | 4 | 5 | CAPITAL_EXPENDITURE_INCURRED | MODEL_JUDGMENT |
| D5_CYCLE_EXPLANATION | UNKNOWN | 2 | ADEQUATE | 8 | 0 | 3 | — | MODEL_JUDGMENT |
| D6_NONCORE_EXPLANATION | MIXED | 3 | STRONG | 8 | 4 | 4 | GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | MODEL_JUDGMENT |
| D7_SUSTAINABILITY_EVIDENCE | UNKNOWN | 2 | ADEQUATE | 8 | 0 | 3 | — | MODEL_JUDGMENT |

证据分表示证据强度，不表示公司质量，也不表示投资吸引力；总分固定为不适用。

**跨维度重复承重**

| fact_id | dimensions | evidence_id |
|---|---|---|
| FACT_d95fd4952f0a60e39d094340 | D2_UTILIZATION_EFFECT | EVID_3154aa1a93149fb86a04d72c |
| FACT_d95fd4952f0a60e39d094340 | D7_SUSTAINABILITY_EVIDENCE | EVID_3154aa1a93149fb86a04d72c |

产品组合部分可在结构维度承重，工艺制程部分可在可持续性维度承重；本维度只援引其中的利用率一项作为机制存在性的文本依据，不构成重复计分。

与上一条同源但属不同年度文件，在本维度的作用是「跨期一致性检验」而非再次证明机制有效；其他维度若引用，引用的是机制内容本身， 两者用途不同，不构成重复计量。

## 八、反方质询与修订

| challenge_id | round | category | target_kind | target_id | disposition | review_count | blocking_triggers |
|---|---|---|---|---|---|---|---|
| CH_001 | 1 | SOURCE_TRACEABILITY | FINDING | D1_PROFITABILITY_CHANGE | RESOLVED_NO_CHANGE | 1 | — |
| CH_002 | 1 | SOURCE_TRACEABILITY | FINDING | D2_UTILIZATION_EFFECT | RESOLVED_WITH_REVISION | 1 | — |
| CH_003 | 1 | ATTRIBUTION_CAUSALITY | FINDING | D3_MIX_EFFECT | RESOLVED_WITH_REVISION | 1 | — |
| CH_004 | 1 | ACCOUNTING_COMPARABILITY | EVIDENCE | EVID_28c333bb3006b183a5e34b57 | RESOLVED_NO_CHANGE | 1 | — |
| CH_005 | 2 | FALSIFICATION_MISSING_EVIDENCE | FINDING | D7_SUSTAINABILITY_EVIDENCE | UNRESOLVED_DOWNGRADED | 1 | — |

| 项 | 值 |
|---|---|
| max_rounds | 2 |
| rounds_used | 1, 2 |
| challenge_run_status | WARN |

**质询导致的方向变化**

| dimension_id | finding_before | finding_after | evidence_score_after | revised_from_challenge_ids |
|---|---|---|---|---|
| D2_UTILIZATION_EFFECT | SUPPORTED | MIXED | 2 | CH_002 |
| D7_SUSTAINABILITY_EVIDENCE | MIXED | UNKNOWN | 2 | CH_005 |

- `CH_001` → RESOLVED_NO_CHANGE
具体数值及其期间、口径和来源见本维度证据表。

季度公告是另一次独立披露。具体数值及其期间、口径和来源见本维度证据表。

- `CH_002` → RESOLVED_WITH_REVISION
本维度方向为 SUPPORTED，但支撑证据同时来自 CAS 口径年报与 IFRS 口径年报。两者是否为同一次原始披露的两种呈报，即伪多源？

一次定向复核确认两条表述指向同一年度同一次原始披露，互相印证不构成独立来源；且本维度承重指标白名单为空，无任何数值证据可独立支撑方向。方向由 SUPPORTED 下调为 MIXED，并在限制中写明伪多源。

- `CH_003` → RESOLVED_WITH_REVISION
本维度把公司「due to the product mix change」等原因说明列为 PRIMARY_SUPPORT。在没有独立证据的情况下，这是否把公司自身的归因升级为已验证的原因？

一次定向复核确认这四条记录均为公司在同一次披露中给出的原因说明，证据集内没有独立佐证。具体数值及其期间、口径和来源见本维度证据表。

- `CH_004` → RESOLVED_NO_CHANGE
具体数值及其期间、口径和来源见本维度证据表。

具体数值及其期间、口径和来源见本维度证据表。

- `CH_005` → UNRESOLVED_DOWNGRADED
在没有现金流或单位成本证据的情况下，MIXED 的方向能否成立？具体数值及其期间、口径和来源见本维度证据表。

两轮内无法在候选集内取得可承重证据，按固定阶梯降级。具体数值及其期间、口径和来源见本维度证据表。

## 九、冲突、UNKNOWN、TBD、隔离项和数据限制

| 项 | 值 |
|---|---|
| quarantined_count | 0 |
| detected_conflict_group_count | 0 |
| unresolved_conflict_group_count | 0 |

本次运行没有任何被隔离的证据，也没有检出冲突组。这是 Snapshot v3 的真实承载力，不是机制缺席：隔离与冲突降级的机制由测试中的合成 fixtures 覆盖，此处如实记录零值。

**gap 聚合（origin_stage × gap_kind）**

| origin_stage | gap_kind | 条数 |
|---|---|---|
| acquire-research-materials | MATERIAL_UNAVAILABLE | 2 |
| acquire-research-materials | SEARCH_NOT_FOUND | 1 |
| analyze-and-score-research-findings | NO_BEARING_METRIC | 3 |
| challenge-research-findings | CHALLENGE_UNRESOLVED | 1 |
| generate-research-report | SENSITIVITY_NOT_GENERATED | 1 |
| govern-and-validate-research-evidence | EVIDENCE_METRIC_ID_MISSING | 1 |
| govern-and-validate-research-evidence | UPSTREAM_DEFECT | 1 |
| normalize-research-facts | NORMALIZATION_UNKNOWN | 4912 |

| priority | 条数 |
|---|---|
| P1 | 4915 |
| P2 | 7 |

本报告不按 gap 优先级筛选。实测绝大多数 gap 都是 P1，优先级在本仓库已失去区分度； 按 P1 筛等于不筛，只会给出一种做过分级的错觉。逐档计数见上表，由本次运行的 gaps.yaml 直接汇总。

该类 gap 是规整阶段对缺失字段的机械登记，逐条展开没有信息量，此处只给聚合计数与口径说明。

**逐条展开的 gap**（聚合类别之外的全部条目）

| gap_id | origin_stage | gap_kind | priority | status | impact_objects |
|---|---|---|---|---|---|
| GAP_ACQUIRE_001 | acquire-research-materials | MATERIAL_UNAVAILABLE | P1 | OPEN | quarterly_materials_2025_q2, quarterly_materials_2025_q3, quarterly_materials_2025_q4, quarterly_materials_2026_q1 |
| GAP_ACQUIRE_002 | acquire-research-materials | SEARCH_NOT_FOUND | P1 | OPEN | average_selling_price, process_application_mix |
| GAP_ACQUIRE_003 | acquire-research-materials | MATERIAL_UNAVAILABLE | P2 | OPEN | quarterly_materials_2025_q4 |
| GAP_ANALYSIS_NO_BEARING_METRIC_D2_UTILIZATION_EFFECT | analyze-and-score-research-findings | NO_BEARING_METRIC | P2 | OPEN | D2_UTILIZATION_EFFECT |
| GAP_ANALYSIS_NO_BEARING_METRIC_D5_CYCLE_EXPLANATION | analyze-and-score-research-findings | NO_BEARING_METRIC | P2 | OPEN | D5_CYCLE_EXPLANATION |
| GAP_ANALYSIS_NO_BEARING_METRIC_D7_SUSTAINABILITY_EVIDENCE | analyze-and-score-research-findings | NO_BEARING_METRIC | P2 | OPEN | D7_SUSTAINABILITY_EVIDENCE |
| GAP_CHALLENGE_UNRESOLVED_DOWNGRADED_CH_005 | challenge-research-findings | CHALLENGE_UNRESOLVED | P2 | OPEN | D7_SUSTAINABILITY_EVIDENCE |
| GAP_EVIDENCE_9aea1f6de4cfa1ee | govern-and-validate-research-evidence | EVIDENCE_METRIC_ID_MISSING | P2 | OPEN | metric_conflict_detection |
| GAP_EVIDENCE_UPSTREAM_PERIOD_MISLABEL | govern-and-validate-research-evidence | UPSTREAM_DEFECT | P1 | OPEN | normalize-research-facts, conflict_candidate_pool |
| GAP_REPORT_GOVERNMENT_FUNDING_SENSITIVITY_ABSENT | generate-research-report | SENSITIVITY_NOT_GENERATED | P2 | OPEN | D6_NONCORE_EXPLANATION, SENSITIVITY_EX_GOVERNMENT_FUNDING |

### 数据限制

#### 已知抽取语义错误（DEMO-KNOWN-ISSUES A1）

规整阶段存在数值抽取语义错误：抽样发现以「个百分点」表述的比率变化被抽成金额型折旧 记录，且该记录 normalization_status=PASS，因而在治理阶段获得 T1 / REPORTED_FACT / USABLE 并可承重。下表是本次运行按同一启发式条件（金额单位且原文含「个百分点」） 重新粗筛的规模，未经人工逐条核对，只作量级参考。本报告的证据表会忠实渲染其中一部分 错抽记录，它们在表中看起来与正确记录无异。Ticket 06 不修复该缺陷（Ticket 03 已冻结）， 只披露。

| 启发式筛查项 | 值 |
|---|---|
| 数值事实总数 | 4575 |
| 金额单位且原文含「个百分点」的记录数 | 179 |

#### D3 唯一承重数值的期间标注缺陷

D3 的唯一承重数值（来源披露平均销售单价）在链路上被标注为财政年度期间，但其来源材料是 半年度报告，即 Ticket 04 登记的 GAP_EVIDENCE_UPSTREAM_PERIOD_MISLABEL。D3 的整个数值 骨架架在这一条记录上。证据表按原样展示该标注并附带其 gap 标记，不改写为看起来正确的 期间。受影响记录见下表。

| evidence_id | metric_id | period | gap_ids |
|---|---|---|---|
| EVID_15431f7b706e456e0fd4ee74 | ASP_SOURCE_REPORTED | FISCAL_YEAR 2025-01-01~2025-12-31 | — |

#### 跨维承重重叠只做全局校验

overlap_note 只能在全部七个维度形成之后做全局校验，进不了逐维度的重生成闸——单维度的 模型判断看不见其他维度选了什么。因此交叉承重的标注是事后核对结果，不是生成期约束。

#### 冻结重放的覆盖边界

本次运行的执行模式是 FROZEN_REPLAY：模型判断产物作为冻结判断输入参与，运行期间不发生 任何模型调用。因此端到端可重跑证明的对象是「从冻结输入到最终产物的确定性重放」，判断层 本身没有在本次运行中被执行。判断层的保证来自 analysis-validation.yaml 的逐项校验与 analysis-attempts.jsonl 的全过程留痕（ADR 0004、ADR 0005）。

## 十、来源、公式、会计口径和溯源附录

### 调节桥接公式与复算

| target_fact_id | rule_id | direction | formula | input_fact_ids | recomputed（链路记录） | recomputed（本报告复算） | source_reported | difference | tolerance | status | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FACT_38c282d11ae39c6e7e3412c0 | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_60242c90758532122b6437d9, FACT_ecaacbdd34d5b0e31c72aebb, FACT_38c282d11ae39c6e7e3412c0 | 2308776000 | 2308776000 | 2308776000 | 0 | 1500.0 | PASS | EXACT_RECONCILIATION |
| FACT_4785b18a79d4f6d34363d025 | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_30001a3b853ed2f76320d428, FACT_c67f5dfd6261b8c244ed7335, FACT_4785b18a79d4f6d34363d025 | 2308776000 | 2308776000 | 2308776000 | 0 | 1500.0 | PASS | EXACT_RECONCILIATION |
| FACT_573f37457844808ac6cf460e | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_0bb7d1ae5a198ee7b7c54366, FACT_f38973e1a4354a7f977bcf28, FACT_573f37457844808ac6cf460e | — | 6346303000 | 6346303000 | — | — | UNKNOWN | COMPARABILITY_MISMATCH |
| FACT_857121d6745122841bdbf89b | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_114d9918fd74ebc063fd6fa8, FACT_a82c43d2e77d03169694c548, FACT_857121d6745122841bdbf89b | 3517877000 | 3517877000 | 3517877000 | 0 | 1500.0 | PASS | EXACT_RECONCILIATION |
| FACT_ad4c9aaee78b68ae4049db16 | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_e91ab61505984c82cbbaf2b0, FACT_bd8e59eb3955bac9950d4cf2, FACT_ad4c9aaee78b68ae4049db16 | — | 4904841000 | 4904841000 | — | — | UNKNOWN | COMPARABILITY_MISMATCH |
| FACT_f5fbdc2c4d3e03f083bd5c97 | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_032ea63b8230e74f6b50013d, FACT_9ae38e094027b6bf1dce3b44, FACT_f5fbdc2c4d3e03f083bd5c97 | 1371656000 | 1371656000 | 1371656000 | 0 | 1500.0 | PASS | EXACT_RECONCILIATION |
| FACT_fbecdcd8a0dae3f6ce254b52 | RECONCILE_CAS_TO_IFRS_V1 | CAS_TO_IFRS | IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL) | FACT_3cb0c9c6f6c40de59e687789, FACT_17ce3bd436951528d4e2014b, FACT_fbecdcd8a0dae3f6ce254b52 | — | 4904841000 | 4904841000 | — | — | UNKNOWN | COMPARABILITY_MISMATCH |

本 Demo 的规整链路上没有任何 DERIVATION 记录，因此这里展示的不是派生值，而是调节桥接的复算核验：每条都给出公式、输入事实、复算值、披露值、差异与状态。状态为 UNKNOWN 的条目是输入口径不匹配或披露精度缺失，按规则不猜测容差。

### 溯源链

报告中每个数字都可沿 evidence_id → fact_id → chunk_id → material_id 逐级回查；上述四个标识符在证据表中原样出现，可直接检索本次运行目录内的权威文件。

### 术语与口径对照表

**metric_id**

| 取值 | 中文说明 |
|---|---|
| REVENUE | 收入 |
| WAFER_REVENUE | 晶圆收入 |
| COST_OF_SALES | 销售成本 |
| GROSS_PROFIT | 毛利 |
| GROSS_MARGIN | 毛利率 |
| PROFIT_FROM_OPERATIONS | 经营利润 |
| OPERATING_MARGIN | 经营利润率 |
| EBITDA | 息税折旧摊销前利润 |
| EBITDA_MARGIN | 息税折旧摊销前利润率 |
| PROFIT_ATTRIBUTABLE_TO_OWNERS | 归属于母公司股东的利润 |
| NET_CASH_FROM_OPERATING_ACTIVITIES | 经营活动产生的现金流量净额 |
| MONTHLY_CAPACITY_EIGHT_INCH_EQUIVALENT | 月产能（8 英寸等值） |
| PERIOD_END_CAPACITY | 期末产能 |
| CAPACITY_UTILIZATION_RATE_SOURCE_REPORTED | 来源披露的产能利用率 |
| WAFER_SHIPMENTS | 晶圆出货量 |
| ASP_SOURCE_REPORTED | 来源披露的平均销售单价 |
| CAPITAL_EXPENDITURE_INCURRED | 已发生资本开支 |
| CASH_PAID_FOR_PROPERTY_PLANT_EQUIPMENT | 购建固定资产支付的现金 |
| CAPITAL_COMMITMENTS_UNPAID | 已承诺未支付的资本承诺 |
| CAPITAL_EXPENDITURE_GUIDANCE | 管理层资本开支指引 |
| PROJECT_INVESTMENT_AMOUNT | 具体产能项目投资额 |
| GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL | 已计入损益的政府资金 |
| OTHER_OPERATING_INCOME | 其他经营收入 |
| DEPRECIATION_EXPENSE | 折旧费用 |
| RESEARCH_AND_DEVELOPMENT_EXPENSE | 研发费用 |
| GLOBAL_SEMICONDUCTOR_SALES | 全球半导体销售额 |
| APPLICATION_REVENUE_SHARE | 应用分类收入占比 |
| WAFER_SIZE_REVENUE_SHARE | 晶圆尺寸收入占比 |

**claim_type**

| 取值 | 中文说明 |
|---|---|
| REPORTED_FACT | 来源直接披露的事实 |
| DERIVED_METRIC | 由披露值派生的指标 |
| MANAGEMENT_ASSERTION | 管理层陈述（非前瞻） |
| MANAGEMENT_GUIDANCE | 管理层指引（前瞻） |
| THIRD_PARTY_VIEW | 第三方观点 |
| ANALYTIC_INFERENCE | 分析性推断（本 Demo 不产生） |
| UNASSESSED | 尚未判定（规整阶段的固定取值） |

**source_tier**

| 取值 | 中文说明 |
|---|---|
| T1 | 发行人法定披露或监管渠道 |
| T2 | 具名机构或行业协会 |
| T3 | 指定媒体或转载全文 |
| T4 | 自动摘要等最低可信层 |

**evidence_status**

| 取值 | 中文说明 |
|---|---|
| USABLE | 可引用且可承重 |
| RESTRICTED | 仅可引用，不可承重 |
| QUARANTINED | 已隔离，不得支撑任何发现 |

**permitted_use**

| 取值 | 中文说明 |
|---|---|
| CITE_AND_BEAR | 可引用并可作为承重证据 |
| CITE_ONLY | 只可引用 |
| NOT_USABLE | 不可使用 |

**audit_status**

| 取值 | 中文说明 |
|---|---|
| AUDITED | 已审计 |
| REVIEWED | 已审阅 |
| UNAUDITED | 未经审计 |
| OUTSIDE_AUDIT_SCOPE | 位于审计范围之外 |
| UNKNOWN | 无法确认审计覆盖范围 |

**period_type**

| 取值 | 中文说明 |
|---|---|
| FISCAL_YEAR | 财政年度 |
| SINGLE_QUARTER | 单一季度 |
| YEAR_TO_DATE | 年初至今累计 |
| TTM | 滚动十二个月 |
| CUSTOM_DURATION | 其他自定义期间 |
| INSTANT | 时点 |

**finding**

| 取值 | 中文说明 |
|---|---|
| SUPPORTED | 证据支持该命题 |
| MIXED | 证据方向不一致 |
| NOT_SUPPORTED | 证据不支持该命题 |
| UNKNOWN | 现有证据无法判断方向 |

**evidence_score**

| 取值 | 中文说明 |
|---|---|
| 0 | UNSCORABLE — 无承重证据 |
| 1 | LIMITED — 单一来源组、单一期间或单点数据 |
| 2 | ADEQUATE — 两个以上独立来源组，或可比的跨期数值 |
| 3 | STRONG — 承重指标上的可比跨期数值、两个以上独立来源组，且承重证据无未决冲突 |

**disposition**

| 取值 | 中文说明 |
|---|---|
| RESOLVED_NO_CHANGE | 复核后维持原发现 |
| RESOLVED_WITH_REVISION | 复核后修订发现 |
| UNRESOLVED_DOWNGRADED | 未解决，按固定阶梯降级 |
| BLOCKING | 未解决且命中固定阻断触发项 |

**reconciliation_status**

| 取值 | 中文说明 |
|---|---|
| PASS | 复算差异为零 |
| WARN | 差异在容差内（ROUNDING_DIFFERENCE） |
| FAIL | 差异超出容差（FORMULA_MISMATCH） |
| UNKNOWN | 输入口径不匹配或披露精度缺失，不猜测容差 |

**run_status**

| 取值 | 中文说明 |
|---|---|
| PASS | 该阶段全部硬条件达标 |
| WARN | 硬条件通过但存在未解决项 |
| FAIL | 存在硬条件失败 |

机器标识符与来源原文跨度一律原样保留、不翻译：翻译标识符会切断溯源，翻译来源原文等于制造一段没有出处的新文本。
