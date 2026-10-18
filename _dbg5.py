import os, sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
os.chdir(r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
os.environ["AGENT_LLM"] = "off"
from agent import orchestrator
from agent.context import AgentContext
ctx = AgentContext(user_id=3, role_id=3, lang="zh")
res = orchestrator.run(ctx, "我最近乳头溢血，该怎么办")
for step in res.get("graph", []):
    print(step)
