import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"app.py", encoding="utf-8").read()
i = s.find("llm agent 落库失败")
print("落库代码位置:", i)
j = s.rfind("def api_", 0, i)
print("所属函数:", s[j:j+40].splitlines()[0])
k = s.find("def api_agent_llm")
print("端点位置:", k, "| 落库是否在端点内:", k < i < s.find("def api_agent_artifact"))
