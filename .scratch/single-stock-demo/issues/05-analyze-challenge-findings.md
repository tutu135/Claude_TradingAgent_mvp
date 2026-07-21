# 05 — 形成并质询 D1–D7 发现

**What to build:** 让用户可以基于治理证据得到围绕主研究问题的七维结构化发现，并让这些发现接受来源、会计、归因和证伪四类反方质询。该 ticket 完成 `analyze-and-score-research-findings` 与 `challenge-research-findings`，但不输出投资建议。

**Blocked by:** 04 — 治理并核验证据。

**Status:** ready-for-agent

- [ ] D1–D7 每个维度输出合法的 `finding`、`evidence_score`、支持证据、反证、替代解释、限制和 gap；证据分 0 必须对应 UNKNOWN。
- [ ] 证据分只表示当前发现的证据强度，高分可以对应 `NOT_SUPPORTED`；不生成加权总分、星级、投资评级，汇总固定为 `overall_score: NOT_APPLICABLE`。
- [ ] 发现只能引用状态允许且未隔离的 `evidence_id`；管理层解释在没有独立证据时仍是 `MANAGEMENT_ASSERTION`，相关性不会被自动表述为因果，也不会静默重复归因。
- [ ] D7 列出可追溯的后续观察指标和明确判定逻辑；只有冻结数据、确认规则或可复算公式支持时才给数值阈值，否则为 UNKNOWN/TBD。
- [ ] 质询覆盖来源与溯源、会计与可比性、归因与因果、证伪与缺证四类，并明确指向 `finding_id` 或 `evidence_id`，不进行泛化的看多/看空辩论。
- [ ] 质询只能使用当前冻结快照和 `as_of` 之前材料；每个问题只有一次定向复核，全流程最多两轮，质询不能直接修改发现。
- [ ] 每项质询使用四种允许处置之一，保留修订前后与理由；两轮后未解决的问题被降级、标记 BLOCKING 或写入 gap，不无限循环。
- [ ] 分析和质询输出不包含买入/卖出/持有、仓位、目标价、估值锚、投资吸引力判断或系统预测，并有正反 fixtures 验证边界。

## Comments

### 冻结规划（2026-07-22 grilling，逐项用户确认）

架构决定见 `docs/adr/0004-layer-analysis-into-deterministic-selection-and-bounded-model-judgment.md`。新术语 `分析候选集`、`承重指标白名单` 已入 `CONTEXT.md`。D1–D7 的维度定义、汇总向量、四类质询、四种处置沿用 spec FR-050/051/052/060/061/072/073，本次不改。

#### 事实基线（来自 `tmp/ticket04-final`，实测）

- 可承重（`USABLE`）数值观察仅 **275** 条；4,300 条数值因 `NORMALIZATION_PARTIAL` 为 `RESTRICTED`。`USABLE` 文本命题 14,927 条，是页级原文而非筛过的命题。
- 按 03 `retrieval_hits.query_family_id` 分维的 `USABLE` 数值/文本：D1 74/2339、D2 10/1231、D3 60/1874、D4 42/1814、D5 **0**/1846、D6 58/2220、D7 18/2605。
- D2 的 10 条数值是 `CAPITAL_EXPENDITURE_INCURRED×8 + REVENUE×1 + PROFIT_FROM_OPERATIONS×1`，**无利用率指标**；D5 无任何可承重数值。
- chunk 文本长度 min 7 / p50 785 / p90 2881 / max 8047 字符；单 chunk CJK 占比最高 0.913。

#### 1. 三层结构（ADR 0004）

选取层（脚本，确定性可哈希）→ 判断层（模型，单维单次调用）→ 校验与派生层（脚本）。模型不产出分数、不产出任何聚合、不接触候选集之外的证据。

#### 2. 候选集选取规则（冻结）

```
每维文本：budget = 60,000 chars, max_selected_chunks = 64, overshoot = 110%
  1. 播种：min(3, available_source_group_count) 个 source_group，各取其最高分 chunk
  2. 填充：其余 chunk 按 (score desc, chunk_id asc)；
     加入后 ≤ budget*1.10 则加入并停止，否则直接停止；达 max_selected_chunks 停止
  3. 选中 chunk 内全部 USABLE TEXT_PROPOSITION 一并进入
每维数值：该维全部 USABLE NUMERIC_OBSERVATION，不占预算，按 fact_id 去重
```

