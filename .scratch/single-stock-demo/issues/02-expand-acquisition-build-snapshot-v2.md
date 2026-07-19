# 02 — 修订采集边界并构建 Snapshot v2

**What to build:** 在不改写 Snapshot v1 的前提下，把采集阶段改为“尽可能广泛获取、后续治理筛选”，并获取目标相关材料、冻结一个可独立复现的 Snapshot v2。该 ticket 同时修订 `acquire-research-materials` 及配套契约/脚本/测试，但不做上下文治理、事实规整、证据治理或分析。

**Blocked by:** 01 — Snapshot v1 已完成并作为不可变历史基线保留。

**Status:** done

- [x] Snapshot v1 `smic-4c110e93f810aa8e` 的身份、清单、状态和冻结文件哈希保持不变；v2 使用新的 `snapshot_id`，可记录 `parent_snapshot_id`，但完整列出并携带自身运行所需的全部材料，不依赖 v1。
- [x] 采集准入只要求：发布时间不晚于 `2026-05-15T23:59:59+08:00`；采集来源、展示发布主体（Displayed Publisher）、发布时间/窗口和 Material Locator 可记录；获得的字节可冻结并用内容哈希复现。进入 v2 的材料统一标记 `ACQUIRED_UNASSESSED`。
- [x] 已确认发布时间晚于 `as_of` 是唯一直接排除内容本身的业务条件。发布时间窗口最晚可能值不晚于 `as_of` 时可纳入，最早可能值晚于 `as_of` 时排除；窗口跨界、日期缺失或边界时区不明时进入 Candidate Holding Area。
- [x] Candidate Holding Area 位于所有 Snapshot 之外，保存高相关但缺少采集来源、展示发布主体、发布时间/窗口或 Material Locator 的候选；候选不获得 `material_id`，不进入 RAG/facts/analysis/report，只有补齐证据并经用户确认后才可进入新的快照。
- [x] “可获取”包括公开材料和用户通过自己的账号、权限或合法渠道手动提供的材料；实现不保存账号、密码、Cookie、Token，不自动登录、不处理验证码、不绕过访问控制。条款 URL、已知限制和 `usage_basis` best-effort 记录，不作为准入门槛，也不要求 `restriction_status=USABLE`。
- [x] 满足准入但当前解析器无法处理的材料仍以原始文件冻结，标记 `parse_status=UNSUPPORTED` 或 `PARTIAL` 并产生 Acquisition Gap；不执行 OCR、音频转写或图片/图表数值理解，也不为该材料生成 chunk、fact 或 evidence。
- [x] 完全相同内容哈希只保留一个材料记录和一份冻结文件；Canonical Material Locator 按“发行人 -> 监管/交易所 -> 具名机构 -> 其他稳定来源”选择，其他入口保存为 Alternate Material Locators。不同哈希版本均保留给后续治理。
- [x] 核心观察期为 FY2023 至 2026 Q1；更早材料只服务于期初基线、交易链、子公司/合并范围、会计政策/重述或必要行业周期基线。
- [x] v2 尽可能获取 2023、2024、2025 三套完整年度材料，每年至少含完整合并 IFRS 报告，并在可获得时另收 A 股 CAS 报告/披露；不得用 2025 年报中的多年摘要代替 2023、2024 完整年报。
- [x] v2 尽可能获取 2025 Q2、Q3、Q4 和 2026 Q1 的发行人业绩公告/结果、财务报表或详细附录、演示材料、已有文字稿/Q&A/纪要和相关交易所披露；不可获得的材料类型记录 Acquisition Gap，但不阻塞快照。
- [x] v2 还应处理公司/证券主数据；产能、利用率、出货、ASP、制程/应用结构、资本开支；政府补助、其他经营收入、IFRS/CAS 调节；晶圆代工、成熟制程和需求周期；中芯北方 49% 股权交易、NSI 交易、子公司/合并范围、会计政策/重述，以及其他直接关联 D1-D7 的材料。
- [x] 每份材料至少映射一个 Acquisition Target，映射只表示采集原因，不输出 `COVERED/PARTIAL` 或提前判断证据完整性。采集 gap 只包括搜索/材料不可获得、Candidate Holding 待确认和材料不可解析。
- [x] 搜索覆盖发行人、监管/交易所、政府/官方行业、具名机构/数据及扩展 Web/媒体/转载/访谈/论坛；目标清单已处理、官方与扩展轮次完成，且一轮补充搜索没有新增目标相关唯一材料后记录 Search Saturation。无材料数量上限，Saturation 不表示数据完整。
- [x] `DEMO_RUN` 不联网，只校验 v2 身份、内容哈希、`as_of` 和最低元数据，并接受 `ACQUIRED_UNASSESSED`；证据等级、内容类型、同源、冲突、隔离和分析资格均留给 Ticket 04，不回写快照。
- [x] fixtures/验收测试覆盖：v1 不变、匿名/转载/不可解析材料准入、晚于 `as_of` 排除、跨界/缺元数据候选暂存、缺条款信息不阻塞、完全重复内容折叠、Target 映射、Search Saturation 和无网络 `DEMO_RUN`。

## Comments

- 2026-07-19：本 ticket 由已确认的采集/证据边界修订新增；此次只完成需求拆票，尚未启动实现。
- 2026-07-19：已完成实现并冻结 Snapshot v2 `smic-95dcd12eba2fe17c`，父快照记录为 `smic-4c110e93f810aa8e`。v2 记录 18 份 `ACQUIRED_UNASSESSED` 材料、40 个清单文件、2 个 Snapshot 外 Candidate Holding 线索、6 个 Acquisition Gap，Search Saturation 状态为 `SATURATED`。
- 2026-07-19：`DEMO_RUN` 已验证 v2 可离线运行；Snapshot v1 manifest 所列 16 个文件哈希复核 0 个不匹配。
- 2026-07-19：CLI 验收测试扩展到 20 个用例，覆盖 v2 采集边界、候选暂存、重复哈希折叠、Search Saturation、最低元数据校验、不可解析/不可 OCR 行为和离线 `DEMO_RUN`。
