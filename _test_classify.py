import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.orchestrator import classify
for q in ("化疗副作用怎么缓解", "乳腺癌早期症状有哪些", "HER2 阳性怎么治", "怎么导出报告"):
    print(q, "->", classify(q, False))
