# 项目导览

**给谁看**：需要快速建立项目整体认知的人，或新开窗口的 agent。

**这份文件的定位**：导航图 + 当前状态 + 已知问题。它**不复制**权威文档的内容，只告诉你去哪读。权威定义永远以 `CONTEXT.md`、`.scratch/single-stock-demo/spec.md`、`contracts/contract-map.md`、`rules/*.yaml` 为准；本文件与它们冲突时，以它们为准。

---

## 1. 项目在做什么

用一份**冻结**的中芯国际（`688981.SH`）真实公开资料，跑通一条完整的投研分析流水线，验证「每个数字都能追溯回原文出处」这件事在工程上能不能成立。

主研究问题（冻结）：

> 截至 `as_of`，中芯国际的经常性经营盈利能力发生了哪些可验证的变化，现有证据在多大程度上支持其已进入可持续改善阶段？

问题开放，允许得出支持 / 部分支持 / 反驳 / 证据不足任一结果。

**成功标准不是预测准确率，而是报告准确、全面、可核验。**

### 明确不做的事

- 不是产品，是个人 / 非商业 / 本地 / 不可对外发布的一次性 Demo
- 不输出买卖建议、目标价、估值锚、仓位建议、投资评级、系统预测
- 不做 OCR、音频转写、图表读数 —— 读不出来就记 gap
- 不建通用架构：无 DAG、队列、调度器、数据库、插件系统、规则 DSL、预留扩展点
- 缺数不许用 0 / 空串 / 模型估计顶替，一律 `UNKNOWN` / `TBD` + `gaps.yaml`

详见 [AGENTS.md](../AGENTS.md) 的 "Demo simplicity" 与 [docs/product/demo-scope.md](product/demo-scope.md)。

---

## 2. 固定案例参数

| 项 | 值 |
|---|---|
| 公司 / 证券 | 中芯国际 / `688981.SH`（科创板 A 股） |
| `as_of` | `2026-05-15T23:59:59+08:00`（Asia/Shanghai） |
| 核心观察期 | FY2023 – 2026 Q1 |
| 当前快照 | v3 `smic-a283e95e2c9e8068`，20 份材料，**下游唯一输入** |
| 历史快照 | v1 `smic-4c110e93f810aa8e`、v2 `smic-95dcd12eba2fe17c`，均不可变、不许覆盖 |
| 分发状态 | `INTERNAL_DEMO_ONLY` |

`as_of` 是**信息最晚公开时间**，不是财报期末、不是采集时间。港股披露可作为同一发行人的候选材料，但**不构成第二标的**，不得混用港股行情或估值口径。

---

## 3. 数据流

```
真实公开来源（港交所 / 巨潮 / SIA / 电话会纪要）
   │  ① acquire-research-materials
   │     准入检查（时间 ≤ as_of + 有出处 + 可哈希）→ 解析 PDF/HTML → 冻结
   ▼
Snapshot v3   20 份材料，全部标 ACQUIRED_UNASSESSED
   │  ② govern-research-context
   │     切结构原子 chunk → 固定中英文查询族 → BM25 → 选候选上下文
   ▼
context.jsonl            3,399 chunk（候选上下文）
   │  ③ normalize-research-facts
   │     Decimal 保精度、单位/期间/口径规整、IFRS-CAS 桥接、固定白名单派生
   ▼
normalized-facts.jsonl   20,114 条事实
   │  ④ govern-and-validate-research-evidence     ← 已实现到这
   │     T1-T4 信源分级 / 六类内容类型 / 同源组去重 / 冲突组 / 隔离 / FR-043 校验
   ▼
governed-evidence.jsonl  20,114 条证据
   │  ⑤ analyze-and-score-research-findings       ← 下一步（Ticket 05）
   ▼  D1-D7 结构化发现 + 证据分（无总分、无评级）
   │  ⑥ challenge-research-findings
   ▼  四类反方质询，最多两轮
   │  ⑦ generate-research-report                  ← Ticket 06
   ▼
report.md   每个数字可沿 evidence_id → fact_id → chunk_id → material_id 回溯到原文位置
```

**溯源链**（权威定义见 [contracts/contract-map.md](../contracts/contract-map.md)）：

