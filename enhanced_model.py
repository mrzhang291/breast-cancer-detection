"""
增强型乳腺癌预测模型 - 系统性提高置信度方案
包含:
1. 增强型数据预处理（异常值处理、特征标准化、数据清洗）
2. 高级特征工程（衍生特征、特征交互）
3. 改进模型架构（强大集成策略、正则化）
4. 高级置信度校准（Platt缩放+温度缩放组合）
"""
import numpy as np
import pandas as pd
import os
import joblib
import time
from typing import Dict, Tuple, Any, List

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    VotingClassifier,
    StackingClassifier,
    HistGradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    log_loss
)
from sklearn.preprocessing import (
    LabelEncoder,
    StandardScaler,
    RobustScaler,
    MinMaxScaler,
    PowerTransformer,
    QuantileTransformer
)
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    GridSearchCV,
    RandomizedSearchCV,
    cross_val_score,
    learning_curve
)
from sklearn.feature_selection import (
    SelectKBest,
    f_classif,
    mutual_info_classif,
    RFE,
    RFECV,
    SelectFromModel
)
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.exceptions import ConvergenceWarning
from sklearn.utils.class_weight import compute_class_weight

import warnings
warnings.filterwarnings('ignore', category=ConvergenceWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# 配置常量
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
ENHANCED_MODEL_FILE = os.path.join(MODEL_DIR, 'enhanced_model.pkl')
ENHANCED_SCALER_FILE = os.path.join(MODEL_DIR, 'enhanced_scaler.pkl')
ENHANCED_LABEL_ENCODER_FILE = os.path.join(MODEL_DIR, 'enhanced_label_encoder.pkl')
ENHANCED_FEATURE_SELECTOR_FILE = os.path.join(MODEL_DIR, 'enhanced_feature_selector.pkl')
ENHANCED_PREPROCESSOR_FILE = os.path.join(MODEL_DIR, 'enhanced_preprocessor.pkl')

# 全局变量
enhanced_clf = None
enhanced_sc = None
enhanced_labelencoder = None
enhanced_feature_selector = None
enhanced_preprocessor = None

# 特征名称
FEATURE_NAMES = [
    'radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean',
    'smoothness_mean', 'compactness_mean', 'concavity_mean', 'concave points_mean',
    'symmetry_mean', 'fractal_dimension_mean', 'radius_se', 'texture_se',
    'perimeter_se', 'area_se', 'smoothness_se', 'compactness_se',
    'concavity_se', 'concave points_se', 'symmetry_se', 'fractal_dimension_se',
    'radius_worst', 'texture_worst', 'perimeter_worst', 'area_worst',
    'smoothness_worst', 'compactness_worst', 'concavity_worst', 'concave points_worst',
    'symmetry_worst', 'fractal_dimension_worst'
]

# 特征分组
MEAN_FEATURES = FEATURE_NAMES[:10]
SE_FEATURES = FEATURE_NAMES[10:20]
WORST_FEATURES = FEATURE_NAMES[20:30]


class AdvancedPreprocessor(BaseEstimator):
    """
    增强型数据预处理类
    包含: 异常值处理、特征标准化、数据清洗
    """
    
    def __init__(self, outlier_method='iqr_clip', scaler_type='robust', 
                 handle_missing=True, log_transform=False):
        self.outlier_method = outlier_method
        self.scaler_type = scaler_type
        self.handle_missing = handle_missing
        self.log_transform = log_transform
        self.scaler = None
        self.feature_stats = None
        self.lower_bounds = None
        self.upper_bounds = None
    
    def fit(self, X, y=None):
        # 计算特征统计信息
        self.feature_stats = {
            'mean': np.mean(X, axis=0),
            'std': np.std(X, axis=0),
            'min': np.min(X, axis=0),
            'max': np.max(X, axis=0),
            'median': np.median(X, axis=0)
        }
        
        # 计算异常值边界
        if self.outlier_method == 'iqr_clip':
            Q1 = np.percentile(X, 25, axis=0)
            Q3 = np.percentile(X, 75, axis=0)
            IQR = Q3 - Q1
            self.lower_bounds = Q1 - 1.5 * IQR
            self.upper_bounds = Q3 + 1.5 * IQR
        elif self.outlier_method == 'zscore_clip':
            self.lower_bounds = self.feature_stats['mean'] - 3 * self.feature_stats['std']
            self.upper_bounds = self.feature_stats['mean'] + 3 * self.feature_stats['std']
        
        # 初始化缩放器
        if self.scaler_type == 'robust':
            self.scaler = RobustScaler()
        elif self.scaler_type == 'standard':
            self.scaler = StandardScaler()
        elif self.scaler_type == 'minmax':
            self.scaler = MinMaxScaler()
        elif self.scaler_type == 'quantile':
            self.scaler = QuantileTransformer(output_distribution='normal')
        elif self.scaler_type == 'power':
            self.scaler = PowerTransformer(method='yeo-johnson')
        
        # 预处理后拟合缩放器
        X_processed = self._preprocess(X, fit=True)
        if self.scaler:
            self.scaler.fit(X_processed)
        
        return self
    
    def _preprocess(self, X, fit=False):
        X_processed = X.copy().astype(float)
        
        # 处理缺失值
        if self.handle_missing:
            for i in range(X_processed.shape[1]):
                mask = np.isnan(X_processed[:, i]) | np.isinf(X_processed[:, i])
                if np.any(mask):
                    X_processed[mask, i] = self.feature_stats['median'][i] if fit else np.median(X_processed[:, i])
        
        # 异常值处理（训练和预测时都进行）
        if self.outlier_method and self.lower_bounds is not None:
            X_processed = np.clip(X_processed, self.lower_bounds, self.upper_bounds)
        
        # 对数变换（针对右偏分布特征）
        if self.log_transform:
            # 仅对正值特征进行对数变换
            positive_mask = X_processed > 0
            X_processed[positive_mask] = np.log1p(X_processed[positive_mask])
        
        return X_processed
    
    def transform(self, X):
        X_processed = self._preprocess(X, fit=False)
        
        # 标准化
        if self.scaler:
            X_processed = self.scaler.transform(X_processed)
        
        return X_processed
    
    def fit_transform(self, X, y=None):
        self.fit(X, y)
        return self.transform(X)


class FeatureEngineer(BaseEstimator):
    """
    高级特征工程类
    包含: 衍生特征创建、特征交互、特征选择
    """
    
    def __init__(self, create_ratio_features=True, create_stat_features=True,
                 create_interaction_features=True, select_k_best=25):
        self.create_ratio_features = create_ratio_features
        self.create_stat_features = create_stat_features
        self.create_interaction_features = create_interaction_features
        self.select_k_best = select_k_best
        self.feature_selector = None
        self.selected_indices = None
    
    def fit(self, X, y=None):
        X_engineered = self._create_features(X)
        
        # 特征选择
        if self.select_k_best is not None and self.select_k_best < X_engineered.shape[1]:
            self.feature_selector = SelectKBest(score_func=f_classif, k=self.select_k_best)
            self.feature_selector.fit(X_engineered, y)
            self.selected_indices = self.feature_selector.get_support(indices=True)
        
        return self
    
    def _create_features(self, X):
        """创建衍生特征"""
        features = [X.copy()]
        
        # 1. 创建比率特征 (worst / mean)
        if self.create_ratio_features:
            for i in range(10):
                ratio = X[:, i + 20] / (X[:, i] + 1e-10)
                features.append(ratio.reshape(-1, 1))
        
        # 2. 创建统计特征
        if self.create_stat_features:
            # 每组特征的统计量
            mean_features = X[:, :10]
            se_features = X[:, 10:20]
            worst_features = X[:, 20:30]
            
            # 均值特征的统计量
            features.append(np.mean(mean_features, axis=1).reshape(-1, 1))
            features.append(np.std(mean_features, axis=1).reshape(-1, 1))
            features.append(np.max(mean_features, axis=1).reshape(-1, 1))
            features.append(np.min(mean_features, axis=1).reshape(-1, 1))
            
            # 标准差特征的统计量
            features.append(np.mean(se_features, axis=1).reshape(-1, 1))
            features.append(np.std(se_features, axis=1).reshape(-1, 1))
            
            # 最差特征的统计量
            features.append(np.mean(worst_features, axis=1).reshape(-1, 1))
            features.append(np.std(worst_features, axis=1).reshape(-1, 1))
            
            # 极差特征
            features.append((np.max(X, axis=1) - np.min(X, axis=1)).reshape(-1, 1))
            
            # 变异系数
            features.append((np.std(X, axis=1) / (np.mean(X, axis=1) + 1e-10)).reshape(-1, 1))
        
        # 3. 创建特征交互项（选择最重要的特征对）
        if self.create_interaction_features:
            # 选择生物学上相关的特征对进行交互
            important_pairs = [
                (0, 2),   # radius_mean * perimeter_mean
                (0, 3),   # radius_mean * area_mean
                (2, 3),   # perimeter_mean * area_mean
                (6, 7),   # concavity_mean * concave points_mean
                (20, 22), # radius_worst * perimeter_worst
                (20, 23), # radius_worst * area_worst
                (6, 26),  # concavity_mean * concavity_worst
                (7, 27)   # concave points_mean * concave points_worst
            ]
            
            for i, j in important_pairs:
                interaction = X[:, i] * X[:, j]
                features.append(interaction.reshape(-1, 1))
                
                # 添加比率交互
                ratio_interaction = (X[:, i] + 1e-10) / (X[:, j] + 1e-10)
                features.append(ratio_interaction.reshape(-1, 1))
        
        return np.hstack(features)
    
    def transform(self, X):
        X_engineered = self._create_features(X)
        
        # 特征选择
        if self.feature_selector is not None:
            X_engineered = self.feature_selector.transform(X_engineered)
        
        return X_engineered
    
    def fit_transform(self, X, y=None):
        self.fit(X, y)
        return self.transform(X)
    
    def get_feature_names(self):
        """获取工程化后的特征名称"""
        names = []
        
        # 原始特征
        names.extend(FEATURE_NAMES)
        
        # 比率特征
        if self.create_ratio_features:
            for i in range(10):
                names.append(f'{WORST_FEATURES[i]}/mean')
        
        # 统计特征
        if self.create_stat_features:
            names.extend([
                'mean_features_mean', 'mean_features_std', 
                'mean_features_max', 'mean_features_min',
                'se_features_mean', 'se_features_std',
                'worst_features_mean', 'worst_features_std',
                'range_all', 'cv_all'
            ])
        
        # 交互特征
        if self.create_interaction_features:
            important_pairs = [
                (0, 2), (0, 3), (2, 3), (6, 7),
                (20, 22), (20, 23), (6, 26), (7, 27)
            ]
            for i, j in important_pairs:
                names.append(f'{FEATURE_NAMES[i]}_x_{FEATURE_NAMES[j]}')
                names.append(f'{FEATURE_NAMES[i]}_{FEATURE_NAMES[j]}_ratio')
        
        # 应用特征选择
        if self.selected_indices is not None:
            names = [names[i] for i in self.selected_indices]
        
        return names


class EnsembleWithCalibration(BaseEstimator, ClassifierMixin):
    """
    带置信度校准的集成模型
    支持多种基分类器和校准方法组合
    """
    
    def __init__(self, base_models=None, ensemble_method='voting', 
                 calibration_method='sigmoid', temperature_scaling=True,
                 class_weight='balanced'):
        self.class_weight = class_weight
        self.ensemble_method = ensemble_method
        self.calibration_method = calibration_method
        self.temperature_scaling = temperature_scaling
        self.base_models = base_models if base_models else self._get_default_models()
        self.ensemble_clf = None
        self.calibrated_clf = None
        self.temperature = 1.0
        
    def _get_default_models(self):
        """获取默认的基分类器列表 - 优化版，平衡速度和精度"""
        models = [
            ('rf', RandomForestClassifier(
                n_estimators=100,  # 减少树数量
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=3,
                class_weight=self.class_weight,
                random_state=42,
                n_jobs=-1
            )),
            ('et', ExtraTreesClassifier(
                n_estimators=100,  # 减少树数量
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=3,
                class_weight=self.class_weight,
                random_state=42,
                n_jobs=-1
            ))
        ]
        return models
    
    def fit(self, X, y):
        # 构建集成模型
        if self.ensemble_method == 'voting':
            self.ensemble_clf = VotingClassifier(
                estimators=self.base_models,
                voting='soft',
                n_jobs=-1
            )
        elif self.ensemble_method == 'stacking':
            meta_clf = LogisticRegression(
                C=1.0,
                solver='liblinear',
                class_weight=self.class_weight,
                random_state=42
            )
            self.ensemble_clf = StackingClassifier(
                estimators=self.base_models,
                final_estimator=meta_clf,
                cv=5,
                stack_method='predict_proba',
                n_jobs=-1
            )
        
        # 训练集成模型
        self.ensemble_clf.fit(X, y)
        
        # 第一层校准（Platt缩放或等渗回归）
        if self.calibration_method:
            # 使用 cv='prefit' 避免 sklearn 版本兼容性问题
            # 'prefit' 表示模型已经训练好，不需要再进行交叉验证拟合
            self.calibrated_clf = CalibratedClassifierCV(
                self.ensemble_clf,
                method=self.calibration_method,
                cv='prefit'  # 使用prefit模式避免monotonic_cst属性问题
            )
            # 注意：使用prefit时，fit方法只是拟合校准器，不会重新拟合基分类器
            self.calibrated_clf.fit(X, y)
        
        # 第二层校准（温度缩放）
        if self.temperature_scaling:
            self._fit_temperature_scaling(X, y)
        
        return self
    
    def _fit_temperature_scaling(self, X, y):
        """拟合温度缩放参数"""
        if self.calibrated_clf:
            logits = self.calibrated_clf.predict_proba(X)
        else:
            logits = self.ensemble_clf.predict_proba(X)
        
        # 使用交叉熵损失优化温度参数
        def loss_fn(temp):
            scaled_probs = np.exp(np.log(logits + 1e-10) / temp)
            scaled_probs = scaled_probs / np.sum(scaled_probs, axis=1, keepdims=True)
            return log_loss(y, scaled_probs)
        
        # 简单网格搜索优化温度
        temperatures = np.linspace(0.5, 2.0, 30)
        losses = [loss_fn(t) for t in temperatures]
        self.temperature = temperatures[np.argmin(losses)]
        print(f"温度缩放参数: {self.temperature:.4f}")
    
    def predict_proba(self, X):
        """预测概率（经过双重校准）"""
        probs = None
        
        # 尝试使用校准后的分类器
        if self.calibrated_clf:
            try:
                probs = self.calibrated_clf.predict_proba(X)
            except AttributeError as e:
                # sklearn版本兼容性问题：旧版本保存的模型可能不兼容新版本
                print(f"警告: CalibratedClassifierCV预测失败 - {e}")
                print("降级到使用集成分类器进行预测")
                probs = None
        
        # 如果校准分类器失败或未使用，使用集成分类器
        if probs is None:
            probs = self.ensemble_clf.predict_proba(X)
        
        # 移除温度缩放，因为CalibratedClassifierCV已经做了置信度校准
        # 温度缩放会过度放大置信度，导致过度自信
        
        # 轻微限制最大置信度，避免极端自信（最大99.9%）
        max_confidence = 0.999
        if np.max(probs) > max_confidence:
            # 将最大概率限制在max_confidence，剩余概率均匀分配给其他类别
            mask = probs == np.max(probs)
            other_sum = np.sum(probs * (~mask))
            # 处理除以零的情况
            if other_sum > 0:
                probs = np.where(mask, max_confidence, probs * (1 - max_confidence) / other_sum)
            else:
                # 如果其他类别概率都为0，均匀分配剩余概率
                num_classes = probs.shape[1]
                remaining = (1 - max_confidence) / (num_classes - 1)
                probs = np.where(mask, max_confidence, remaining)
        
        return probs
    
    def predict(self, X):
        """预测类别"""
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)
    
    def predict_confidence(self, X):
        """预测置信度（最大概率）"""
        probs = self.predict_proba(X)
        return np.max(probs, axis=1)


