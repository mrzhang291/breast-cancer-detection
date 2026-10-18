import os, sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
os.chdir(r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
os.environ["AGENT_LLM"] = "off"
from agent import orchestrator
from agent.context import AgentContext
ctx = AgentContext(user_id=3, role_id=3, lang="zh")
res = orchestrator.run(ctx, "怎么批量导入数据")
print("status:", res["status"])
print("intent:", repr(res["intent"]))
print("graph:", [(s["node"], s["verdict"], s.get("error")) for s in res.get("graph", [])])
print("steps:", len(res.get("steps") or []))
print("answer head:", (res.get("answer_md") or "")[:120].replace(chr(10), " "))
