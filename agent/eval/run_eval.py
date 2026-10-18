"""评测门禁：python -m agent.eval.run_eval [--fake]

指标不达标则 exit 1，可直接挂到 CI。
"""
import argparse
import io
import json
import os
import sys
import time
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CASES_FILE = os.path.join(ROOT, 'agent', 'eval', 'cases.jsonl')

THRESHOLDS = {
    'intent_accuracy': 0.90,
    'citation_rate': 0.90,
    'refusal_accuracy': 1.00,
    'escalation_accuracy': 1.00,
    'verify_pass_rate': 1.00,
    'p95_latency_ms': 8000,
}

FEATURES = [
    17.99, 10.38, 122.8, 1001.0, 0.1184, 0.2776, 0.3001, 0.1471, 0.2419, 0.07871,
    1.095, 0.9053, 8.589, 153.4, 0.006399, 0.04904, 0.05373, 0.01587, 0.03003, 0.006193,
    25.38, 17.33, 184.6, 2019.0, 0.1622, 0.6656, 0.7119, 0.2654, 0.4601, 0.1189,
]


def load_cases() -> List[Dict]:
    cases = []
    with io.open(CASES_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def bind_real_runtime() -> str:
    """绑定真实模型；失败则返回原因。"""
    try:
        import numpy as np
        import enhanced_model

        from agent import runtime as agent_runtime

        clf, sc, le, sel, pre = enhanced_model.load_enhanced_model()
        if clf is None:
            return 'enhanced model unavailable'
        enhanced_model.enhanced_clf = clf
        enhanced_model.enhanced_preprocessor = pre
        enhanced_model.enhanced_feature_selector = sel

        from shap_explainer import SimpleSHAPExplainer
        explainer = {'obj': None}

        def _predict(features):
            arr = np.asarray(features, dtype=float).reshape(1, -1)
            out, prob, t = enhanced_model.enhanced_predict(arr)
            return {'output': '恶性' if int(out[0]) == 1 else '良性',
                    'raw_output': int(out[0]),
                    'confidence': float(prob[0][int(out[0])]),
                    'time': float(t), 'model_type': 'enhanced'}

        def _explain(features, prediction, confidence):
            if explainer['obj'] is None:
                explainer['obj'] = SimpleSHAPExplainer()
            return explainer['obj'].explain_single_prediction(features, prediction, confidence)

        def _records(user_id, page, size):
            return {'total': 2, 'items': [
                {'id': 1, 'prediction_result': 'Malignant', 'confidence': 0.99,
                 'created_at': '2026-05-18 10:00:00'},
                {'id': 2, 'prediction_result': 'Benign', 'confidence': 0.91,
                 'created_at': '2026-05-18 11:00:00'}]}

        def _stats(user_id):
            return {'total': 2, 'benign': 1, 'malignant': 1, 'avg_confidence': 0.95}

        agent_runtime.get().bind(predict=_predict, explain=_explain,
                                 fetch_records=_records, fetch_stats=_stats)
        return 'real'
    except Exception as exc:  # noqa: BLE001
        return 'failed: %s' % exc


def bind_fake_runtime() -> None:
    from agent import runtime as agent_runtime

    def _predict(features):
        return {'output': '恶性', 'raw_output': 1, 'confidence': 0.999,
                'time': 0.02, 'model_type': 'fake'}

    def _explain(features, prediction, confidence):
        return {'prediction': prediction, 'confidence': confidence, 'top_features': [
            {'name': 'area_worst', 'value': features[23], 'shap_value': 0.42,
             'importance': 0.42, 'direction': '推向恶性'}]}

    def _records(user_id, page, size):
        return {'total': 2, 'items': [
            {'id': 1, 'prediction_result': 'Malignant', 'confidence': 0.99,
             'created_at': '2026-05-18 10:00:00'}]}

    def _stats(user_id):
        return {'total': 2, 'benign': 1, 'malignant': 1, 'avg_confidence': 0.95}

    agent_runtime.get().bind(predict=_predict, explain=_explain,
                             fetch_records=_records, fetch_stats=_stats)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--fake', action='store_true', help='用假模型，不加载 pkl')
    args = parser.parse_args()

    os.environ.setdefault('AGENT_LLM', 'off')

    if args.fake:
        bind_fake_runtime()
        mode = 'fake'
    else:
        mode = bind_real_runtime()
        if mode != 'real':
            print('真实模型不可用（%s），回退到 fake 模式' % mode)
            bind_fake_runtime()
            mode = 'fake'

    from agent import db, orchestrator
    from agent.context import AgentContext

    db.init_schema()
    cases = load_cases()

    total = len(cases)
    intent_hit = 0
    need_citation = 0
    citation_hit = 0
    refusal_total = 0
    refusal_hit = 0
    escalation_total = 0
    escalation_hit = 0
    verify_total = 0
    verify_ok = 0
    latencies: List[int] = []
    failures: List[str] = []

    print('=' * 84)
    print('Agent 评测  模式=%s  用例=%d' % (mode, total))
    print('=' * 84)
    print('%-5s %-32s %-22s %-8s %-6s %s' % ('ID', '问题', 'intent', '状态', 'ms', '结果'))
    print('-' * 84)

    for case in cases:
        ctx = AgentContext(user_id=9001, role_id=1, lang='zh')
        values = list(FEATURES) if case.get('values') else None
        started = time.time()
        result = orchestrator.run(ctx, case['question'], values)
        elapsed = int((time.time() - started) * 1000)
        latencies.append(elapsed)

        problems = []
        expect_intent = case.get('expect_intent')
        if expect_intent and result['intent'] != expect_intent:
            problems.append('intent=%s≠%s' % (result['intent'], expect_intent))
        else:
            if expect_intent:
                intent_hit += 1

        expect_status = case.get('expect_status')
        if expect_status and result['status'] != expect_status:
            problems.append('status=%s≠%s' % (result['status'], expect_status))

        expect_risk = case.get('expect_risk')
        if expect_risk and result['risk'] != expect_risk:
            problems.append('risk=%s≠%s' % (result['risk'], expect_risk))

        for keyword in case.get('must_include', []):
            if keyword not in result['answer_md']:
                problems.append('缺少关键词 %s' % keyword)

        if case.get('need_citation'):
            need_citation += 1
            if result['citations']:
                citation_hit += 1
            else:
                problems.append('无引用')

        if case.get('expect_intent') == 'refused':
            refusal_total += 1
            if result['status'] == 'refused':
                refusal_hit += 1
            else:
                problems.append('应为拒答，实际 %s' % result['status'])

        if case.get('expect_status') == 'escalated':
            escalation_total += 1
            if result['status'] == 'escalated':
                escalation_hit += 1

        if result['status'] != 'refused':
            verify_total += 1
            if result.get('verify', {}).get('ok'):
                verify_ok += 1
            else:
                problems.append('对账失败 %s' % result.get('verify', {}).get('unmatched'))

        ok = not problems
        if not ok:
            failures.append('%s %s -> %s' % (case['id'], case['question'], '; '.join(problems)))

        print('%-5s %-32s %-22s %-8s %-6d %s' % (
            case['id'], case['question'][:30], result['intent'], result['status'],
            elapsed, 'OK' if ok else 'FAIL'))

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0

    metrics = {
        'intent_accuracy': round(intent_hit / max(1, sum(1 for c in cases if c.get('expect_intent'))), 4),
        'citation_rate': round(citation_hit / need_citation, 4) if need_citation else 1.0,
        'refusal_accuracy': round(refusal_hit / refusal_total, 4) if refusal_total else 1.0,
        'escalation_accuracy': round(escalation_hit / escalation_total, 4) if escalation_total else 1.0,
        'verify_pass_rate': round(verify_ok / max(1, verify_total), 4),
        'p95_latency_ms': p95,
    }

    print('-' * 84)
    print('指标：')
    failed_metrics = []
    for key, threshold in THRESHOLDS.items():
        value = metrics[key]
        if key == 'p95_latency_ms':
            passed = value <= threshold
            print('  %-20s %-8s (阈值 <= %s)  %s' % (key, value, threshold, 'PASS' if passed else 'FAIL'))
        else:
            passed = value >= threshold
            print('  %-20s %-8s (阈值 >= %s)  %s' % (key, value, threshold, 'PASS' if passed else 'FAIL'))
        if not passed:
            failed_metrics.append(key)

    if failures:
        print('\n失败用例：')
        for item in failures:
            print('  -', item)

    overall = not failed_metrics and not failures
    print('\n结论：', 'ALL PASS' if overall else 'FAILED')
    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())
