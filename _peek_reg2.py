import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"templates\register.html", encoding="utf-8").read()
body = s[s.index("<body"):]
print(body[2600:6020])
