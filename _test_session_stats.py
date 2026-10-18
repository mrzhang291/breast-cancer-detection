import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent import db
db.init_schema()
sid = db.create_session("3", "验证会话工具")
db.add_message(sid, "user", "你好")
db.add_message(sid, "assistant", "你好呀")
print("session_stats:", {k: v for k, v in db.session_stats("3").items() if k != "recent_sessions"})
db.delete_session(sid, "3")
