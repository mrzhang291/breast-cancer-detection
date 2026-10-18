import os, sys
sys.path.insert(0, r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
os.chdir(r"C:\Users\zcj00\乳腺癌\breast-cancer-detection")
sys.stdout.reconfigure(encoding="utf-8")
os.environ["AGENT_LLM"] = "off"

from agent.tools import sql
try:
    print("plan:", sql.plan_sql("恶性病例的平均面积比良性高多少")[0][:120])
    print("validate:", sql.validate_sql(sql.plan_sql("恶性病例的平均面积")[0])[:100])
    rows = sql.run_sql(sql.validate_sql(sql.plan_sql("恶性病例的平均面积")[0]))
    print("rows:", len(rows), rows[:3])
except Exception as exc:
    import traceback; traceback.print_exc()
