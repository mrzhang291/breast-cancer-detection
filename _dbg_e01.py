import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent import db, orchestrator, runtime
from agent.context import AgentContext
from agent.tests.conftest import _fake_explain, _fake_predict, _fake_records, _fake_stats
runtime.get().bind(predict=_fake_predict, explain=_fake_explain, fetch_records=_fake_records, fetch_stats=_fake_stats)
db.init_schema()
r = orchestrator.run(AgentContext(user_id=3, role_id=3), "这个结果什么意思？严重吗")
print("intent:", r["intent"], "| status:", r["status"])
print("answer:", (r["answer_md"] or "")[:300].replace("\n", " "))
print("citations:", r["citations"][:5])
