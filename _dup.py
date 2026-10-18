import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
src = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
for name in ["_compose_usage", "_compose_feature", "_compose_history"]:
    lines = [i+1 for i, l in enumerate(src.splitlines()) if l.startswith("def %s(" % name)]
    print(name, "定义位置:", lines)
