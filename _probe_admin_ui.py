import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
root = "admin_backend"
html = []
for cur, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "instance")]
    for f in files:
        p = os.path.join(cur, f)
        if f.endswith((".html", ".js")):
            html.append(p)
print("前端文件数:", len(html))
for p in html[:12]:
    print("  ", p, os.path.getsize(p)//1024, "KB")

abs_refs = rel_refs = api_calls = 0
sample = []
for p in html:
    s = open(p, encoding="utf-8", errors="ignore").read()
    abs_refs += len(re.findall(r'(?:href|src|action)="/', s))
    rel_refs += len(re.findall(r'(?:href|src|action)="(?!\/|http|#)', s))
    api_calls += len(re.findall(r'[\'"`]/api/', s))
    for m in re.finditer(r'[\'"`](/api/[a-zA-Z0-9_/\-]*)', s):
        if len(sample) < 6:
            sample.append(m.group(1))
print("\n模板中绝对路径:", abs_refs, " 相对路径:", rel_refs, " /api 调用:", api_calls)
print("接口示例:", sample)
