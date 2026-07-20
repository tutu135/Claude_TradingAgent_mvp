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
