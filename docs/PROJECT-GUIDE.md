# 项目导览

**给谁看**：需要快速建立项目整体认知的人，或新开窗口的 agent。

**这份文件的定位**：导航图 + 当前状态 + 已知问题。它**不复制**权威文档的内容，只告诉你去哪读。权威定义永远以 `CONTEXT.md`、`.scratch/single-stock-demo/spec.md`、`contracts/contract-map.md`、`rules/*.yaml` 为准；本文件与它们冲突时，以它们为准。

**状态：六张票全部 done，端到端跑通**（2026-07-22，main `0facd28`）。

---

## 0. 三十秒速览

用一份**冻结**的中芯国际（`688981.SH`）真实公开资料，跑通一条完整的投研分析流水线，验证「每个数字都能追溯回原文出处」这件事在工程上能不能成立。

主研究问题（冻结）：

> 截至 `as_of`，中芯国际的经常性经营盈利能力发生了哪些可验证的变化，现有证据在多大程度上支持其已进入可持续改善阶段？

问题开放，允许得出支持 / 部分支持 / 反驳 / 证据不足任一结果。**成功标准不是预测准确率，而是报告准确、全面、可核验。**

| 项 | 值 |
|---|---|
| 公司 / 证券 | 中芯国际 / `688981.SH`（科创板 A 股） |
| `as_of` | `2026-05-15T23:59:59+08:00`（Asia/Shanghai） |
| 核心观察期 | FY2023 – 2026 Q1 |
| 当前快照 | v3 `smic-a283e95e2c9e8068`，20 份材料，**下游唯一材料输入** |
| 历史快照 | v1 `smic-4c110e93f810aa8e`、v2 `smic-95dcd12eba2fe17c`，不可变 |
| 执行模式 | `FROZEN_REPLAY`（运行期零模型调用） |
| 分发状态 | `INTERNAL_DEMO_ONLY` / `PENDING_HUMAN_REVIEW` |
| 代码量 | `scripts/` 8 个 CLI 约 9,700 行；`tests/` 约 7,000 行，144 tests |

`as_of` 是**信息最晚公开时间**，不是财报期末、不是采集时间。港股披露可作为同一发行人的候选材料，但**不构成第二标的**。

### 明确不做的事

- 不是产品，是个人 / 非商业 / 本地 / 不可对外发布的一次性 Demo
- 不输出买卖建议、目标价、估值锚、仓位建议、投资评级、系统预测
- 不做 OCR、音频转写、图表读数 —— 读不出来就记 gap
- 不建通用架构：无 DAG、队列、调度器、数据库、插件系统、规则 DSL、预留扩展点
- 缺数不许用 0 / 空串 / 模型估计顶替，一律 `UNKNOWN` / `TBD` + `gaps.yaml`

详见 [AGENTS.md](../AGENTS.md) 的 "Demo simplicity" 与 [docs/product/demo-scope.md](product/demo-scope.md)。

---

## 1. 一次运行长什么样

```bash
python scripts/validate_demo_run.py preflight        # 清空运行目录 + 校验冻结输入
python scripts/acquire_research_materials.py DEMO_RUN --case-file ... --snapshot-dir ...
python scripts/govern_research_context.py            --output-dir single-stock-demo-run
python scripts/normalize_research_facts.py           --output-dir single-stock-demo-run
python scripts/govern_validate_research_evidence.py  --output-dir single-stock-demo-run
python scripts/analyze_and_score_research_findings.py select   ... # 再 finalize
python scripts/challenge_research_findings.py        --output-dir single-stock-demo-run
python scripts/validate_demo_run.py gate             # 算 governance_status + 定报告形态
python scripts/generate_research_report.py           # report.md + report-validation.yaml
python scripts/validate_demo_run.py finalize-manifest
```

完整参数见 `.claude/skills/single-stock-research-orchestrator/SKILL.md`（**七阶段顺序的唯一权威处**）。全流程约 1 分 45 秒。

**关键性质**：两次连续干净重放的 `report.md`、`report-validation.yaml`、`run-integrity.yaml` 字节一致；`manifest.yaml` 除 `generated_at` 外一致。

---

## 2. 数据流

