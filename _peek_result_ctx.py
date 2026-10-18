import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("render_template('result.html'")
print(s[i:i+500])
print("\n=== last_prediction 写入处 ===")
j = s.find("session['last_prediction']")
print(s[max(0,j-300):j+500])
