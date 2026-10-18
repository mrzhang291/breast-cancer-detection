import io, sys
sys.stdout.reconfigure(encoding="utf-8")
a = io.open(r"app.py", encoding="utf-8").read()
i = a.find("@app.route('/api/samples/random'")
print(a[i:i+800])
