import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("session['batch_results']")
print("剩余读取上下文:\n", s[max(0,i-300):i+200])
j = s.find("def shap_analyze_by_index")
if j < 0:
    j = s.find("@app.route('/shap-analyze/<int:index>')")
print("\n=== shap-analyze ===\n", s[j:j+900])
