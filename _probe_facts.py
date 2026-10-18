import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"agent\tools\predict.py", encoding="utf-8").read()
print("predict fact kind:", re.findall(r"make_fact\(\s*\n?\s*'([a-z_]+)'", lines)[:3])
e = io.open(r"agent\tools\explain.py", encoding="utf-8").read()
print("explain fact kind:", re.findall(r"make_fact\(\s*\n?\s*'([a-z_]+)'", e)[:3])
print("\n=== explain payload 结构（前 700）===")
i = e.find("make_fact")
print(e[i:i+700])