```
material_id → chunk_id → fact_id → evidence_id → finding_id → challenge_id
                                    ↘ gap_id
```

不引入通用 `artifact_id` / `run_id` / `case_id`。版本由 `snapshot_id` + 文件哈希 + `manifest.yaml` 表达。

**两种运行模式**：`SNAPSHOT_BUILD` 可联网采集；`DEMO_RUN` 只读冻结输入，绝不联网、绝不接受晚于 `as_of` 的材料。

---

## 4. 核心概念（速查）

完整定义在 [CONTEXT.md](../CONTEXT.md)，这里只讲最容易误解的几条。

**整条链的骨架是「降级链」——材料不会自动变成证据，每一步都要过关。**

| 概念 | 一句话 |
|---|---|
| 采集准入 vs 证据准入 | **刻意分离**（[ADR 0002](adr/0002-separate-acquisition-from-evidence-governance.md)）。采集只管「有没有出处、时间对不对、字节能不能哈希复现」，**不判断真假可信**；能不能拿来支撑结论是后面证据治理的事 |
| `ACQUIRED_UNASSESSED` | 材料进快照时的统一状态。**进快照 ≠ 可信** |
| Chunk 结构原子 | 不用固定长度滑窗。PDF 按章节段落组、表格按带表头的行组、HTML 按标题栏目、transcript 按发言人轮次。`chunk_id` 不随查询和排名变化 |
| 固定查询族 | 版本化的中英文子查询，各自独立 BM25 后取并集。**禁止运行时模型扩写或改写查询** |
| 规整事实 | 保留 `raw_*` 原值 + 换算公式 + 规整轨迹，永不覆盖原文 |
| 证据状态三档 | `USABLE`（可引用**且可承重**）> `RESTRICTED`（可引用**不可承重**）> `QUARANTINED`（隔离，下游不许引）。判定是短路优先级 `QUARANTINED > RESTRICTED > USABLE` |
| 承重发现 | 结论方向直接依赖某条证据 = 该证据「承重」。**只有 USABLE 能承重**。管理层电话会说「利用率显著改善」可以写进报告，但不能成为「利用率确实改善了」的支撑 |
| 同源组 | 同一份原始披露的不同入口算**一个**来源。转载不增加确认数量，不靠转载数量投票 |
| 晶圆口径 | 8 寸 / 12 寸 / 8 寸等效**不是单位缩放**，除非原文给了换算规则否则禁止互换 |
| 结构分类集合 | 只有原文明确说了「完整且互斥」才可校验合计。**接近 100% 不能反推集合完整** |
| UNKNOWN vs TBD | UNKNOWN = 资料不足无法确定的**事实**；TBD = 待指定角色决定的**规则或业务选择** |

---

## 5. 目录职责

| 路径 | 是什么 | 权威性 |
|---|---|---|
| `CONTEXT.md` | 领域词汇表 | **权威** |
| `.scratch/single-stock-demo/spec.md` | 冻结需求（做什么 / 为什么 / 怎么验收） | **权威** |
| `.scratch/single-stock-demo/issues/01-06.md` | 本地 issue tracker，六张票 | **权威** |
| `.scratch/single-stock-demo/05-grilling-brief.md` | Ticket 05 的 grilling 简报 | 工作稿 |
| `contracts/contract-map.md` | 八个 Skill 之间的文件边界与溯源链 | **权威** |
| `rules/accounting.yaml` | 会计规整规则 | **权威**，单一来源 |
| `rules/context-retrieval.yaml` | 分块 / 分词 / BM25 / 查询族规则 | **权威**，单一来源 |
| `rules/source-governance.yaml` | 信源分级 / 内容类型 / 冲突 / 证据状态 | **权威**，单一来源 |
| `docs/adr/` | 三个架构决策记录 | **权威** |
| `docs/product/demo-scope.md` | 范围与非目标 | **权威** |
| `docs/product/open-questions.md` | 开放问题表（OQ-001..006） | **权威** |
| `AGENTS.md` / `CLAUDE.md` | agent 工作规则、简约原则、边界约束 | **权威** |
| `scripts/*.py` | 四个 CLI，真正干活的代码（~5,900 行） | 实现 |
| `tests/*.py` | 四份对应测试（~4,600 行，58 tests） | 实现 |
| `single-stock-demo-v3/` | **当前唯一输入**。`raw/` 原件 + `parsed/` 解析结果 + 清单 | 冻结产物 |
| `single-stock-demo/`、`single-stock-demo-v2/` | Snapshot v1 / v2，历史，不可变 | 冻结产物 |
| `single-stock-demo-v2-candidate-holding/` | 候选材料暂存区，**在所有快照之外**，不进入下游 | 非快照 |
| `tmp/ticket03-final/` | 03 产出：`context.jsonl`、`normalized-facts.jsonl` 等 | 中间产物 |
| `tmp/ticket04-final/` | 04 产出：`governed-evidence.jsonl`、`evidence-validation.yaml` | 中间产物 |
| `tmp/ticket03-baseline/`、`tmp/ticket03-normalized/` | 早期迭代残留 | 可清理 |
| `现有资料/` | 委托公司资料收集用文档 | **不是需求**，见下 |
| `.claude/skills/` | Skill 定义 | 实现 |
| `.agents/skills/` | 上面那份的 Codex 镜像，改一处要同步两处 | 实现 |

