# SHAP 功能快速启动指南

## 🚀 30秒快速开始

### 步骤1：安装SHAP依赖
```bash
pip install shap==0.43.0
# 或更新全部依赖
pip install -r requirements.txt
```

### 步骤2：启动应用
```bash
python app.py
```
应用通常运行在 `http://localhost:5000`

### 步骤3：使用SHAP功能
1. 访问 `http://localhost:5000/` 登录
2. 填入30个肿瘤特征进行预测
3. 在结果页面点击 **"SHAP 分析"** 按钮
4. 自动跳转到SHAP可解释性分析页面

## 📊 SHAP 分析页面说明

### 三个选项卡内容

| 选项卡 | 功能 | 说明 |
|--------|------|------|
| **特征分析** | 顶部3个特征 | 显示最影响预测的特征及其方向 |
| **可视化图表** | 三种SHAP图 | Waterfall图、Bar图、Summary图 |
| **详细解释** | 结果解释 | SHAP原理及该预测的具体解释 |

### 特征方向说明
- 🔴 **红色（↑ 推向恶性）** - 该特征值较高，倾向恶性诊断
- 🟢 **绿色（↓ 推向良性）** - 该特征值较低，倾向良性诊断

## 📁 新增文件清单

✅ `shap_explainer.py` - SHAP 解释核心模块  
✅ `templates/shap_analysis.html` - 前端分析页面  
✅ `static/shap/` - 图表输出目录  
✅ `SHAP_GUIDE.md` - 完整说明文档  
✅ `QUICKSTART_SHAP.md` - 本快速指南  

## 🔧 技术细节

### 模型信息
- 模型类型: Random Forest Classifier (100 trees)
- 输入特征: 30个肿瘤特性指标
- 输出: 二分类 (0=良性, 1=恶性)
- 特征缩放: StandardScaler 标准化

### 生成的图表
```
static/shap/
├── force_plot.png      # Waterfall图 - 单样本解释
├── bar_plot.png        # Bar图 - 特征排名
└── summary_plot.png    # Summary图 - 全体重要性
```

### API 端点
```
GET  /shap-analysis      # 查看SHAP分析页面
POST /shap-generate      # 生成SHAP解释（JSON API）
GET  /shap-features      # 获取特征列表
```

## 🎯 典型工作流

```
1. 登录系统
        ↓
2. 输入30个肿瘤指标
        ↓
3. 点击预测按钮
        ↓
4. 得到预测结果页面
        ↓
5. 点击"SHAP 分析"按钮 ← 新功能！
        ↓
6. 查看可解释性分析
        ↓
7. 理解AI决策依据
```

## 💡 使用技巧

### 技巧1：快速对比
- 进行多次预测，比较不同SHAP分析结果
- 理解特征如何影响预测

### 技巧2：特征学习
- 查看Summary图，学习每个特征的整体影响
- 点击特征卡片可以查看具体值

### 技巧3：医患沟通
- 使用SHAP图表向患者解释诊断依据
- 清晰展示哪些指标更重要

## ⚠️ 重要提示

- **不是医学诊断工具** - SHAP分析仅用于学术研究和教育
- **需要专业医生** - 任何诊断都必须由医疗专业人士确认
- **基于数据模型** - 解释程度受训练数据和模型质量限制

## 🐛 常见问题

**Q: 为什么SHAP分析很慢？**  
A: 首次生成SHAP图表需要时间。后续访问会更快。

**Q: 图表文件在哪里？**  
A: 在 `static/shap/` 目录，包含PNG图像文件。

**Q: 能否修改输出路径？**  
A: 可以，编辑 `shap_explainer.py` 第20行的 `SHAP_OUTPUT_DIR`。

**Q: 支持多用户吗？**  
A: 支持，每个用户的预测都会生成独立的SHAP分析。

## 📚 了解更多

- 完整文档：查看 `SHAP_GUIDE.md`
- SHAP官方：https://shap.readthedocs.io/
- 乳腺癌诊断：https://www.cancer.org/

## ✨ 功能亮点

✨ **现代化UI** - 响应式设计，支持移动端  
✨ **三种图表** - Waterfall、Bar、Summary  
✨ **特征对比** - 直观显示推向恶性/良性的特征  
✨ **完整解释** - 详细说明结果的医学含义  
✨ **即插即用** - 无需改路径，直接集成现有项目  

---

**现在可以开始使用SHAP功能了！** 🎉

部署步骤:
```bash
# 1. 更新依赖
pip install shap==0.43.0

# 2. 启动Flask应用
python app.py

# 3. 浏览器访问
# http://localhost:5000

# 4. 登录 → 预测 → SHAP分析 ✅
```
