"""
简化的SHAP 可解释AI模块 - 用于乳腺癌预测的特征解释
避免matplotlib启动时导入问题
"""
import os
import json
import numpy as np
import pandas as pd
# 完全移除matplotlib导入，避免启动问题
# from implementation import random_forest_train, sc
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# 特征名称（与数据集对应）
FEATURE_NAMES = [
    'radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean',
    'smoothness_mean', 'compactness_mean', 'concavity_mean', 'concave points_mean',
    'symmetry_mean', 'fractal_dimension_mean', 'radius_se', 'texture_se',
    'perimeter_se', 'area_se', 'smoothness_se', 'compactness_se',
    'concavity_se', 'concave points_se', 'symmetry_se', 'fractal_dimension_se',
    'radius_worst', 'texture_worst', 'perimeter_worst', 'area_worst',
    'smoothness_worst', 'compactness_worst', 'concavity_worst', 'concave_worst',
    'symmetry_worst', 'fractal_dimension_worst'
]

SHAP_OUTPUT_DIR = 'static/shap'
DIAGNOSIS_TO_TEXT = {0: '良性 (Benign)', 1: '恶性 (Malignant)'}

# 创建输出目录
os.makedirs(SHAP_OUTPUT_DIR, exist_ok=True)


class SimpleSHAPExplainer:
    """简化的SHAP解释器类 - 使用特征重要性近似SHAP值"""

    def __init__(self, clf=None):
        """
        初始化简化解释器
        :param clf: 训练好的分类器
        """
        self.scaler = StandardScaler()

        # 训练数据用于计算基准
        dataset = pd.read_csv('Breast Cancer Data.csv')
        X = dataset.iloc[:, 2:32].values
        y = dataset.iloc[:, 1].values

        from sklearn.preprocessing import LabelEncoder
        labelencoder_X_1 = LabelEncoder()
        y = labelencoder_X_1.fit_transform(y)

        self.scaler.fit(X)  # 拟合缩放器
        X_scaled = self.scaler.transform(X)

        # 始终使用本地训练的分类器（避免版本兼容性问题）
        self.clf = RandomForestClassifier(n_estimators=100, random_state=42)
        self.clf.fit(X_scaled, y)

        # 计算特征重要性（近似SHAP值）
        self.feature_importance = self.clf.feature_importances_

        # 计算基准预测概率
        self.baseline_proba = np.mean(self.clf.predict_proba(X_scaled), axis=0)

    def explain_single_prediction(self, raw_input_data, prediction, confidence):
        """
        为单条预测生成简化解释
        :param raw_input_data: 原始输入数据(未缩放) - 30个特征列表
        :param prediction: 预测结果 'Benign' 或 'Malignant'
        :param confidence: 置信度
        :return: 返回包含解释数据的字典
        """
        # 数据缩放
        X_sample = np.asarray(raw_input_data, dtype=float).reshape(1, -1)
        raw_values = np.asarray(raw_input_data, dtype=float)
        X_sample_scaled = self.scaler.transform(X_sample)

        # 获取预测概率
        proba = self.clf.predict_proba(X_sample_scaled)[0]

        # 确定分类标签
        prediction_label = 1 if prediction == 'Malignant' else 0

        # 简化的SHAP值计算（基于特征重要性和预测差异）
        shap_values = self._calculate_simple_shap(X_sample_scaled[0], prediction_label)

        # 生成简化图表（文本描述）
        # 注意：展示给用户的一律是原始量纲数值，而不是标准化后的 z-score
        explanation_data = self._generate_text_explanation(
            shap_values, raw_values, prediction_label
        )

        # 提取顶部特征信息
        top_features = self._get_top_features(shap_values, raw_values)

        return {
            'prediction': prediction,
            'confidence': confidence,
            'top_features': top_features,
            'explanation': explanation_data,
            'baseline_proba': float(self.baseline_proba[prediction_label]),
            'prediction_proba': float(proba[prediction_label])
        }

    def _calculate_simple_shap(self, feature_values, prediction_label):
        """
        计算简化的SHAP值
        使用特征重要性乘以特征值作为近似
        """
        # 标准化特征值
        feature_means = np.mean(self.scaler.transform(
            pd.read_csv('Breast Cancer Data.csv').iloc[:, 2:32].values
        ), axis=0)

        # 计算特征偏离均值的程度
        deviations = feature_values - feature_means

        # SHAP值近似：重要性 × 偏离程度 × 预测方向
        shap_values = self.feature_importance * deviations

        # SHAP值的符号直接表示特征对恶性预测的影响：
        # 正SHAP值：特征值增加恶性概率（推向恶性）
        # 负SHAP值：特征值降低恶性概率（推向良性）
        # 不根据预测结果调整符号，保持客观反映特征的实际影响

        return shap_values

    def _generate_text_explanation(self, shap_values, feature_values, prediction_label):
        """生成文本形式的解释"""
        abs_shap = np.abs(shap_values)
        top_indices = np.argsort(abs_shap)[::-1][:5]  # 前5个最重要的特征

        explanation = {
            'summary': f"模型预测为{'恶性' if prediction_label else '良性'}，置信度基于以下关键特征：",
            'top_features': []
        }

        for i, idx in enumerate(top_indices):
            feature_name = FEATURE_NAMES[idx]
            feature_value = feature_values[idx]
            shap_value = shap_values[idx]
            importance = abs_shap[idx]

            direction = "推向恶性" if shap_value > 0 else "推向良性"

            explanation['top_features'].append({
                'rank': i + 1,
                'name': feature_name,
                'value': float(feature_value),
                'importance': float(importance),
                'direction': direction,
                'shap_value': float(shap_value)
            })

        return explanation

    def _get_top_features(self, shap_values, feature_values, top_k=6):
        """
        提取顶部特征
        :param shap_values: SHAP值数组
        :param feature_values: 特征值数组
        :param top_k: 返回前k个特征（增加数量以便显示对立方向的特征）
        :return: 特征列表
        """
        abs_shap = np.abs(shap_values)
        top_indices = np.argsort(abs_shap)[::-1][:top_k]

        top_features = []
        for idx in top_indices:
            top_features.append({
                'name': FEATURE_NAMES[idx],
                'value': float(feature_values[idx]),
                'shap_value': float(shap_values[idx]),
                'importance': float(abs_shap[idx]),
                'direction': '↑ 推向恶性' if shap_values[idx] > 0 else '↓ 推向良性'
            })

        return top_features


def get_feature_explanation(prediction_dict):
    """
    获取特征解释数据（不需要生成新的图表）
    用于在结果页面快速显示信息
    """
    raw_data = prediction_dict.get('data', [])
    output = prediction_dict.get('output', 'Unknown')
    confidence = prediction_dict.get('confidence', 0)

    if not raw_data or len(raw_data) != 30:
        return None

    # 创建简化的解释器
    explainer = SimpleSHAPExplainer()

    # 获取解释
    explanation = explainer.explain_single_prediction(raw_data, output, confidence)

    return {
        'prediction': output,
        'confidence': confidence,
        'top_features': explanation['top_features']
    }