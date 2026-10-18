import sys, io, os
sys.stdout.reconfigure(encoding="utf-8")
import reporting
pdf = reporting.Report()
print("font_ok:", pdf.font_ok, "| font_path 存在:", os.path.exists(reporting.FONT_PATH))
pdf.add_page()
pdf.use(9)
print("w:", pdf.w, "x:", pdf.x, "l:", pdf.l_margin, "r:", pdf.r_margin)
pdf.cell(38, 6.5, "结果")
print("after cell x:", pdf.x)
try:
    pdf.multi_cell(0, 6.5, "恶性")
    print("multi_cell OK, x:", pdf.x)
except Exception as exc:
    print("multi_cell 失败:", exc)