```
真实公开来源（港交所 / 巨潮 / SIA / 电话会纪要）
   │  ① acquire-research-materials
   │     准入检查（时间 ≤ as_of + 有出处 + 可哈希）→ 解析 PDF/HTML → 冻结
   ▼
Snapshot v3   20 份材料，全部 ACQUIRED_UNASSESSED        ← 只读
   │  ② govern-research-context        retrieval_status = PASS
   ▼
context.jsonl            3,399 chunk 全量入库，其中 candidate_context=true 仅 415
   │  ③ normalize-research-facts       normalization_run_status = WARN
   ▼
normalized-facts.jsonl   20,114 条事实（TEXT 15,539 / NUMERIC 4,575 / DERIVATION 0）
   │  ④ govern-and-validate-research-evidence   validation_status = WARN
   ▼
governed-evidence.jsonl  20,114 条证据（USABLE 15,202 / RESTRICTED 4,912 / QUARANTINED 0）
   │  ⑤ analyze-and-score-research-findings     analysis_run_status = PASS
   │     select（确定性挑候选集）→ 模型判断 → finalize（脚本反算证据分 + 12 项校验）
   ▼  D1–D7 结构化发现 + 证据分（无总分、无评级）
   │  ⑥ challenge-research-findings              challenge_run_status = WARN
   ▼  四类反方质询，最多两轮，一问一次定向复核
   │  ⑦ generate-research-report
   ▼
report.md   十章节 + 证据表；每个数字可沿链回溯到原文位置
```

**溯源链**（权威定义见 [contracts/contract-map.md](../contracts/contract-map.md)）：

```
material_id → chunk_id → fact_id → evidence_id → finding_id → challenge_id
                                    ↘ gap_id
```

不引入通用 `artifact_id` / `run_id` / `case_id`。版本由 `snapshot_id` + 文件哈希 + `manifest.yaml` 表达。

**两种运行模式**：`SNAPSHOT_BUILD` 可联网采集；`DEMO_RUN` 只读冻结输入，绝不联网、绝不接受晚于 `as_of` 的材料。

---

## 3. 三个位置：只读输入 vs 可重建输出

这是理解仓库布局的关键，也是 06 纠正过的一处旧文档错误（产物**不写回快照目录**）。

| 位置 | 是什么 | 可否重建 |
|---|---|---|
| `single-stock-demo-v3/` | 冻结快照：材料 + 采集元数据 | 否，只读 |
| `frozen-analysis-inputs/` | **冻结判断输入**：模型产出的发现与质询，带哈希与绑定 | 否，只读 |
| `single-stock-demo-run/` | 运行目录：上述七阶段的全部产物 | 是，每次清空重建 |

`frozen-analysis-inputs/frozen-inventory.yaml` 是信任根，记录 5 个文件的 sha256 + `selection_hash` + `analysis_rule_version`；`preflight` 拿它逐项比对。**行尾是哈希的一部分**——`.gitattributes` 把工作区钉死为 LF，否则 Windows 上新克隆会直接哈希不符。

运行目录只保留 `report.md`、`report-validation.yaml`、`run-gate.yaml` 入库（字节稳定），其余 95MB gitignore；`manifest.yaml` 按设计带 `generated_at`，不入库。

---

## 4. 核心概念（速查）

完整定义在 [CONTEXT.md](../CONTEXT.md)（五节：案例与时间 / 材料与证据 / 分析与输出 / 编排与运行 / 不确定性），这里只讲最容易误解的。

**整条链的骨架是「降级链」——材料不会自动变成证据，每一步都要过关。**

