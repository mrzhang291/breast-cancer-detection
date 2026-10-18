import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/result.html", encoding="utf-8").read()
for kw in ("#agentRunBtn", "#agentAskBtn", "agentCaseBtn", "agentInspectBtn", "function agentRun", "runAgent"):
    idx = [m.start() for m in re.finditer(re.escape(kw), s)]
    print("%-16s %s" % (kw, idx[:5]))
i = s.find("#agentRunBtn")
print(s[max(0,i-200):i+700])
