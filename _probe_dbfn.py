import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
d = io.open(r"agent\db.py", encoding="utf-8").read()
print("db 函数:", re.findall(r"^def ([a-z_]+)\(", d, re.M))
