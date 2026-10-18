import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
print("行数:", len(o.splitlines()))

print("\n=== 公开入口函数 ===")
for m in re.finditer(r"^def ([a-z_]+)\(([^)]*)\)", o, re.M):
    print("  def %s(%s)" % (m.group(1), m.group(2)[:90]))

print("\n=== 意图识别 ===")
i = o.find("def _route")
print(o[i:i+900] if i>0 else "未找到 _route")

print("\n=== 工具注册 ===")
t = io.open(r"agent\tools\__init__.py", encoding="utf-8").read()
print(t[:800])
