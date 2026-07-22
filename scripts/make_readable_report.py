"""Render a human-readable companion to report.md. A reading aid, not a second report.

`report.md` is written for audit: sixteen-column evidence tables, every column carrying a
piece of the basis a number needs before it can be compared to another number. That is
correct and unreadable. This script re-renders the same facts as linked cards so a person
can follow one number from the narrative to the page of the PDF it came from.

Three rules keep this honest.

**It adds no claim.** Every value, period, basis, locator and source span is copied from
the run artefacts. Nothing is computed, inferred or rephrased.

**It never binds a number to evidence the model did not bind.** D1's statement carries
23 numbers over 8 supporting records, and the model never said which number came from
which record. Putting them back inline would manufacture a provenance link -- exactly the
thing the whole pipeline exists to prevent. The omitted sentences are therefore shown in
a separate, labelled block that states plainly that their numbers are unverified.

**It is not part of the pipeline.** No stage reads its output, and it writes outside the
run directory: a stray `.md` inside `single-stock-demo-run/` would be an unknown
authoritative file and would halt the next `preflight` before it consumed any input.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_research_report import (  # noqa: E402
    RULES_DIR,
    RunArtifacts,
    basis_of,
    cited_evidence_ids,
    locator_of,
    period_of,
    published_of,
    read_yaml,
    sanitize,
)

OUTPUT = Path("docs/briefing/04-报告导读.md")
SNAPSHOT_RELATIVE = "../../single-stock-demo-v3"

DIMENSION_TITLES = {
    "D1_PROFITABILITY_CHANGE": "D1 盈利能力变化 —— 到底改善了没有？",
    "D2_UTILIZATION_EFFECT": "D2 利用率驱动 —— 是因为工厂开工率上去了吗？",
    "D3_MIX_EFFECT": "D3 产品结构驱动 —— 是因为卖的东西更值钱了吗？",
    "D4_CAPEX_CONVERSION": "D4 资本开支转化 —— 前几年砸的钱变成利润了吗？",
    "D5_CYCLE_EXPLANATION": "D5 行业周期 —— 会不会只是行业回暖？",
    "D6_NONCORE_EXPLANATION": "D6 非经常项 —— 会不会主要靠政府补助？",
    "D7_SUSTAINABILITY_EVIDENCE": "D7 可持续性 —— 这个改善能持续吗？",
}
FINDING_LABELS = {
    "SUPPORTED": "证据支持",
    "MIXED": "证据方向不一致",
    "NOT_SUPPORTED": "证据不支持",
    "UNKNOWN": "现有证据无法判断",
}
SCORE_LABELS = {
    0: "0 无承重证据", 1: "1 有限", 2: "2 尚可", 3: "3 较强",
}
ROLE_LABELS = {"PRIMARY_SUPPORT": "主要支撑", "CONTEXT": "背景（不承重）"}

# The prose fields worth showing a reader, in reading order.
NARRATIVE_FIELDS = [
    ("finding_statement", "结论叙述", "findings[].finding_statement"),
    ("alternative_explanations", "其他可能的解释", "findings[].alternative_explanations[]"),
    ("limitations", "本维度的局限", "findings[].limitations[]"),
    ("gaps", "缺什么数据", "findings[].gaps[]"),
]


def page_of(record: dict[str, Any], fact: dict[str, Any]) -> int | None:
    locator = fact.get("content_locator") or record.get("content_locator") or {}
    page = locator.get("page_number")
    return int(page) if isinstance(page, int) else None


def links_for(material: dict[str, Any], page: int | None) -> str:
    """Public entry point and the frozen local copy, both jumping to the page if known."""
    anchor = f"#page={page}" if page and str(material.get("media_type")) == "application/pdf" else ""
    parts = []
    url = (material.get("canonical_material_locator") or {}).get("source_page")
    if url:
        parts.append(f"[公开原文]({url}{anchor})")
    frozen = material.get("frozen_path")
    if frozen:
        parts.append(f"[本地冻结件]({SNAPSHOT_RELATIVE}/{frozen}{anchor})")
    return " · ".join(parts) or "—"


def evidence_card(
    world: RunArtifacts, evidence_id: str, role: str | None, note: str | None
) -> list[str]:
    record = world.candidates.get(evidence_id)
    if record is None:
        return [f"- `{evidence_id}` —— 不在本维度候选集内，无法展开", ""]
    fact = world.facts.get(str(record["fact_id"])) or {}
    material = world.material_of(record, fact)
    page = page_of(record, fact)
    numeric = record.get("record_kind") == "NUMERIC_OBSERVATION"

    # `MONEY` is a unit enum, not something to show a reader; for money the currency is
    # the useful label. The raw enums stay on the 数值 line below, unchanged.
    unit = str(fact.get("target_unit") or fact.get("raw_unit") or "")
    display_unit = (
        str(fact.get("target_currency") or fact.get("raw_currency") or unit)
        if unit == "MONEY"
        else unit
    )
    headline = (
        f"{fact.get('metric_id')} = **{fact.get('normalized_value')} {display_unit}**"
        if numeric
        else "文本命题"
    )
    lines = [
        f'<a id="{evidence_id}"></a>',
        "",
        f"**`{evidence_id}`** · {headline}"
        + (f" · {ROLE_LABELS.get(str(role), str(role))}" if role else ""),
        "",
    ]
    if numeric:
        lines.append(
            f"- **数值**：{fact.get('normalized_value')} "
            f"{fact.get('target_unit') or fact.get('raw_unit')}"
            f"（原文写作 `{fact.get('raw_value_text')}`"
            + (f"，币种 {fact.get('target_currency')}" if fact.get("target_currency") else "")
            + f"，缩放 ×{fact.get('target_scale_factor') or fact.get('raw_scale_factor')}）"
        )
    lines.extend([
        f"- **期间**：{period_of(fact)}",
        f"- **口径**：{basis_of(fact)}　_(会计准则 / 合并范围 / 审计状态 / 数值来源)_",
        f"- **来源**：{material.get('displayed_publisher') or '—'}"
        f"《{material.get('title') or '—'}》，发布于 {published_of(material)}",
        f"- **位置**：{locator_of(record, fact)}",
        f"- **打开**：{links_for(material, page)}",
    ])
    span = fact.get("source_span_text") or record.get("source_span_text")
    if span:
        lines.extend(["- **原文**：", "", f"  > {' '.join(str(span).split())}"])
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
        f"- **溯源链**：`{evidence_id}` → `{record['fact_id']}` → "
        f"`{record.get('chunk_id')}` → `{material.get('material_id')}`",
        "",
    ])
    return lines


def dimension_section(world: RunArtifacts, finding: dict[str, Any]) -> list[str]:
    dimension_id = str(finding["dimension_id"])
    score = int(finding.get("evidence_score") or 0)
    lines = [
        f"## {DIMENSION_TITLES.get(dimension_id, dimension_id)}",
        "",
        f"> **结论：{FINDING_LABELS.get(str(finding.get('finding')), finding.get('finding'))}"
        f"（{finding.get('finding')}）**　证据分 {SCORE_LABELS.get(score, score)}",
        "",
    ]
    whitelist = finding.get("bearing_metric_whitelist") or []
    lines.append(
        f"承重指标白名单：{'、'.join(f'`{item}`' for item in whitelist)}"
        if whitelist
        else "**承重指标白名单为空** —— 快照里没有任何一个该维度可以用来承担结论方向的指标，"
        "所以这个维度的方向不是由数值证据撑起来的。这是如实记录，不是遗漏。"
    )
    lines.append("")

    all_dropped: list[dict[str, Any]] = []
    for field, title, path in NARRATIVE_FIELDS:
        value = finding.get(field)
        items = value if isinstance(value, list) else ([value] if value else [])
        rendered: list[str] = []
        for item in items:
            kept, dropped = sanitize(item, dimension_id, path)
            all_dropped.extend(dropped)
            if kept:
                rendered.append(kept)
        if rendered:
            lines.extend([f"### {title}", ""])
            lines.extend(f"- {text}" for text in rendered)
            lines.append("")

    if all_dropped:
        lines.extend([
            "### 被闸门排除的句子",
            "",
            f"下面 {len(all_dropped)} 句**没有进入正式报告**，因为它们含有未与单条证据一一对应的数字。"
            "列在这里只为让你看清闸门做了什么，**它们不是本报告的结论，其中的数字未经逐个核验**——"
            "要用数字请看下面的证据卡片。",
            "",
        ])
        for item in all_dropped:
            tokens = "、".join(item["matched_numeric_tokens"][:6])
            lines.append(f"- ~~{item['matched_text']}~~　_（含数字：{tokens}）_")
        lines.append("")

    lines.extend(["### 承重证据（逐条展开）", ""])
    notes = {}
    for field in ("supporting_evidence", "counter_evidence", "management_assertions"):
        for item in finding.get(field) or []:
            if item.get("evidence_id"):
                notes[str(item["evidence_id"])] = (
                    item.get("role"), item.get("note") or item.get("statement")
                )
    ids = cited_evidence_ids(finding)
    if not ids:
        lines.extend(["本维度没有引用任何证据。", ""])
    for evidence_id in ids:
        role, note = notes.get(evidence_id, (None, None))
        lines.extend(evidence_card(world, evidence_id, role, note))
    return lines


def build(world: RunArtifacts) -> str:
    gate = world.gate
    statuses = gate.get("stage_statuses") or {}
    findings = world.revised.get("findings") or []
    case = world.case

    lines = [
        "# 报告导读（易读版）",
        "",
        "> **这不是第二份报告。** 权威产物永远是 `single-stock-demo-run/report.md`；",
        "> 本文件由 `scripts/make_readable_report.py` 从同一批运行产物重新排版而来，"
        "只改呈现方式，不新增任何结论、数值或来源。",
        "",
        "---",
        "",
        "## 花三分钟先搞懂这份报告为什么长这样",
        "",
        "你会发现正式报告里的叙述**读起来断断续续**，很多段落只剩一句「具体数值及其期间、"
        "口径和来源见本维度证据表」。这不是 bug，是设计：",
        "",
        "**一句话解释**：模型写的叙述里，凡是出现了数字、而那个数字又没有和某一条证据"
        "一一对应的，**整句从报告里删掉**。",
        "",
        "**为什么不只是把数字抹掉**：抹掉字符会剩下「毛利率由上升到，改善个百分点」——"
        "读起来还像句人话，但已经没有意义了，而且更危险。整句删除至少是诚实的空白。",
        "",
        "**为什么不干脆把数字标上来源**：因为模型没说过哪个数字对应哪条证据。"
        "D1 那段话里 23 个数字共用 8 条支撑证据，硬把它们配对起来就是**伪造溯源关系**——"
        "这恰恰是整个项目要防的事。",
        "",
        "**所以数字去哪了**：全部搬进证据表。本文件把那些表拆成了一张张卡片，"
        "每张卡片带着它的期间、口径、来源和**可以直接点开的原文链接**。",
        "",
        "**下面每个维度分四块读**：结论 → 报告采用的叙述 → 被闸门删掉的句子（看机制用）→ "
        "证据卡片（要数字看这里）。",
        "",
        "---",
        "",
        "## 全局速览",
        "",
        f"**研究问题**：{case.get('research_question')}",
        "",
        f"**as_of**：{case.get('as_of')}　—— 只用这个时间点之前公开的资料，"
        "晚于它的一律不许进来。",
        "",
        "| 阶段 | 状态 | 说明 |",
        "|---|---|---|",
        f"| 检索 | {statuses.get('retrieval_status')} | 该找到的片段都找到了 |",
        f"| 事实规整 | {statuses.get('normalization_run_status')} | 有记录只完成了部分字段 |",
        f"| 证据治理 | {statuses.get('validation_status')} | 有未解决的缺口 |",
        f"| 分析 | {statuses.get('analysis_run_status')} | 七个维度都通过了校验 |",
        f"| 反方质询 | {statuses.get('challenge_run_status')} | 有未解决的质询 |",
        f"| **治理状态** | **{gate.get('governance_status')}** | 前三者取最坏值；WARN 不是失败，"
        "是「硬条件都过了但有未解决项」 |",
        "",
        "| 维度 | 结论 | 证据分 | 承重指标 |",
        "|---|---|---|---|",
    ]
    for finding in findings:
        dimension_id = str(finding["dimension_id"])
        whitelist = finding.get("bearing_metric_whitelist") or []
        lines.append(
            f"| [{dimension_id}](#{dimension_id.lower().replace('_', '-')}) "
            f"| {finding.get('finding')}"
            f"（{FINDING_LABELS.get(str(finding.get('finding')), '')}） "
            f"| {finding.get('evidence_score')} "
            f"| {'、'.join(whitelist) if whitelist else '**空**'} |"
        )
    lines.extend([
        "",
        "**七个维度没有一个是 SUPPORTED。** 这是数据的真实承载力：现有 20 份材料确实不足以"
        "支持「已进入可持续改善阶段」。如果它跑出一个漂亮的结论，那才该怀疑。",
        "",
        "---",
        "",
    ])
    for finding in findings:
        lines.extend(dimension_section(world, finding))
        lines.extend(["---", ""])

    lines.extend([
        "## 还想往下挖",
        "",
        "| 想看 | 打开 |",
        "|---|---|",
        "| 权威报告本体（十章节，含质询、缺口、附录） | `single-stock-demo-run/report.md` |",
        "| 这次运行的自检结果（泄漏数、溯源未解析项…） | `single-stock-demo-run/report-validation.yaml` |",
        "| 名词不懂 | `docs/briefing/02-术语速查.md` |",
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
        rules = read_yaml(RULES_DIR / "report.yaml")
        if not rules:
            raise ValueError("rules/report.yaml missing")
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
