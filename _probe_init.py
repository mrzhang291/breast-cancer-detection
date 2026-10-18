import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\db.py", encoding="utf-8").read()
i = s.find("def init_schema(")
print("=== init_schema ===")
print(s[i:i+600])
j = s.find("def get_run(")
print("=== get_run ===")
print(s[j:j+400])
