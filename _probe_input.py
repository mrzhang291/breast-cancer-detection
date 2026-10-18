import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
i = o.find("def add_input_fact")
print(o[i:i+420])
e = io.open(r"agent\tools\explain.py", encoding="utf-8").read()
j = e.find("top = ")
print("\n=== explain top 结构 ===")
print(e[j-400:j+500])
