import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("@app.route('/batch-predict'")
print(s[i+1500:i+4200])
