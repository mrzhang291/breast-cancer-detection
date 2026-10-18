import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent import grounding
FACTS = [
    {'kind': 'prediction', 'payload': {'output': '良性', 'confidence': 0.9973}},
    {'kind': 'shap', 'payload': {'prediction': '良性', 'top_features': [{'name_zh': '凹点平均值'}]}},
    {'kind': 'stat', 'payload': {'total': 105}},
    {'kind': 'input', 'payload': {'features': [{'name': 'radius_mean', 'value': 11.84}]}},
]
CITATIONS = ['FEAT-024', 'DOC-MODEL-002']
for ans in ("本次判断为良性，置信度 99.73%。另外模型准确率高达 99.99%。",
            "本次判断为良性。置信度 99.73%。建议定期复查。"):
    r = grounding.ground(ans, FACTS, CITATIONS)
    print("ANS:", ans)
    print("  dropped:", r['dropped_count'], r['dropped'])
    print("  coverage:", r['coverage'], "ok:", r['ok'])
    print("  answer:", r['answer_md'])
    print("  claims:", [(c['sentence'][:18], [s['label'] for s in c['sources']], c['advice']) for c in r['claims']])