| 概念 | 一句话 |
|---|---|
| 采集准入 vs 证据准入 | **刻意分离**（[ADR 0002](adr/0002-separate-acquisition-from-evidence-governance.md)）。采集只管「有没有出处、时间对不对、字节能不能哈希复现」，**不判断真假可信** |
| `ACQUIRED_UNASSESSED` | 材料进快照时的统一状态。**进快照 ≠ 可信** |
| Chunk 结构原子 | 不用固定长度滑窗。PDF 按章节段落组、表格按带表头的行组、HTML 按标题栏目、transcript 按发言人轮次 |
| 固定查询族 | 版本化的中英文子查询，各自独立 BM25 后取并集。**禁止运行时模型扩写或改写查询** |
| 证据状态三档 | `USABLE`（可引用**且可承重**）> `RESTRICTED`（可引用**不可承重**）> `QUARANTINED`（隔离，下游不许引） |
| 承重发现 | 结论方向直接依赖某条证据 = 该证据「承重」。**只有 USABLE 能承重**。管理层说「利用率显著改善」可以写进报告，但不能成为「利用率确实改善了」的支撑 |
| 同源组 | 同一份原始披露的不同入口算**一个**来源。转载不增加确认数量 |
| 承重指标白名单 | 每个维度只有名单内的 `metric_id` 能承担结论方向（[ADR 0004](adr/0004-layer-analysis-into-deterministic-selection-and-bounded-model-judgment.md)）。**D2/D5/D7 名单为空、D3 只有一条**，如实披露不修补 |
| 证据分 0–3 | 由脚本从选中证据**反算**，模型不产出分数。分 0 强制 UNKNOWN；反之不成立。无加权总分，`overall_score` 恒为 `NOT_APPLICABLE` |
| 冻结重放 | 模型判断产物是只读输入，运行期零模型调用（[ADR 0005](adr/0005-replay-frozen-judgment-and-keep-the-orchestrator-a-validator.md)）。端到端证明的是「冻结输入 → 最终产物」的确定性重放，不是判断层被重新执行 |
| 治理状态 | 只由检索 / 规整 / 证据治理三者取最坏值合成 = **WARN**。分析与质询状态**不并入**，并列展示 |
| 完整性失败 vs 内容级失败 | 前者（输入不可信）→ `DIAGNOSTIC_ONLY`，**不含任何结论**；后者（结论不合格）→ `FULL_REPORT` + 显著标警。永远有报告，没有静默停止 |
| 证据表 / 未绑定数字 | 数字**只出现在证据表**。模型散文按**整句排除**（不是删字符），最终门禁回读渲染后的 `report.md` 断言自由叙述区数字为 0 |
| 范围识别 | 确定性三规则：命中禁止输出词表→真实拒答；提到同业→免责；晚于 `as_of`→免责。**不用模型分类** |
| 晶圆口径 | 8 寸 / 12 寸 / 8 寸等效**不是单位缩放**，除非原文给了换算规则否则禁止互换 |
| UNKNOWN vs TBD | UNKNOWN = 资料不足无法确定的**事实**；TBD = 待指定角色决定的**规则或业务选择** |

---

## 5. 目录职责

| 路径 | 是什么 | 权威性 |
|---|---|---|
| `CONTEXT.md` | 领域词汇表（每条带 `_Avoid_` 反例） | **权威** |
| `.scratch/single-stock-demo/spec.md` | 冻结需求，20 节，FR 编号 | **权威** |
| `.scratch/single-stock-demo/issues/01–06.md` | 本地 issue tracker，六张票；`## Comments` 里是冻结规划 | **权威** |
| `contracts/contract-map.md` | 八个 Skill 之间的文件边界与溯源链 | **权威** |
| `rules/accounting.yaml` | 会计规整规则 | **权威**，单一来源 |
| `rules/context-retrieval.yaml` | 分块 / 分词 / BM25 / 查询族 | **权威**，单一来源 |
| `rules/source-governance.yaml` | 信源分级 / 内容类型 / 冲突 / 证据状态 | **权威**，单一来源 |
| `rules/analysis.yaml` | 承重指标白名单 / 评分 / 禁止输出词表 / 质询回路 | **权威**，单一来源 |
| `rules/report.yaml` | 十章节 / 证据表列 / 散文扫描字段 / 范围识别 / 术语表 / 固定披露 | **权威**，单一来源 |
| `docs/adr/0001–0005` | 五个架构决策记录 | **权威** |
| `docs/product/demo-scope.md` | 范围与非目标 | **权威** |
| `docs/product/open-questions.md` | OQ-001..006（4 RESOLVED / 1 UNKNOWN / 1 TBD） | **权威** |
| `AGENTS.md` / `CLAUDE.md` | agent 工作规则、简约原则、边界约束 | **权威** |
| `DEMO-KNOWN-ISSUES.md` | 已知问题清单 A/B/C/D/E/F 六组 | **权威**（问题登记册） |
| `scripts/*.py` | 8 个 CLI，真正干活的代码 | 实现 |
| `tests/*.py` | 8 份对应测试，144 tests | 实现 |
| `.claude/skills/` | Skill 定义（8 个业务 + 若干通用开发流程） | 实现 |
| `.agents/skills/` | 上面那份的 Codex 镜像，**改一处要同步两处** | 实现 |
| `single-stock-demo-v3/` | **当前唯一材料输入**。`raw/` 原件 + `parsed/` 解析结果（57MB，未入库） | 冻结产物 |
| `frozen-analysis-inputs/` | 冻结判断输入 + 哈希清单 | 冻结产物 |
| `single-stock-demo-run/` | 运行目录，可重建 | 可重建 |
| `single-stock-demo/`、`single-stock-demo-v2/` | Snapshot v1 / v2，历史，不可变 | 冻结产物 |
| `single-stock-demo-v2-candidate-holding/` | 候选材料暂存区，**在所有快照之外** | 非快照 |
| `tmp/ticket0N-*/` | **历史残留**。06 之后不再被任何 Skill / 脚本 / 测试引用，可整体删除 | 可清理 |
| `现有资料/` | 委托公司资料收集用文档 | **不是需求**，见下 |

