import io, sys
sys.stdout.reconfigure(encoding="utf-8")
a = io.open(r"app.py", encoding="utf-8").read()
i = a.find("@app.route('/api/samples/random'")
seg = a[i:i+2200]
j = seg.find("return jsonify")
print(seg[j-500:j+400])