### `现有资料/` 的边界（重要）

`投研资料交付总说明.md`、`投研数据交付Prompt.md`、`投研流程与经验交付Prompt.md` 是**面向委托公司的资料索取工具**。

- 不是产品需求，不是客户确认过的业务流程，不是 Demo 运行时 prompt
- 只能当「可能的输入材料清单」参考，**绝不能用来扩展或覆盖冻结 Spec**

### 集中脚本原则

`scripts/` 下是集中 CLI，**Skill 里不重复写脚本**。Skill 只是指令，实际计算都在这四个 CLI 里，保证可复现。规则只有一份权威定义，Skill 与脚本引用同一版本。

---

## 6. 「我想了解 X，该读哪」

| 想了解 | 读 |
|---|---|
| 术语到底什么意思 | `CONTEXT.md`（每条都带 `_Avoid_` 反例，很有用） |
| 需求 / 验收标准 | `.scratch/single-stock-demo/spec.md` |
| 某张票要做什么、做到哪了 | `.scratch/single-stock-demo/issues/0N-*.md` 的勾选框和 Comments |
| 文件之间怎么衔接、ID 怎么串 | `contracts/contract-map.md` |
| 为什么这么设计 | `docs/adr/0001`（冻结快照）、`0002`（采集/证据分离）、`0003`（冲突检测限白名单） |
| 会计口径怎么规整 | `rules/accounting.yaml` |
| 检索 / 分块 / 分词怎么定的 | `rules/context-retrieval.yaml` |
| 信源等级、冲突、证据状态怎么判 | `rules/source-governance.yaml` |
| 采集是怎么实现的 | `scripts/acquire_research_materials.py` |
| 上下文治理实现 | `scripts/govern_research_context.py` |
| 事实规整实现（最大，2,371 行） | `scripts/normalize_research_facts.py` |
| 证据治理实现 | `scripts/govern_validate_research_evidence.py` |
| 有哪些未决问题、谁来拍板 | `docs/product/open-questions.md` |
| 一条真实数据长什么样 | `tmp/ticket03-final/normalized-facts.jsonl` 抽一行看 |

---

## 7. 当前进度

| 票 | 内容 | 状态 |
|---|---|---|
| 01 | 采集并冻结 Snapshot v1 | done |
| 02 | 放宽采集边界，构建 Snapshot v2 → v3 | done |
| 03 | 上下文治理 + 事实规整 | done |
| 04 | 证据治理与核验 | done（main `945a57a`，58 tests pass，真实数据 `WARN`） |
| 05 | D1-D7 发现 + 反方质询 | **ready-for-agent — 下一步** |
| 06 | 编排器 + 报告生成 + 端到端验收 | 等 05 |

### Skill 实现状态

八个 Skill 中**已实现四个**（01-04 对应的采集、上下文治理、事实规整、证据治理）。

**尚未实现**：`single-stock-research-orchestrator`、`analyze-and-score-research-findings`、`challenge-research-findings`、`generate-research-report`。

