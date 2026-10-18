import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/_assistant.html", encoding="utf-8").read()
print("refreshAgentContext 定义:", s.count("function refreshAgentContext"))
print("renderGrounding 定义:", s.count("function renderGrounding"))
i = s.find("function refreshAgentContext")
print(s[max(0,i-300):i+700])
