"""
轻量化优化实现 - 确保预测时间<500ms
"""
import numpy as np
import pandas as pd
import os
import joblib
import time
from typing import Dict, Tuple, Any

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, brier_score_loss, classification_report, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder, RobustScaler
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.calibration import CalibratedClassifierCV

# 配置常量
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
LIGHT_MODEL_FILE = os.path.join(MODEL_DIR, 'light_model.pkl')
LIGHT_SCALER_FILE = os.path.join(MODEL_DIR, 'light_scaler.pkl')
LIGHT_LABEL_ENCODER_FILE = os.path.join(MODEL_DIR, 'light_label_encoder.pkl')
LIGHT_FEATURE_SELECTOR_FILE = os.path.join(MODEL_DIR, 'light_feature_selector.pkl')

# 全局变量
light_clf = None
light_sc = None
light_labelencoder = None
light_feature_selector = None


def load_and_preprocess_data(filepath: str = 'Breast Cancer Data.csv') -> Tuple[np.ndarray, np.ndarray, LabelEncoder]:
    """加载和预处理数据"""
    df = pd.read_csv(filepath)
    X = df.iloc[:, 2:32].values
    y = df.iloc[:, 1].values
    
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    return X, y_encoded, label_encoder


def detect_and_handle_outliers(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """异常值处理"""
    X_processed = X.copy()
    
    for i in range(X.shape[1]):
        Q1 = np.percentile(X[:, i], 25)
        Q3 = np.percentile(X[:, i], 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        X_processed[:, i] = np.clip(X_processed[:, i], lower_bound, upper_bound)
    
    return X_processed, y


def train_light_model() -> Tuple[Any, Any, Any, Any, Dict]:
    """训练轻量化优化模型"""
    global light_clf, light_sc, light_labelencoder, light_feature_selector
    
    print("=" * 60)
    print("轻量化优化模型训练开始")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. 加载数据
    X, y, light_labelencoder = load_and_preprocess_data()
    print(f"数据加载完成: {X.shape[0]}样本, {X.shape[1]}特征")
    
    # 2. 异常值处理
    X_clean, y_clean = detect_and_handle_outliers(X, y)
    
    # 3. 数据集划分
    X_train, X_test, y_train, y_test = train_test_split(
        X_clean, y_clean, test_size=0.2, random_state=42, stratify=y_clean
    )
    print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")
    
    # 4. 数据标准化
    light_sc = RobustScaler()
    X_train_scaled = light_sc.fit_transform(X_train)
    X_test_scaled = light_sc.transform(X_test)
    
    # 5. 特征选择（选择20个最佳特征）
    light_feature_selector = SelectKBest(score_func=f_classif, k=20)
    X_train_selected = light_feature_selector.fit_transform(X_train_scaled, y_train)
    X_test_selected = light_feature_selector.transform(X_test_scaled)
    print(f"特征选择: 从{X.shape[1]}个特征中选择20个特征")
    
    # 6. 训练随机森林（减少树的数量）
    print("\n=== 模型训练 ===")
    base_rf = RandomForestClassifier(
        n_estimators=100,  # 减少树的数量
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42
    )
    base_rf.fit(X_train_selected, y_train)
    
    # 7. 置信度校准
    light_clf = CalibratedClassifierCV(
        base_rf, method='sigmoid', cv=5
    )
    light_clf.fit(X_train_selected, y_train)
    
    # 8. 评估
    print("\n=== 综合性能评估 ===")
    y_pred = light_clf.predict(X_test_selected)
    y_proba = light_clf.predict_proba(X_test_selected)
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'roc_auc': roc_auc_score(y_test, y_proba[:, 1]),
        'brier': brier_score_loss(y_test, y_proba[:, 1])
    }
    
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")
    
    print("\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=['Benign', 'Malignant']))
    
    print("\n混淆矩阵:")
    print(confusion_matrix(y_test, y_pred))
    
    # 9. 置信区间分析（简化版）
    print("\n=== 置信区间分析 ===")
    np.random.seed(42)
    auc_scores = []
    for _ in range(100):
        indices = np.random.randint(0, len(y_test), len(y_test))
        y_true_boot = y_test[indices]
        y_proba_boot = y_proba[indices]
        auc = roc_auc_score(y_true_boot, y_proba_boot[:, 1])
        auc_scores.append(auc)
    
    lower = np.percentile(auc_scores, 2.5)
    upper = np.percentile(auc_scores, 97.5)
    mean_auc = np.mean(auc_scores)
    metrics.update({'mean_auc': mean_auc, 'lower_ci': lower, 'upper_ci': upper})
    
    print(f"AUC-ROC均值: {mean_auc:.4f}")
    print(f"95%置信区间: [{lower:.4f}, {upper:.4f}]")
    
    # 10. 保存模型
    try:
        joblib.dump(light_clf, LIGHT_MODEL_FILE)
        joblib.dump(light_sc, LIGHT_SCALER_FILE)
        joblib.dump(light_labelencoder, LIGHT_LABEL_ENCODER_FILE)
        joblib.dump(light_feature_selector, LIGHT_FEATURE_SELECTOR_FILE)
        print(f"\n轻量化模型已保存到: {LIGHT_MODEL_FILE}")
    except Exception as e:
        print(f"保存模型失败: {e}")
    
    total_time = time.time() - start_time
    print(f"\n训练完成，总耗时: {total_time:.2f}秒")
    
    return light_clf, light_sc, light_labelencoder, light_feature_selector, metrics


def _fix_sklearn_version_compatibility(model):
    """修复 sklearn 版本兼容性问题 - 添加缺失的 monotonic_cst 属性"""
    import sklearn.tree
    import sklearn.ensemble
    import sklearn.calibration
    
    def add_monotonic_cst(obj):
        # 处理决策树
        if isinstance(obj, sklearn.tree.DecisionTreeClassifier):
            if not hasattr(obj, 'monotonic_cst'):
                obj.monotonic_cst = None
            # 继续检查嵌套结构
            if hasattr(obj, 'estimators_'):
                for estimator in obj.estimators_:
                    add_monotonic_cst(estimator)
            if hasattr(obj, 'estimator'):
                add_monotonic_cst(obj.estimator)
            return
        
        # 处理 RandomForestClassifier
        if isinstance(obj, sklearn.ensemble.RandomForestClassifier):
            if not hasattr(obj, 'monotonic_cst'):
                obj.monotonic_cst = None
            # 处理其中的决策树
            if hasattr(obj, 'estimators_'):
                for estimator in obj.estimators_:
                    add_monotonic_cst(estimator)
            # 继续检查嵌套结构
            if hasattr(obj, 'estimator'):
                add_monotonic_cst(obj.estimator)
            return
        
        # 处理 CalibratedClassifierCV
        if isinstance(obj, sklearn.calibration.CalibratedClassifierCV):
            # 处理 calibrated_classifiers_ 中的模型
            if hasattr(obj, 'calibrated_classifiers_'):
                for clf in obj.calibrated_classifiers_:
                    add_monotonic_cst(clf)
            # 处理 estimator 属性
            if hasattr(obj, 'estimator'):
                add_monotonic_cst(obj.estimator)
            return
        
        # 处理集成模型中的基分类器（如 VotingClassifier, StackingClassifier）
        if hasattr(obj, 'estimators_'):
            for estimator in obj.estimators_:
                if isinstance(estimator, tuple):
                    add_monotonic_cst(estimator[1])
                else:
                    add_monotonic_cst(estimator)
        
        # 处理嵌套的 estimator 属性
        if hasattr(obj, 'estimator'):
            add_monotonic_cst(obj.estimator)
    
    add_monotonic_cst(model)
    return model


def force_single_thread(model, _depth: int = 0):
    """把模型内部所有 n_jobs 强制改成 1（单样本推理不需要并行）。

    n_jobs=-1 会让 joblib 在预测时创建线程池，受限环境（沙箱/容器）下
    创建管道会被拒绝，导致预测接口 500。串行推理在单样本上更快。
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


def load_light_model() -> Tuple[Any, Any, Any, Any]:
    """加载轻量化模型"""
    global light_clf, light_sc, light_labelencoder, light_feature_selector
    
    files = [
        LIGHT_MODEL_FILE,
        LIGHT_SCALER_FILE,
        LIGHT_LABEL_ENCODER_FILE,
        LIGHT_FEATURE_SELECTOR_FILE
    ]
    
    if all(os.path.exists(f) for f in files):
        try:
            light_clf = joblib.load(LIGHT_MODEL_FILE)
            light_sc = joblib.load(LIGHT_SCALER_FILE)
            light_labelencoder = joblib.load(LIGHT_LABEL_ENCODER_FILE)
            light_feature_selector = joblib.load(LIGHT_FEATURE_SELECTOR_FILE)
            
            # 修复 sklearn 版本兼容性问题
            light_clf = _fix_sklearn_version_compatibility(light_clf)

            # 关闭并行，避免单样本推理时创建线程池
            light_clf = force_single_thread(light_clf)

            print("轻量化模型加载成功!")
            return light_clf, light_sc, light_labelencoder, light_feature_selector
        except Exception as e:
            print(f"加载轻量化模型失败: {e}")
            return None, None, None, None
    return None, None, None, None


def light_predict(inp: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """轻量化预测函数"""
    start_time = time.time()
    
    # 1. 数据标准化
    inp_scaled = light_sc.transform(inp)
    
    # 2. 特征选择
    inp_selected = light_feature_selector.transform(inp_scaled)
    
    # 3. 预测
    output = light_clf.predict(inp_selected)
    prob = light_clf.predict_proba(inp_selected)
    
    # 4. 限制置信度上限，避免过度自信
    # 将概率限制在 [0.5, 0.99] 范围内
    prob = np.clip(prob, 0.5, 0.99)
    # 重新归一化概率
    prob = prob / prob.sum(axis=1, keepdims=True)
    
    elapsed_time = time.time() - start_time
    
    return output, prob, elapsed_time


# 全局基础模型变量
basic_clf = None
basic_sc = None

def init_basic_model():
    """初始化基础模型（用于降级方案）"""
    global basic_clf, basic_sc
    
    if basic_clf is not None:
        return
    
    try:
        # 创建一个简单的随机森林分类器
        basic_clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        # 创建简单的标准化器
        basic_sc = RobustScaler()
        
        # 使用内置数据训练基础模型
        from implementation_optimized import load_data
        
        # load_data 返回 (X, y, labelencoder)
        X, y, _ = load_data()
        X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 训练标准化器
        basic_sc.fit(X_train)
        X_train_scaled = basic_sc.transform(X_train)
        
        # 训练分类器
        basic_clf.fit(X_train_scaled, y_train)
        print("基础随机森林模型初始化成功!")
    except Exception as e:
        print(f"基础模型初始化失败: {e}")
        basic_clf = None


def basic_predict(inp: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """基础随机森林预测函数（用于降级方案）"""
    start_time = time.time()
    
    # 如果基础模型未初始化，先初始化
    if basic_clf is None:
        init_basic_model()
    
    # 数据标准化
    inp_scaled = basic_sc.transform(inp)
    
    # 预测
    output = basic_clf.predict(inp_scaled)
    prob = basic_clf.predict_proba(inp_scaled)
    
    elapsed_time = time.time() - start_time
    
    return output, prob, elapsed_time


def test_prediction_performance():
    """测试预测性能"""
    print("\n" + "=" * 60)
    print("预测性能测试")
    print("=" * 60)
    
    # 加载模型
    clf, sc, le, selector = load_light_model()
    
    # 创建测试数据
    test_data = np.array([[14.127, 19.289, 91.969, 654.889, 0.096, 0.104, 0.088, 0.048, 0.174, 0.062,
                           0.281, 1.216, 2.034, 27.853, 0.007, 0.025, 0.032, 0.012, 0.020, 0.003,
                           16.269, 25.677, 107.261, 819.638, 0.132, 0.254, 0.271, 0.116, 0.290, 0.080]])
    
    # 测试预测时间
    print("\n=== 预测性能测试 ===")
    times = []
    for i in range(20):
        start = time.time()
        out, prob, t = light_predict(test_data)
        end = time.time()
        times.append(end - start)
        print(f'第{i+1}次: {(end - start)*1000:.2f}ms')
    
    print(f'\n平均预测时间: {np.mean(times)*1000:.2f}ms')
    print(f'中位数预测时间: {np.median(times)*1000:.2f}ms')
    print(f'最大预测时间: {np.max(times)*1000:.2f}ms')
    print(f'最小预测时间: {np.min(times)*1000:.2f}ms')
    
    if np.mean(times) < 0.5:
        print('\n✓ 预测时间符合要求！(< 500ms)')
    else:
        print('\n⚠ 预测时间超过500ms！')
    
    print(f'\n预测结果: {"Malignant" if out[0] == 1 else "Benign"}')
    print(f'置信度: {prob[0][out[0]]:.4f}')


if __name__ == '__main__':
    # 训练轻量化模型
    train_light_model()
    
    # 测试预测性能
    test_prediction_performance()
