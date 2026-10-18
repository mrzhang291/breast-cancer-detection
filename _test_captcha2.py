import sys
sys.stdout.reconfigure(encoding="utf-8")
from app import app

with app.test_client() as c:
    r = c.get("/login")
    print("GET /login:", r.status_code, "含验证码:", 'id="captcha"' in r.get_data(as_text=True))

    r = c.get("/captcha.png")
    print("GET /captcha.png:", r.status_code, r.headers.get("Content-Type"))

    with c.session_transaction() as sess:
        code = sess.get("captcha")
    print("session 中的验证码:", code)

    r = c.post("/login", data={"username": "admin", "password": "admin123", "captcha": code.lower()},
               follow_redirects=False)
    print("用正确验证码登录（小写输入）:", r.status_code, r.headers.get("Location"))

with app.test_client() as c:
    c.get("/captcha.png")
    with c.session_transaction() as sess:
        code = sess.get("captcha")
    r = c.post("/login", data={"username": "admin", "password": "admin123", "captcha": "ZZZZ"},
               follow_redirects=False)
    print("错误验证码登录:", r.status_code, "提示:", "验证码不正确" in r.get_data(as_text=True))

    # 验证码一次性：用过之后再提交同一 code 应失败
    r2 = c.post("/login", data={"username": "admin", "password": "admin123", "captcha": code},
                follow_redirects=False)
    print("重复使用旧验证码:", "验证码不正确" in r2.get_data(as_text=True))
