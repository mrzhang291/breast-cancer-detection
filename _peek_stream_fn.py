import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\llm_agent.py", encoding="utf-8").read()
i = s.find("def stream_llm_agent")
seg = s[i:i+2000]
print(seg[:1600])
