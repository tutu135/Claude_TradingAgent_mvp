# 06 — 编排黄金案例并生成内部报告

**What to build:** 让用户可以对冻结的中芯国际黄金案例启动一次固定流程，依次完成八个 Skills，得到每个数字均可追溯、经过质询且明确展示治理限制的 Markdown 内部报告。该 ticket 完成 `single-stock-research-orchestrator`、`generate-research-report` 和端到端验收。

**Blocked by:** 05 — 形成并质询 D1–D7 发现。

**Status:** ready-for-agent

- [ ] 编排器按固定七阶段顺序调用八个 Skills，只负责输入检查、阶段结果、停止/降级和最多两轮质询回路；阶段 Skill 不直接互调。
- [ ] 编排器使用至少 3 个应触发问题和 3 个不应触发问题验证范围识别，不引入通用 DAG、队列、调度器、数据库、模型路由或插件系统。
- [ ] 报告按确认的十个章节输出，清楚分开研究问题、分析框架和流程状态；D1–D7、质询修订、冲突、UNKNOWN/TBD、隔离和数据限制均可见。
- [ ] 报告中的每个数字均显示或可直接追溯来源、发布时间、报告期间/时点、单位、币种、缩放、口径和 `evidence_id`；派生值还展示公式与输入。
- [ ] 固定 `distribution_status=INTERNAL_DEMO_ONLY`，独立显示 `governance_status=PASS/WARN/FAIL` 和 `PENDING_HUMAN_REVIEW`；即使 FAIL 也生成显著标警的内部诊断报告，隔离数据不支撑发现。
- [ ] 报告不生成 PDF、网页、Dashboard、API 或外部分发物，也不包含交易指令、仓位建议、目标价锚、投资吸引力判断和系统预测。
- [ ] 端到端运行证明 `DEMO_RUN` 不实时联网、拒绝 `as_of` 越界材料，任一报告数字可沿 `evidence_id -> fact_id -> chunk_id -> material_id` 回溯，派生公式可复算，同源转载不会增加独立证据。
- [ ] 端到端运行证明冲突会被隔离并使发现降级，缺数产生 UNKNOWN/gap，政府补助保持双口径，D1–D7 状态合法，质询不超过两轮，FAIL 仍有诊断报告且没有禁止输出。
- [ ] 最终产物清单记录 `snapshot_id`、规则版本、权威文件哈希、生成时间、治理/分发/人工复核状态；固定案例文件完整且 CSV 如存在只作为派生视图。
- [ ] 实现只包含确认的八个 Skills、集中脚本、单一规则来源和固定案例文件；每个组件都能对应 Spec 验收条件，没有为未来产品预建基础设施。

## Comments
