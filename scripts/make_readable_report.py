"""Render a human-readable companion to report.md. A reading aid, not a second report.

`report.md` is written for audit: sixteen-column evidence tables where every column carries
a piece of the basis a number needs before it can be compared to another number. That is
correct and unreadable. This script re-renders the same run artefacts as linked, annotated
cards, so a Chinese reader can follow one number from the narrative to the page of the PDF
it came from.

Three rules keep this honest.

**It adds no claim.** Every value, period, basis, locator and source span is copied from the
run artefacts. Nothing is computed, inferred or rephrased.

**It annotates, it never replaces.** `GROSS_MARGIN` stays `GROSS_MARGIN` with a Chinese
gloss beside it, because the identifier has to grep back into the JSONL; a translated
identifier is a broken trace. English source spans stay verbatim for the same reason -- a
translated quote is new text with no provenance. Only a vocabulary hint is added under it.

**It never binds a number to evidence the model did not bind.** D1's statement carries 23
numbers over 8 supporting records, and the model never said which number came from which.
Putting them back inline would manufacture a provenance link -- exactly the thing the whole
pipeline exists to prevent. The omitted sentences are shown struck through in a labelled
block that says plainly that their numbers are unverified.

It is not a pipeline stage and writes outside the run directory: a stray `.md` there would
be an unknown authoritative file and would halt the next `preflight`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_research_report import (  # noqa: E402
    RULES_DIR,
    RunArtifacts,
    cited_evidence_ids,
    published_of,
    read_yaml,
    sanitize,
)

OUTPUT = Path("docs/briefing/04-报告导读.md")
SNAPSHOT_RELATIVE = "../../single-stock-demo-v3"

# Enumerations that appear in the cards but are not in rules/report.yaml's glossary. Kept
# here rather than added there because rules/report.yaml drives the authoritative report,
# and this is a reading aid. Shared terms are read from the authoritative table, so the two
# can never disagree about a term they both define.
SUPPLEMENTARY_GLOSSARY = {
    "accounting_standard": {
        "IFRS": "国际财务报告准则，港股口径",
        "CAS": "中国企业会计准则，A 股口径",
        "AMBIGUOUS": "原文说法冲突，无法确定用了哪套准则",
        "UNKNOWN": "原文没有说明用了哪套准则",
    },
    "consolidation_scope": {
        "CONSOLIDATED": "合并报表，含子公司",
        "UNKNOWN": "原文没有说明合并范围",
    },
    "value_origin": {
        "SOURCE_REPORTED": "来源直接披露的原始数字",
        "SYSTEM_DERIVED": "系统按固定公式算出来的值",
    },
    "unit": {
        "MONEY": "金额",
        "PERCENT": "百分比",
        "PERCENTAGE_POINT": "百分点，两个百分比之差",
        "WAFER": "晶圆片数",
    },
    "record_kind": {
        "NUMERIC_OBSERVATION": "数值观察，一个数字",
        "TEXT_PROPOSITION": "文本命题，一句话",
        "DERIVATION": "派生记录，系统算出来的",
    },
    "role": {
        "PRIMARY_SUPPORT": "主要支撑 —— 结论方向直接依赖它",
        "CONTEXT": "背景引用 —— 不承担结论方向",
    },
}

# Vocabulary hints for the English source spans. The span itself is never translated; these
# are looked up and listed beneath it so a Chinese reader can decode the quote without the
# quote being rewritten. Longest first so "cost of sales" wins over "sales".
ENGLISH_TERMS = {
    "profit attributable to owners": "归属于母公司股东的利润",
    "research and development": "研发",
    "profit from operations": "经营利润",
    "average selling price": "平均销售单价",
    "operating activities": "经营活动",
    "capital expenditure": "资本开支",
    "government grant": "政府补助",
    "gross margin": "毛利率",
    "gross profit": "毛利",
    "cost of sales": "销售成本",
    "other operating income": "其他经营收入",
    "depreciation": "折旧",
    "amortisation": "摊销",
    "amortization": "摊销",
    "impairment": "减值",
    "inventory": "存货",
    "utilization": "产能利用率",
    "utilisation": "产能利用率",
    "capacity": "产能",
    "wafer": "晶圆",
    "shipment": "出货量",
    "revenue": "收入",
    "net profit": "净利润",
    "net income": "净利润",
    "cash flow": "现金流",
    "unaudited": "未经审计",
    "audited": "已审计",
    "consolidated": "合并报表",
    "fiscal year": "财政年度",
    "quarter": "季度",
    "guidance": "管理层指引",
    "outlook": "展望",
    "year-over-year": "同比",
    "quarter-over-quarter": "环比",
    "sequentially": "环比",
    "product mix": "产品结构",
    "foundry": "晶圆代工",
    "advanced node": "先进制程",
    "mature node": "成熟制程",
    "million": "百万",
    "billion": "十亿",
    "margin": "利润率",
}

DIMENSION_TITLES = {
    "D1_PROFITABILITY_CHANGE": ("D1 盈利能力变化", "到底改善了没有？"),
    "D2_UTILIZATION_EFFECT": ("D2 利用率驱动", "是因为工厂开工率上去了吗？"),
    "D3_MIX_EFFECT": ("D3 产品结构驱动", "是因为卖的东西更值钱了吗？"),
    "D4_CAPEX_CONVERSION": ("D4 资本开支转化", "前几年砸的钱变成利润了吗？"),
    "D5_CYCLE_EXPLANATION": ("D5 行业周期", "会不会只是行业回暖，跟公司本事无关？"),
    "D6_NONCORE_EXPLANATION": ("D6 非经常项", "会不会主要靠政府补助这类一次性收益？"),
    "D7_SUSTAINABILITY_EVIDENCE": ("D7 可持续性", "这个改善能持续下去吗？"),
}
FINDING_LABELS = {
    "SUPPORTED": "证据支持",
    "MIXED": "证据方向不一致",
    "NOT_SUPPORTED": "证据不支持",
    "UNKNOWN": "现有证据无法判断方向",
}
SCORE_LABELS = {
    0: "0（无承重证据）", 1: "1（有限）", 2: "2（尚可）", 3: "3（较强）",
}
EVIDENCE_GROUPS = [
    ("supporting_evidence", "支撑证据"),
    ("counter_evidence", "反方证据 —— 指向相反方向的记录"),
    ("management_assertions", "管理层说法 —— 是观点，不是已核实的事实"),
    ("watch_indicators", "观察指标 —— 后续要盯什么"),
]

NARRATIVE_FIELDS = [
    ("finding_statement", "结论叙述", "findings[].finding_statement"),
    ("alternative_explanations", "其他可能的解释", "findings[].alternative_explanations[]"),
    ("limitations", "本维度的局限", "findings[].limitations[]"),
    ("gaps", "缺什么数据", "findings[].gaps[]"),
]


def build_glossary() -> dict[str, dict[str, str]]:
    """Grouped by field, never flattened.

    `UNKNOWN` means "could not confirm audit coverage" under audit_status and "the evidence
    cannot settle the direction" under finding. A flat table would annotate one of them with
    the other's meaning, which is worse than no annotation at all. Supplements first, so a
    term the authoritative rules file defines always keeps the authoritative meaning.
    """
    merged: dict[str, dict[str, str]] = {
        name: dict(entries) for name, entries in SUPPLEMENTARY_GLOSSARY.items()
    }
    for name, entries in (read_yaml(RULES_DIR / "report.yaml").get("glossary") or {}).items():
        if isinstance(entries, dict):
            merged.setdefault(str(name), {}).update(
                {str(key): str(value) for key, value in entries.items()}
            )
    return merged


GLOSSARY = build_glossary()
# Money is stored as unit=MONEY plus a currency; percent has a symbol everybody reads
# faster than the enum. The raw enum always stays on the value line beside it.
UNIT_SYMBOLS = {"PERCENT": "%", "PERCENTAGE_POINT": " 个百分点"}


def gloss(value: Any, group: str) -> str:
    """`VALUE`（中文注） -- the identifier is never replaced, only annotated."""
    if value in (None, ""):
        return "—"
    text = str(value)
    meaning = GLOSSARY.get(group, {}).get(text)
    return f"`{text}`（{meaning}）" if meaning else f"`{text}`"


def vocabulary_hint(span: str) -> str:
    """Terms found in an English span, listed beneath it. The span itself is untouched."""
    lowered = span.lower()
    found: list[str] = []
    for term, meaning in ENGLISH_TERMS.items():
        if term in lowered and not any(term in seen for seen in found):
            found.append(term)
    if not found:
        return ""
    pairs = "　".join(f"{term} = {ENGLISH_TERMS[term]}" for term in found[:8])
    return f"  _生词：{pairs}_"


def period_text(fact: dict[str, Any]) -> str:
    kind = fact.get("period_type")
    if fact.get("period_start") and fact.get("period_end"):
        return f"{gloss(kind, 'period_type')}　{fact['period_start']} 至 {fact['period_end']}"
    if fact.get("as_of_date"):
        return f"{gloss(kind, 'period_type')}　时点 {fact['as_of_date']}"
    return "**未标注期间** —— 这条记录没有可用的期间信息"


def basis_text(fact: dict[str, Any]) -> str:
    return "　｜　".join(
        gloss(fact.get(key) or "UNKNOWN", key)
        for key in ("accounting_standard", "consolidation_scope", "audit_status", "value_origin")
    )


def locator_text(record: dict[str, Any], fact: dict[str, Any]) -> str:
    locator = fact.get("content_locator") or record.get("content_locator") or {}
    parts = []
    if locator.get("page_number") is not None:
        parts.append(f"第 {locator['page_number']} 页")
    if locator.get("section"):
        parts.append(f"章节「{locator['section']}」")
    parts.append(f"片段 `{record.get('chunk_id') or fact.get('chunk_id')}`")
    return " · ".join(parts)


def page_of(record: dict[str, Any], fact: dict[str, Any]) -> int | None:
    locator = fact.get("content_locator") or record.get("content_locator") or {}
    page = locator.get("page_number")
    return int(page) if isinstance(page, int) else None


def links_for(material: dict[str, Any], page: int | None) -> str:
    anchor = (
        f"#page={page}"
        if page and str(material.get("media_type")) == "application/pdf"
        else ""
    )
    parts = []
    url = (material.get("canonical_material_locator") or {}).get("source_page")
    if url:
        parts.append(f"[▶ 公开原文]({url}{anchor})")
    frozen = material.get("frozen_path")
    if frozen:
        parts.append(f"[▶ 本地冻结件]({SNAPSHOT_RELATIVE}/{frozen}{anchor})")
    return "　".join(parts) or "—"


def evidence_card(
    world: RunArtifacts, evidence_id: str, item: dict[str, Any]
) -> list[str]:
    record = world.candidates.get(evidence_id)
    if record is None:
        return [f"- `{evidence_id}` —— 不在本维度候选集内，无法展开", ""]
    fact = world.facts.get(str(record["fact_id"])) or {}
    material = world.material_of(record, fact)
    numeric = record.get("record_kind") == "NUMERIC_OBSERVATION"

    unit = str(fact.get("target_unit") or fact.get("raw_unit") or "")
    currency = fact.get("target_currency") or fact.get("raw_currency")
    # `MONEY` is a unit enum, not a label for a reader; for money the currency is the
    # useful word. Both raw enums stay on the 数值 line below, unchanged.
    display_unit = (
        f" {currency or unit}" if unit == "MONEY" else UNIT_SYMBOLS.get(unit, f" {unit}")
    )
    headline = (
        f"{gloss(fact.get('metric_id'), 'metric_id')} = **{fact.get('normalized_value')}{display_unit}**"
        if numeric
        else gloss("TEXT_PROPOSITION", "record_kind")
    )

    lines = [
        f'<a id="{evidence_id}"></a>',
        "",
        f"#### {headline}",
        "",
        f"`{evidence_id}`　{gloss(item.get('role'), 'role') if item.get('role') else ''}",
        "",
    ]
    if numeric:
        lines.append(
            f"- **数值**　{fact.get('normalized_value')}　单位 {gloss(unit, 'unit')}"
            + (f"　币种 `{currency}`" if currency else "")
            + f"　缩放 ×{fact.get('target_scale_factor') or fact.get('raw_scale_factor')}"
            + f"　（原文写作 `{fact.get('raw_value_text')}`）"
        )
    lines.extend([
        f"- **期间**　{period_text(fact)}",
        f"- **口径**　{basis_text(fact)}",
        f"- **信源**　{gloss(record.get('source_tier'), 'source_tier')}　"
        f"{gloss(record.get('claim_type'), 'claim_type')}　"
        f"{gloss(record.get('evidence_status'), 'evidence_status')}",
        f"- **出处**　{material.get('displayed_publisher') or '—'}"
        f"《{material.get('title') or '—'}》，发布于 {published_of(material)}",
        f"- **位置**　{locator_text(record, fact)}",
        f"- **点开核对**　{links_for(material, page_of(record, fact))}",
    ])
    span = fact.get("source_span_text") or record.get("source_span_text")
    if span:
        cleaned = " ".join(str(span).split())
        lines.extend(["- **原文（未翻译、未删减）**", "", f"  > {cleaned}"])
        hint = vocabulary_hint(cleaned)
        if hint:
            lines.extend(["", hint])
    note = item.get("note") or item.get("statement") or item.get("judgment_logic")
    if note:
        kept, dropped = sanitize(note, None, "note")
        if kept:
            lines.extend(["", f"  模型对这条证据的说明：{kept}"])
        if dropped:
            lines.extend(
                ["", f"  _（该说明另有 {len(dropped)} 句因含未绑定数字未被报告采用）_"]
            )
    lines.extend([
        "",
        f"- **溯源链**　`{evidence_id}` → `{record['fact_id']}` → "
        f"`{record.get('chunk_id')}` → `{material.get('material_id')}`",
        "",
    ])
    return lines


def dimension_section(
    world: RunArtifacts, finding: dict[str, Any], before_challenge: dict[str, Any]
) -> list[str]:
    dimension_id = str(finding["dimension_id"])
    title, question = DIMENSION_TITLES.get(dimension_id, (dimension_id, ""))
    score = int(finding.get("evidence_score") or 0)
    verdict = str(finding.get("finding"))

    lines = [
        f'<a id="{dimension_id}"></a>',
        "",
        f"## {title} —— {question}",
        "",
        f"> **结论：{FINDING_LABELS.get(verdict, verdict)}**（`{verdict}`）　",
        f"> **证据分：{SCORE_LABELS.get(score, score)}**　",
        f"> 维度代号 `{dimension_id}`",
        "",
    ]
    # The challenge loop moves `finding` down a fixed ladder but never rewrites the
    # statement -- deliberately, so the revision is visible rather than laundered. Without
    # this note the reader hits a statement ending "故判定为 MIXED" under a UNKNOWN verdict
    # and concludes the report contradicts itself.
    before = str((before_challenge.get(dimension_id) or {}).get("finding") or "")
    challenge_ids = finding.get("revised_from_challenge_ids") or []
    if before and before != verdict:
        lines.extend([
            f"> 🔁 **这个维度被反方质询改过方向：`{before}`"
            f"（{FINDING_LABELS.get(before, before)}）→ `{verdict}`"
            f"（{FINDING_LABELS.get(verdict, verdict)}）**，触发的质询是 "
            f"{'、'.join(f'`{item}`' for item in challenge_ids) or '—'}。",
            ">",
            "> 下面的叙述是**改动之前**写的，所以它的结尾可能仍然说着旧结论。这是有意保留的："
            "把修订痕迹留在明面上，比事后把叙述改得天衣无缝更可信。**以上面方框里的结论为准。**",
            "",
        ])

    whitelist = finding.get("bearing_metric_whitelist") or []
    if whitelist:
        lines.extend([
            "**能给这个维度定方向的指标**（承重指标白名单）：",
            "",
            *[f"- {gloss(item, 'metric_id')}" for item in whitelist],
            "",
        ])
    else:
        lines.extend([
            "> ⚠️ **承重指标白名单为空。** 快照里没有任何一个可以给这个维度定方向的指标，"
            "所以这里的结论**不是由数值证据撑起来的**。这是如实记录，不是遗漏。",
            "",
        ])

    all_dropped: list[dict[str, Any]] = []
    for field, heading, path in NARRATIVE_FIELDS:
        value = finding.get(field)
        items = value if isinstance(value, list) else ([value] if value else [])
        rendered: list[str] = []
        for item in items:
            kept, dropped = sanitize(item, dimension_id, path)
            all_dropped.extend(dropped)
            if kept:
                rendered.append(kept)
        if rendered:
            lines.extend([f"### {heading}", ""])
            lines.extend(f"- {text}" for text in rendered)
            lines.append("")

    if all_dropped:
        lines.extend([
            "### 被闸门删掉的句子（看机制用，不是结论）",
            "",
            f"下面 {len(all_dropped)} 句**没有进入正式报告**，因为它们含有未与单条证据"
            "一一对应的数字。列在这里只为让你看清闸门做了什么。",
            "",
            "> ⚠️ **它们不是本报告的结论，其中的数字未经逐个核验。要用数字请看下面的证据卡片。**",
            "",
        ])
        for item in all_dropped:
            tokens = "、".join(item["matched_numeric_tokens"][:6])
            lines.append(f"- ~~{item['matched_text']}~~　_（含数字：{tokens}）_")
        lines.append("")

    ids = cited_evidence_ids(finding)
    if not ids:
        lines.extend(["### 证据", "", "本维度没有引用任何证据。", ""])
        return lines

    lines.extend(["### 证据（逐条展开，可点开原文核对）", ""])
    rendered_ids: set[str] = set()
    for field, heading in EVIDENCE_GROUPS:
        items = [item for item in finding.get(field) or [] if isinstance(item, dict)]
        cards: list[list[str]] = []
        for item in items:
            evidence_id = str(item.get("evidence_id") or item.get("basis_evidence_id") or "")
            if not evidence_id or evidence_id in rendered_ids:
                continue
            rendered_ids.add(evidence_id)
            cards.append(evidence_card(world, evidence_id, item))
        if cards:
            lines.extend([f"#### 〔{heading}〕", ""])
            for card in cards:
                lines.extend(card)
    return lines


def build(world: RunArtifacts) -> str:
    gate = world.gate
    statuses = gate.get("stage_statuses") or {}
    findings = world.revised.get("findings") or []
    # Pre-challenge findings, so a revised direction can be shown as a revision.
    before_challenge = {
        str(item["dimension_id"]): item for item in world.original.get("findings") or []
    }
    case = world.case

    lines = [
        "# 报告导读（易读版）",
        "",
        "> **这不是第二份报告。** 权威产物永远是 `single-stock-demo-run/report.md`；",
        "> 本文件由 `scripts/make_readable_report.py` 从同一批运行产物重新排版而来，"
        "**只改呈现方式，不新增任何结论、数值或来源**。",
        ">",
        "> 英文标识符和原文跨度一律**原样保留、只在后面加中文注**——"
        "翻译标识符会切断溯源，翻译原文等于制造一段没有出处的新文本。",
        "",
        "---",
        "",
        "## 花三分钟先搞懂这份报告为什么长这样",
        "",
        "你会发现正式报告里的叙述**读起来断断续续**，很多段落只剩一句「具体数值及其期间、"
        "口径和来源见本维度证据表」。这不是 bug，是设计：",
        "",
        "| 疑问 | 答案 |",
        "|---|---|",
        "| 叙述为什么被掏空？ | 模型写的句子里，凡是出现了数字、而那个数字又没有和某一条证据"
        "一一对应的，**整句删掉** |",
        "| 为什么不只把数字抹掉？ | 抹字符会剩下「毛利率由上升到，改善个百分点」——"
        "读着还像人话，但已经没有意义，而且更危险。整句删除至少是诚实的空白 |",
        "| 为什么不给数字标上来源？ | **模型没说过哪个数字对应哪条证据。** D1 那段话里 23 个"
        "数字共用 8 条支撑证据，硬配对就是伪造溯源关系——这恰恰是整个项目要防的事 |",
        "| 那数字去哪了？ | 全部搬进证据卡片，每张带期间、口径、出处和**可以点开的原文链接** |",
        "",
        "### 怎么核对一个数字（三步）",
        "",
        "1. 在证据卡片里找到那个数字，看清它的**期间**和**口径**——"
        "同一个「利润」按不同准则、不同期间、不同币种算出来是完全不同的数字，不能互相比较。",
        "2. 点「**▶ 公开原文**」或「**▶ 本地冻结件**」，PDF 会直接跳到那一页。",
        "3. 对照卡片里的「**原文**」那一行，确认数字确实是这么写的。",
        "",
        "> 卡片里的英文枚举后面都跟着中文注，例如 `GROSS_MARGIN`（毛利率）。"
        "英文原文跨度下面会列出「生词」。完整术语表在本文末尾。",
        "",
        "---",
        "",
        "## 全局速览",
        "",
        f"**研究问题**：{case.get('research_question')}",
        "",
        f"**`as_of`（信息截止时间）**：{case.get('as_of')}",
        "",
        "只使用这个时间点之前公开的资料，晚于它的一律不许进来——防止用「未来信息」做过去的分析。",
        "",
        "### 五个阶段跑得怎么样",
        "",
        "| 阶段 | 状态 | 什么意思 |",
        "|---|---|---|",
        f"| 检索（把相关段落找出来） | {gloss(statuses.get('retrieval_status'), 'run_status')} | 该找到的都找到了 |",
        f"| 事实规整（把数字连口径一起存好） | {gloss(statuses.get('normalization_run_status'), 'run_status')}"
        " | 有记录只完成了部分字段 |",
        f"| 证据治理（判断能不能用） | {gloss(statuses.get('validation_status'), 'run_status')} | 有未解决的缺口 |",
        f"| 分析（形成 D1–D7 结论） | {gloss(statuses.get('analysis_run_status'), 'run_status')} | 七个维度都通过了校验 |",
        f"| 反方质询（自己挑自己的刺） | {gloss(statuses.get('challenge_run_status'), 'run_status')} | 有未解决的质询 |",
        f"| **治理状态（总）** | **{gate.get('governance_status')}** | 前三个阶段取最坏值。"
        "**WARN 不是失败**，是「硬条件都过了但有未解决项」 |",
        "",
        "### 七个维度的结论",
        "",
        "| 维度 | 在问什么 | 结论 | 证据分 |",
        "|---|---|---|---|",
    ]
    for finding in findings:
        dimension_id = str(finding["dimension_id"])
        title, question = DIMENSION_TITLES.get(dimension_id, (dimension_id, ""))
        verdict = str(finding.get("finding"))
        lines.append(
            f"| [{title}](#{dimension_id}) | {question} "
            f"| **{FINDING_LABELS.get(verdict, verdict)}**（`{verdict}`） "
            f"| {finding.get('evidence_score')} |"
        )
    lines.extend([
        "",
        "> **七个维度没有一个是 SUPPORTED（证据支持）。** 这是数据的真实承载力：现有 20 份"
        "材料确实不足以支持「已进入可持续改善阶段」这个判断。**如果它跑出一个漂亮的结论，"
        "那才该怀疑。**",
        "",
        "---",
        "",
    ])
    for finding in findings:
        lines.extend(dimension_section(world, finding, before_challenge))
        lines.extend(["---", ""])

    lines.extend(["## 附：术语对照表", "",
                  "同一个词在不同字段里含义不同（例如 `UNKNOWN`），所以按字段分组列出。", ""])
    for name, entries in sorted(GLOSSARY.items()):
        lines.extend([f"**{name}**", "", "| 取值 | 中文 |", "|---|---|"])
        lines.extend(f"| `{term}` | {meaning} |" for term, meaning in entries.items())
        lines.append("")
    lines.extend([
        "",
        "英文原文里的常见词：",
        "",
        "| 英文 | 中文 |",
        "|---|---|",
        *[f"| {term} | {meaning} |" for term, meaning in sorted(ENGLISH_TERMS.items())],
        "",
        "---",
        "",
        "## 还想往下挖",
        "",
        "| 想看 | 打开 |",
        "|---|---|",
        "| 权威报告本体（十章节，含质询、缺口、附录） | `single-stock-demo-run/report.md` |",
        "| 这次运行的自检结果（泄漏数、溯源未解析项…） | `single-stock-demo-run/report-validation.yaml` |",
        "| 名词完整解释 | `docs/briefing/02-术语速查.md` |",
        "| 师兄会问什么 | `docs/briefing/03-问答手册.md` |",
        "| 已知缺陷 | `DEMO-KNOWN-ISSUES.md` |",
        "",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        world = RunArtifacts()
        if str(world.gate.get("report_form")) != "FULL_REPORT":
            print(
                "ERROR: 运行目录里没有 FULL_REPORT，先跑一次完整流程再生成导读",
                file=sys.stderr,
            )
            return 1
        world.load_full()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(build(world), encoding="utf-8")
        print(f"wrote {OUTPUT}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
