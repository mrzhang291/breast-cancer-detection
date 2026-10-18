import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")
for f in ["deploy/deploy.sh", "deploy/nginx.conf", "deploy/breast-cancer.service", "deploy/backup.sh"]:
    data = io.open(f, "rb").read()
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n")
    print("%-34s CRLF=%d  LF=%d  -> %s" % (f, crlf, lf, "CRLF(需修)" if crlf else "LF(OK)"))
