import io, sys
sys.stdout.reconfigure(encoding="utf-8")
src = io.open("app.py", encoding="utf-8").read()
for key in ["预测结果:", "'confidence': confidence", "prediction_data.get('confidence'", "render_template('result.html', output=output"]:
    i = src.find(key)
    print("KEY:", key, "->", i)
    if i >= 0:
        print(repr(src[max(0,i-120):i+160]))
    print("-" * 60)
