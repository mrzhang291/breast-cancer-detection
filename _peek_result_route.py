import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("@app.route('/result')")
print(s[i:i+900])
