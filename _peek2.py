import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
src = io.open(r"templates\result.html", encoding="utf-8").read()
i = src.find("根据你的预测结果和输入的特征数据")
print("描述文字位置:", i)
if i > 0:
    print(repr(src[i-700:i+300]))
