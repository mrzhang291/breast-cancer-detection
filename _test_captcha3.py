import sys
sys.stdout.reconfigure(encoding="utf-8")
from app import app, _CAPTCHA_STORE

with app.test_client() as c:
    r = c.get("/login")
    print("登录页含验证码:", 'id="captcha"' in r.get_data(as_text=True))

    r = c.get("/captcha.png")
    cid = c.get_cookie("captcha_id").value
    code = _CAPTCHA_STORE[cid][0]
    print("cookie 里的 id:", cid[:12], "... 长度", len(cid))
    print("服务端存的答案:", code)

    # 会话 cookie 里不该出现答案
    sess_cookie = c.get_cookie("session")
    leaked = bool(sess_cookie and code in sess_cookie.value)
    print("答案是否泄露到 session cookie:", leaked)

    r = c.post("/login", data={"username": "admin", "password": "admin123", "captcha": code},
               follow_redirects=False)
    print("正确验证码登录:", r.status_code, r.headers.get("Location"))

    print("用过之后是否作废:", cid not in _CAPTCHA_STORE)

with app.test_client() as c:
    c.get("/captcha.png")
    r = c.post("/login", data={"username": "admin", "password": "admin123", "captcha": "AAAA"},
               follow_redirects=False)
    print("错误验证码登录:", r.status_code, "提示:", "验证码不正确" in r.get_data(as_text=True))

with app.test_client() as c:
    r = c.post("/login", data={"username": "admin", "password": "admin123", "captcha": "AAAA"},
               follow_redirects=False)
    print("完全没取验证码就提交:", "验证码不正确" in r.get_data(as_text=True))
