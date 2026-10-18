import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"admin_backend\api\prediction_api.py", encoding="utf-8").read()
i = s.find("public/user/predictions")
print(s[max(0,i-300):i+900] if i>0 else "未找到，搜索其它文件")
