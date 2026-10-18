import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\db.py", encoding="utf-8").read()
print("缓存表:", re.findall(r"CREATE TABLE IF NOT EXISTS (\w*cache\w*)", s))
print("CACHE_VERSION:", re.findall(r"CACHE_VERSION\s*=\s*['\"]([^'\"]+)", io.open(r"agent\cache.py", encoding="utf-8").read()))
