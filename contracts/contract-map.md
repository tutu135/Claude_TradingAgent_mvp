# 单股票投研 Demo 契约地图

## 目的与权威性

本文件冻结八个 Skills 之间的文件边界、权威格式和最小溯源链。字段级契约在实现阶段依本地图建立，但不得扩展为通用工作流模型。

Demo 不定义 `ResearchCase`、`ResearchRun`、`StageArtifact`、通用消息信封或数据库实体。所有文件都属于唯一的中芯国际黄金案例；通过固定文件名、内容哈希和下列业务 ID 建立联系。

## 固定案例产物

```text
<snapshot-dir>/
  case.yaml
  snapshot-manifest.yaml
  materials.jsonl
  raw/
  parsed/
  context.jsonl
  normalized-facts.jsonl
  governed-evidence.jsonl
  validation.yaml
  findings.yaml
  challenges.yaml
  gaps.yaml
  report.md
  manifest.yaml
```

Snapshot v1 `smic-4c110e93f810aa8e` 保持不可变；Snapshot v2 `smic-95dcd12eba2fe17c` 是 Ticket 02 的自包含历史结果；当前 Ticket 03 唯一输入为 Snapshot v3 `smic-a283e95e2c9e8068`，其 `parent_snapshot_id` 指向 v2，但运行时不依赖 v1/v2。v3 完整携带 20 份 `ACQUIRED_UNASSESSED` 材料及冻结产物。高相关但未满足采集准入的内容只进入 Snapshot 之外的候选材料暂存区，不属于上述权威产物。

`data-snapshot.csv` 是可选兼容视图，只能从权威 JSONL 派生。它不得被阶段 Skill 反向读取为事实源。

## 格式约定

- YAML：单例配置、汇总、状态和规则引用。
- JSONL：材料、片段、事实和证据等逐条记录。
- Markdown：供人阅读的内部报告。
- 时间：ISO 8601，必须带时区；案例时区为 `Asia/Shanghai`。
- 数值：数值、单位、币种、缩放因子和期间分开保存，不把单位拼入数字字符串。
- 缺失：不得使用空字符串、零或模型估计代替 UNKNOWN/TBD；详细原因写入 `gaps.yaml`。
- 哈希：冻结文件和原始内容记录稳定内容哈希，用于重现与防止静默改写。
- 采集状态：进入新快照的材料统一为 `ACQUIRED_UNASSESSED`；治理结果不回写快照。

## 业务 ID 溯源链

```text
material_id -> chunk_id -> fact_id -> evidence_id -> finding_id -> challenge_id
                                      \-> gap_id
```

- `material_id`：一份取得材料或数据记录。
- `chunk_id`：材料中可精确定位的上下文片段；是否进入候选上下文由片段的独立选择状态表示。
- `fact_id`：技术标准化和会计规整后的候选事实或派生指标。
- `evidence_id`：完成信源治理并被声明为可用、受限或隔离的事实记录。
- `finding_id`：D1-D7 中某个结构化发现。
- `challenge_id`：针对发现或承重证据的反方质询。
- `gap_id`：UNKNOWN/TBD 缺口。

不增加通用 `artifact_id`、`run_id` 或 `case_id`。版本由 `snapshot_id`、文件哈希和 `manifest.yaml` 表达。

## 文件契约

### `case.yaml`

固定研究入口。至少包含：

- `case_origin: model_generated`
- 公司、`688981.SH`、A 股/上交所科创板标识
- `as_of: 2026-05-15T23:59:59+08:00`
- 主研究问题
- 必需数据覆盖
- 报告与禁止输出边界
- 当前规则版本引用

### `snapshot-manifest.yaml`

冻结快照清单。至少包含：`snapshot_id`、可选 `parent_snapshot_id`、创建时间、`as_of`、唯一材料数、材料定位数、文件相对路径与哈希、构建方式，以及个人非商业使用假设。还要按 `acquisition_target` 记录搜索渠道、取得材料、候选暂存数量、具体材料缺口和搜索状态；搜索状态只表示 `IN_PROGRESS` 或 `SATURATED`，不得用 `COVERED/PARTIAL` 声称事实完整。

每个快照必须自包含。更新材料、采集元数据或规则时生成新 `snapshot_id`，不得原地伪装成同一快照。`DEMO_RUN` 只验证快照身份、哈希、`as_of`、必需采集元数据和文件完整性，不要求材料已是 `USABLE`。

### `materials.jsonl`

一行一份唯一内容的研究材料及其采集元数据。至少包含：

- `material_id`、`source_id`、标题、展示发布主体和采集时间；
- 来源显示的发布时间文本、时间精度、最早/最晚可能发布时间及判断依据；
- 规范材料定位和备用材料定位；
- `media_type`、内容哈希、冻结文件定位；
- 至少一个 `acquisition_target`；
- `acquisition_status: ACQUIRED_UNASSESSED`；
- `as_of_eligible` 及理由；
- 解析状态，以及存在时的辅助解析文件定位；
- 可得时的条款入口、已知限制、`usage_basis` 和声称的原始来源。

条款和使用备注是尽力记录的可选元数据，不是采集前置批准。契约不得保存账号、密码、Cookie、Token 或会话标识。相同内容哈希只创建一个 `material_id` 并保存一份内容，优先选择发行人、监管、具名机构再到其他稳定入口作为规范材料定位，其余入口作为备用定位；这不构成信源评级。

