import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\llm.py", encoding="utf-8").read()
print("行数:", len(s.splitlines()))
print(s[400:2200])
print("\n=== 环境变量 DEEPSEEK_API_KEY:", "已设置" if os.environ.get("DEEPSEEK_API_KEY") else "未设置")
