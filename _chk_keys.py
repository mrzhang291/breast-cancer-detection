import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
t = io.open("translations.py", encoding="utf-8").read()
for key in ["remember_me", "forgot_password", "join", "or", "welcome",
            "username_placeholder", "password_placeholder", "confirm_password",
            "agree_terms", "terms_of_service", "privacy_policy",
            "already_have_account", "login_now", "password_weak", "password_medium", "password_strong"]:
    print("%-26s %s" % (key, "存在" if ("'%s'" % key) in t else "缺失"))
print()
# 看 _() 实现
s = io.open("app.py", encoding="utf-8").read()
m = re.search(r"def _\(.*?\n(?:.*\n){0,8}", s)
print("=== _() 实现 ===")
print(m.group(0) if m else "未找到")
