import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
print("simhei 出现:", s.lower().count("simhei"))
for m in re.finditer(r".{60}simhei.{40}", s, re.I):
    print("  ", m.group(0).replace("\n", " ")[:120])
print("\nbatch_results 读取处:")
for m in re.finditer(r".{80}session\[.batch_results.\].{40}", s):
    print("  ", m.group(0).replace("\n", " ")[:150])
