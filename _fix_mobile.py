import io, sys
sys.stdout.reconfigure(encoding="utf-8")

FIX = """
    <style>
        /* 移动端与横向溢出修正 */
        body { overflow-x: hidden; }
        .shell > * { min-width: 0; }
        .panel { width: 100%; }
        .form-card { min-width: 0; }

        @media (max-width: 920px) {
            .panel { padding: 76px 18px 40px; }
            .form-card { max-width: 100%; }
            .lang-switch { top: 14px; right: 14px; left: auto; }
            .lang-switch button { padding: 6px 11px; font-size: 11.5px; }
            .form-head h2 { font-size: 24px; }
        }
    </style>
"""

for name in ("login.html", "register.html"):
    p = "templates/" + name
    s = io.open(p, encoding="utf-8").read()
    if "移动端与横向溢出修正" in s:
        print("[skip]", name)
        continue
    s = s.replace("</head>", FIX + "</head>", 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("[ok  ]", name, "已加修正样式")
