import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read().splitlines()

def show(marker, n=40):
    for i, l in enumerate(o):
        if marker in l:
            print("=== %s (行 %d) ===" % (marker, i+1))
            print("\n".join(o[i:i+n]))
            print()
            return
    print("未找到", marker)

show("INTENT = ", 14)
show("def classify(", 45)
show("def run(", 30)
