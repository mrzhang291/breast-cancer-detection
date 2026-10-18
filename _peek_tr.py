import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("translations.py", encoding="utf-8").read()
print("总行数:", len(s.splitlines()))
print(s[:900])
print("...")
i = s.find("'remember_me'")
print("=== 附近 remember_me ===")
print(s[max(0,i-200):i+300])
