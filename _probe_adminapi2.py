import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
for name in ("get_predictions_from_admin", "get_statistics_from_admin", "register_user_on_admin", "get_admin_token", "delete_prediction_from_admin", "clear_all_predictions_from_admin"):
    i = s.find("def %s(" % name)
    if i < 0:
        print(name, "未找到")
        continue
    seg = s[i:i+900]
    url = re.findall(r"['\"](/[a-zA-Z0-9_/<>{}\-]+)['\"]", seg)
    fstr = re.findall(r"f['\"]([^'\"]*api[^'\"]*)['\"]", seg)
    print("%-34s url=%s fstr=%s" % (name, url[:4], fstr[:2]))