当前无法可靠提取的材料仍可写入本文件并冻结，解析状态标为 `UNSUPPORTED` 或 `PARTIAL`，但不得形成上下文片段。发布时间区间跨越 `as_of`，或采集来源/展示发布主体/发布时间依据/材料定位尚无法记录的内容，不写入本文件，留在候选材料暂存区。已确认发布时间晚于 `as_of` 的内容不进入当前快照。

### 候选材料暂存区

候选材料暂存区是非权威的工作区，不属于任何 Snapshot。它仅保存高相关候选文件或线索、发现时间、已知入口、目标映射、缺少的采集证据和用户确认状态；不分配正式 `material_id`，不进入 RAG、事实提取、治理、分析或报告。补齐采集准入后，候选内容只能进入新的快照版本。

### `context.jsonl`

一行一个上下文片段。对当前快照中所有可提取、与研究目标相关的 `ACQUIRED_UNASSESSED` 材料按可复现边界完成分块后，全部片段都写入本文件，而不是只保存检索命中。每行至少包含：`chunk_id`、`material_id`、页码/章节/表格等内容定位、片段文本或数据、片段哈希、分块方法、检索关键词、`candidate_context`、命中的固定 `query_id` 以及选择原因。

BM25 索引覆盖本文件中的全部片段；`normalize-research-facts` 只处理 `candidate_context=true` 的候选上下文。固定查询的预期片段即使未被召回，也保留其 `chunk_id` 并作为已知漏召回记录。选择状态只表示与研究问题的相关性，不判断真实性、信源等级、内容类型或证据资格；检索命中不表示事实成立。

权威片段采用可复现的结构原子，不使用固定 token 长度的重叠窗口：PDF 正文按章节内段落组切分；表格片段必须共同保留表头、单位、期间、数据行和相关脚注，大表按行组拆分时重复携带这些解释要素；HTML 按标题栏目切分；transcript 按 speaker turn 切分并保留所属栏目。命中结果可以关联相邻 `chunk_id` 供阅读或解释，但相邻扩展不产生新的权威片段。`chunk_id` 由材料、结构定位和片段内容稳定确定，不受查询、排名或 Top-K 变化影响。

固定查询以版本化 Query Family 管理；主研究问题和 D1-D7 分别映射查询族，每族包含显式的中英文子查询。每个子查询独立执行 BM25，并保存原始查询、分词结果、命中排名和分数；查询族以子查询命中并集形成候选。运行时不得由模型临时扩写同义词、改写查询或改变固定查询集。

查询族分为两类职责：`RESEARCH` 包含主研究问题和 D1-D7，用于研究相关性召回及 VR-003 验收；`NORMALIZATION_GUARD` 至少包含 `G_ACCOUNTING_SCOPE`、`G_PERIOD_UNIT` 和 `G_ADJUSTMENT_BRIDGE`，分别定位会计准则/合并范围/审计重述、期间/时点/币种单位，以及政府补助/其他营业收入/折旧研发/IFRS-CAS 调节。两类命中都可进入候选上下文，但分别验收；护栏命中不得被解释为 D1-D7 的支持证据。

BM25 使用仓库内固定版本的中英混合分词器。索引文本执行 Unicode NFKC、英文小写化以及空白/标点规整，但不得改写权威片段原文或原文哈希；中文先按版本化投研词表最长匹配，未匹配汉字段使用重叠二元字组；英文按单词和数字切分，复合词同时保留整体和组成部分。分词器固定保留 IFRS、CAS、USD、R&D、EBITDA、晶圆尺寸和制程节点等领域符号，并把 `4Q25`、`Q4 2025`、`2025 Q4` 等明确期间写法增加为同一规范期间 token。停用词表固定版本；同义表达只能通过显式子查询处理。检索记录必须保存分词器/词表版本及每个子查询的实际 tokens。

每个固定子查询定义显式 `anchor_tokens`；片段至少命中一个锚点且 BM25 分数大于 0 才参与候选截断。每个子查询选择全局 Top 20，且同一材料最多保留 5 个直接命中；第 20 名同分时保留全部同分片段，但单材料上限仍生效。排序固定为 `score desc, chunk_id asc`。不得设置跨查询通用的绝对 BM25 分数阈值，也不得比较不同子查询的原始分数。截断参数的任何修改必须由固定验收集上的漏召回结果支持，并更新检索规则版本和产物哈希。

候选过滤只能识别结构性噪声，例如导航、Cookie/登录提示、广告/订阅/投资 CTA、站点页脚、联系方式和重复页眉页脚。此类片段及其检索命中仍保留在 `context.jsonl` 和检索记录中，但固定为 `candidate_context=false` 并记录 `filter_reason=STRUCTURAL_BOILERPLATE`；不得静默删除。`AI Summary` 等来源页面的实质栏目不属于结构噪声，可以被召回，但必须保留栏目身份且不得与 transcript 混合。过滤不得使用信源等级、内容类型、可信度、观点方向或证据资格。

直接命中标记 `DIRECT_HIT`；其前后各一个同材料、同栏目结构相邻片段标记 `ADJACENT_CONTEXT` 并进入候选上下文。扩展不得跨材料或栏目边界；自包含表格不做相邻扩展。直接命中、结构过滤命中和相邻扩展都必须保留来源 `query_id` 与选择原因。

