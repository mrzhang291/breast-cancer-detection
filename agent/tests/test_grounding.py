"""grounding 单元测试。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent import grounding  # noqa: E402

FACTS = [
    {'kind': 'prediction', 'payload': {'output': '良性', 'confidence': 0.9973}},
    {'kind': 'shap', 'payload': {'prediction': '良性',
                                 'top_features': [{'name_zh': '凹点平均值'}]}},
    {'kind': 'stat', 'payload': {'total': 105}},
    {'kind': 'input', 'payload': {'features': [{'name': 'radius_mean', 'value': 11.84}]}},
]
CITATIONS = ['FEAT-024', 'DOC-MODEL-002']


def test_bad_number_sentence_is_dropped():
    answer = '本次判断为良性，置信度 99.73%。另外模型准确率高达 99.99%。'
    result = grounding.ground(answer, FACTS, CITATIONS)
    assert result['dropped_count'] == 1
    assert '99.99' not in result['answer_md']
    assert '99.73' in result['answer_md']


def test_claim_without_source_marked_as_inference():
    facts = [f for f in FACTS if f['kind'] != 'prediction']
    result = grounding.ground('本次判断为恶性。', facts, CITATIONS)
    assert result['unsupported']
    assert '（推断）' in result['answer_md']


def test_claim_with_source_not_marked():
    result = grounding.ground('本次判断为良性，置信度 99.73%。', FACTS, CITATIONS)
    assert result['coverage'] >= 0.99
    assert '（推断）' not in result['answer_md']
    claim = result['claims'][0]
    assert any(s['kind'] == 'prediction' for s in claim['sources'])


def test_advice_sentence_not_required_to_cite():
    result = grounding.ground('建议 3–6 个月复查，如出现不适请及时就医。', FACTS, CITATIONS)
    assert result['claims'][0]['advice'] is True
    assert result['coverage'] == 1.0


def test_coverage_between_groups():
    answer = '本次判断为良性。置信度 99.73%。建议定期复查。'
    result = grounding.ground(answer, FACTS, CITATIONS)
    assert 0 < result['coverage'] <= 1.0
    assert result['ok'] is True
