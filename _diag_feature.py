"""诊断：特征问题为何没有引用。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('AGENT_LLM', 'off')

from agent import db, runtime  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.tests.conftest import (_fake_explain, _fake_predict,  # noqa: E402
                                  _fake_records, _fake_stats)

runtime.get().bind(predict=_fake_predict, explain=_fake_explain,
                   fetch_records=_fake_records, fetch_stats=_fake_stats)
db.init_schema()

from agent import orchestrator  # noqa: E402

result = orchestrator.run(AgentContext(user_id=3, role_id=3), '面积平均值是什么意思')
print('intent:', result['intent'])
print('citations:', result['citations'])
print('facts:', [f.get('kind') for f in result.get('facts') or []])
for fact in result.get('facts') or []:
    if fact.get('kind') == 'clause':
        hits = (fact.get('payload') or {}).get('hits') or []
        print('命中:', [(h.get('clause_id'), round(float(h.get('score') or 0), 1)) for h in hits])
print('answer 前 120:', (result.get('answer_md') or '')[:120].replace('\n', ' '))
