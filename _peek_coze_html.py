import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("admin_backend/templates/coze_chat.html", encoding="utf-8").read()
print("textarea/input:", re.findall(r"<(textarea|input)[^>]*>", s)[:6])
print("ids:", re.findall(r"id=\"([^\"]+)\"", s)[:20])
print("点击发送函数:", re.findall(r"function (\w+)\(", s)[:12])
print("chat 请求:", s.count("/api/coze/chat"), "| 消息容器 class:", re.findall(r"class=\"(msg[^\"]*|chat[^\"]*|bubble[^\"]*)\"", s)[:8])