RAG 使用与 `snapshot_id` 和查询规则版本绑定的 locator 级固定验收集。标注分为：`MUST_HIT`（承重数字、关键机制或规整前提，漏召回构成硬失败）、`SHOULD_HIT`（补充相关片段，用于量化已知漏召回）和 `NEGATIVE_CONTROL`（结构噪声，命中后仍不得成为候选上下文）。每条至少记录 `query_family_id`、`material_id`、预期 Content Locator、标注等级和相关性理由。标注只判断查询是否应找到该位置，不判断真实性、信源等级、内容类型或证据资格；快照或查询规则变化时生成新版本，不得在看到运行结果后静默修改预期。

RAG 验收只以未被结构过滤的 `DIRECT_HIT` 计数。每个子查询分别执行已确认的 Top 20 截断，再按 `chunk_id` 合并为 Query Family 结果；Family 不做第二次 Top 20 截断。同一片段命中多个子查询时只计一次召回，并保留全部 `matched_query_ids`。`MUST_HIT Recall` 必须为 100%；`SHOULD_HIT Recall` 总体至少为 80%，且任一有标注的 Query Family 不得低于 60%。

Precision 按每个子查询的 `Precision@min(5,N)` 计算，其中 `N` 是该子查询返回的合格直接命中数；前 `min(5,N)` 条必须全部完成人工主题相关性标注，`N=0` 时 Precision 为 0。每个子查询的 Precision 必须至少为 60%。此处相关性不判断真实性、信源等级、内容类型或证据资格。

`NEGATIVE_CONTROL` 成为候选上下文的比例必须为 0；`MUST_HIT` 的 Material/Content Locator 准确率必须为 100%；数字类 `MUST_HIT` 必须完整保留表头、单位、期间和相关脚注；同一快照、代码和规则版本的两次干净重建必须产生相同的 `context.jsonl` 与检索结果哈希。这些指标是 Ticket 03 的 RAG 验收门槛，不是发布门禁。

RAG 核验输出独立的 `retrieval_status: PASS | WARN | FAIL`。该状态只评价固定查询、召回、过滤、定位和可复现性，不评价事实正确性、信源等级、内容类型、证据充分性或报告资格；`PASS` 结果仍只是候选上下文，不能成为治理证据或发布依据。

- `PASS`：全部 RAG 验收指标达标，可进入事实规整并满足 Ticket 03 的 RAG 验收条件。
- `WARN`：所有硬条件通过，但 `SHOULD_HIT Recall` 或 Precision 未达目标；允许继续规整以检查影响，必须把漏召回写入检索结果和 `gaps.yaml`，Ticket 03 不自动验收通过，也不自动引入 Embedding。
- `FAIL`：关键召回、负控、定位、数字解释要素或确定性任一硬条件失败。快照/哈希/确定性/普遍定位等全局故障阻断全部规整；可明确限定到 Query Family 的局部故障只阻断受影响候选，不影响其他合格候选继续规整并记录 gap；无法可靠界定影响范围时按全局故障处理。失败仍输出诊断用上下文和检索核验结果。

Embedding/混合检索只在 BM25 为 `WARN` 且实验前已登记具体词法漏召回时允许做一次同集对比。实验结果分为：`ADOPTED`（将 WARN 转为 PASS，所有硬指标不退化，可进入 Demo）、`IMPROVED_NOT_ADOPTED`（恢复至少一个预登记 `SHOULD_HIT` 或改善对应 Family Recall，硬指标不退化但整体仍为 WARN，只保存实验记录）和 `REJECTED`（未恢复目标漏召回或任一硬指标退化）。BM25 为 PASS 时不实验；BM25 为 FAIL 时先修复分块、查询、词表或定位。未达到 `ADOPTED` 的实验不得改变候选选择规则或增加运行依赖。

### `normalized-facts.jsonl`

一行一个原子规整事实。记录结构只能是 `NUMERIC_OBSERVATION`、`TEXT_PROPOSITION` 或 `DERIVATION`：数值表格中每个主体、指标、期间/时点和口径组合单独生成 `fact_id`；一句原文包含多个数值或一个数值与归因命题时分别拆行；派生记录新建 `fact_id` 并引用全部输入，不覆盖报告值。同一内容在不同材料或片段中重复披露时分别保留，不在规整阶段合并、投票或去重。`record_kind` 只描述结构，不能替代最终内容分类，所有记录的 `claim_type` 仍为 `UNASSESSED`。

`TEXT_PROPOSITION` 必须保留未删减的 `source_span_text`、说话人或发布主体、栏目、陈述时点以及原文明确的目标期间。拆分不得丢失否定、条件、不确定措辞或适用主体/产品/地域/期间范围；复合句拆成多项时，共同限定条件必须随每项保存并共同引用完整原文跨度。可以另存 `polarity`、`condition_text`、`uncertainty_text`、`applicability_scope` 和非权威的原文措辞提示，但歧义时留空而不推断；无法无损拆分时保留为一个命题。数值观察与解释命题分别建记录并交叉引用，不得把“可能、预计、取决于”等改成确定陈述，也不得把定性词转换为自造数值。

每行至少包含：

- `fact_id`、上游 `chunk_id` 和 `material_id`；
- 指标/声明名称、主体、期间或时点、原始值、原始单位/币种/缩放；
- 规整值、目标单位/币种/缩放、技术转换轨迹；
- 会计准则、合并范围、审计状态、报告类型；
- `claim_type: UNASSESSED`，以及可选且非权威的原文自我描述或候选分类提示；
- 派生公式、输入 `fact_id`、汇率来源（如适用）；
- 可比性状态、规整状态和 gap 引用。

