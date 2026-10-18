import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
a = io.open(r"app.py", encoding="utf-8").read()
i = a.find("def batch_predict(")
seg = a[i:i+2600]
for m in re.finditer(r"results\.append\(\{(.{0,300})", seg, re.S):
    print(m.group(1)[:300])
    break
print("---")
for key in ("prediction_result", "prediction", "confidence", "file_name", "row_index"):
    print(key, "出现在 batch_predict 段:", key in seg)