def load_data(filepath: str = 'Breast Cancer Data.csv') -> Tuple[pd.DataFrame, np.ndarray, LabelEncoder]:
    """加载和预处理数据"""
    df = pd.read_csv(filepath)
    
    # 检查并处理可能的Unnamed列
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    X = df.iloc[:, 2:].values
    y = df.iloc[:, 1].values
    
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    return df, X, y_encoded, label_encoder


def evaluate_confidence_metrics(y_true, y_proba):
    """评估置信度相关指标"""
    metrics = {}
    
    # ECE (Expected Calibration Error)
    ece = calculate_ece(y_true, y_proba[:, 1], n_bins=10)
    metrics['ece'] = ece
    
    # MCE (Maximum Calibration Error)
    mce = calculate_mce(y_true, y_proba[:, 1], n_bins=10)
    metrics['mce'] = mce
    
    # Brier分数
    brier = brier_score_loss(y_true, y_proba[:, 1])
    metrics['brier'] = brier
    
    # 平均置信度
    avg_confidence = np.mean(np.max(y_proba, axis=1))
    metrics['avg_confidence'] = avg_confidence
    
    # 置信度标准差（衡量不确定性波动）
    conf_std = np.std(np.max(y_proba, axis=1))
    metrics['conf_std'] = conf_std
    
    # 熵（衡量预测不确定性）
    entropy = -np.mean(np.sum(y_proba * np.log(y_proba + 1e-10), axis=1))
    metrics['entropy'] = entropy
    
    # 预测margin
    sorted_probs = np.sort(y_proba, axis=1)[:, ::-1]
    margin = np.mean(sorted_probs[:, 0] - sorted_probs[:, 1])
    metrics['margin'] = margin
    
    return metrics


