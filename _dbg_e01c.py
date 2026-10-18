import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent import db, orchestrator, runtime
from agent.context import AgentContext
from agent.tests.conftest import _fake_explain, _fake_predict, _fake_records, _fake_stats
runtime.get().bind(predict=_fake_predict, explain=_fake_explain, fetch_records=_fake_records, fetch_stats=_fake_stats)
db.init_schema()
F = [17.99, 10.38, 122.8, 1001.0, 0.1184, 0.2776, 0.3001, 0.1471, 0.2419, 0.07871,
     1.095, 0.9053, 8.589, 153.4, 0.006399, 0.04904, 0.05373, 0.01587, 0.03003, 0.006193,
     25.38, 17.33, 184.6, 2019.0, 0.1622, 0.6656, 0.7119, 0.2654, 0.4601, 0.1189]
ctx = AgentContext(user_id=9001, role_id=1, lang='zh')
r = orchestrator.run(ctx, "这个结果什么意思？严重吗", F)
print("intent:", r["intent"], "| status:", r["status"])
print("answer 前 400:", (r["answer_md"] or "")[:400].replace("\n", " "))
print("citations:", r["citations"][:5])
