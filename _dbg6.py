import os, sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
os.chdir(r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
os.environ["AGENT_LLM"] = "off"
from agent import orchestrator
from agent.context import AgentContext
for q in ["SHAP 分析怎么用", "怎么批量导入数据"]:
    ctx = AgentContext(user_id=3, role_id=3, lang="zh")
    res = orchestrator.run(ctx, q)
    print("=" * 70)
    print("Q:", q, "| status:", res["status"])
    print(res["answer_md"][:700])
