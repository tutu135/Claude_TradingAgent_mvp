import yaml, json, copy

DERIVED = {"evidence_score","evidence_score_label","evidence_score_basis",
           "finding_reason_code","generation_attempts","bearing_metric_whitelist",
           "revised_from_challenge_ids"}
DERIVED_ITEM = {"fact_id","proposed_threshold"}

doc = yaml.safe_load(open('tmp/ticket05-final/findings.yaml', encoding='utf-8'))
by_id = {f['dimension_id']: f for f in doc['findings']}

def stripped(dim):
    f = copy.deepcopy(by_id[dim])
    for k in list(f):
        if k in DERIVED:
            del f[k]
    for field in ("supporting_evidence","counter_evidence","management_assertions","watch_indicators"):
        if field in f:
            f[field] = [{k:v for k,v in item.items() if k not in DERIVED_ITEM} for item in f[field]]
    return f

# --- CH_002: D2 pseudo-multi-source -> revision (direction weakened, evidence unchanged)
d2 = stripped('D2_UTILIZATION_EFFECT')
d2['finding'] = 'MIXED'
d2['finding_statement'] = (
    '候选证据集中不存在可承重的产能利用率数值记录，本维度只能依据公司自身披露的文本表述。'
    '定向复核发现，中国企业会计准则口径年报与国际财务报告准则口径年报的相关表述来自同一年度的同一次原始披露，'
    '两者互相印证不构成独立多来源。在此口径下，利用率在公司的成本与毛利说明中被列为与盈利能力变化同时出现的因素之一，'
    '但证据集内没有独立于公司自身表述的记录，方向由 SUPPORTED 下调为 MIXED。'
)
d2['limitations'] = list(d2['limitations']) + [
    '经质询确认：CAS 与 IFRS 两个口径的年报表述属同一次原始披露的两种呈报，构成伪多源，不能作为独立来源一致性的依据。'
]

# --- CH_003: D3 company cause-of-change wording moved out of supporting evidence
d3 = stripped('D3_MIX_EFFECT')
ATTRIB = {
    'EVID_e4b206094f5890f4cf04ffc1',
    'EVID_c2538a34f11c5131292d1fe8',
    'EVID_43289a6874cc99aca0fa341c',
    'EVID_1c3dc864090cac8f4c9a9b23',
}
moved = [s for s in d3['supporting_evidence'] if s['evidence_id'] in ATTRIB]
d3['supporting_evidence'] = [s for s in d3['supporting_evidence'] if s['evidence_id'] not in ATTRIB]
d3['management_assertions'] = list(d3.get('management_assertions') or []) + [
    {'evidence_id': s['evidence_id'],
     'statement': '公司在该次披露中把产品结构变化列为毛利率或平均售价变动的说明之一；本阶段保留为公司具名表述，不作独立确认。'}
    for s in moved
]
d3['finding_statement'] = (
    '经质询后重述：本维度可承重的数值指标只有一条 FY2025 的 ASP_SOURCE_REPORTED（6482 CNY），无同口径跨期可比值；'
    '应用结构占比在 2025 年报中确有可观察位移（智能手机 37.8% 升至 43.2%，消费电子 27.8% 降至 23.1%），'
    '而按尺寸划分的 12 英寸占比在两年间基本持平。公司关于「产品结构变化」的说明已全部移入管理层表述，不再作为支撑证据。'
    '在剩余可承重证据下，结构变化与售价、成本或毛利之间的关系只能表述为同期并存，方向维持 MIXED。'
)
d3['limitations'] = list(d3['limitations']) + [
    '经质询确认：公司自身的「产品结构变化」归因语句在证据集内没有独立佐证，已保留为管理层表述而非验证后的原因。'
]

