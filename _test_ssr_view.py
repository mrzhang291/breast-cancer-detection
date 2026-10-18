import sys, traceback
sys.stdout.reconfigure(encoding="utf-8")
import app as appmod
appmod.app.config["TESTING"] = True
client = appmod.app.test_client()
with client.session_transaction() as sess:
    sess["username"] = "zcj"; sess["role_id"] = 3; sess["user_id"] = 3
try:
    r = client.get("/knowledge")
    print("status", r.status_code)
    print(r.data[:300])
except Exception:
    traceback.print_exc()
