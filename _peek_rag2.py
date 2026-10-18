import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\rag\index.py", encoding="utf-8").read()
i = s.find("def search(")
print(s[i:i+2200])
