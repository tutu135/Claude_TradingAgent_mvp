set -e
export PYTHONIOENCODING=utf-8
R=single-stock-demo-run
echo "--- stage 0 preflight"
python scripts/validate_demo_run.py preflight
echo "--- stage 1 acquire DEMO_RUN"
python scripts/acquire_research_materials.py DEMO_RUN --case-file single-stock-demo-v3/case.yaml --snapshot-dir single-stock-demo-v3
echo "--- stage 2 context"
python scripts/govern_research_context.py --snapshot-dir single-stock-demo-v3 --rules-file rules/context-retrieval.yaml --acceptance-file tests/fixtures/retrieval-acceptance-smic-v3.yaml --output-dir $R
echo "--- stage 3 normalize"
python scripts/normalize_research_facts.py --snapshot-dir single-stock-demo-v3 --context-file $R/context.jsonl --retrieval-file $R/retrieval-validation.yaml --rules-file rules/accounting.yaml --existing-gaps-file single-stock-demo-v3/gaps.yaml --output-dir $R
echo "--- stage 4 evidence"
python scripts/govern_validate_research_evidence.py --snapshot-dir single-stock-demo-v3 --facts-file $R/normalized-facts.jsonl --context-file $R/context.jsonl --rules-file rules/source-governance.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
echo "--- stage 5a select"
python scripts/analyze_and_score_research_findings.py select --snapshot-dir single-stock-demo-v3 --context-file $R/context.jsonl --facts-file $R/normalized-facts.jsonl --evidence-file $R/governed-evidence.jsonl --rules-file rules/analysis.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
echo "--- stage 5b finalize (FROZEN_REPLAY)"
python scripts/analyze_and_score_research_findings.py finalize --analysis-inputs $R/analysis-inputs.jsonl --model-findings frozen-analysis-inputs/findings-attempt-1.yaml --model-findings frozen-analysis-inputs/findings-attempt-2.yaml --rules-file rules/analysis.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
echo "--- stage 6 challenge"
python scripts/challenge_research_findings.py --findings-file $R/findings.yaml --analysis-inputs $R/analysis-inputs.jsonl --model-challenges frozen-analysis-inputs/challenges-model.yaml --rules-file rules/analysis.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
echo "--- gate"
python scripts/validate_demo_run.py gate
echo "--- stage 7 report"
python scripts/generate_research_report.py
echo "--- finalize manifest"
python scripts/validate_demo_run.py finalize-manifest
echo "--- done"