- **选取单位是 chunk 不是命题**：检索分挂在 chunk 上，同 chunk 内几十条命题共享分数，纯 top-N 命题会坍缩——实测 D1/D2/D5 的 top-40 命题全部落在**同 1 个 chunk、1 个 source_group**（全集有 11–12 个组）。
- **不做 token 门禁**：60,000 字符在最坏 CJK 比例下上界约 60k tokens（含数值证据），对 200k 窗口有 3 倍余量。引 tokenizer 近似或调 `count_tokens` 都会破坏离线确定性，属为已被兜住的边界加依赖。
- **达预算时停止，不跳过高分长 chunk 去捡低分短 chunk**（保持"按相关性取前 N"语义）。
- 单文件 `analysis-inputs.jsonl`，首条 `SELECTION_SUMMARY` 记 `candidate_chunks / selected_chunks / selected_chars / source_group_count / min_selected_score / skipped_due_budget[]`。不另开审计文件——该文件不是 prompt，prompt 由脚本从中拼装。
- gap 只在三种情况记：`source_group_count < min(3, available)`、该维 0 条文本、或数值与文本皆空。逐条截断不记 gap。

#### 3. `evidence_score` 由脚本反算（模型不给分）

```
0  无可承重证据
1  单一来源、单一期间或单点证据
2  多来源一致支持，或存在可比较的跨期数值
3  跨期可比较数值 + ≥2 独立 source_group + 无 CONFLICT_UNRESOLVED
   + 该数值 metric_id 属于该维承重指标白名单
```

- **单向绑定**：`score==0` 必须 `UNKNOWN`；但 `UNKNOWN` 可以是 0–2 分（证据冲突、方向不明也会 UNKNOWN）。双向绑定比 spec FR-051 更严，是自造约束，不采用。
- 「有一条数值就得 2 分」不成立——单条数值可能单来源单期间且与该维问题无关。
- **承重指标白名单（已确认，冻结）**

  入表规则（唯一，描述性而非规范性）：**某指标进入某维白名单，当且仅当 ① 它是该维正当的承重指标，且 ② 它在该维候选集中至少有 1 条 `USABLE` 记录。** 不列举全快照零记录的指标名——那是为假设输入建结构。

  ```
  D1: GROSS_MARGIN, GROSS_PROFIT, PROFIT_FROM_OPERATIONS,
      PROFIT_ATTRIBUTABLE_TO_OWNERS, REVENUE, COST_OF_SALES
  D2: ∅
  D3: ASP_SOURCE_REPORTED
  D4: CAPITAL_EXPENDITURE_INCURRED, DEPRECIATION_EXPENSE
  D5: ∅
  D6: GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL, OTHER_OPERATING_INCOME
  D7: ∅
  ```

  - **不设"背景指标"第二份清单**：不在白名单里即为背景/限制说明，靠省略表达，不重复维护两处。
  - D2 空：该维 10 条可承重数值是 `CAPITAL_EXPENDITURE_INCURRED×8 + REVENUE×1 + PROFIT_FROM_OPERATIONS×1`，无任何利用率/产能指标。
  - D5 空：该维 0 条可承重数值。
  - D7 空：唯一正当的承重指标 `NET_CASH_FROM_OPERATING_ACTIVITIES` 的 6 条 `USABLE` 记录全部落在 `RQ_MAIN`/`D1`/`D3` 族，**无一进入 D7 候选集**；该维现有的 18 条数值（REVENUE/COST_OF_SALES/GROSS_PROFIT/GROSS_MARGIN）是结果指标，用它们证明可持续性属循环论证，不入表。记缺口：**OCF 记录存在但未被 D7 固定查询族命中**（03 查询族已冻结，05 不改）。
  - 后果如实披露：七维中 D2/D5/D7 数值承重为空，D3 仅 1 条（按评分规则最多 1 分）。这是 v3 的真实承载力，由 `SELECTION_SUMMARY` 明示，不做补救。

#### 4. 无总分 / 无投资建议（FR-073）

- **结构闸**：输出 schema `additionalProperties: false`，不存在推荐/估值/综合评级字段；`overall_score` 是脚本写入的常量 `NOT_APPLICABLE`，不来自模型；跨维算术在 schema 里无处落地。
- **高精度词表闸**：只禁明确的投资动作与判断——买入/卖出/持有/增持/减持/目标价/仓位/低估/高估/估值具吸引力/投资价值 + 英文对应。**不禁**「建议、预计、有望、估值」等普通词（"管理层预计扩产"是合法表达，宽词表会大量误报）。前瞻内容只能进 `management_assertions` 并具名引证。
- 正反 fixtures 各一：合法发现 PASS；塞入投资动作语言的应 FAIL 并指出命中词。

