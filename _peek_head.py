import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/records.html", encoding="utf-8").read()
print(s[:900])
