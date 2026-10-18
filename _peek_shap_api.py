import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
print("=== shap/cases 路由 ===")
for m in re.finditer(r"@app\.route\('(/[^']*(shap|case|similar)[^']*)'[^)]*\)", s):
    print(" ", m.group(0)[:90])
print("\n=== last_prediction 结构 ===")
i = s.find("last_prediction")
print(s[max(0,i-200):i+400].replace("\n", " ")[:600])
print("\n=== result 渲染时传入变量 ===")
for m in re.finditer(r"render_template\('result\.html'(.*?)\)", s, re.S):
    print(m.group(0)[:400])
    break
