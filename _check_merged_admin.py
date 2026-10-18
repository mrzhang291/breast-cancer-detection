import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"admin_backend\templates\admin.html", encoding="utf-8").read()
print("长度:", len(s))
print("冲突标记 <<<<<<<:", s.count("<<<<<<<"), "=======:", s.count(">>>>>>>"))
print("/console/ 出现:", s.count("/console/"))
print("首 200 字符:", s[:200].replace("\n", " "))