产能、出货、利用率和 ASP 只按当前案例固定指标映射。产能和出货必须保留 `wafer_basis=PHYSICAL_8_INCH|PHYSICAL_12_INCH|EIGHT_INCH_EQUIVALENT|SOURCE_DEFINED_OTHER|UNKNOWN`；实体晶圆和等值晶圆不是可直接缩放的同一单位，只有来源明确给出换算公式时才允许固定派生换算。月产能、期末产能和季度平均产能使用不同 metric/basis 字段，不因标签相似而直接比较。利用率仅保存来源披露值，不用产能与出货反推。

来源披露 ASP 保存为 `NUMERIC_OBSERVATION`；`revenue / shipment` 得到的隐含 ASP 只能新建 `DERIVATION`，且收入和出货的主体、期间、业务范围、币种及晶圆口径必须完全一致。来源 ASP 与隐含 ASP 不覆盖或自动合并。上述规则直接写入固定指标表和少量函数，不建设制造业单位转换器。

制程和应用结构必须保留原始分类标签、`composition_set_id`、`composition_denominator_id`、期间、主体和分类体系版本；收入占比、晶圆收入占比、出货占比和产能占比属于不同分母，不得互换或合计。节点、`28nm及以上`、FinFET 和应用分类只有命中固定显式映射时才可归组，分类体系变化标记 `TAXONOMY_CHANGE`，不建设通用制程分类树。

分类合计核验只对计算前已经由表格标题、结构、脚注或固定案例规则确认 `set_completeness=COMPLETE` 且 `mutual_exclusivity=CONFIRMED` 的同分母集合执行，同时要求主体、期间和统计口径一致，且明细中不混入小计或总计。不得用“合计接近 100%”反向推断完整或互斥。条件不满足时为 `CHECK_NOT_APPLICABLE`，不得产生舍入或公式错误；满足时按各分类披露精度核验 100% 或来源明确总计，容差内为 `ROUNDING_DIFFERENCE`，超出为 `FORMULA_MISMATCH`，但原分类观察仍保留。

资本开支采用不同固定 `metric_id` 区分已发生资本开支、购建资产现金流支出、已承诺未支付金额、管理层计划/指引和具体产能项目投资；它们分别保留而不得自动合并、替代或从计划推断实际发生。Ticket 03 只规整金额、币种、期间、状态和项目归属，不推断资本开支已转化为产能、收入、效率或利润，因果判断留给后续分析。

每条规整记录使用 `normalization_status=PASS|PARTIAL|BLOCKED`。PASS 表示原子内容、定位和该记录类型的必需规整字段完整且转换有效；PARTIAL 表示原始内容和定位可安全保存，但部分规整属性为 UNKNOWN，只能用于不依赖缺失字段的用途；BLOCKED 表示某项映射、比较、转换、派生或桥接无法安全完成，不生成对应结果值，但保留输入、阻断原因和 gap。BLOCKED 不表示来源披露错误。

规整运行另存 `normalization_run_status=PASS|WARN|FAIL`，固定按 `FAIL > WARN > PASS` 汇总。定位链或输入哈希断裂、契约结构非法、重复业务 ID、转换轨迹自相矛盾或两次干净重建不一致为 FAIL；不存在 FAIL，但任一目标记录为 PARTIAL/BLOCKED 或存在未解决规整 gap 时为 WARN；其余为 PASS。该状态只评价规整过程，不复用 `retrieval_status`，也不表示事实正确、证据合格或报告可发布。

局部核验中的 `reconciliation_status=FAIL` 或 `FORMULA_MISMATCH` 不直接升级为运行级 FAIL：它只使对应桥接、结构合计或派生操作变为 BLOCKED，并使规整运行至少为 WARN。只有上述产物完整性或确定性错误才产生 `normalization_run_status=FAIL`，避免同名状态跨层混用。

数值字段必须同时保留原文与确定性机器表达：`raw_value_text` 原样保存；可解析值使用十进制定点字符串并以 Decimal 计算，不得使用 JSON/二进制浮点数。单位、币种和 `scale_factor` 分字段保存。百分比以原显示数值配 `unit=PERCENT` 保存，不静默改为小数比率；百分点使用 `unit=PERCENTAGE_POINT`。明确位于财务数值单元格的括号数可解析为负数，但必须保留原文。不得增加原文未提供的显示精度。

货币金额以 `base_unit_value = raw_numeric_value × raw_scale_factor` 转换到原币基础单位，并保留原币、原缩放和 `reported_precision`。`base_unit_value` 只表示基础单位表达；即使缩放公式是精确乘法，也不表示底层经济金额精确到一个基础单位。后续计算和展示必须携带来源小数位与 `rounding_increment`，不得把缩放后的尾随零解释为更高报告精度，也不得自行推导未披露的真实值区间。

十进制缩放必须是无需舍入的精确转换，并保存 before/after、公式、规则 ID 和 `exact=true`。需要非整除除法或其他不可精确表示的计算属于 `DERIVATION` 或独立单位/币种转换，不得伪装成缩放；必须保存输入、完整公式、Decimal 计算精度、舍入位置、`rounding_mode`、输出小数位、舍入前计算值和最终值。没有已确认舍入规则时不得隐式四舍五入，结果为 UNKNOWN/TBD，且任何舍入不得覆盖原始观察或计算轨迹。