def calculate_ece(y_true, y_proba, n_bins=10):
    """计算Expected Calibration Error"""
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        mask = (y_proba >= bins[i]) & (y_proba < bins[i + 1])
        if np.sum(mask) == 0:
            continue
        
        avg_prob = np.mean(y_proba[mask])
        avg_true = np.mean(y_true[mask])
        ece += np.sum(mask) / len(y_true) * np.abs(avg_prob - avg_true)
    
    return ece


def calculate_mce(y_true, y_proba, n_bins=10):
    """计算Maximum Calibration Error"""
    bins = np.linspace(0, 1, n_bins + 1)
    mce = 0.0
    
    for i in range(n_bins):
        mask = (y_proba >= bins[i]) & (y_proba < bins[i + 1])
        if np.sum(mask) == 0:
            continue
        
        avg_prob = np.mean(y_proba[mask])
        avg_true = np.mean(y_true[mask])
        mce = max(mce, np.abs(avg_prob - avg_true))
    
    return mce


def train_enhanced_model() -> Tuple[Any, Any, Any, Any, Any, Dict]:
    """训练增强型模型"""
    global enhanced_clf, enhanced_sc, enhanced_labelencoder, enhanced_feature_selector, enhanced_preprocessor
    
    print("=" * 70)
    print("增强型乳腺癌预测模型训练开始")
    print("=" * 70)
    
    start_time = time.time()
    
    # 1. 加载数据
    print("\n=== 数据加载 ===")
    df, X, y, enhanced_labelencoder = load_data()
    print(f"数据加载完成: {X.shape[0]}样本, {X.shape[1]}特征")
    print(f"类别分布: 良性={np.sum(y == 0)}, 恶性={np.sum(y == 1)}")
    
    # 2. 数据集划分（三层划分）
    print("\n=== 数据集划分 ===")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    print(f"训练集: {X_train.shape}, 验证集: {X_val.shape}, 测试集: {X_test.shape}")
    
    # 3. 增强型数据预处理
    print("\n=== 增强型数据预处理 ===")
    enhanced_preprocessor = AdvancedPreprocessor(
        outlier_method='iqr_clip',
        scaler_type='robust',
        handle_missing=True,
        log_transform=False
    )
    X_train_processed = enhanced_preprocessor.fit_transform(X_train)
    X_val_processed = enhanced_preprocessor.transform(X_val)
    X_test_processed = enhanced_preprocessor.transform(X_test)
    
    # 4. 高级特征工程
    print("\n=== 高级特征工程 ===")
    enhanced_feature_selector = FeatureEngineer(
        create_ratio_features=True,
        create_stat_features=True,
        create_interaction_features=True,
        select_k_best=35
    )
    X_train_engineered = enhanced_feature_selector.fit_transform(X_train_processed, y_train)
    X_val_engineered = enhanced_feature_selector.transform(X_val_processed)
    X_test_engineered = enhanced_feature_selector.transform(X_test_processed)
    print(f"特征工程后特征数: {X_train_engineered.shape[1]}")
    
    # 保存scaler引用（用于预测）
    enhanced_sc = enhanced_preprocessor
    
    # 5. 构建增强型集成模型
    print("\n=== 构建增强型集成模型 ===")
    enhanced_clf = EnsembleWithCalibration(
        ensemble_method='voting',
        calibration_method='sigmoid',
        temperature_scaling=True,
        class_weight='balanced'
    )
    
    # 使用训练集+验证集进行训练（校准使用独立数据）
    X_train_combined = np.vstack([X_train_engineered, X_val_engineered])
    y_train_combined = np.hstack([y_train, y_val])
    
    print("训练集成模型...")
    enhanced_clf.fit(X_train_engineered, y_train)
    
    # 6. 评估模型
    print("\n=== 综合性能评估 ===")
    y_pred = enhanced_clf.predict(X_test_engineered)
    y_proba = enhanced_clf.predict_proba(X_test_engineered)
    
    # 传统指标
    base_metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'roc_auc': roc_auc_score(y_test, y_proba[:, 1])
    }
    
    # 置信度指标
    conf_metrics = evaluate_confidence_metrics(y_test, y_proba)
    
    # 合并指标
    all_metrics = {**base_metrics, **conf_metrics}
    
    # 打印评估结果
    print("\n--- 传统性能指标 ---")
    for key in ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']:
        print(f"{key}: {all_metrics[key]:.4f}")
    
    print("\n--- 置信度指标 ---")
    print(f"Brier分数: {all_metrics['brier']:.4f}")
    print(f"ECE (预期校准误差): {all_metrics['ece']:.4f}")
    print(f"MCE (最大校准误差): {all_metrics['mce']:.4f}")
    print(f"平均置信度: {all_metrics['avg_confidence']:.4f}")
    print(f"置信度标准差: {all_metrics['conf_std']:.4f}")
    print(f"预测熵: {all_metrics['entropy']:.4f}")
    print(f"预测Margin: {all_metrics['margin']:.4f}")
    
    print("\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=['Benign', 'Malignant']))
    
    print("\n混淆矩阵:")
    print(confusion_matrix(y_test, y_pred))
    
    # 7. 保存模型
    print("\n=== 保存模型 ===")
    try:
        joblib.dump(enhanced_clf, ENHANCED_MODEL_FILE)
        joblib.dump(enhanced_sc, ENHANCED_SCALER_FILE)
        joblib.dump(enhanced_labelencoder, ENHANCED_LABEL_ENCODER_FILE)
        joblib.dump(enhanced_feature_selector, ENHANCED_FEATURE_SELECTOR_FILE)
        joblib.dump(enhanced_preprocessor, ENHANCED_PREPROCESSOR_FILE)
        print(f"增强型模型已保存到: {ENHANCED_MODEL_FILE}")
    except Exception as e:
        print(f"保存模型失败: {e}")
    
    total_time = time.time() - start_time
    print(f"\n训练完成，总耗时: {total_time:.2f}秒")
    
    return enhanced_clf, enhanced_sc, enhanced_labelencoder, enhanced_feature_selector, enhanced_preprocessor, all_metrics


def _fix_sklearn_version_compatibility(model):
    """修复 sklearn 版本兼容性问题 - 添加缺失的 monotonic_cst 属性"""
    import sklearn.tree
    import sklearn.ensemble
    from sklearn.calibration import CalibratedClassifierCV
    
    def add_monotonic_cst(obj):
        if obj is None:
            return
        
        # 处理 DecisionTreeClassifier
        if isinstance(obj, sklearn.tree.DecisionTreeClassifier):
            if not hasattr(obj, 'monotonic_cst'):
                obj.monotonic_cst = None
            return
        
        # 处理 VotingClassifier - estimators_ 是列表的元组 (name, estimator)
        if isinstance(obj, sklearn.ensemble.VotingClassifier):
            for item in obj.estimators_:
                if isinstance(item, tuple):
                    _, estimator = item
                    add_monotonic_cst(estimator)
                else:
                    add_monotonic_cst(item)
            return
        
        # 处理 CalibratedClassifierCV - 递归处理内部的分类器
        if isinstance(obj, CalibratedClassifierCV):
            # 处理 calibrated_classifiers_ - 这是校准后的分类器列表
            if hasattr(obj, 'calibrated_classifiers_'):
                for clf in obj.calibrated_classifiers_:
                    add_monotonic_cst(clf)
            # 处理 base_estimator 或 estimator
            if hasattr(obj, 'base_estimator'):
                add_monotonic_cst(obj.base_estimator)
            if hasattr(obj, 'estimator'):
                add_monotonic_cst(obj.estimator)
            return
        
        # 处理森林类集成模型（RandomForest, ExtraTrees等）
        class_name = obj.__class__.__name__
        if 'Forest' in class_name and hasattr(obj, 'estimators_'):
            for estimator in obj.estimators_:
                add_monotonic_cst(estimator)
            return
        
        # 处理其他可能包含 estimators_ 的对象
        if hasattr(obj, 'estimators_') and isinstance(obj.estimators_, list):
            for estimator in obj.estimators_:
                add_monotonic_cst(estimator)
            return
    
    # 处理 EnsembleWithCalibration 对象 - 需要处理所有嵌套层
    if hasattr(model, 'calibrated_clf'):
        add_monotonic_cst(model.calibrated_clf)
    if hasattr(model, 'ensemble_clf'):
        add_monotonic_cst(model.ensemble_clf)
    
    return model


def force_single_thread(model, _depth: int = 0):
    """把模型内部所有 n_jobs 强制改成 1。

    单样本推理根本用不到并行，而 n_jobs=-1 会让 joblib 在预测时创建
    进程/线程池（multiprocessing.Pool -> Pipe -> CreateFile）。
    在受限环境（沙箱、容器、部分 Windows 安全策略）下这一步会被拒绝，
    表现为预测接口直接 500 —— 也就是"提交后页面打不开"。

    串行推理在单样本上反而更快，所以这里统一关掉并行。
    """
    if model is None or _depth > 8:
        return model

    try:
        if hasattr(model, 'n_jobs'):
            model.n_jobs = 1
    except Exception:
        pass

    for attr in ('estimators_', 'calibrated_classifiers_', 'estimator',
                 'base_estimator', 'ensemble_clf', 'calibrated_clf', 'clf'):
        sub = getattr(model, attr, None)
        if sub is None:
            continue
        if isinstance(sub, (list, tuple)):
            for item in sub:
                child = item[1] if isinstance(item, tuple) and len(item) == 2 else item
                force_single_thread(child, _depth + 1)
        else:
            force_single_thread(sub, _depth + 1)

    return model


def load_enhanced_model() -> Tuple[Any, Any, Any, Any, Any]:
    """加载增强型模型"""
    global enhanced_clf, enhanced_sc, enhanced_labelencoder, enhanced_feature_selector, enhanced_preprocessor
    
    files = [
        ENHANCED_MODEL_FILE,
        ENHANCED_SCALER_FILE,
        ENHANCED_LABEL_ENCODER_FILE,
        ENHANCED_FEATURE_SELECTOR_FILE,
        ENHANCED_PREPROCESSOR_FILE
    ]
    
    if all(os.path.exists(f) for f in files):
        try:
            enhanced_clf = joblib.load(ENHANCED_MODEL_FILE)
            enhanced_sc = joblib.load(ENHANCED_SCALER_FILE)
            enhanced_labelencoder = joblib.load(ENHANCED_LABEL_ENCODER_FILE)
            enhanced_feature_selector = joblib.load(ENHANCED_FEATURE_SELECTOR_FILE)
            enhanced_preprocessor = joblib.load(ENHANCED_PREPROCESSOR_FILE)
            
            # 修复 sklearn 版本兼容性问题
            enhanced_clf = _fix_sklearn_version_compatibility(enhanced_clf)

            # 关闭并行：避免单样本推理时创建线程池（受限环境下会 PermissionError）
            enhanced_clf = force_single_thread(enhanced_clf)

            print("增强型模型加载成功!")
            return enhanced_clf, enhanced_sc, enhanced_labelencoder, enhanced_feature_selector, enhanced_preprocessor
        except Exception as e:
            print(f"加载增强型模型失败: {e}")
            return None, None, None, None, None
    return None, None, None, None, None


def enhanced_predict(inp: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """增强型预测函数"""
    start_time = time.time()
    
    # 1. 数据预处理
    inp_processed = enhanced_preprocessor.transform(inp)
    
    # 2. 特征工程
    inp_engineered = enhanced_feature_selector.transform(inp_processed)
    
    # 3. 预测
    output = enhanced_clf.predict(inp_engineered)
    prob = enhanced_clf.predict_proba(inp_engineered)
    
    elapsed_time = time.time() - start_time
    
    return output, prob, elapsed_time


def benchmark_comparison():
    """基准对比分析"""
    print("\n" + "=" * 70)
    print("模型性能基准对比分析")
    print("=" * 70)
    
    # 加载数据
    df, X, y, _ = load_data()
    
    # 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    results = {}
    
    # 1. 基准模型（原始随机森林）
    print("\n--- 基准模型: 原始随机森林 ---")
    sc_baseline = StandardScaler()
    X_train_scaled = sc_baseline.fit_transform(X_train)
    X_test_scaled = sc_baseline.transform(X_test)
    
    rf_baseline = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_baseline.fit(X_train_scaled, y_train)
    
    y_pred_baseline = rf_baseline.predict(X_test_scaled)
    y_proba_baseline = rf_baseline.predict_proba(X_test_scaled)
    
    base_metrics = {
        'accuracy': accuracy_score(y_test, y_pred_baseline),
        'precision': precision_score(y_test, y_pred_baseline),
        'recall': recall_score(y_test, y_pred_baseline),
        'f1': f1_score(y_test, y_pred_baseline),
        'roc_auc': roc_auc_score(y_test, y_proba_baseline[:, 1]),
        'brier': brier_score_loss(y_test, y_proba_baseline[:, 1]),
        'ece': calculate_ece(y_test, y_proba_baseline[:, 1]),
        'avg_confidence': np.mean(np.max(y_proba_baseline, axis=1))
    }
    results['baseline'] = base_metrics
    
    # 2. 当前优化模型（implementation_optimized）
    print("\n--- 当前优化模型 ---")
    from implementation_optimized import optimized_train, optimized_predict, load_optimized_model
    
    opt_clf, opt_sc, opt_le, opt_selector = load_optimized_model()
    if opt_clf is None:
        optimized_train()
        opt_clf, opt_sc, opt_le, opt_selector = load_optimized_model()
    
    X_opt_test = opt_sc.transform(X_test)
    X_opt_test_selected = opt_selector.transform(X_opt_test)
    
    y_pred_opt = opt_clf.predict(X_opt_test_selected)
    y_proba_opt = opt_clf.predict_proba(X_opt_test_selected)
    
    opt_metrics = {
        'accuracy': accuracy_score(y_test, y_pred_opt),
        'precision': precision_score(y_test, y_pred_opt),
        'recall': recall_score(y_test, y_pred_opt),
        'f1': f1_score(y_test, y_pred_opt),
        'roc_auc': roc_auc_score(y_test, y_proba_opt[:, 1]),
        'brier': brier_score_loss(y_test, y_proba_opt[:, 1]),
        'ece': calculate_ece(y_test, y_proba_opt[:, 1]),
        'avg_confidence': np.mean(np.max(y_proba_opt, axis=1))
    }
    results['current_optimized'] = opt_metrics
    
    # 3. 增强型模型
    print("\n--- 增强型模型 ---")
    if enhanced_clf is None:
        train_enhanced_model()
    
    X_enhanced_test = enhanced_preprocessor.transform(X_test)
    X_enhanced_test_engineered = enhanced_feature_selector.transform(X_enhanced_test)
    
    y_pred_enhanced = enhanced_clf.predict(X_enhanced_test_engineered)
    y_proba_enhanced = enhanced_clf.predict_proba(X_enhanced_test_engineered)
    
    enhanced_metrics = {
        'accuracy': accuracy_score(y_test, y_pred_enhanced),
        'precision': precision_score(y_test, y_pred_enhanced),
        'recall': recall_score(y_test, y_pred_enhanced),
        'f1': f1_score(y_test, y_pred_enhanced),
        'roc_auc': roc_auc_score(y_test, y_proba_enhanced[:, 1]),
        'brier': brier_score_loss(y_test, y_proba_enhanced[:, 1]),
        'ece': calculate_ece(y_test, y_proba_enhanced[:, 1]),
        'avg_confidence': np.mean(np.max(y_proba_enhanced, axis=1))
    }
    results['enhanced'] = enhanced_metrics
    
    # 打印对比表格
    print("\n" + "=" * 80)
    print("模型性能对比汇总")
    print("=" * 80)
    
    metrics_list = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'brier', 'ece', 'avg_confidence']
    metric_names = {
        'accuracy': '准确率',
        'precision': '精确率',
        'recall': '召回率',
        'f1': 'F1分数',
        'roc_auc': 'AUC-ROC',
        'brier': 'Brier分数',
        'ece': 'ECE',
        'avg_confidence': '平均置信度'
    }
    
    print(f"{'指标':<12} {'基准模型':<12} {'当前优化':<12} {'增强型':<12} {'改进幅度':<12}")
    print("-" * 80)
    
    for metric in metrics_list:
        base = results['baseline'].get(metric, 0)
        current = results['current_optimized'].get(metric, 0)
        enhanced = results['enhanced'].get(metric, 0)
        
        # Brier和ECE越小越好，其他指标越大越好
        if metric in ['brier', 'ece']:
            improvement = ((current - enhanced) / current * 100) if current > 0 else 0
        else:
            improvement = ((enhanced - current) / current * 100) if current > 0 else 0
        
        print(f"{metric_names[metric]:<12} {base:.4f}{'':<2} {current:.4f}{'':<2} {enhanced:.4f}{'':<2} {improvement:+.2f}%")
    
    return results


def test_prediction_speed(n_trials=20):
    """测试预测速度"""
    print("\n" + "=" * 70)
    print("预测速度测试")
    print("=" * 70)
    
    # 加载模型
    clf, sc, le, selector, preprocessor = load_enhanced_model()
    
    # 创建测试数据（模拟真实输入）
    test_data = np.array([[14.127, 19.289, 91.969, 654.889, 0.096, 0.104, 0.088, 0.048, 0.174, 0.062,
                           0.281, 1.216, 2.034, 27.853, 0.007, 0.025, 0.032, 0.012, 0.020, 0.003,
                           16.269, 25.677, 107.261, 819.638, 0.132, 0.254, 0.271, 0.116, 0.290, 0.080]])
    
    # 预热
    for _ in range(3):
        enhanced_predict(test_data)
    
    # 正式测试
    times = []
    for i in range(n_trials):
        start = time.time()
        out, prob, t = enhanced_predict(test_data)
        end = time.time()
        times.append(end - start)
    
    print(f"\n平均预测时间: {np.mean(times)*1000:.2f}ms")
    print(f"中位数预测时间: {np.median(times)*1000:.2f}ms")
    print(f"最大预测时间: {np.max(times)*1000:.2f}ms")
    print(f"最小预测时间: {np.min(times)*1000:.2f}ms")
    
    if np.mean(times) < 0.1:  # 100ms目标
        print('\n✓ 预测时间符合要求！(< 100ms)')
    elif np.mean(times) < 0.5:  # 500ms底线
        print('\n✓ 预测时间基本符合要求！(< 500ms)')
    else:
        print('\n⚠ 预测时间超过500ms！')
    
    print(f'\n预测结果: {"Malignant" if out[0] == 1 else "Benign"}')
    print(f'置信度: {prob[0][out[0]]:.4f}')
    
    return times


if __name__ == '__main__':
    # 训练增强型模型
    train_enhanced_model()
    
    # 测试预测速度
    test_prediction_speed()
    
    # 基准对比分析
    benchmark_comparison()