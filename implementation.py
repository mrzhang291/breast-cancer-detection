import numpy as np
import pandas as pd
import os
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from time import time

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(MODEL_DIR, 'random_forest_model.pkl')
SCALER_FILE = os.path.join(MODEL_DIR, 'scaler.pkl')
LABEL_ENCODER_FILE = os.path.join(MODEL_DIR, 'label_encoder.pkl')

clf = None
sc = None
labelencoder_X_1 = None
X_test = None


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


y_test = None


def random_forest_train():
	dataset = pd.read_csv('Breast Cancer Data.csv')
	X = dataset.iloc[:, 2:32].values
	y = dataset.iloc[:, 1].values

	global labelencoder_X_1
	labelencoder_X_1 = LabelEncoder()
	y = labelencoder_X_1.fit_transform(y)

	global X_test, y_test
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 0)

	global sc, clf
	sc = StandardScaler()
	X_train = sc.fit_transform(X_train)
	X_test = sc.transform(X_test)

	clf = RandomForestClassifier(n_estimators=100)
	clf.fit(X_train, y_train)

	save_model(clf, sc, labelencoder_X_1)

	return clf

def save_model(clf, sc, labelencoder_X_1):
	"""保存模型到文件"""
	try:
		joblib.dump(clf, MODEL_FILE)
		joblib.dump(sc, SCALER_FILE)
		joblib.dump(labelencoder_X_1, LABEL_ENCODER_FILE)
		print(f"模型已保存到: {MODEL_FILE}")
	except Exception as e:
		print(f"保存模型失败: {e}")

def load_model():
	global clf, sc, labelencoder_X_1

	if os.path.exists(MODEL_FILE) and os.path.exists(SCALER_FILE) and os.path.exists(LABEL_ENCODER_FILE):
		try:
			clf = joblib.load(MODEL_FILE)
			sc = joblib.load(SCALER_FILE)
			labelencoder_X_1 = joblib.load(LABEL_ENCODER_FILE)
			print("模型加载成功!")
			return clf, sc, labelencoder_X_1
		except Exception as e:
			print(f"加载模型失败: {e}")
			return None, None, None
	return None, None, None

def random_forest_test():
	global clf, X_test, y_test
	t = time()
	output = clf.predict(X_test)
	acc = accuracy_score(y_test, output)
	print("The accuracy of testing data: ",acc)
	print("The running time: ",time()-t)

def random_forest_predict(clf, sc, inp):
	t = time()
	# 修复 sklearn 版本兼容性问题
	clf = _fix_sklearn_version_compatibility(clf)
	inp = sc.transform(inp)
	output = clf.predict(inp)
	prob = clf.predict_proba(inp)
	print("The running time: ",time()-t)

	return output, prob, time()-t