import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\cache.py", encoding="utf-8").read()
print(re.findall(r"CACHE_VERSION\s*=\s*['\"]([^'\"]+)", s))
