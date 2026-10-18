import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("def get_predictions_from_admin")
print(s[i:i+1200])