`.claude/skills/` 下其余的（tdd、grilling、code-review、domain-modeling、handoff、implement、to-spec、to-tickets 等）是**通用开发流程 Skill**，不属于这八个业务 Skill。

### 工作节奏

先 grill（把规划往死里质询）→ 冻结规划 → **换一个新窗口** implement。规划和实现不在同一个窗口里做。

---

## 8. 已知问题与风险

按重要性排序。这些是执行中发现但**尚未写进任何票**的东西。

### 8.1 抽取语义准确率没有门禁（最需要关注）

规整阶段只保证「诚实记录抽到了什么、怎么换算的」，**不保证抽对了**。而下游 04 的信源分级看的是**材料等级**（年报 = T1），不是**这条抽取的正确性**——所以一条错抽的数字照样一路绿灯变成 `USABLE`、可承重。

实例（`FACT_ecbb3d82b20ae58fed788265`，2025 半年报）：

```
原文：  息税折旧摊销前利润率（%） 53.8 52.4 增加1.4个百分点
抽成：  metric_id = DEPRECIATION_EXPENSE
        raw_unit = MONEY，1.4 × 1000 = 1400 元
状态：  normalization_status = PASS → T1 / REPORTED_FACT / USABLE
```

指标认错（匹配到「折旧」二字）、单位认错（百分点当成钱）、语义完全错位。

粗筛：`raw_unit=MONEY` 但原文片段含「百分点」的记录，**4,575 条数字事实中有 179 条（约 3.9%）**。这只是启发式，不是精确统计，但说明不是孤例。

**对 Ticket 05 的影响**：D1-D7 要从两万条里挑证据支撑结论。若挑中这类记录，「每个数字可追溯」就变成「能追溯到出处，但追过去发现读错了」。

### 8.2 证据状态分布可疑

```
20,114 条事实 → 20,114 条证据，一条没少
USABLE 15,202  RESTRICTED 4,912  QUARANTINED 0
T1 19,544  T2 203  T3 278  T4 89
```

`QUARANTINED` 为 0、`USABLE` 占 76%。隔离条件（越过 `as_of` / 定位解析不出 / 规整 `BLOCKED`）确实一条都没触发，逻辑上说得通，但**整条链没有任何一处真的把东西挡下来**，这削弱了「治理」的展示效果。

### 8.3 Ticket 04 真实数据是 `WARN` 不是 `PASS`

具体警告项待查（见 `tmp/ticket04-final/evidence-validation.yaml`）。可能影响 05 某些维度的证据充分性。

### 8.4 冲突检测被缩到白名单

[ADR 0003](adr/0003-scope-conflict-detection-to-whitelisted-metric-facts.md) 把冲突检测限制到人工核验过的 `fact_id` 白名单，目前白名单只有 2 条用户确认的 FY2024 利润事实。这是「简约」的取舍，但也意味着**冲突处理能力在 Demo 里几乎没被展示**。

### 8.5 事实数量级偏大

3,399 个候选片段抽出 20,114 条事实（平均每片段 6 条），其中 `TEXT_PROPOSITION` 占 77%。05 阶段需要从中挑选证据，选择策略必须明确，否则要么淹没、要么随意。

### 8.6 Ticket 05 的评分规则还没定死

要求是「证据分 0 必须对应 UNKNOWN」「高分可以对应 `NOT_SUPPORTED`」「不许有加权总分，汇总固定 `overall_score: NOT_APPLICABLE`」——但**具体怎么算分尚未冻结**。这是 05 grilling 的主战场。

### 8.7 仓库里的历史残留

三个快照目录 + `tmp/` 下多轮中间产物。哪些是审计必须保留、哪些可清理，目前没有明确说明。

---

## 9. 新窗口怎么开

```
读 docs/PROJECT-GUIDE.md，然后回答我：<具体问题>
```

按话题分窗口：换话题就换窗口；同一话题深挖就 `/compact` 继续；要动手写代码一定换窗口。

---

*本文件是导览，不是权威。发现它与 `CONTEXT.md` / `spec.md` / `rules/` 冲突时，改本文件，不要改那些。*