每个数值记录必须有 `value_status`：`PRESENT`、`EXPLICIT_ZERO`、`NOT_APPLICABLE`、`NOT_REPORTED`、`UNPARSEABLE` 或 `UNKNOWN`。只有原文明确为零，或表格图例明确说明破折号代表零且该图例可定位时，才能使用 `EXPLICIT_ZERO`；空白、破折号和 `N/A` 不得自动转为零。不能确定其语义时使用 `UNKNOWN` 并登记 gap。

指标和主体只通过当前案例的固定版本映射表规范化。每条记录保留 `source_metric_label`、`source_entity_label`、`mapping_status=MAPPED|UNMAPPED|AMBIGUOUS` 和命中的 `mapping_rule_id`；只有命中已确认别名及定义时才填写规范 `metric_id`/`entity_id`。映射前只允许为生成匹配键执行 Unicode NFKC、英文大小写统一、首尾/连续空白和等价标点规整，以及匹配显式登记的缩写/别名；原始标签不变。禁止字符串相似度、词干推断、停用词删除、Embedding 或模型语义归并。映射表版本和内容哈希必须写入运行记录。

映射成功不表示可比。可比性评估必须绑定明确 `comparison_basis_id` 或具体输入 `fact_id`，并分别保存 `comparability_status=NOT_ASSESSED|COMPARABLE|COMPARABILITY_BREAK|UNKNOWN` 和固定原因码；不得保存没有比较对象的笼统可比状态。原因至少覆盖主体范围、会计准则、期间类型/长度、币种、单位缩放、审计/版本、指标定义、重述和合并范围变化。`UNMAPPED`、`AMBIGUOUS`、`UNKNOWN` 或 `COMPARABILITY_BREAK` 不得进入对应比较或派生计算，并登记 gap。

期间使用显式解析状态和日期边界。`period_mapping_status` 为 `MAPPED|UNKNOWN|AMBIGUOUS`；只有 MAPPED 时 `period_nature=DURATION|INSTANT` 和 `period_type=FISCAL_YEAR|SINGLE_QUARTER|YEAR_TO_DATE|TTM|CUSTOM_DURATION|INSTANT` 才必须有值。UNKNOWN/AMBIGUOUS 时期间字段可为 `null`，但必须引用 gap，且不得进入期间比较或派生。DURATION 保存 `period_start`/`period_end`，INSTANT 保存 `as_of_date`；不得仅以 `2025Q2` 表示期间。

`fiscal_quarter` 只用于真实单季度；累计期使用 `ytd_through_quarter`。`stated_duration_months` 仅在原文明确或日期组成完整自然月期间时可选填写；起止日期完整时按首尾日期均包含确定性计算 `duration_days`。期间比较以准确日期、期间类型和会计口径为主，不能仅凭月数或天数判断。

材料直接披露的 TTM 保存为 `record_kind=NUMERIC_OBSERVATION`、`period_type=TTM`、`value_origin=SOURCE_REPORTED`；系统以四个可比单季度计算的 TTM 新建 `record_kind=DERIVATION`、`value_origin=SYSTEM_DERIVED` 并引用全部输入 `fact_id`。两者不得覆盖或合并。

累计数相减只允许两个同财政年度、相同起点的 YEAR_TO_DATE 期间数生成一个完整财政单季度，且 metric/entity、会计准则、合并范围、币种、单位、指标定义、审计/复核状态、报告版本和重述基础完全一致，输入均绑定同一比较基准并为 COMPARABLE。完整季度按当前中芯国际黄金案例的固定自然年度季度边界验证，不建设通用财政日历引擎；实际出现特殊报告期时降级为 AMBIGUOUS/gap。

成功结果新建 `record_kind=DERIVATION`、`value_origin=SYSTEM_DERIVED`、`derivation_type=YTD_DIFFERENCE`，引用两个输入并保存公式，输出 audit status 为 OUTSIDE_AUDIT_SCOPE，不得覆盖报告值或机械年化。输入精度影响使用 `input_precision_effect=ROUNDED|UNROUNDED|UNKNOWN`：任一输入明确为缩放/舍入披露值时为 ROUNDED；只有两者均明确未舍入时为 UNROUNDED；否则为 UNKNOWN。ROUNDED 时输出精度不得高于较粗输入；UNKNOWN 仍只能表达“披露值之差”，不得声称更高经济精度。任一条件失败时保留 `derivation_status=BLOCKED`、COMPARABILITY_BREAK、原因码和 gap，不生成数值。

系统派生只允许当前黄金案例固定白名单：`YTD_DIFFERENCE`、`TTM_SUM`、`GROSS_MARGIN`、`OPERATING_MARGIN`、`OPERATING_CASH_FLOW_MARGIN`、`PERIOD_CHANGE_PERCENT`、`MARGIN_CHANGE_PP`、当前不可用的 `CURRENCY_CONVERSION`，以及之后按正式规则变更流程加入的具体调整桥接公式。每项直接实现为固定函数和 `derivation_rule_id`，不建设公式 DSL，不接受运行时自由公式，并覆盖正常、缺失、不可比和边界 fixtures。