challenges = [
    {
        'challenge_id': 'CH_001',
        'round': 1,
        'category': 'SOURCE_TRACEABILITY',
        'target_kind': 'FINDING',
        'target_id': 'D1_PROFITABILITY_CHANGE',
        'question': '本维度证据分为 3，依赖「两个以上独立同源组」。4Q25 毛利率 19.2% 同时出现在 SG_SMIC_2025_Q4_RESULTS 与 SG_SMIC_2026_Q1_DISCLOSURE，是否属于伪多源，从而使证据分虚高？',
        'disposition': 'RESOLVED_NO_CHANGE',
        'reason': '一次定向复核：承重的跨期可比数值是 2025 年报中 FY2025 与 FY2024 的 GROSS_MARGIN 对比，来自年度报告这一次原始披露；季度公告是另一次独立披露。被质疑的 19.2% 重复对已在限制中披露，且未作为跨期比较的承重项，证据分依据不变。',
    },
    {
        'challenge_id': 'CH_002',
        'round': 1,
        'category': 'SOURCE_TRACEABILITY',
        'target_kind': 'FINDING',
        'target_id': 'D2_UTILIZATION_EFFECT',
        'question': '本维度方向为 SUPPORTED，但支撑证据同时来自 CAS 口径年报与 IFRS 口径年报。两者是否为同一次原始披露的两种呈报，即伪多源？',
        'disposition': 'RESOLVED_WITH_REVISION',
        'reason': '一次定向复核确认两条表述指向同一年度同一次原始披露，互相印证不构成独立来源；且本维度承重指标白名单为空，无任何数值证据可独立支撑方向。方向由 SUPPORTED 下调为 MIXED，并在限制中写明伪多源。',
        'revision': {'dimension_id': 'D2_UTILIZATION_EFFECT', 'finding_after': d2},
    },
    {
        'challenge_id': 'CH_003',
        'round': 1,
        'category': 'ATTRIBUTION_CAUSALITY',
        'target_kind': 'FINDING',
        'target_id': 'D3_MIX_EFFECT',
        'question': '本维度把公司「due to the product mix change」等原因说明列为 PRIMARY_SUPPORT。在没有独立证据的情况下，这是否把公司自身的归因升级为已验证的原因？',
        'disposition': 'RESOLVED_WITH_REVISION',
        'reason': '一次定向复核确认这四条记录均为公司在同一次披露中给出的原因说明，证据集内没有独立佐证。按 FR-052 保留为 MANAGEMENT_ASSERTION，移出支撑证据并重述发现。',
        'revision': {'dimension_id': 'D3_MIX_EFFECT', 'finding_after': d3},
    },
    {
        'challenge_id': 'CH_004',
        'round': 1,
        'category': 'ACCOUNTING_COMPARABILITY',
        'target_kind': 'EVIDENCE',
        'target_id': 'EVID_28c333bb3006b183a5e34b57',
        'question': '该折旧记录来源为半年度材料却被标注为 FISCAL_YEAR 2025 全年，且同一 DEPRECIATION_EXPENSE 指标在候选集内同时存在百分比型与金额型取值。它是否可比、是否已污染 D4 的折旧压力判断？',
        'disposition': 'RESOLVED_NO_CHANGE',
        'reason': '一次定向复核确认该记录及同类折旧记录均未进入 D4 的支撑证据，仅在限制中披露；D4 的证据分来自 CAPITAL_EXPENDITURE_INCURRED 的跨期可比值。上游期间标注缺陷已由 04 阶段的 GAP_EVIDENCE_UPSTREAM_PERIOD_MISLABEL 承接，本阶段不重复登记。',
    },
    {
        'challenge_id': 'CH_005',
        'round': 2,
        'category': 'FALSIFICATION_MISSING_EVIDENCE',
        'target_kind': 'FINDING',
        'target_id': 'D7_SUSTAINABILITY_EVIDENCE',
        'follow_up_of': 'CH_001',
        'question': '可持续性判断缺少任何经营现金流证据：候选集内 18 条数值全部是结果指标，承重指标白名单为空。在没有现金流或单位成本证据的情况下，MIXED 的方向能否成立？',
        'disposition': 'UNRESOLVED_DOWNGRADED',
        'reason': '一次定向复核确认冻结快照内存在 NET_CASH_FROM_OPERATING_ACTIVITIES 记录，但无一被冻结的 D7 查询族命中，因而不在本维度候选集内；03 查询族已冻结，本阶段不得改动。两轮内无法在候选集内取得可承重证据，按固定阶梯降级。',
    },
]

out = {'snapshot_id': 'smic-a283e95e2c9e8068', 'challenges': challenges}
open('tmp/ticket05-model/challenges-model.yaml','w',encoding='utf-8').write(
    yaml.safe_dump(out, allow_unicode=True, sort_keys=False))
print('written', len(challenges))
