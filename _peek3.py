import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")
needles = ["详细的医学分析", "AI 将提供", "AI将提供", "医学分析和见解", "deep_analysis_desc"]
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "myenv310", "node_modules")]
    for f in files:
        if not f.endswith((".html", ".py", ".json")):
            continue
        p = os.path.join(root, f)
        try:
            s = io.open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for n in needles:
            if n in s:
                idx = s.find(n)
                print("HIT", p, "|", n, "|", repr(s[max(0,idx-120):idx+120]))
