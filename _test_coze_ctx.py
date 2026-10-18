import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "admin_backend")
from app import app
with app.app_context():
    import coze_context
    snap = coze_context.snapshot()
    for k in ("users_total", "active_users_today", "active_users_7d", "predictions_7d",
              "new_users_today", "new_users_7d", "avg_predictions_per_active_user_7d"):
        print("  %-34s %s" % (k, snap.get(k)))
    print("  assistant:", snap.get("assistant"))
    text = coze_context.prompt_context()
    print("\n活跃度提示行:")
    for line in text.splitlines():
        if "活跃" in line or "会话" in line:
            print("  ", line)
