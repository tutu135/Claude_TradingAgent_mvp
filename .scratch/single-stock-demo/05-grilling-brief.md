# 05 grilling 简报 — 给下一个新窗口

**用途**：在新窗口起 `/grill-with-docs` 打磨 ticket 05（形成并质询 D1–D7 发现）时先读这份。目标是逼出一份逐项确认的冻结规划，落进 `05-analyze-challenge-findings.md` 的 `## Comments`（必要时加 ADR / CONTEXT 术语），然后**再换窗口** `/implement`。
memory 会自动加载（`ticket04-done.md`、`ticket03-done-ticket04-next.md`），所以项目状态不用重述。这份只补 memory 覆盖不到的两块：05 的判断题议程 + 用户在意什么。

## 现在在哪

- 01–04 全部 done。04 提交在 main `945a57a`。
- 04 产物（05 的输入）：`tmp/ticket04-final/governed-evidence.jsonl`（20,114 条治理证据，1:1 派生自事实）+ `evidence-validation.yaml`（真实运行 WARN）+ `gaps.yaml`。**注意 `tmp/` 是 gitignored**，跑一遍 04 的 CLI 才有；命令见 skill `govern-and-validate-research-evidence`。
- 关键可用性字段：只有 `evidence_status=USABLE`（15,202 条）可承重发现；`RESTRICTED`（4,912）仅可引用/展示/作冲突一方；`QUARANTINED`（0）不可引用。tier T1 19,544 / T2 203 / T3 278 / T4 89。

## 05 要做什么

完成两个 skill：`analyze-and-score-research-findings` 与 `challenge-research-findings`。D1–D7 七维发现 + 四类反方质询（来源溯源 / 会计可比 / 归因因果 / 证伪缺证）。**绝不输出投资建议。** 8 条验收在票里。

## 真正的判断题（grilling 该打的靶）

这些是 05 里没有默认答案、需要和用户逐条敲定的地方——04 的 grilling 也是这么干的：

1. **D1–D7 到底是哪七维**：主研究问题是什么？七个维度各自的命题、以及每维的"承重证据"来自 04 的哪些 `evidence_id`？（先确认 USABLE 集合够不够支撑每一维，还是某些维注定 UNKNOWN。）
2. **evidence_score 的语义与刻度**：分值范围、0 分↔UNKNOWN 的硬绑定、"高分可对应 `NOT_SUPPORTED`"怎么落地。**明确禁止**加权总分 / 星级 / 评级，`overall_score` 恒 `NOT_APPLICABLE`——这条要像 04 的"零冲突≠未运行"一样，用机制保证而不是靠自觉。
3. **相关≠因果的护栏**：怎么用确定性规则防止把相关自动表述成因果、防止静默重复归因。管理层解释在无独立证据时保持 `MANAGEMENT_ASSERTION`（04 已经这么分类了，05 要接住）。
4. **质询的处置与终止**：四种允许处置是哪四种？"每问题一次定向复核、全程最多两轮、两轮未决则降级/BLOCKING/写 gap"怎么编码成不会死循环的状态机。质询不能直接改发现——修订前后 + 理由都要留。
5. **D7 后续观察指标**：数值阈值只有冻结数据/确认规则/可复算公式支持时才给，否则 UNKNOWN/TBD。判定逻辑要可追溯。
6. **"无投资建议"边界的正反 fixture**：买卖持有/仓位/目标价/估值锚/吸引力判断/预测都禁止——需要反例 fixture 证明边界能挡住。
7. **确定性与重建**：是否延续 03/04 的"两次干净重建哈希一致 + 全量事实的验证 run status"模式？分析阶段有模型判断成分，要想清楚哪些是确定性规则、哪些真的需要模型，以及后者如何保持可复现/可审计。这可能是 05 最难、最该在 grilling 里解决的一块。

## 这个用户在意什么（据这一路观察，用来定 grilling 的语气和取舍）


- **规划先行、做扎实再往前**。用户选过 option A：先把 03 做扎实再进 04。节奏固定是 grill→冻结逐项确认的规划→换窗口 implement。重视做对 > 做快。
- **Demo 简约、反过度设计**。显式禁止 DSL / 插件 / 为假设输入建抽象（AGENTS.md "Demo simplicity"）。规则单一权威定义，不复制。04 code-review 时我特意没为 `resolution_order` 建规则解释器，就是守这条。05 别为"将来多维/多股"预留架构。


