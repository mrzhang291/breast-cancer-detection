import sys
sys.stdout.reconfigure(encoding="utf-8")
import app as appmod
client = appmod.app.test_client()
with client.session_transaction() as sess:
    sess["username"] = "zcj"
    sess["user_id"] = 3
try:
    r = client.get("/features")
    print("status:", r.status_code)
    print(r.data.decode("utf-8", "ignore")[:600])
except Exception as exc:
    import traceback
    traceback.print_exc()
