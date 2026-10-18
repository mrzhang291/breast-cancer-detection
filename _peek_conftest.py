import io, sys
sys.stdout.reconfigure(encoding="utf-8")
print(io.open(r"agent\tests\conftest.py", encoding="utf-8").read())