所有派生输入先通过指标、主体、期间、准则、范围、币种、单位、定义和版本可比检查；来源披露值与系统复算值分别保留，派生不得覆盖来源。分母缺失或为零时阻断。`PERIOD_CHANGE_PERCENT` 只在正基期且无符号变化时生成；基期为零、负数或前后符号变化分别以 `BLOCKED_ZERO_DENOMINATOR`、`BLOCKED_NON_POSITIVE_BASE`、`BLOCKED_SIGN_CHANGE` 阻断，只保留绝对变化和原因。来源直接披露的此类变化率仍作为 SOURCE_REPORTED 保存，但不得自动表述为增长或下降。

`TTM_SUM` 必须由四个不同、连续、互不重叠的 SINGLE_QUARTER 输入组成，日期无缺口覆盖连续十二个月，且全部会计与技术口径可比；禁止累计期相加、重复季度或缺季度。任何新增调整桥接公式必须在运行前显式加入白名单、分配固定规则 ID、更新规则版本/哈希并补齐 fixtures，不能以“后续调整”作为开放入口。

IFRS/CAS 桥接只实现一个固定方向 `CAS_TO_IFRS`，公式为 `IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL)`；不接受运行时反向复算。每行必须标记 `row_role=BASE|ADJUSTMENT_DETAIL|SUBTOTAL|TARGET`，只有 `ADJUSTMENT_DETAIL` 进入求和，`SUBTOTAL` 和 `TARGET` 只用于定位与核验，防止明细、小计和总计重复计入。调整行同时保留来源显示符号、`bridge_operation=ADD|SUBTRACT` 和已经规范为目标方向的 `normalized_signed_amount`；固定公式只使用该带符号金额一次，ADD 对应正值、SUBTRACT 对应负值，不再叠加解释来源符号。

桥接只在基础值、全部调整明细和目标值的 `metric_id`/指标定义、权益归属（包括 `OWNERS_OF_PARENT` 与 `TOTAL_GROUP`）、主体及合并范围、会计准则角色、币种、单位缩放、报告版本和重述基础均明确匹配时执行。流量指标必须具有完全相同的 `period_start`、`period_end`、`period_type` 和期间长度；时点指标必须具有完全相同的 `as_of_date`，两类不得混接。缺失或不匹配时桥接为 UNKNOWN/不可用并登记 gap，不建设自动近似匹配。

复算差异为 `recomputed_ifrs_target - source_reported_ifrs_target`。差异恰为零时 `reconciliation_status=PASS`；非零时容差固定为 `0.5 × (CAS 基础值、全部调整明细及 IFRS 目标值的 rounding_increment 之和)`，绝对差异不超过容差时为 `WARN/ROUNDING_DIFFERENCE`，超过容差时为 `FAIL/FORMULA_MISMATCH`。若任一必要披露精度缺失，则只有差异恰为零可 PASS；非零差异一律为 UNKNOWN/不可用，不猜测容差。

复算结果只作为 IFRS 目标记录中的 `reconciliation_check` 元数据，保存方向、规则 ID、输入 `fact_id`、各行角色/操作、公式、复算值、披露目标值、差异、容差和状态；不得新建来源事实或覆盖报告值。`FORMULA_MISMATCH` 只使该桥接无效并生成 gap，CAS 基础值、调整项和 IFRS 目标值的原子记录全部保留。当前案例直接实现上述一个函数及正常、舍入差异、重复小计、口径不匹配和公式不匹配 fixtures，不建设通用 reconciliation engine。

政府资金调整只生成与报告 IFRS 主口径并列的敏感性，不覆盖报告值。只有政府资金确认金额可分离、可追溯，且与报告 `profit from operations`/revenue 的期间、主体、准则、合并范围和币种一致并能证明已计入该营业利润时，才允许固定公式 `SENSITIVITY_EX_GOVERNMENT_FUNDING = reported profit from operations - included government funding` 及相应利润率。输出必须展示报告值、调整项、敏感性值及全部输入 `fact_id`，不得称为公司报告值或自动标为一次性/非经常性。

可调整政府资金严格限定为目标期间内已确认为损益、能够单独计量，并有明确依据证明进入同口径 `profit from operations` 的金额。仅收到但未计入损益的现金、资本/权益投入、资产补助余额、尚未摊销的递延收益、仅影响资产账面价值的补助、计入所得税而非营业利润的税收优惠、计入位置未知或已由其他调整剔除的金额均不得调整；递延收益只允许使用明确计入当期基础营业利润的释放额。

只有定性说明而无可分离金额时保留 TEXT_PROPOSITION，敏感性数值为 UNKNOWN。不得以全部 `other operating income` 代替政府资金，也不得把 CAS 非经常性损益表的政府补助直接从 IFRS 营业利润扣除；除非存在同期间、同范围、同币种且可追溯的 IFRS/CAS 桥接。折旧和研发不参与该调整。输出固定称为“政府资金剔除敏感性营业利润/率”，不得称为真实、正常或唯一规整利润。

Ticket 03 初始调整白名单只包含上述政府资金敏感性。资产处置、减值、汇兑、股权交易、启动成本、股份支付、其他营业收入和 CAS 非经常性项目可以抽取，但不得自动调整 IFRS 营业利润。其他候选项只保留观察/命题并创建 `ADJUSTMENT_TBD` gap，原因码限定为 `NOT_PROVEN_IN_BASE_METRIC`、`AMOUNT_NOT_SEPARABLE`、`CASH_VS_PNL_MISMATCH`、`PERIOD_OR_SCOPE_MISMATCH`、`DIRECTION_UNCONFIRMED`、`DUPLICATION_RISK`、`CAPITAL_OR_BALANCE_SHEET_ITEM`、`AWAITING_USER_CONFIRMATION`。用户确认且满足可分离、可重算、计入基础指标后，仍须正式加入白名单、分配规则 ID、换版并增加 fixtures；不建设动态调整或审批框架。

