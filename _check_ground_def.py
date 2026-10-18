import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/llm_agent.py", encoding="utf-8").read()
i = s.find("def _ground")
print("def _ground 位置:", i)
print(s[max(0,i-200):i+500] if i>0 else "未找到")
print("\n_ground( 出现次数:", s.count("_ground("))
