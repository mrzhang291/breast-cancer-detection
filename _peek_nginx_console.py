import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"deploy\nginx.conf", encoding="utf-8").read()
i = s.find("location /console/")
print(s[i:i+320])