数值来源和换汇状态分别保存。`value_origin` 仅为 `SOURCE_REPORTED|SYSTEM_DERIVED`；来源直接披露的任何币种都是 SOURCE_REPORTED。`currency_conversion_status` 仅为 `NOT_REQUIRED|COMPLETED|UNAVAILABLE`。系统换汇必须新建 `record_kind=DERIVATION`、`value_origin=SYSTEM_DERIVED`、`currency_conversion_status=COMPLETED` 的记录，引用原始 `fact_id`、冻结汇率来源/事实、汇率类型、日期、公式和舍入规则，不得把目标币种值写回原观察。

只有明确的跨币种计算需求才触发换汇检查；无需求时为 NOT_REQUIRED。需要换汇但当前冻结快照没有合格汇率时为 UNAVAILABLE，生成 gap 且不生成派生值。当前 v3 不包含独立汇率材料，禁止运行时联网、模型常识、报告发布日期汇率或一条汇率覆盖多个期间。未完成转换的不同币种记录不得跨币种加总、相减、计算比率或利润率，应对该比较标记 `COMPARABILITY_BREAK/CURRENCY_MISMATCH`。CNY 和 USD 观察可分别保留并在各自币种口径内处理，但 CAS 仍只用于调节和差异解释，不形成第二套主分析结论。

会计准则、币种、合并范围和审计状态必须逐字段独立解析、继承和降级，不能作为一组打包继承。每个字段分别保存 value、source level、来源 locator/`chunk_id` 和 rule ID；局部表格/单元格说明优先于章节，章节优先于明确适用的文档级说明，无依据时该字段单独为 UNKNOWN。一个字段已知不得带动其他字段取值；冲突无法确定适用范围时该字段为 AMBIGUOUS 并登记 gap。实现只需四个固定字段的直接查找规则，不建设通用元数据继承框架。

`audit_status` 仅为 `AUDITED|REVIEWED|UNAUDITED|OUTSIDE_AUDIT_SCOPE|UNKNOWN`。AUDITED 只可继承到审计意见明确覆盖的财务报表及附注；年报中的管理层讨论、经营 KPI、演示数据或其他补充信息不得因位于已审计年报而自动成为 AUDITED。明确位于审计范围之外时使用 OUTSIDE_AUDIT_SCOPE；无法确认覆盖范围时使用 UNKNOWN；UNAUDITED 只在适用文档或章节明确声明时使用。

同一期间和口径的版本选择只认发行人在 `as_of` 前明确标注的 restated/re-presented/重述/重新列报关系。每项相关记录保存 `report_version_id`、`restatement_status=ORIGINAL|RESTATED|UNRESOLVED`、可选 `restates_fact_id` 和 `comparison_preferred`；只有重述对象的期间、指标、主体和范围可以确定时才能建立 `restates_fact_id`。明确重述值可作为会计比较优先版本，但原始披露不得覆盖、合并或删除，且该优先状态不代表 Ticket 04 的证据资格。

同一目标发生多次明确重述时，`as_of` 前发布时间最新的明确重述值为比较优先版本，并保留各版本及其直接关系。若数值不同但材料未明确说明重述或重新列报关系，则全部记录标记 `restatement_status=UNRESOLVED`，比较产生 `VERSION_CONFLICT` 和 gap，不得仅凭数值差异、发布日期或模型判断自动选值。当前案例只实现上述固定字段和选择函数，不建设通用版本图或重述引擎。

### `governed-evidence.jsonl`

一行一项治理证据。至少包含：`evidence_id`、`fact_id`、最终 `source_tier`、最终 `claim_type`、使用状态、材料与内容定位、同源组、冲突组、冲突处置、可支持用途、隔离原因和 gap 引用。该阶段统一拥有真实性/可信度核验、T1–T4、内容类型、同源、冲突、隔离和证据资格判断。原始材料缺失或无法建立内容定位的记录不能成为可用证据，也不能以 T4 代替。

### `validation.yaml`

确定性核验汇总。至少包含：契约完整性、哈希、`as_of`、定位、单位/币种/期间、派生公式、冲突、隔离、RAG 定位检查的通过/警告/失败明细，以及总状态 `PASS`、`WARN` 或 `FAIL`。FAIL 不阻止内部诊断报告生成，但失败数据不能支撑发现。

### `findings.yaml`

按 D1-D7 保存发现。每项至少包含：`finding_id`、维度、命题、`finding`、`evidence_score`、支持/反驳 `evidence_id`、推理说明、替代解释、限制、gap 引用和修订版本。

本 Demo 每个维度恰有一项发现，因此 `finding_id` 即 `dimension_id`，不另设重复标识；修订版本另存 `findings-revised.yaml`，原始 `findings.yaml` 保持不变。

允许的 `finding`：`SUPPORTED`、`MIXED`、`NOT_SUPPORTED`、`UNKNOWN`。允许的 `evidence_score`：`0`（UNSCORABLE）、`1`（LIMITED）、`2`（ADEQUATE）、`3`（STRONG）。分数表示证据强度，不表示公司质量或投资吸引力；分数 0 必须对应 UNKNOWN，反向不成立。分数由脚本从被选中的证据反算，模型不产出分数；`overall_score` 是脚本写入的常量 `NOT_APPLICABLE`。

