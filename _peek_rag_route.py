import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("api_rag_search")
print(s[max(0,i-200):i+700])
j = s.find("def knowledge_page")
print("\n=== knowledge_page ===\n", s[j:j+700])
