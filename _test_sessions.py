import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent import db
db.init_schema()
sid = db.create_session("3", "测试会话")
db.add_message(sid, "user", "你好")
db.add_message(sid, "assistant", "你好呀")
print("创建:", sid)
print("列表:", [(s["id"], s["title"], s["messages"]) for s in db.list_sessions("3")])
print("消息:", [(m["role"], m["content"]) for m in db.list_messages(sid)])
print("删除:", db.delete_session(sid, "3"))
print("删除后:", db.list_sessions("3"))