### `analysis-inputs.jsonl`

分析阶段的确定性产物：首条 `SELECTION_SUMMARY` 记录每维的候选/选中 chunk 数、字符数、同源组数、最低选中分和因预算停止的 chunk；其后是逐条 `CANDIDATE_CHUNK` 与 `CANDIDATE_EVIDENCE`。它是该维分析的封闭证据集，模型 prompt 由脚本从中拼装，发现不得引用其外的任何 `evidence_id`。

### `analysis-attempts.jsonl` 与 `analysis-validation.yaml`

`analysis-attempts.jsonl` 保存每个维度每次模型输出的全文与校验错误（每维最多两次）。`analysis-validation.yaml` 给出 12 项具名校验的 PASS/WARN/FAIL、被拒绝尝试摘要和 `analysis_run_status`。由于判断层是模型调用，本阶段不承诺逐字重建；保证来自校验通过与全过程留痕。

### `challenges.yaml`

保存最多两轮质询。每项至少包含：`challenge_id`、轮次、质询类型、目标 `finding_id`/`evidence_id`、问题、允许复核范围、答复、处置、修订前后引用和未解决影响。处置只能是 `RESOLVED_NO_CHANGE`、`RESOLVED_WITH_REVISION`、`UNRESOLVED_DOWNGRADED`、`BLOCKING`。

每项由脚本写入 `review_count: 1`（每个问题只做一次定向复核），并在两轮后按固定触发清单决定降级还是 `BLOCKING`；不设与 `BLOCKING` 语义重叠的 `severity` 轴。该文件同时保存对修订后发现重跑的全部分析校验。

### `gaps.yaml`

案例执行期唯一缺口登记册。每项至少包含：`gap_id`、`origin_stage`、`gap_kind`、问题、影响对象、当前处理、确认人、所需证据、优先级和状态。采集缺口只描述搜索、材料可得性、候选确认或内容提取，不得直接声明事实 UNKNOWN 或证据不足；事实 UNKNOWN/TBD 和证据缺口由后续阶段产生。它不承担长期任务管理，也不替代产品开放问题文档。

### `report.md`

内部 Demo 报告。固定章节、数字引用和禁止输出见冻结 Spec。每个数值必须能反查至 `evidence_id` 或明确标记为被隔离/UNKNOWN；来源观点必须显示 `claim_type`。

### `manifest.yaml`

本次黄金案例产物清单。至少包含：使用的 `snapshot_id`、规则版本、每个权威文件的路径与哈希、生成时间、`governance_status`、`distribution_status: INTERNAL_DEMO_ONLY`、人工复核状态和工具版本摘要。它不是通用 Run 对象。

## Skill 输入输出

| 顺序 | Skill | 读取 | 写入 |
|---|---|---|---|
| 1 | `acquire-research-materials` | `case.yaml`、来源、人工材料和候选线索 | 自包含快照、`snapshot-manifest.yaml`、`materials.jsonl`、采集缺口；候选暂存记录留在快照外 |
| 2 | `govern-research-context` | `case.yaml`、快照与可提取待治理材料 | `context.jsonl`、RAG 检索核验结果、缺口 |
| 3 | `normalize-research-facts` | 上下文、会计规则 | `normalized-facts.jsonl`、缺口 |
| 4 | `govern-and-validate-research-evidence` | 材料、规整事实、信源与冲突规则 | `governed-evidence.jsonl`、`validation.yaml`、缺口 |
| 5 | `analyze-and-score-research-findings` | 可用治理证据、上下文、分析规则 | `analysis-inputs.jsonl`、`findings.yaml`、`analysis-attempts.jsonl`、`analysis-validation.yaml`、缺口 |
| 6 | `challenge-research-findings` | 证据、发现、分析规则 | `challenges.yaml`、`findings-revised.yaml`、缺口，向编排器返回需复核目标 |
| 7 | `generate-research-report` | 所有权威产物、报告规则 | `report.md`、`manifest.yaml` |
| 编排 | `single-stock-research-orchestrator` | `case.yaml` 和阶段状态 | 固定顺序、停止/降级决策、最多两轮定向回路 |

## 单一规则来源

实现时只建立一份权威规则定义，建议固定为：

```text
rules/
  accounting.yaml
  context-retrieval.yaml
  source-governance.yaml
  analysis.yaml
  report.yaml
```

`analysis.yaml` 同时承载评分、承重指标白名单、禁止输出词表和质询回路参数：本 Demo 的分析与质询共用一套冻结常量，拆成两份规则文件只会制造需要同步的两处真相。

Skills 只引用规则版本和解释执行职责，不复制完整规则正文。配套脚本集中放在项目级 `scripts/`，不随各 Skill 复制，也不建设 SDK、插件接口或动态规则引擎。

## 轻量 RAG 契约

关键词/BM25 是必需基线；Embedding/混合检索仅为可选实验。索引只读取可提取且目标相关的待治理材料，是可删除、可由 `context.jsonl` 与冻结材料重建的本地派生物，不进入权威产物。检索验证至少记录查询、命中 `chunk_id`、内容定位是否正确和已知漏召回；检索分数不得转化为证据强度或来源可信度。