### `现有资料/` 的边界（重要）

`投研资料交付总说明.md`、`投研数据交付Prompt.md`、`投研流程与经验交付Prompt.md` 是**面向委托公司的资料索取工具**。不是产品需求，不是客户确认过的业务流程，不是 Demo 运行时 prompt。只能当「可能的输入材料清单」参考，**绝不能用来扩展或覆盖冻结 Spec**。

### 集中脚本原则

`scripts/` 下是集中 CLI，**Skill 里不重复写脚本**。Skill 只是指令，实际计算都在 CLI 里。规则只有一份权威定义，Skill 与脚本引用同一版本。特别地，`validate_demo_run.py` 只做裁判（三个子命令，不 import 阶段脚本、不 subprocess 调它们、不含"下一步是什么"的控制流）——七阶段顺序住在 Skill 的 Markdown 里。

---

## 6. 「我想了解 X，该读哪」

| 想了解 | 读 |
|---|---|
| 术语到底什么意思 | `CONTEXT.md` |
| 需求 / 验收标准 | `.scratch/single-stock-demo/spec.md`（FR-0xx 编号） |
| 某张票做了什么、怎么决策的 | `.scratch/single-stock-demo/issues/0N-*.md` 的勾选框 + `## Comments` |
| 文件之间怎么衔接、ID 怎么串 | `contracts/contract-map.md` |
| 为什么这么设计 | `docs/adr/`：`0001` 冻结快照 / `0002` 采集与证据分离 / `0003` 冲突检测限白名单 / `0004` 分析分层 / `0005` 冻结重放 + 编排器只做裁判 |
| 怎么跑一次完整流程 | `.claude/skills/single-stock-research-orchestrator/SKILL.md` |
| 报告为什么长这样 | `rules/report.yaml` + `.claude/skills/generate-research-report/SKILL.md` |
| 会计口径怎么规整 | `rules/accounting.yaml` |
| 检索 / 分块 / 分词怎么定的 | `rules/context-retrieval.yaml` |
| 信源等级、冲突、证据状态怎么判 | `rules/source-governance.yaml` |
| D1–D7 怎么选证据、怎么算分 | `rules/analysis.yaml` + `scripts/analyze_and_score_research_findings.py` |
| 有哪些已知缺陷 | `DEMO-KNOWN-ISSUES.md` |
| 有哪些未决问题、谁来拍板 | `docs/product/open-questions.md` |
| **最终报告实际长什么样** | `single-stock-demo-run/report.md` |
| **这次运行的自检结果** | `single-stock-demo-run/report-validation.yaml` |
| 一条真实数据长什么样 | `single-stock-demo-run/normalized-facts.jsonl` 抽一行（需先跑一次） |

**代码入口**：`acquire_research_materials.py`（采集 1,324 行）、`govern_research_context.py`（上下文 1,062）、`normalize_research_facts.py`（规整 2,371，最大）、`govern_validate_research_evidence.py`（证据 1,169）、`analyze_and_score_research_findings.py`（分析 1,443）、`challenge_research_findings.py`（质询 435）、`generate_research_report.py`（报告 1,352）、`validate_demo_run.py`（裁判 558）。

---

## 7. 进度与实测结果

| 票 | 内容 | 状态 |
|---|---|---|
| 01 | 采集并冻结 Snapshot v1 | done |
| 02 | 放宽采集边界，构建 Snapshot v2 → v3 | done |
| 03 | 上下文治理 + 事实规整 | done |
| 04 | 证据治理与核验 | done（`945a57a`） |
| 05 | D1–D7 发现 + 反方质询 | done（`1349c1c`） |
| 06 | 编排 + 报告生成 + 端到端验收 | done（`0facd28`） |

八个业务 Skill 全部实现。`.claude/skills/` 下其余的（tdd、grilling、code-review、implement 等）是**通用开发流程 Skill**，不属于这八个。

### 黄金案例实测结果（这些是真实数字，不是目标值）

