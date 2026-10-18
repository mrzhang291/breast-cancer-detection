import io
lines = io.open(r"agent\tests\test_agent.py", encoding="utf-8").read().splitlines()
for i in range(138, 158):
    print("%3d| %s" % (i+1, lines[i]))
