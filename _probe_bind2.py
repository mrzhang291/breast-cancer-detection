import io, sys
sys.stdout.reconfigure(encoding="utf-8")
a = io.open(r"app.py", encoding="utf-8").read()
i = a.find("def _agent_bind_runtime")
seg = a[i:i+3000]
j = seg.find("fetch_records")
print(seg[max(0,j-400):j+900])