| 项 | 实测 |
|---|---|
| 五个阶段状态 | PASS / WARN / WARN / PASS / WARN |
| `governance_status` | **WARN** |
| D1–D7 方向 | 5 MIXED（D1/D2/D3/D4/D6）+ 2 UNKNOWN（D5/D7），**无一 SUPPORTED**；证据分 2–3 |
| 质询 | 5 条：2 无改动 / 2 修订 / 1 降级；2 条触发方向翻转（D2 `SUPPORTED→MIXED`、D7 `MIXED→UNKNOWN`） |
| 散文数字 | 检出 442，整句排除 126 句，**泄漏 0** |
| 证据表 | 85 行，溯源链未解析项 0 |
| 调节桥接复算 | 7 条：4 PASS / 3 UNKNOWN |
| 冲突组 / 隔离 | **0 / 0** |
| 政府补助敏感性 | **0 条**（报告口径 15 条存在，但无一满足可分离且已计入同口径） |
| gaps | 4,922（`NORMALIZATION_UNKNOWN` 4,912；P1 4,915 / P2 7） |

**读这张表的正确方式**：0 和 WARN 不是 bug，是 v3 的真实承载力。项目的立场是**如实披露 > 好看**——冲突、隔离、敏感性、FAIL 报告这四个机制在真实数据上没有观察对象，因此由合成 fixtures 证明机制存在，报告里把零值和原因原样写出来，**绝不造数据**。

---

## 8. 已知问题（完整版见 `DEMO-KNOWN-ISSUES.md`）

按重要性排序。这些**都已在报告中披露**，但都未修复。

| # | 问题 | 要害 |
|---|---|---|
| A1 | **抽取语义错误没有门禁**（最需要关注） | 「EBITDA 利润率提高 1.4 个百分点」被抽成 `DEPRECIATION_EXPENSE = 1400 元`，且 `normalization_status=PASS` → T1 / USABLE / 可承重。启发式粗筛 4,575 条数值中约 179 条（3.9%）。**三档证据状态全在判元数据健不健全，没有一条在判抽取语义对不对** |
| A2 | 隔离机制从未被真实数据触发 | `QUARANTINED` 恒为 0。是采集挡住了，还是机制没被检验过——目前无法区分 |
| A3 | 事实到证据 1:1，证据治理没筛掉任何记录 | 04 的作用是贴标签不是收窄，收窄责任全压在 05 挑证据 |
| A4 | 冲突检测被缩到 2 条白名单事实 | [ADR 0003](adr/0003-scope-conflict-detection-to-whitelisted-metric-facts.md) 的有意取舍，代价是这个能力在 Demo 里展示不出来 |
| A5 | gap 优先级轴失去区分度 | 4,922 条里 4,915 条 P1。报告因此明确声明不按优先级筛，改按 `origin_stage × gap_kind` 聚合 |
| B1/B2 | 表头兜底可能静默失效；PDF 表格结构可能在解析阶段就被压平 | **未验证**。B2 结论决定 A1 该修哪一层，验证优先级最高 |
| — | D3 唯一承重数值期间标注错误 | `ASP_SOURCE_REPORTED` 标 `FISCAL_YEAR` 但来自半年报。D3 整个数值骨架架在这一条上，报告原样展示并附 gap，不洗白 |
| — | 跨维 `overlap_note` 只能全局校验 | 单维模型判断看不见其他维度，进不了逐次重生成闸 |

### 06 实现期发现的两个真实坑（已修）

1. **假闸门**：散文数字门禁最初扫的是 sanitizer 自己的输出，恒等于 0。已改为回读渲染后的 `report.md`，只有结构行和逐字匹配的固定说明可豁免。
2. **CRLF 破哈希**：Windows 上 git 默认 CRLF 检出会改变冻结判断输入的字节，新克隆 `preflight` 直接失败。已用 `.gitattributes` 钉死 LF。

---

## 9. 工作节奏与新窗口

先 grill（把规划往死里质询）→ 冻结规划写进 ticket 的 `## Comments` → **换一个新窗口** implement。规划和实现不在同一个窗口里做。

新窗口开场：

```
读 docs/PROJECT-GUIDE.md，然后回答我：<具体问题>
```

按话题分窗口：换话题就换窗口；同一话题深挖就 `/compact` 继续；要动手写代码一定换窗口。

---

*本文件是导览，不是权威。发现它与 `CONTEXT.md` / `spec.md` / `rules/` 冲突时，改本文件，不要改那些。*