#### 5. 相关 / 因果 / 重复归因

- **系统不自主生成因果结论**。只允许两类表述：非因果关联（「同时变化」「伴随」「与……一致」）；明确来源归因（「公司称……主要由于……」），后者归入 `management_assertions` 并带 `evidence_id`。
- 未归因的因果词（导致/推动/带动/因此 + drove/led to）**直接 FAIL**，不降级为 MIXED。（"有数值证据才准说因果"已否决：数字只证明相关，不证明因果。）
- `claim_type == MANAGEMENT_ASSERTION` 的证据不得进 `supporting_evidence`，只能进 `management_assertions`；违反即 FAIL。
- **重复归因**：仅当同一 `fact_id` 在多个维度都作为 `PRIMARY_SUPPORT` 时，才强制填 `overlap_note`；缺 note 即 FAIL。背景/限制类引用不作要求（否则产出大量模板文字）。脚本输出 `cross_attribution` 交叉表，不判断是否真的重复计算，只强制显式说明。

#### 6. 质询回路

- 模型按四类出问题，对象必须是已存在的 `finding_id`/`evidence_id`（脚本校验存在性）；回路控制全在脚本：`round ∈ {1,2}`、`review_count ≤ 1`、`disposition` 取 spec FR-061 的四值。
- 修订另存 `findings-revised.yaml`，保留原始 `findings.yaml`，记录被哪些 `challenge_id` 触发；`RESOLVED_WITH_REVISION` 必带 `finding_before/finding_after/reason`，修订后重跑全部校验。
- **不加 `severity` 字段**——`BLOCKING` 已是 FR-061 的处置之一，再加一条重叠语义的轴需要额外消歧规则。改为固定 BLOCKING 触发清单：两轮未决时命中「引用候选集外证据 / 引用非 USABLE 证据 / 命中投资建议词表 / 涉及 `CONFLICT_UNRESOLVED` / 修订后该维无任何承重证据」任一条 → 强制 `BLOCKING`；否则 `UNRESOLVED_DOWNGRADED`。两者都追加 gap。

#### 7. D7 阈值

- `watch_indicators` 每条须有 `indicator / judgment_logic / threshold / threshold_basis`。
- 数字阈值只允许两种依据：来源直接披露的阈值，或 04 已冻结的可复算公式。**仅引用一个含数字的 `evidence_id` 不构成依据**。
- 模型给出无依据数字时不静默删除：保留 `proposed_threshold`，正式 `threshold` 改 `UNKNOWN`，记 `REJECTED_NO_BASIS` + gap。
- 预期真实结果：绝大多数阈值为 `UNKNOWN`（D7 仅 18 条可承重数值，且均为结果指标）。不为让 D7 看起来完整而人为设阈值。

#### 8. 校验失败处置（有界，不死循环）

```
1. 仅重生成失败维度（输入 = 该维冻结候选集切片），最多 1 次
2. 两次输出与两次校验错误全部写入 analysis-attempts.jsonl
3. 仍 FAIL → finding=UNKNOWN, evidence_score=0,
   finding_reason_code=ANALYSIS_VALIDATION_FAILED,
   GAP_ANALYSIS_VALIDATION_FAILED, generation_attempts=2
4. analysis_run_status = FAIL（沿用 03/04 的 FAIL > WARN > PASS）
5. 报告照常生成（FR-072），沿用固定 distribution_status=INTERNAL_DEMO_ONLY
```

- 不重跑全部七维，避免已通过维度无关漂移。
- `finding_reason_code` 区分 `NO_BEARING_EVIDENCE`（真无证据）与 `ANALYSIS_VALIDATION_FAILED`（被强制归零），防止下游误读。
- **不新增 `publishable` / `report_status` 字段**：本 Demo 恒不可发布，FR-072 的固定 `distribution_status` 已表达；把恒定值做成字段会暗示它可能变。

#### 9. 产物清单

`analysis-inputs.jsonl`（含 SELECTION_SUMMARY）、`findings.yaml`、`analysis-attempts.jsonl`、`analysis-validation.yaml`、`challenges.yaml`、`findings-revised.yaml`、追加的 `gaps.yaml`。

#### 实现前待办

无。规划已逐项确认冻结，含承重指标白名单。实现时把白名单写入规则文件（与 04 同样放在冻结规则文件里，绑定 `snapshot_id`，不新建规则解释器）。
