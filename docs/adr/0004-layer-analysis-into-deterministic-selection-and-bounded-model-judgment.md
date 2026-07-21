---
status: accepted
date: 2026-07-22
decision-makers: user
---

# 分析阶段分层：确定性选取 + 受限模型判断，重建保证从哈希移到校验

Ticket 01–04 的每个阶段都是确定性脚本，验收方式是两次干净重建产出相同哈希。Ticket 05 沿用不了这套：把段落原文判定为"支持 D2 利用率命题"必然是语义判断，没有规则能替代。因此 05 拆成三层——**确定性选取 → 受限模型判断 → 确定性校验与派生**——并明确接受"分析产物不是位级可重建的"，把可信度保证从"哈希一致"移到"校验通过 + 全过程留痕"。

这个决定的直接依据是 04 产物的真实分布。20,114 条治理证据中可承重（`USABLE`）的数值观察只有 **275** 条，另有 4,300 条数值因 `NORMALIZATION_PARTIAL`（缺 `metric_id`）被压成 `RESTRICTED`；`USABLE` 文本命题有 14,927 条，但它们是带定位的页级原文，不是被筛过的命题。按 03 的 `retrieval_hits.query_family_id` 归到七维后，各维可承重数值为 D1 74、D2 10、D3 60、D4 42、D5 **0**、D6 58、D7 18，文本则各有 1,231–2,605 条。也就是说：D1/D4/D6 有真实的数值骨架，D2/D3/D5 的结论只能建立在原文语义上，而各维文本量远超单次可读范围。全确定性会让 D2–D7 几乎全部落 `UNKNOWN`，全模型则同时丢掉可审计性和"无投资建议"的机械保证。

被否决的替代方案有两个。**全确定性规则**产出诚实但空洞：七维里五维恒为 `UNKNOWN`，质询回路没有可质询对象，FR-050/FR-060 的机制无法真实跑通。**全模型驱动**（Skill 指令直接读证据写发现）能填满七维，但产物不可重建、不可审计，且没有任何机制阻止它引用候选集外证据或写出估值语言——而 FR-073 的禁止输出是硬要求，不能靠自觉。

分层后各层职责固定。**选取层**（脚本）按冻结规则从 `USABLE` 集合中为每维产出 `analysis-inputs.jsonl`，完全确定性、哈希可复现；模型看不到候选集之外的任何证据。**判断层**（模型，单维单次调用）只输出方向、证据 ID 列表与限制文字，不产出分数、不产出聚合、不接触别的维度。**校验与派生层**（脚本）反算 `evidence_score`、写入常量 `overall_score=NOT_APPLICABLE`、执行引用合法性与禁止输出检查——分数和聚合字段永远不来自模型。

关键推论是 `query_family_id` 的语义边界：**它只表示某条证据被该维查询命中，不表示它天然适合为该维承重或评分。** 一条证据要进入最终评分，必须同时满足属于冻结候选集、`evidence_status=USABLE`、被模型显式选中、角色合法，且数值证据的 `metric_id` 属于该维的承重指标白名单。实测证明这条不是空话：D2 的 10 条可承重数值是 `CAPITAL_EXPENDITURE_INCURRED×8 + REVENUE×1 + PROFIT_FROM_OPERATIONS×1`，没有一条是利用率；若只按"该维有数值"给分，D2 会靠资本开支数字拿到虚高的证据分。

代价明确并如实披露。两次运行的 `findings.yaml` 可能不逐字相同，因此模型输出被**冻结成文件当作输入**，而不是每次重生成；重建保证由 `analysis-validation.yaml` 提供——引用合法性、候选集封闭性、分数与状态绑定、禁止输出词表、因果表述归因、跨维重复承重说明，逐项 PASS/WARN/FAIL 带原因。校验失败的处置有界：**仅重生成失败维度，最多一次**，两次输出与两次校验错误全部留在 `analysis-attempts.jsonl`；仍失败则该维强制 `finding=UNKNOWN`、`evidence_score=0`、`finding_reason_code=ANALYSIS_VALIDATION_FAILED` 并记 `GAP_ANALYSIS_VALIDATION_FAILED`，`analysis_run_status=FAIL`。报告按 FR-072 照常生成，沿用固定 `distribution_status=INTERNAL_DEMO_ONLY`，不新增 `publishable` 或 `report_status` 字段——本 Demo 恒不可发布，把恒定值做成字段会暗示它可能变。
