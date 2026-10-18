import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
paths = sorted(set(re.findall(r"ADMIN_API_URL\s*\+\s*['\"]([^'\"]+)", s)))
for p in paths:
    print("  /api" + p)
for name in ("get_predictions_from_admin", "get_statistics_from_admin", "register_user_on_admin", "get_admin_token"):
    i = s.find("def %s(" % name)
    if i > 0:
        seg = s[i:i+600]
        m = re.findall(r"['\"](/api/[a-zA-Z0-9_/<>\-]+)['\"]", seg)
        print("%-28s %s" % (name, m[:3]))
