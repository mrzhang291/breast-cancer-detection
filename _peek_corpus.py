import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\rag\corpus.py", encoding="utf-8").read()
print(s[:1800])
