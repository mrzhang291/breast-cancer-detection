import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"admin_backend\api\prediction_api.py", encoding="utf-8").read()
i = s.find("def get_public_user_predictions")
print(s[i:i+2000])
