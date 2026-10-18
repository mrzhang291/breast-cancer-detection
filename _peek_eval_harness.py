import io, sys
sys.stdout.reconfigure(encoding="utf-8")
src = io.open("agent/eval/run_eval.py", encoding="utf-8").read()
print(src[:2200])
