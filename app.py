# 标准库导入
import json
import os
import random
import time
import threading
import subprocess
import signal
import sys
from datetime import datetime
from time import time as time_func
import urllib.request
import urllib.error

# 第三方库导入
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, redirect, session, jsonify, g, send_file

from fpdf import FPDF
import io

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

# 本地模块导入
from light_optimization import train_light_model, load_light_model, light_predict
from enhanced_model import train_enhanced_model, load_enhanced_model, enhanced_predict, EnsembleWithCalibration, AdvancedPreprocessor, FeatureEngineer

ADMIN_API_URL = 'http://127.0.0.1:5001/api'

def get_user_id_from_admin(username):
    """从管理后台数据库获取用户ID"""
    try:
        import sqlite3
        admin_db_path = os.path.join(os.path.dirname(__file__), 'admin_backend', 'instance', 'admin.db')
        if not os.path.exists(admin_db_path):
            print(f"管理后台数据库不存在: {admin_db_path}")
            return None
        conn = sqlite3.connect(admin_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        conn.close()
        if user_row:
            return user_row[0]
        return None
    except Exception as e:
        print(f"获取用户ID失败: {e}")
        return None

def check_user_active(username):
    """检查用户是否被禁用"""
    try:
        import sqlite3
        admin_db_path = os.path.join(os.path.dirname(__file__), 'admin_backend', 'instance', 'admin.db')
        if not os.path.exists(admin_db_path):
            print(f"管理后台数据库不存在: {admin_db_path}")
            return True  # 如果数据库不存在，默认允许登录
        conn = sqlite3.connect(admin_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        conn.close()
        if user_row:
            return user_row[0] == 1
        return True  # 如果用户不存在，默认允许登录（由其他逻辑处理）
    except Exception as e:
        print(f"检查用户状态失败: {e}")
        return True

def get_admin_token(username, password):
    """从管理端获取JWT token"""
    try:
        data = json.dumps({
            'username': username,
            'password': password
        }).encode('utf-8')

        req = urllib.request.Request(
            f'{ADMIN_API_URL}/login',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                token = result_data.get('data', {}).get('token')
                if token:
                    print(f"成功获取管理端token")
                    return token
            else:
                print(f"获取token失败: {result_data.get('message')}")
                return None
    except Exception as e:
        print(f"获取token失败: {e}")
        return None

def register_user_on_admin(username, password):
    """在管理端注册新用户"""
    try:
        data = json.dumps({
            'username': username,
            'password': password
        }).encode('utf-8')

        req = urllib.request.Request(
            f'{ADMIN_API_URL}/register',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                user_data = result_data.get('data', {})
                print(f"成功在管理端注册用户: {username}, ID: {user_data.get('id')}")
                return user_data
            else:
                print(f"管理端注册失败: {result_data.get('message')}")
                return None
    except Exception as e:
        print(f"管理端注册失败: {e}")
        return None

def upload_prediction_to_admin(user_id, features, result, confidence):
    """上传预测记录到管理后台数据库"""
    try:
        all_30_features_json = json.dumps({f'feature_{i+1}': float(features[i]) for i in range(30)})
        data = json.dumps({
            'user_id': user_id,
            'all_30_features_json': all_30_features_json,
            'prediction_result': result,
            'confidence': float(confidence)
        }).encode('utf-8')

        req = urllib.request.Request(
            f'{ADMIN_API_URL}/predictions',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                print(f"成功上传预测记录到管理后台: UserID={user_id}, Result={result}")
                return True
            else:
                print(f"上传预测记录失败: {result_data.get('message')}")
                return False
    except Exception as e:
        print(f"上传预测记录到管理后台失败: {e}")
        return False

def get_predictions_from_admin(user_id, page=1, page_size=100, result_filter=None, sort_by='newest'):
    """从管理后台获取用户预测记录（使用公开接口）"""
    try:
        params = f'user_id={user_id}&page={page}&page_size={page_size}&sort_by={sort_by}'
        if result_filter:
            params += f'&result_filter={result_filter}'

        req = urllib.request.Request(
            f'{ADMIN_API_URL}/public/user/predictions?{params}',
            method='GET'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                return result_data.get('data', {})
            else:
                print(f"获取预测记录失败: {result_data.get('message')}")
                return {'items': [], 'total': 0, 'page': 1, 'page_size': page_size}
    except Exception as e:
        print(f"获取预测记录失败: {e}")
        return {'items': [], 'total': 0, 'page': 1, 'page_size': page_size}

def get_statistics_from_admin(user_id):
    """从管理后台获取用户统计信息（使用公开接口）"""
    try:
        req = urllib.request.Request(
            f'{ADMIN_API_URL}/public/user/statistics?user_id={user_id}',
            method='GET'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                data = result_data.get('data', {})
                # 确保返回的数据包含所有必要字段
                return {
                    'total': data.get('total', 0),
                    'malignant': data.get('malignant', 0),
                    'benign': data.get('benign', 0),
                    'avg_confidence': data.get('avg_confidence', 0.0)
                }
            else:
                print(f"获取统计信息失败: {result_data.get('message')}")
                return {'total': 0, 'malignant': 0, 'benign': 0, 'avg_confidence': 0.0}
    except Exception as e:
        print(f"获取统计信息失败: {e}")
        return {'total': 0, 'malignant': 0, 'benign': 0, 'avg_confidence': 0.0}

from shap_explainer import SimpleSHAPExplainer, FEATURE_NAMES
from translations import get_translation, translations

# 配置常量
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# 全局模型变量
clf = None
sc = None
feature_selector = None

# 高级优化模型变量
advanced_clf = None
advanced_sc = None
advanced_feature_selector = None

# 轻量化优化模型变量
light_clf = None
light_sc = None
light_feature_selector = None

# 增强型模型变量（用于提高置信度）
enhanced_clf = None
enhanced_preprocessor = None
enhanced_feature_selector = None
enhanced_model_ready = False

# 全局状态标志
model_ready = False
shap_ready = False

# 全局SHAP解释器
global_shap_explainer = None

# 线程锁
model_lock = threading.Lock()

# AI助手响应缓存 - 改为用户级缓存
# 结构: {user_id: {cache_key: {'answer': str, 'time': float}}}
user_ai_cache = {}
ai_cache_lock = threading.Lock()
AI_CACHE_MAX_SIZE = 50  # 每个用户最大缓存条数
AI_CACHE_EXPIRE_TIME = 3600  # 缓存过期时间（秒）

# 获取当前语言
def get_current_lang():
	return session.get('lang', 'zh')

# 获取当前用户ID
def get_current_user_id():
	return session.get('user_id', 'anonymous')

# 翻译函数
def _(key):
	return get_translation(key, get_current_lang())

def get_cached_answer(prompt: str):
	"""从用户缓存获取答案（考虑用户和语言）"""
	user_id = get_current_user_id()
	current_lang = session.get('lang', 'zh')
	cache_key = f"{prompt}_{current_lang}"
	
	with ai_cache_lock:
		if user_id not in user_ai_cache:
			return None
		if cache_key in user_ai_cache[user_id]:
			cached = user_ai_cache[user_id][cache_key]
			if time.time() - cached['time'] < AI_CACHE_EXPIRE_TIME:
				return cached['answer']
			else:
				# 缓存过期，删除
				del user_ai_cache[user_id][cache_key]
	return None


def set_cached_answer(prompt: str, answer: str):
	"""设置用户缓存答案（考虑用户和语言）"""
	user_id = get_current_user_id()
	current_lang = session.get('lang', 'zh')
	cache_key = f"{prompt}_{current_lang}"
	
	with ai_cache_lock:
		# 确保用户缓存存在
		if user_id not in user_ai_cache:
			user_ai_cache[user_id] = {}
		
		user_cache = user_ai_cache[user_id]
		
		# 如果缓存已满，删除最旧的
		if len(user_cache) >= AI_CACHE_MAX_SIZE:
			oldest_key = min(user_cache.keys(), key=lambda k: user_cache[k]['time'])
			del user_cache[oldest_key]
		
		user_cache[cache_key] = {
			'answer': answer,
			'time': time.time()
		}

def clear_user_cache(user_id: str):
	"""清空指定用户的缓存"""
	with ai_cache_lock:
		if user_id in user_ai_cache:
			del user_ai_cache[user_id]
			print(f"DEBUG - 用户 {user_id} 的缓存已清空")


def get_system_prompt():
	"""根据当前语言设置返回AI系统提示词"""
	current_lang = session.get('lang', 'zh')
	if current_lang == 'en':
		return 'You are a breast cancer prediction AI assistant named "Pink Guardian". Your responsibilities are:\n\n1. Answer questions about using the breast cancer prediction system (such as prediction operations, data import/export, viewing history records, etc.)\n2. Answer medical knowledge related to breast cancer (such as early screening, diagnosis methods, treatment options, prognosis, etc.)\n3. For questions unrelated to breast cancer or this system, politely explain that you mainly focus on the breast cancer field\n\nImportant notes:\n- You cannot replace professional doctors diagnosis\n- Recommend users to consult professional doctors for health issues\n- Answer in English, friendly and warm tone'
	else:
		return '你是一个专注于乳腺癌预测的AI助手，名叫"粉红守护"。你的职责是：\n\n1. 回答关于乳腺癌预测系统的使用问题（如预测操作、数据导入导出、历史记录查看等）\n2. 回答乳腺癌相关的医学知识（如早期筛查、诊断方法、治疗方案、预后等）\n3. 对于与乳腺癌或本系统无关的问题，请礼貌地说明你主要专注于乳腺癌领域\n\n重要提示：\n- 你不能替代专业医生的诊断\n- 建议用户对于健康问题咨询专业医生\n- 回答用中文，语气友好温暖'


from ai_improved import generate_answer

def call_deepseek(prompt: str, skip_cache=False):
	user_id = get_current_user_id()
	current_lang = session.get('lang', 'zh')
	
	print(f"="*50)
	print(f"DEBUG - 用户ID: {user_id}")
	print(f"DEBUG - 当前语言: {current_lang}")
	print(f"DEBUG - 用户问题: {prompt}")
	print(f"DEBUG - 是否跳过缓存: {skip_cache}")
	
	# 如果不跳过缓存，先检查缓存
	if not skip_cache:
		cached_answer = get_cached_answer(prompt)
		if cached_answer:
			print(f"DEBUG - 使用缓存答案 (user={user_id})")
			print(f"="*50)
			return cached_answer, None
	
	answer = generate_answer(prompt, current_lang)
	
	# 如果不跳过缓存，保存到缓存
	if not skip_cache:
		set_cached_answer(prompt, answer)
	
	print(f"DEBUG - 生成新答案 (user={user_id}, lang={current_lang})")
	print(f"="*50)
	return answer, None


def get_local_answer(prompt: str) -> str:
	"""本地模拟AI回答（支持中英文）"""
	current_lang = session.get('lang', 'zh')
	prompt_lower = prompt.lower()
	
	if current_lang == 'en':
		# 英文回答
		if 'accuracy' in prompt_lower or 'accurate' in prompt_lower:
			return 'This system uses Random Forest algorithm for breast cancer prediction, with an accuracy of approximately 96-98% on the test set. However, please note that this is only an auxiliary tool and cannot replace professional medical diagnosis.'
		elif 'benign' in prompt_lower or 'malignant' in prompt_lower or 'tumor' in prompt_lower:
			return 'Benign tumors usually grow slowly, do not spread to other parts of the body, and have a good prognosis. Malignant tumors are invasive and may metastasize, requiring timely treatment. The prediction results of this system are for reference only. Please consult a professional doctor for confirmation.'
		elif 'interpret' in prompt_lower or 'result' in prompt_lower or 'results' in prompt_lower:
			return 'Interpreting prediction results:\n\n[Benign] High probability of benign tumor. But remember, this is a data-based prediction and cannot replace pathological diagnosis. Regular follow-up is recommended.\n\n[Malignant] High probability of malignant tumor. Strongly recommend consulting a professional doctor for further examination and confirmation as soon as possible.\n\nImportant note: This system only provides auxiliary prediction. The final diagnosis must be determined by a professional doctor based on pathological reports.'
		elif 'replace' in prompt_lower or 'doctor' in prompt_lower:
			return 'The prediction results of this system are for reference only and cannot replace professional medical diagnosis. If you have any health concerns, please consult professional medical personnel.'
		elif 'feature' in prompt_lower or 'parameter' in prompt_lower or 'features' in prompt_lower:
			return 'This system uses 30 features of breast tumors for prediction, including mean features (such as radius_mean, texture_mean, etc.), standard deviation features, and worst features. These features are derived from cell morphology measurement data in pathological reports.'
		elif 'use' in prompt_lower or 'operate' in prompt_lower or 'usage' in prompt_lower or 'how to' in prompt_lower:
			return 'Usage: Enter the 30 feature values from the pathology report in the form, then click the "Submit Prediction" button to get the prediction result. You can also click "Load Sample Data" to experience quickly, or use the "Batch Prediction" function to process multiple samples.'
		elif 'history' in prompt_lower or 'record' in prompt_lower or 'records' in prompt_lower:
			return 'After logging in, click "Prediction History" in the user menu at the top right corner to view your historical prediction records. The system saves all your prediction results and supports filtering by result type.'
		elif 'batch' in prompt_lower or 'bulk' in prompt_lower:
			return 'The batch prediction function allows you to upload a CSV file containing multiple samples for batch analysis and supports exporting standardized PDF reports. Select "Batch Prediction" from the user menu to use this feature.'
		elif 'screening' in prompt_lower or 'early' in prompt_lower or 'detect' in prompt_lower:
			return 'Early breast cancer screening is very important. Common methods include mammography, breast ultrasound, and breast MRI. Regular screening is recommended for women, especially those with a family history.'
		elif 'treatment' in prompt_lower or 'therapy' in prompt_lower:
			return 'Breast cancer treatment methods include surgery, radiotherapy, chemotherapy, endocrine therapy, and targeted therapy. The specific treatment plan must be determined by the doctor based on tumor type, stage, and patient condition.'
		elif 'prognosis' in prompt_lower or 'survival' in prompt_lower or 'outcome' in prompt_lower:
			return 'Breast cancer prognosis is related to multiple factors such as tumor stage, grade, and hormone receptor status. Early detection and standardized treatment can significantly improve survival rates. Please follow your doctor advice for treatment and follow-up.'
		elif 'model' in prompt_lower or 'algorithm' in prompt_lower:
			return 'This system uses the Random Forest algorithm, which is an ensemble learning method that improves accuracy by constructing multiple decision trees and combining their predictions. The model is trained using breast tumor datasets.'
		else:
			return 'Thank you for your question! This system focuses on breast cancer prediction. If you have questions about breast cancer, I would be happy to help. Important note: The information provided by this system is for reference only and cannot replace professional medical advice.'
	else:
		# 中文回答
		if '准确率' in prompt or '准确' in prompt:
			return '本系统使用随机森林算法进行乳腺癌预测，在测试集上的准确率约为96-98%。但请注意，这只是一个辅助工具，不能替代专业医生的诊断。'
		elif '良性' in prompt or '恶性' in prompt:
			return '良性肿瘤通常生长缓慢，不会扩散到身体其他部位，预后较好；恶性肿瘤具有侵袭性，可能会转移，需要及时治疗。本系统的预测结果仅供参考，请务必咨询专业医生进行确诊。'
		elif '解读' in prompt or '结果' in prompt:
			return '解读预测结果：\n\n【良性】预测为良性肿瘤的可能性较高。但请记住，这是基于数据的预测，不能替代病理诊断。建议定期复查。\n\n【恶性】预测为恶性肿瘤的可能性较高。强烈建议尽快咨询专业医生进行进一步检查和确诊。\n\n重要提示：本系统仅提供辅助预测，最终诊断需由专业医生根据病理报告确定。'
		elif '替代' in prompt or '医生' in prompt:
			return '本系统的预测结果仅供参考，不能替代专业医生的诊断。如果您有任何健康疑虑，请务必咨询专业的医疗人员。'
		elif '特征' in prompt or '参数' in prompt:
			return '本系统使用乳腺肿瘤的30个特征进行预测，包括均值特征（如radius_mean, texture_mean等）、标准差特征和最差特征。这些特征来自病理报告中的细胞形态测量数据。'
		elif '使用' in prompt or '操作' in prompt:
			return '使用方法：在表单中输入病理报告中的30个特征值，点击"提交预测"按钮即可获得预测结果。您也可以点击"加载示例数据"快速体验，或使用"批量预测"功能处理多个样本。'
		elif '历史记录' in prompt or '记录' in prompt:
			return '登录后点击右上角用户菜单中的"预测记录"即可查看您的历史预测记录。系统会保存您的所有预测结果，并支持按结果类型筛选。'
		elif '批量预测' in prompt or '批量' in prompt:
			return '批量预测功能允许您上传包含多个样本的CSV文件进行批量分析，并支持导出标准化的PDF报告。在用户菜单中选择"批量预测"即可使用此功能。'
		elif '筛查' in prompt or '早期' in prompt:
			return '乳腺癌早期筛查非常重要，常见方法包括乳腺X线检查（钼靶）、乳腺超声和乳腺MRI。建议女性定期进行筛查，特别是有家族史的人群。'
		elif '治疗' in prompt:
			return '乳腺癌的治疗方法包括手术、放疗、化疗、内分泌治疗和靶向治疗等。具体治疗方案需由医生根据肿瘤类型、分期和患者情况综合决定。'
		elif '预后' in prompt:
			return '乳腺癌的预后与肿瘤分期、分级、激素受体状态等多种因素有关。早期发现和规范治疗可以显著提高生存率。请务必遵循医生的建议进行治疗和随访。'
		elif '模型' in prompt:
			return '本系统采用随机森林算法，这是一种集成学习方法，通过构建多个决策树并综合它们的预测结果来提高准确性。模型使用乳腺肿瘤数据集进行训练。'
		else:
			return '感谢您的提问！本系统专注于乳腺癌预测相关领域。如果您有关于乳腺癌的问题，我很乐意为您解答。重要提示：本系统提供的信息仅供参考，不能替代专业医疗建议。'


app = Flask(__name__)
app.url_map.strict_slashes = False
app.secret_key = os.environ.get('APP_SECRET_KEY', 'change_this_secret_key')

# 禁用模板和静态文件缓存
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


# 全局SHAP explainer（在app启动时初始化）
global_shap_explainer = None

# 语言切换路由
@app.route('/set-lang/<lang>')
def set_lang(lang):
	"""设置语言"""
	if lang in ['zh', 'en']:
		session['lang'] = lang
	# 获取上一个页面URL，默认返回首页
	referrer = request.referrer or '/'
	# 如果referrer是/predict（POST-only路由），检查是否有预测结果，有则重定向到结果页面
	if referrer and referrer.endswith('/predict'):
		prediction_data = session.get('last_prediction')
		if prediction_data:
			return redirect('/result')
		return redirect('/')
	# 如果referrer是/result页面，且有预测数据，保持在结果页面
	if referrer and referrer.endswith('/result'):
		prediction_data = session.get('last_prediction')
		if prediction_data:
			return redirect('/result')
	# 如果referrer是/batch-predict（POST-only路由），检查是否有批量预测结果
	if referrer and referrer.endswith('/batch-predict'):
		batch_results = session.get('batch_results')
		if batch_results:
			return redirect('/batch-results')
		return redirect('/batch')
	# 如果referrer是/batch-results页面，且有批量预测数据，保持在结果页面
	if referrer and referrer.endswith('/batch-results'):
		batch_results = session.get('batch_results')
		if batch_results:
			return redirect('/batch-results')
	return redirect(referrer)

# 上下文处理器，将翻译函数传递给所有模板
@app.context_processor
def inject_translation():
	from translations import get_translation
	def translate(key):
		try:
			lang = session.get('lang', 'zh') if session else 'zh'
			return get_translation(key, lang)
		except Exception:
			return key
	return {
		'_': translate,
		'current_lang': session.get('lang', 'zh') if session else 'zh',
		'is_chinese': (session.get('lang', 'zh') if session else 'zh') == 'zh',
		'is_english': (session.get('lang', 'zh') if session else 'zh') == 'en'
	}


def get_user_from_db(username, password):
	"""通过管理后台API验证用户"""
	try:
		import requests
		
		# 调用管理后台的登录API验证用户
		response = requests.post('http://127.0.0.1:5001/api/login', 
								json={'username': username, 'password': password})
		
		if response.status_code == 200:
			data = response.json()
			if data.get('code') == 200 and data.get('data'):
				user_data = data['data']['user']
				return {
					'id': user_data['id'],
					'username': user_data['username'],
					'email': user_data.get('email'),
					'role_id': user_data.get('role_id')
				}
		else:
			print(f'管理后台API返回错误: {response.status_code}')
	except Exception as e:
		print(f'从管理后台验证用户失败: {e}')
	return None



# ==================== 登录图形验证码 ====================
# 答案只存在服务端内存里：Flask 默认 session 是客户端签名 cookie，
# 把答案放进 session 等于把答案交给浏览器，验证码就失去意义。
try:
	from PIL import Image, ImageDraw, ImageFont, ImageFilter
	_PIL_AVAILABLE = True
except Exception:  # noqa: BLE001
	_PIL_AVAILABLE = False

import secrets

_CAPTCHA_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
_CAPTCHA_TTL = 300
_CAPTCHA_STORE = {}


def _captcha_gc():
	now = time.time()
	for key in [k for k, v in _CAPTCHA_STORE.items() if v[1] < now]:
		_CAPTCHA_STORE.pop(key, None)


def _captcha_font(size):
	"""优先用系统里的粗体字体，找不到就退回默认位图字体。"""
	for path in ('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
	             '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
	             '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf',
	             'C:/Windows/Fonts/arialbd.ttf',
	             'C:/Windows/Fonts/msyhbd.ttc'):
		if os.path.exists(path):
			try:
				return ImageFont.truetype(path, size)
			except Exception:  # noqa: BLE001
				continue
	return ImageFont.load_default()


def _captcha_image(code):
	width, height = 132, 46
	img = Image.new('RGB', (width, height), (246, 248, 252))
	draw = ImageDraw.Draw(img)

	for _ in range(260):
		draw.point((random.randint(0, width - 1), random.randint(0, height - 1)),
		           fill=(random.randint(178, 222),) * 3)

	for _ in range(4):
		draw.line([(random.randint(0, width), random.randint(0, height)),
		           (random.randint(0, width), random.randint(0, height))],
		          fill=(random.randint(150, 200), random.randint(150, 200), random.randint(205, 240)),
		          width=1)

	font = _captcha_font(28)
	for i, ch in enumerate(code):
		layer = Image.new('RGBA', (44, height), (0, 0, 0, 0))
		ImageDraw.Draw(layer).text(
			(7, 5), ch, font=font,
			fill=(random.randint(35, 80), random.randint(45, 90), random.randint(120, 180)))
		layer = layer.rotate(random.uniform(-16, 16), resample=Image.BICUBIC)
		img.paste(layer, (6 + i * 30, random.randint(0, 5)), layer)

	return img.filter(ImageFilter.SMOOTH)


def _captcha_check(entered):
	"""校验并立即作废；返回 True/False。"""
	cid = request.cookies.get('captcha_id')
	if not cid:
		return False
	entry = _CAPTCHA_STORE.pop(cid, None)
	if not entry:
		return False
	code, expire_at = entry
	if time.time() > expire_at:
		return False
	return (entered or '').strip().upper() == code.upper()


@app.route('/captcha.png')
def captcha_png():
	"""生成验证码图片。答案存服务端，客户端只拿到一个随机 id。"""
	if not _PIL_AVAILABLE:
		return '', 503
	_captcha_gc()

	code = ''.join(random.choice(_CAPTCHA_CHARS) for _ in range(4))
	cid = secrets.token_hex(16)
	_CAPTCHA_STORE[cid] = (code, time.time() + _CAPTCHA_TTL)

	buffer = io.BytesIO()
	_captcha_image(code).save(buffer, 'PNG')
	buffer.seek(0)

	response = send_file(buffer, mimetype='image/png')
	response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
	response.headers['Pragma'] = 'no-cache'
	response.set_cookie('captcha_id', cid, max_age=_CAPTCHA_TTL,
	                    httponly=True, samesite='Lax')
	return response


@app.route('/login', methods=['GET', 'POST'])
def login():
	if 'username' in session:
		print(f'User already logged in: {session["username"]}')
		return redirect('/')
	error = None
	if request.method == 'POST':
		username = request.form.get('username', '').strip()
		password = request.form.get('password', '')
		print(f'Login attempt for user: {username}')

		# ---- 验证码校验 ----
		# 自动化测试/运维可通过内部令牌跳过（令牌不出现在任何前端页面）
		internal_ok = bool(INTERNAL_TOKEN) and request.headers.get('X-Internal-Token') == INTERNAL_TOKEN
		if not internal_ok:
			if not _captcha_check(request.form.get('captcha')):
				print(f'验证码校验失败 for user: {username}')
				return render_template('login.html', error='验证码不正确，请重新输入')

		# 优先从数据库验证用户（管理后台创建的用户）
		user_from_db = get_user_from_db(username, password)
		if user_from_db:
			print(f'用户 {username} 从数据库验证成功')
			session['username'] = username
			session['lang'] = session.get('lang', 'zh')
			session['user_id'] = user_from_db['id']
			session['role_id'] = user_from_db.get('role_id') or 3
			
			# 获取管理端token
			token = get_admin_token(username, password)
			if token:
				session['admin_token'] = token
				print(f'获取到管理端token')
			
			print(f'Login successful for user: {username}')
			return redirect('/')
		error = '用户名或密码错误'
		print(f'Login failed for user: {username}')
	return render_template('login.html', error=error)


@app.route('/check-user-status', methods=['GET'])
def check_user_status():
	"""检查当前用户是否被禁用"""
	if 'username' not in session:
		return jsonify({'status': 'not_logged_in'})
	
	username = session['username']
	is_active = check_user_active(username)
	
	if not is_active:
		# 用户已被禁用，清除session
		session.clear()
		return jsonify({'status': 'disabled'})
	
	return jsonify({'status': 'active'})


@app.route('/register', methods=['GET', 'POST'])
def register():
	if 'username' in session:
		return redirect('/')
	error = None
	if request.method == 'POST':
		username = request.form.get('username', '').strip()
		password = request.form.get('password', '')
		confirm_password = request.form.get('confirm_password', '')
		if not username or not password:
			error = '用户名和密码不能为空'
		elif password != confirm_password:
			error = '两次输入密码不一致'
		else:
			# 先尝试在管理端注册
			admin_register_result = register_user_on_admin(username, password)
			if admin_register_result:
				session['username'] = username
				session['user_id'] = admin_register_result.get('id', username)
				session['role_id'] = admin_register_result.get('role_id') or 3
				session['lang'] = 'zh'
				# 获取管理端token
				token = get_admin_token(username, password)
				if token:
					session['admin_token'] = token
				return redirect('/')
			else:
				error = '注册失败，请稍后重试'
	return render_template('register.html', error=error)


@app.route('/logout')
def logout():
	# 清空用户的AI缓存
	user_id = session.get('user_id')
	if user_id:
		clear_user_cache(user_id)
	session.pop('username', None)
	session.pop('user_id', None)
	return redirect('/login')


@app.route('/')
def index():
	if 'username' not in session:
		return redirect('/login')
	return render_template('home.html')

@app.route('/result')
def result():
	"""显示预测结果页面（GET请求）"""
	if 'username' not in session:
		return redirect('/login')
	
	# 从session获取预测结果
	prediction_data = session.get('last_prediction')
	if not prediction_data:
		return redirect('/')
	
	# 获取当前语言设置
	current_lang = session.get('lang', 'zh')
	
	# 根据原始数值结果和当前语言动态翻译
	raw_output = prediction_data.get('raw_output', None)
	if raw_output is not None:
		# 使用原始数值结果进行翻译
		if current_lang == 'en':
			output = 'Malignant' if raw_output == 1 else 'Benign'
		else:
			output = '恶性' if raw_output == 1 else '良性'
	else:
		# 兼容旧的数据格式
		output = prediction_data.get('output', '')
	
	raw_confidence = prediction_data.get('confidence', 0)
	confidence = prediction_data.get('confidence_calibrated', raw_confidence)
	return render_template('result.html', output=output, confidence=confidence, raw_confidence=raw_confidence, time=prediction_data.get('time', 0), model_type=prediction_data.get('model_type', 'enhanced'))

@app.route('/predict', methods=['POST'])
def predict():
    global light_clf, light_sc, light_feature_selector, model_ready
    global enhanced_clf, enhanced_model_ready

    if 'username' not in session:
        return redirect('/login')

    # ---------- 1. 解析 30 项输入（缺项/非数字 -> 友好提示，不再 500） ----------
    data = []
    for i in range(1, 31):
        raw = (request.form.get('value' + str(i)) or '').strip()
        if raw == '':
            return render_template('result.html', output='输入不完整', confidence=0, time=0,
                                   input_error='第 %d 项特征没有填写，请补齐 30 项后再提交。' % i)
        try:
            data.append(float(raw))
        except ValueError:
            return render_template('result.html', output='输入有误', confidence=0, time=0,
                                   input_error='第 %d 项「%s」不是有效数字，请检查后重试。' % (i, raw))

    print('预测输入数据: %s' % data)

    # ---------- 2. 模型就绪检查 ----------
    if not model_ready or light_clf is None or light_sc is None or light_feature_selector is None:
        return render_template('result.html', output='模型加载中', confidence=0, time=0,
                               model_not_ready=True)

    data_np = np.asarray(data, dtype=float).reshape(1, -1)

    # ---------- 3. 预测：增强型优先，失败自动降级到轻量模型 ----------
    out = None
    prob = None
    t = 0.0
    model_type = 'light'

    if enhanced_model_ready and enhanced_clf is not None:
        try:
            out, prob, t = enhanced_predict(data_np)
            model_type = 'enhanced'
            print('使用增强型模型完成预测: out=%s' % (out,))
        except Exception as e:
            app.logger.exception('增强型模型预测失败，降级到轻量模型: %s', e)
            out = None

    if out is None:
        try:
            out, prob, t = light_predict(data_np)
            model_type = 'light'
            print('使用轻量化模型完成预测: out=%s' % (out,))
        except Exception as e:
            app.logger.exception('轻量模型预测失败: %s', e)
            return render_template('result.html', output='预测失败', confidence=0, time=0,
                                   model_error='模型暂时不可用，请稍后重试；若持续失败请联系管理员。')

    output = '恶性' if int(out[0]) == 1 else '良性'
    confidence = float(prob[0][int(out[0])])

    # 校准后的概率（保序回归）：主界面展示它，原始值留作对照
    calibrated = confidence
    try:
        from agent import uncertainty as _uncertainty
        calibrated = _uncertainty.calibrate(confidence)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning('置信度校准失败: %s', exc)

    print('预测结果: %s, 置信度: %.4f (校准后 %.4f)' % (output, confidence, calibrated))
    print('预测耗时: %.6f 秒' % t)
    if t > 0.5:
        print('警告: 预测时间过长: %.4f 秒，建议优化！' % t)

    # ---------- 4. 写入 session（供结果页、AI 分析、SHAP 使用） ----------
    session['last_prediction'] = {
        'output': output,
        'raw_output': int(out[0]),
        'confidence': confidence,
        'confidence_calibrated': calibrated,
        'data': data,
        'use_enhanced': (model_type == 'enhanced'),
        'time': t,
        'model_type': model_type,
    }

    # ---------- 5. 上报管理后台（失败不影响本次预测） ----------
    username = session.get('username', 'anonymous')
    user_id = session.get('user_id', username)
    try:
        upload_prediction_to_admin(user_id, data, output, confidence)
    except Exception as e:
        app.logger.warning('上报预测记录失败（已忽略）: %s', e)

    return redirect('/result')


@app.route('/ai-query', methods=['POST'])
def ai_query():
    """AI 助手入口：转交 agent 编排器（工具 + RAG + 护栏）。"""
    if 'username' not in session:
        return jsonify({'error': '请先登录'}), 403

    data = request.get_json(silent=True) or {}
    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return jsonify({'error': '请输入问题内容。'}), 400

    lang = data.get('lang', session.get('lang', 'zh'))
    if lang in ('zh', 'en'):
        session['lang'] = lang

    if not _agent_bind_runtime():
        return jsonify({'error': '模型尚未就绪，请稍后重试。'}), 503

    last = session.get('last_prediction') or {}
    ctx = _agent_ctx(prompt)
    try:
        result = _agent_orch.run(ctx, prompt, last.get('data'))
    except Exception as exc:  # noqa: BLE001
        app.logger.exception('ai-query 失败')
        return jsonify({'error': '分析失败：%s' % str(exc)[:120]}), 500

    return jsonify({
        'answer': result['answer_md'],
        'citations': result['citations'],
        'run_id': result['run_id'],
        'intent': result['intent'],
        'intent_label': result['intent_label'],
        'status': result['status'],
        'risk': result['risk'],
    })


def normalize_record(record):
    """把后台返回的记录统一成 dict。

    历史原因：/api/public/user/record/<id> 返回的是数组
    [id, username, result, confidence, created_at, 30 个特征值]，
    而列表接口返回的是对象。这里做一次归一化，避免调用方各写一套。
    """
    if isinstance(record, dict):
        data = dict(record)
        data.setdefault('features', data.get('features') or {})
        return data
    if isinstance(record, (list, tuple)) and len(record) >= 5:
        data = {
            'id': record[0],
            'username': record[1],
            'prediction_result': record[2],
            'confidence': record[3],
            'created_at': record[4],
            'features': {},
        }
        for idx, value in enumerate(record[5:35], start=1):
            data['features']['feature_%d' % idx] = value
        return data
    return {}


INTERNAL_TOKEN = os.environ.get('INTERNAL_TOKEN', 'dsh-local-internal')


def _admin_call(path, method='GET', payload=None, timeout=8):
    """调用管理后台的内部接口（带共享令牌）。返回 (ok, data)。"""
    try:
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(
            ADMIN_API_URL + path,
            data=body,
            method=method,
            headers={'Content-Type': 'application/json', 'X-Internal-Token': INTERNAL_TOKEN},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('code') == 200, data
    except Exception as exc:  # noqa: BLE001
        app.logger.warning('内部调用失败 %s %s: %s', method, path, exc)
        return False, {}


def delete_record_remote(record_id, user_id):
    return _admin_call('/public/user/record/%d?user_id=%s' % (int(record_id), user_id),
                       method='DELETE')


def clear_records_remote(user_id):
    return _admin_call('/public/user/predictions/clear', method='POST',
                       payload={'user_id': user_id})


@app.route('/records')
def records():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    user_id = session.get('user_id', username)
    print(f'Current user: {username} (ID: {user_id})')

    result_filter = request.args.get('filter')
    sort_by = request.args.get('sort', 'newest')
    page = int(request.args.get('page', 1))
    limit = 20
    offset = (page - 1) * limit

    # 从管理后台获取统计信息
    stats = get_statistics_from_admin(user_id)
    print(f'Statistics from admin: {stats}')

    # 从管理后台获取预测记录
    # 前端已经传递的是英文值(Malignant/Benign)，直接使用即可
    api_filter = result_filter if result_filter else None

    api_result = get_predictions_from_admin(user_id, page=page, page_size=limit, result_filter=api_filter, sort_by=sort_by)
    items = api_result.get('items', [])
    total = api_result.get('total', 0)
    print(f'Records from admin: {len(items)}, Total: {total}')
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    records = []
    for item in items:
        features = item.get('features', {})
        records.append({
            'id': item.get('id'),
            'username': username,
            'result': item.get('prediction_result'),
            'confidence': item.get('confidence'),
            'predict_time': item.get('created_at'),
            'duration': 0,
            'radius_mean': features.get('feature_1', 0),
            'texture_mean': features.get('feature_2', 0),
            'perimeter_mean': features.get('feature_3', 0),
            'area_mean': features.get('feature_4', 0)
        })

    def build_url(page=1):
        params = []
        if result_filter:
            params.append(f'filter={result_filter}')
        if sort_by != 'newest':
            params.append(f'sort={sort_by}')
        params.append(f'page={page}')
        return '/records?' + '&'.join(params)

    return render_template('records.html',
                           records=records,
                           stats=stats,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           result_filter=result_filter,
                           search_query='',
                           sort_by=sort_by,
                           build_url=build_url)


@app.route('/record/<int:record_id>')
@app.route('/record/<int:record_id>/partial')
def record_detail(record_id):
    if 'username' not in session:
        if request.path.endswith('/partial'):
            return jsonify({'error': '请先登录'}), 403
        return redirect('/login')

    # 从管理后台获取记录详情
    try:
        req = urllib.request.Request(
            f'{ADMIN_API_URL}/public/user/record/{record_id}',
            method='GET'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                # 详情模板按数组下标取字段（record[0..34]），这里保持原始结构
                record = result_data.get('data', {})
            else:
                if request.path.endswith('/partial'):
                    return jsonify({'error': '记录不存在'}), 404
                return redirect('/records')
    except Exception as e:
        print(f"获取记录详情失败: {e}")
        if request.path.endswith('/partial'):
            return jsonify({'error': '获取记录详情失败'}), 500
        return redirect('/records')

    if request.path.endswith('/partial'):
        return render_template('record_partial.html', record=record)
    return render_template('record.html', record=record)


@app.route('/delete-record/<int:record_id>', methods=['POST'])
def delete_record_route(record_id):
    if 'username' not in session:
        return redirect('/login')

    user_id = session.get('user_id', session.get('username'))
    ok, _ = delete_record_remote(record_id, user_id)
    if not ok:
        app.logger.warning('删除记录 %s 失败', record_id)
    return redirect('/records?deleted=%d' % (1 if ok else 0))


@app.route('/delete-all-records', methods=['POST'])
def delete_all_records():
    if 'username' not in session:
        return redirect('/login')

    user_id = session.get('user_id', session.get('username'))
    ok, data = clear_records_remote(user_id)
    deleted = (data.get('data') or {}).get('deleted', 0) if ok else 0
    return redirect('/records?cleared=%d' % deleted)


@app.route('/export-records-csv')
def export_records_csv():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    user_id = session.get('user_id', username)

    from flask import Response
    import csv
    import io

    api_result = get_predictions_from_admin(user_id, page=1, page_size=10000)
    items = api_result.get('items', [])

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ID', 'Username', 'Result', 'Confidence', 'Prediction Time'])

    for item in items:
        writer.writerow([
            item.get('id'),
            username,
            item.get('prediction_result'),
            f"{item.get('confidence', 0)*100:.2f}%",
            item.get('created_at', '')
        ])

    output.seek(0)
    # 添加UTF-8 BOM，确保Excel正确识别中文
    csv_content = '\ufeff' + output.getvalue()
    return Response(
        csv_content.encode('utf-8'),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=prediction_records.csv'}
    )


@app.route('/export-records-pdf')
def export_records_pdf():
    """PDF导出功能 - 使用FPDF库生成PDF，支持中文"""
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    user_id = session.get('user_id', username)

    try:
        from fpdf import FPDF
        import io
        import os
        from flask import make_response

        api_result = get_predictions_from_admin(user_id, page=1, page_size=10000)
        items = api_result.get('items', [])

        pdf = FPDF()
        pdf.add_page()
        
        # 尝试加载中文字体，支持多种路径
        font_paths = [
            'C:\\Windows\\Fonts\\simhei.ttf',
            'C:\\Windows\\Fonts\\simsun.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/Library/Fonts/SimHei.ttf'
        ]
        
        font_loaded = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdf.add_font('Custom', '', font_path, uni=True)
                    font_loaded = True
                    break
                except:
                    continue
        
        if font_loaded:
            pdf.set_font('Custom', '', 12)
        else:
            # 如果中文字体加载失败，使用默认字体并转换中文
            pdf.set_font('Helvetica', '', 12)

        # 标题
        title_text = '预测记录报告' if font_loaded else 'Prediction Records Report'
        pdf.set_font('Custom' if font_loaded else 'Helvetica', '', 16)
        pdf.cell(0, 20, title_text, 0, 1, 'C')
        
        # 基本信息
        pdf.set_font('Custom' if font_loaded else 'Helvetica', '', 12)
        user_label = '用户:' if font_loaded else 'User:'
        time_label = '生成时间:' if font_loaded else 'Generated:'
        count_label = '总记录数:' if font_loaded else 'Total Records:'
        pdf.cell(0, 10, f'{user_label} {username}', 0, 1)
        pdf.cell(0, 10, f'{time_label} {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
        pdf.cell(0, 10, f'{count_label} {len(items)}', 0, 1)
        pdf.ln(5)
        
        # 表格标题
        # 不使用粗体，避免字体加载问题
        pdf.set_font('Custom' if font_loaded else 'Helvetica', '', 11)
        id_label = 'ID'
        time_col_label = '预测时间' if font_loaded else 'Time'
        result_label = '结果' if font_loaded else 'Result'
        conf_label = '置信度' if font_loaded else 'Confidence'
        pdf.cell(20, 10, id_label, 1, 0, 'C')
        pdf.cell(45, 10, time_col_label, 1, 0, 'C')
        pdf.cell(30, 10, result_label, 1, 0, 'C')
        pdf.cell(30, 10, conf_label, 1, 1, 'C')
        
        # 表格内容
        pdf.set_font('Custom' if font_loaded else 'Helvetica', '', 10)
        for item in items:
            record_id = str(item.get('id', 'N/A'))
            predict_time = str(item.get('created_at', 'N/A'))[:19]
            result = str(item.get('prediction_result', 'N/A'))
            # 如果没有中文字体，转换中文结果
            if not font_loaded:
                if result == '良性':
                    result = 'Benign'
                elif result == '恶性':
                    result = 'Malignant'
            confidence = item.get('confidence', 0)
            confidence_str = f"{confidence * 100:.1f}%"
            
            pdf.cell(20, 10, record_id, 1, 0, 'C')
            pdf.cell(45, 10, predict_time, 1, 0, 'C')
            pdf.cell(30, 10, result, 1, 0, 'C')
            pdf.cell(30, 10, confidence_str, 1, 1, 'C')

        # 输出PDF
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment; filename=prediction_records.pdf')

        return response

    except Exception as e:
        print(f"PDF export error: {e}")
        import traceback
        traceback.print_exc()

        from flask import make_response
        response = make_response(f"PDF export failed: {str(e)}")
        response.status_code = 500
        return response


@app.route('/trends')
def trends():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    user_id = session.get('user_id', username)

    api_result = get_predictions_from_admin(user_id, page=1, page_size=10000)
    items = api_result.get('items', [])

    records = []
    for item in items:
        features = item.get('features', {})
        records.append({
            'id': item.get('id'),
            'username': username,
            'result': item.get('prediction_result'),
            'confidence': item.get('confidence'),
            'predict_time': item.get('created_at'),
            'duration': 0,
            'radius_mean': features.get('feature_1', 0),
            'texture_mean': features.get('feature_2', 0),
            'perimeter_mean': features.get('feature_3', 0),
            'area_mean': features.get('feature_4', 0),
            'smoothness_mean': features.get('feature_5', 0),
            'compactness_mean': features.get('feature_6', 0),
            'concavity_mean': features.get('feature_7', 0),
            'concave_points_mean': features.get('feature_8', 0),
            'symmetry_mean': features.get('feature_9', 0),
            'fractal_dimension_mean': features.get('feature_10', 0),
            'radius_se': features.get('feature_11', 0),
            'texture_se': features.get('feature_12', 0),
            'perimeter_se': features.get('feature_13', 0),
            'area_se': features.get('feature_14', 0),
            'smoothness_se': features.get('feature_15', 0),
            'compactness_se': features.get('feature_16', 0),
            'concavity_se': features.get('feature_17', 0),
            'concave_points_se': features.get('feature_18', 0),
            'symmetry_se': features.get('feature_19', 0),
            'fractal_dimension_se': features.get('feature_20', 0),
            'radius_worst': features.get('feature_21', 0),
            'texture_worst': features.get('feature_22', 0),
            'perimeter_worst': features.get('feature_23', 0),
            'area_worst': features.get('feature_24', 0),
            'smoothness_worst': features.get('feature_25', 0),
            'compactness_worst': features.get('feature_26', 0),
            'concavity_worst': features.get('feature_27', 0),
            'concave_points_worst': features.get('feature_28', 0),
            'symmetry_worst': features.get('feature_29', 0),
            'fractal_dimension_worst': features.get('feature_30', 0)
        })

    return render_template('trends.html', records=records)


@app.route('/batch')
def batch():
    if 'username' not in session:
        return redirect('/login')
    
    return render_template('batch.html')


@app.route('/batch-results')
def batch_results():
    if 'username' not in session:
        return redirect('/login')
    
    if 'batch_results' not in session:
        return redirect('/batch')
    
    results = session['batch_results']
    return render_template('batch_results.html', results=results)


@app.route('/download-template')
def download_template():
    if 'username' not in session:
        return redirect('/login')
    
    # 创建模板DataFrame
    import pandas as pd
    import io
    from flask import send_file
    
    # 特征名称和说明
    features = [
        'radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean',
        'smoothness_mean', 'compactness_mean', 'concavity_mean', 'concave_points_mean',
        'symmetry_mean', 'fractal_dimension_mean',
        'radius_se', 'texture_se', 'perimeter_se', 'area_se',
        'smoothness_se', 'compactness_se', 'concavity_se', 'concave_points_se',
        'symmetry_se', 'fractal_dimension_se',
        'radius_worst', 'texture_worst', 'perimeter_worst', 'area_worst',
        'smoothness_worst', 'compactness_worst', 'concavity_worst', 'concave_points_worst',
        'symmetry_worst', 'fractal_dimension_worst'
    ]
    
    # 创建模板数据
    template_data = {
        '特征名称': features,
        '填写说明': ['请输入数值'] * len(features),
        '正常参考范围': [
            '6.98-14.12', '9.71-19.28', '43.79-99.7', '143.5-654.9',
            '0.05-0.1', '0.01-0.1', '0-0.1', '0-0.05',
            '0.1-0.2', '0.05-0.08',
            '0.1-0.5', '0.5-2.0', '0.7-5.0', '10-100',
            '0.001-0.01', '0.001-0.03', '0-0.05', '0-0.02',
            '0.001-0.03', '0.0001-0.01',
            '7.93-16.26', '12.02-25.2', '50.41-124.9', '185.2-970.6',
            '0.07-0.13', '0.02-0.25', '0-0.4', '0-0.2',
            '0.15-0.3', '0.06-0.1'
        ]
    }
    
    df = pd.DataFrame(template_data)
    
    # 创建Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='模板')
    output.seek(0)
    
    return send_file(output, download_name='breast_cancer_prediction_template.xlsx', as_attachment=True)


@app.route('/batch-predict', methods=['POST'])
def batch_predict():
    print("=== 批量预测请求到达 ===")
    if 'username' not in session:
        print("用户未登录")
        return redirect('/login')
    
    print(f"登录用户: {session['username']}")
    
    if 'file' not in request.files:
        print("错误: 没有找到文件")
        return render_template('batch.html', error='请选择文件')
    
    file = request.files['file']
    print(f"文件名: {file.filename}")
    
    if file.filename == '':
        print("错误: 文件名为空")
        return render_template('batch.html', error='请选择文件')
    
    # 处理文件
    import pandas as pd
    import io
    
    try:
        # 读取文件
        print(f"尝试读取文件: {file.filename}")
        if file.filename.endswith('.csv'):
            # 先尝试不指定header，让pandas自己推断
            df = pd.read_csv(file)
            # 检查第一行是否可能是数据（所有列名看起来像数字）
            all_numeric_cols = all(str(c).replace('.', '').isdigit() for c in df.columns[:min(5, len(df.columns))])
            if all_numeric_cols and len(df.columns) >= 30:
                # 如果列名看起来都是数字，说明第一行被当作表头了，重新读取
                file.seek(0)  # 重置文件指针
                df = pd.read_csv(file, header=None)
                print("检测到纯数据格式，重新读取文件（无表头）")
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            print(f"错误: 文件格式不支持: {file.filename}")
            return render_template('batch.html', error='仅支持CSV和Excel文件')
        
        print(f"文件读取成功，行数: {len(df)}, 列数: {len(df.columns)}")
        print(f"列名: {list(df.columns)}")
        
        global light_clf, light_sc, model_ready
        
        # 检查模型是否就绪
        if light_clf is None or light_sc is None or light_feature_selector is None:
            return render_template('batch.html', error='模型正在加载中，请稍后重试')
        
        # 判断文件格式：
        # 格式1: 纯数据格式，30行(特征) x N列(样本)，第一列可能是特征名
        # 格式2: 模板格式，包含说明列（特征名称、填写说明、正常参考范围）
        
        # 检查是否为模板格式（包含说明列）
        is_template_format = False
        if len(df.columns) >= 3:
            # 检查前3列是否为说明列
            first_col_name = str(df.columns[0]).strip().lower()
            if first_col_name in ['特征名称', 'feature', 'radius_mean', '0']:
                # 检查第一行第一列是否为特征名称
                try:
                    first_value = str(df.iloc[0, 0]).strip().lower()
                    if first_value in ['radius_mean', 'radius', '半径', '特征名称']:
                        is_template_format = True
                except:
                    pass
        
        if is_template_format:
            # 模板格式：跳过前3列说明列，从第4列开始是数据列
            # 每行代表一个特征，每列代表一个样本
            data_columns = df.columns[3:]  # 从第4列开始是数据
            if len(data_columns) == 0:
                return render_template('batch.html', error='没有找到数据列，请在模板文件的D列及以后填入数据')
            
            print(f"模板格式检测：数据列数量 = {len(data_columns)}")
            print(f"数据列名称: {list(data_columns)}")
            
            # 转置处理：每列变成一行
            results = []
            for col_idx, col_name in enumerate(data_columns):
                try:
                    # 获取这一列的30个特征值
                    print(f"正在处理列: {col_name}")
                    data = df[col_name].values.astype(float)
                    print(f"数据长度: {len(data)}, 前5个值: {data[:5]}")
                    
                    if len(data) != 30:
                        results.append({
                            'index': col_idx + 1,
                            'features': data.tolist(),
                            'output': 'Error',
                            'confidence': 0,
                            'error': f'特征数量不正确，期望30个，实际{len(data)}个'
                        })
                        continue
                    
                    data_np = data.reshape(1, -1)
                    if enhanced_model_ready and enhanced_clf is not None:
                        out, prob, t = enhanced_predict(data_np)
                    else:
                        out, prob, t = light_predict(data_np)

                    print(f"预测结果: {out[0]}, 置信度: {prob[0][out[0]]}")
                    
                    result = {
                        'index': col_idx + 1,
                        'features': data.tolist(),
                        'raw_data': data.tolist(),  # 保存原始数据用于SHAP分析
                        'output': 'Malignant' if out[0] == 1 else 'Benign',
                        'confidence': float(prob[0][out[0]])
                    }
                    results.append(result)
                except Exception as e:
                    print(f"处理列 {col_name} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # 检查模型是否正确加载
                    print(f"light_clf: {light_clf}")
                    print(f"light_sc: {light_sc}")
                    print(f"model_ready: {model_ready}")
                    # 检查数据
                    print(f"data: {data if 'data' in locals() else 'not defined'}")
                    if 'data' in locals():
                        print(f"data shape: {data.shape if hasattr(data, 'shape') else 'no shape'}")
                    results.append({
                        'index': col_idx + 1,
                        'features': [],
                        'output': 'Error',
                        'confidence': 0,
                        'error': str(e)
                    })
        else:
            # 纯数据格式：每行是一个样本，30列特征
            if len(df.columns) < 30:
                return render_template('batch.html', error=f'文件格式不正确，需要至少30个特征列，当前{len(df.columns)}列')
            
            # 使用前30列
            df = df.iloc[:, :30]
            
            results = []
            for idx, row in df.iterrows():
                try:
                    data = row.values.astype(float)
                    data_np = data.reshape(1, -1)
                    if enhanced_model_ready and enhanced_clf is not None:
                        out, prob, t = enhanced_predict(data_np)
                    else:
                        out, prob, t = light_predict(data_np)

                    result = {
                        'index': idx + 1,
                        'features': data.tolist(),
                        'raw_data': data.tolist(),  # 保存原始数据用于SHAP分析
                        'output': 'Malignant' if out[0] == 1 else 'Benign',
                        'confidence': float(prob[0][out[0]])
                    }
                    results.append(result)
                except Exception as e:
                    results.append({
                        'index': idx + 1,
                        'features': row.values.tolist(),
                        'output': 'Error',
                        'confidence': 0,
                        'error': str(e)
                    })
        
        # 保存批量结果到session
        session['batch_results'] = results

        # 将批量预测记录上传到管理后台
        username = session.get('username', 'anonymous')
        user_id = session.get('user_id', username)
        saved_count = 0

        for result in results:
            if result['output'] != 'Error':
                # 获取特征列表（30个特征）
                features = result.get('features', [])
                if len(features) == 30:
                    # 上传预测记录到管理后台
                    if upload_prediction_to_admin(user_id, features, result['output'], result['confidence']):
                        saved_count += 1

        print(f"批量预测完成，已上传 {saved_count} 条记录到管理后台")

        return render_template('batch_results.html', results=results)
    except Exception as e:
        return render_template('batch.html', error=f'处理文件时出错: {str(e)}')


@app.route('/export-pdf/<int:record_id>')
def export_pdf(record_id):
    if 'username' not in session:
        return redirect('/login')
    
    username = session['username']
    
    # 从管理后台获取记录详情（与记录列表使用相同数据源）
    try:
        req = urllib.request.Request(
            f'{ADMIN_API_URL}/public/user/record/{record_id}',
            method='GET'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result_data = json.loads(response.read().decode('utf-8'))
            if result_data.get('code') == 200:
                record = normalize_record(result_data.get('data'))
            else:
                return redirect('/records')
    except Exception as e:
        print(f"获取记录详情失败: {e}")
        return redirect('/records')
    
    # 生成PDF报告
    from fpdf import FPDF
    import io
    from flask import send_file
    
    pdf = FPDF()
    pdf.add_page()
    
    # 设置中文字体
    pdf.add_font('SimHei', '', 'C:\\Windows\\Fonts\\simhei.ttf', uni=True)
    pdf.set_font('SimHei', '', 12)
    
    # 标题
    pdf.set_font('SimHei', '', 16)
    pdf.cell(0, 20, '乳腺癌检测报告', 0, 1, 'C')
    

    
    # 基本信息
    pdf.set_font('SimHei', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f'用户: {username}', 0, 1)
    pdf.cell(0, 10, f'预测时间: {record.get("created_at", "")}', 0, 1)
    pdf.ln(10)
    
    # 预测结果
    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '预测结果', 0, 1)
    pdf.set_font('SimHei', '', 12)
    result_text = '恶性' if record.get('prediction_result') == 'Malignant' else '良性'
    pdf.cell(0, 10, f'结果: {result_text}', 0, 1)
    pdf.cell(0, 10, f'置信度: {(record.get("confidence") or 0) * 100:.2f}%', 0, 1)
    pdf.ln(10)
    
    # 特征值
    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '特征值', 0, 1)
    pdf.set_font('SimHei', '', 10)
    
    feature_names = [
        '半径平均值', '纹理平均值', '周长平均值', '面积平均值',
        '平滑度平均值', '紧凑度平均值', '凹度平均值', '凹点平均值',
        '对称性平均值', '分形维数平均值',
        '半径标准差', '纹理标准差', '周长标准差', '面积标准差',
        '平滑度标准差', '紧凑度标准差', '凹度标准差', '凹点标准差',
        '对称性标准差', '分形维数标准差',
        '半径最大值', '纹理最大值', '周长最大值', '面积最大值',
        '平滑度最大值', '紧凑度最大值', '凹度最大值', '凹点最大值',
        '对称性最大值', '分形维数最大值'
    ]
    
    features = record.get('features') or {}
    for i, name in enumerate(feature_names):
        value = features.get('feature_%d' % (i + 1))
        if value is None:
            continue
        pdf.cell(90, 8, f'{name}:', 0, 0)
        pdf.cell(90, 8, f'{float(value):.4f}', 0, 1)
    
    # 建议
    pdf.ln(10)
    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '建议', 0, 1)
    pdf.set_font('SimHei', '', 12)
    
    if record.get('prediction_result') == 'Malignant':
        pdf.multi_cell(0, 10, '建议：请立即前往正规医疗机构进行进一步检查，包括病理活检等专业诊断。根据CSCO乳腺癌诊疗指南，早期诊断和治疗可以显著提高治愈率。')
    else:
        pdf.multi_cell(0, 10, '建议：结果为良性，但仍建议定期复查，保持健康的生活方式。如有异常症状，请及时就医。')
    
    # 输出PDF
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    
    return send_file(output, download_name=f'breast_cancer_report_{record_id}.pdf', as_attachment=True)


@app.route('/export-pdf-batch/<int:index>')
def export_pdf_batch(index):
    if 'username' not in session:
        return redirect('/login')
    
    if 'batch_results' not in session:
        print(f"ERROR: batch_results not in session")
        return redirect('/batch')
    
    results = session['batch_results']
    print(f"batch_results length: {len(results)}, requested index: {index}")
    
    if index < 0 or index >= len(results):
        print(f"ERROR: index out of range: {index} >= {len(results)}")
        return redirect('/batch')
    
    result = results[index]
    
    # 生成PDF报告
    from fpdf import FPDF
    import io
    from flask import send_file
    
    pdf = FPDF()
    pdf.add_page()
    
    # 设置中文字体
    pdf.add_font('SimHei', '', 'C:\\Windows\\Fonts\\simhei.ttf', uni=True)
    pdf.set_font('SimHei', '', 12)
    
    # 标题
    pdf.set_font('SimHei', '', 16)
    pdf.cell(0, 20, '乳腺癌检测报告', 0, 1, 'C')
    

    
    # 基本信息
    pdf.set_font('SimHei', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f'用户: {session.get("username")}', 0, 1)
    pdf.cell(0, 10, f'预测时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
    pdf.cell(0, 10, f'序号: {result["index"]}', 0, 1)
    pdf.ln(10)
    
    # 预测结果
    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '预测结果', 0, 1)
    pdf.set_font('SimHei', '', 12)
    result_text = '恶性' if result['output'] == 'Malignant' else '良性'
    pdf.cell(0, 10, f'结果: {result_text}', 0, 1)
    pdf.cell(0, 10, f'置信度: {result["confidence"] * 100:.2f}%', 0, 1)
    pdf.ln(10)
    
    # 特征值
    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '特征值', 0, 1)
    pdf.set_font('SimHei', '', 10)
    
    feature_names = [
        '半径平均值', '纹理平均值', '周长平均值', '面积平均值',
        '平滑度平均值', '紧凑度平均值', '凹度平均值', '凹点平均值',
        '对称性平均值', '分形维数平均值',
        '半径标准差', '纹理标准差', '周长标准差', '面积标准差',
        '平滑度标准差', '紧凑度标准差', '凹度标准差', '凹点标准差',
        '对称性标准差', '分形维数标准差',
        '半径最大值', '纹理最大值', '周长最大值', '面积最大值',
        '平滑度最大值', '紧凑度最大值', '凹度最大值', '凹点最大值',
        '对称性最大值', '分形维数最大值'
    ]
    
    for i, name in enumerate(feature_names):
        if i < len(result['features']):
            pdf.cell(90, 8, f'{name}:', 0, 0)
            pdf.cell(90, 8, f'{result["features"][i]:.4f}', 0, 1)
    
    # 建议
    pdf.ln(10)
    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '建议', 0, 1)
    pdf.set_font('SimHei', '', 12)
    
    if result['output'] == 'Malignant':
        pdf.multi_cell(0, 10, '建议：请立即前往正规医疗机构进行进一步检查，包括病理活检等专业诊断。根据CSCO乳腺癌诊疗指南，早期诊断和治疗可以显著提高治愈率。')
    else:
        pdf.multi_cell(0, 10, '建议：结果为良性，但仍建议定期复查，保持健康的生活方式。如有异常症状，请及时就医。')
    
    # 输出PDF
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    
    return send_file(output, download_name=f'breast_cancer_report_batch_{result["index"]}.pdf', as_attachment=True)


@app.route('/export-batch-results')
def export_batch_results():
    if 'username' not in session:
        return redirect('/login')

    if 'batch_results' not in session:
        return redirect('/batch')

    results = session['batch_results']

    pdf = FPDF()
    pdf.add_page()

    pdf.add_font('SimHei', '', 'C:\\Windows\\Fonts\\simhei.ttf', uni=True)
    pdf.set_font('SimHei', '', 16)
    pdf.cell(0, 20, '乳腺癌批量检测报告', 0, 1, 'C')

    pdf.set_font('SimHei', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f'用户: {session.get("username")}', 0, 1)
    pdf.cell(0, 10, f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
    pdf.cell(0, 10, f'记录数量: {len(results)}', 0, 1)
    pdf.ln(10)

    pdf.set_font('SimHei', '', 14)
    pdf.cell(0, 10, '检测结果汇总', 0, 1)
    pdf.set_font('SimHei', '', 11)

    header_color = (102, 126, 234)
    pdf.set_fill_color(*header_color)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(20, 10, '序号', 1, 0, 'C', True)
    pdf.cell(40, 10, '预测结果', 1, 0, 'C', True)
    pdf.cell(40, 10, '置信度', 1, 0, 'C', True)
    pdf.cell(80, 10, '建议', 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    benign_count = 0
    malignant_count = 0

    for result in results:
        result_text = '恶性' if result['output'] == 'Malignant' else '良性' if result['output'] == 'Benign' else '错误'
        confidence_text = f"{result['confidence'] * 100:.2f}%" if result['output'] != 'Error' else '-'

        if result['output'] == 'Benign' or result['output'] == 'Benign':
            benign_count += 1
        elif result['output'] == 'Malignant' or result['output'] == 'Malignant':
            malignant_count += 1

        if result['output'] == 'Malignant':
            pdf.set_fill_color(255, 235, 238)
            pdf.set_text_color(183, 28, 28)
        elif result['output'] == 'Benign':
            pdf.set_fill_color(232, 245, 233)
            pdf.set_text_color(27, 94, 32)
        else:
            pdf.set_fill_color(248, 248, 248)
            pdf.set_text_color(97, 97, 97)

        pdf.cell(20, 10, str(result['index']), 1, 0, 'C', True)
        pdf.cell(40, 10, result_text, 1, 0, 'C', True)
        pdf.cell(40, 10, confidence_text, 1, 0, 'C', True)

        if result['output'] == 'Malignant':
            pdf.cell(80, 10, '建议进一步检查', 1, 1, 'C', True)
        elif result['output'] == 'Benign':
            pdf.cell(80, 10, '定期复查', 1, 1, 'C', True)
        else:
            pdf.cell(80, 10, '-', 1, 1, 'C', True)

    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('SimHei', '', 12)
    pdf.cell(0, 10, f'统计: 良性 {benign_count} 例, 恶性 {malignant_count} 例', 0, 1)
    pdf.ln(5)

    pdf.set_font('SimHei', '', 10)
    pdf.multi_cell(0, 8, '注：本报告仅供辅助参考，不能替代专业医生的诊断意见。如有异常，请及时前往正规医疗机构就诊。')

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)

    return send_file(output, download_name='breast_cancer_batch_report.pdf', as_attachment=True, mimetype='application/pdf')


@app.route('/shap-analyze/<int:index>')
def shap_analyze(index):
    """SHAP分析路由 - 为批量预测记录提供特征重要性分析"""
    if 'username' not in session:
        return jsonify({'error': '请先登录'}), 403
    
    if 'batch_results' not in session:
        return jsonify({'error': '没有可用的批量预测数据'}), 400
    
    results = session['batch_results']
    
    if index < 0 or index >= len(results):
        return jsonify({'error': '无效的记录索引'}), 400
    
    result = results[index]
    
    if result['output'] == 'Error':
        return jsonify({'error': '该记录预测失败，无法进行SHAP分析'}), 400
    
    # 获取原始数据
    raw_data = result.get('raw_data', [])
    
    if not raw_data or len(raw_data) != 30:
        return jsonify({'error': '缺少原始特征数据'}), 400
    
    # 调用SHAP解释器
    from shap_explainer import get_feature_explanation
    
    prediction_dict = {
        'data': raw_data,
        'output': result['output'],
        'confidence': result['confidence']
    }
    
    shap_result = get_feature_explanation(prediction_dict)
    
    if shap_result is None:
        return jsonify({'error': 'SHAP分析失败'}), 500
    
    return jsonify({
        'success': True,
        'prediction': result['output'],
        'confidence': result['confidence'],
        'top_features': shap_result.get('top_features', []),
        'index': index
    })


@app.route('/ai-analyze', methods=['POST'])
def ai_analyze():
    """AI 深度分析：统一走 agent 的 report 意图（不再单独维护一套 prompt）。"""
    if 'username' not in session:
        return jsonify({'error': '请先登录'}), 403

    prediction_data = session.get('last_prediction')
    if not prediction_data:
        return jsonify({'error': '没有可用的预测数据，请先进行预测。'}), 400

    values = prediction_data.get('data') or []
    if len(values) != 30:
        return jsonify({'error': '输入数据不完整，请重新进行预测。'}), 400

    if not _agent_bind_runtime():
        return jsonify({'error': '模型尚未就绪，请稍后重试。'}), 503

    question = '生成一份完整的分析报告'
    ctx = _agent_ctx(question)
    try:
        result = _agent_orch.run(ctx, question, values)
    except Exception as exc:  # noqa: BLE001
        app.logger.exception('ai-analyze 失败')
        return jsonify({'error': '分析失败：%s' % str(exc)[:120]}), 500

    return jsonify({
        'answer': result['answer_md'],
        'citations': result['citations'],
        'run_id': result['run_id'],
        'intent': result['intent'],
        'cached': False,
        'validation': result.get('verify', {}),
    })


@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    """生成结构化分析报告（原 Coze 工作流已由本地 agent 取代）。"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'success': False, 'message': '模型尚未就绪，请稍后重试'}), 503

    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '生成一份完整的分析报告').strip()
    last = session.get('last_prediction') or {}
    values = last.get('data')
    if not values:
        return jsonify({'success': False, 'message': '请先完成一次预测'}), 400

    ctx = _agent_ctx(question)
    ctx.intent = 'report'
    try:
        result = _agent_orch.run(ctx, question, values)
    except Exception as exc:  # noqa: BLE001
        app.logger.exception('生成报告失败')
        return jsonify({'success': False, 'message': str(exc)[:200]}), 500

    return jsonify({
        'success': True,
        'data': {'report': result['answer_md'],
                 'citations': result['citations'],
                 'run_id': result['run_id']},
    })


# ==================== SHAP 可解释性相关路由 ====================

@app.route('/shap-analysis')
def shap_analysis():
	"""显示SHAP可解释性分析页面"""
	if 'username' not in session:
		return redirect('/login')
	
	# 从session获取最后一次预测
	last_prediction = session.get('last_prediction')
	if not last_prediction:
		return render_template('shap_analysis.html', 
							 error='没有找到最近的预测，请先进行预测。')
	
	return render_template('shap_analysis.html', 
						 prediction=last_prediction)


@app.route('/shap-generate', methods=['POST'])
def shap_generate():
	"""生成SHAP解释图表"""
	if 'username' not in session:
		return jsonify({'error': '请先登录'}), 403
	
	try:
		# 从request获取数据
		data = request.json
		raw_data = data.get('data', [])
		prediction = data.get('prediction', 'Unknown')
		confidence = data.get('confidence', 0)
		
		if len(raw_data) != 30:
			return jsonify({'error': '数据格式错误'}), 400
		
		# 检查SHAP解释器是否就绪
		global global_shap_explainer, shap_ready
		
		# 如果SHAP解释器未就绪，尝试运行时初始化
		if not shap_ready or global_shap_explainer is None:
			print("SHAP解释器未就绪，尝试运行时初始化...")
			try:
				# 双重检查锁定模式，确保线程安全
				with model_lock:
					if global_shap_explainer is None:
						global_shap_explainer = SimpleSHAPExplainer()
						shap_ready = True
						print("SHAP解释器运行时初始化成功!")
			except Exception as init_error:
				print(f"SHAP解释器运行时初始化失败: {init_error}")
				return jsonify({'error': 'SHAP解释器初始化失败，请刷新页面重试'}), 503
		
		# 生成解释
		explanation = global_shap_explainer.explain_single_prediction(
			raw_data, prediction, confidence
		)
		
		# 对于简化SHAP实现，不需要图表路径，直接返回解释数据
		return jsonify({
			'success': True,
			'explanation': explanation
		})
	except Exception as e:
		print(f"SHAP生成错误: {str(e)}")
		import traceback
		traceback.print_exc()
		return jsonify({'error': f'SHAP分析失败: {str(e)}'}), 500


@app.route('/api/ai-batch-analysis', methods=['POST'])
def api_ai_batch_analysis():
    """趋势分析：统一走 agent（原实现内置了第二处硬编码密钥，已移除）。"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'success': False, 'error': '模型尚未就绪'}), 503

    question = '请分析我最近的预测趋势，并给出建议'
    ctx = _agent_ctx(question)
    try:
        result = _agent_orch.run(ctx, question, None)
    except Exception as exc:  # noqa: BLE001
        app.logger.exception('趋势分析失败')
        return jsonify({'success': False, 'error': str(exc)[:150]}), 500

    return jsonify({'success': True, 'analysis': result['answer_md'],
                    'citations': result['citations'], 'run_id': result['run_id']})


@app.route('/shap-features', methods=['GET'])
def shap_features():
	"""获取SHAP特征列表"""
	return jsonify({
		'features': FEATURE_NAMES,
		'count': len(FEATURE_NAMES)
	})

@app.route('/clear-ai-history', methods=['POST'])
def clear_ai_history():
	"""清除用户的AI询问记录"""
	if 'user_id' not in session:
		return jsonify({'success': False, 'message': '未登录'}), 401
	
	user_id = session['user_id']
	
	# 清除用户的AI缓存
	with ai_cache_lock:
		if user_id in user_ai_cache:
			user_ai_cache[user_id] = {}
	
	return jsonify({'success': True, 'message': '记录已清除'})

# ==================== Agent / RAG 接口 ====================

from agent import db as _agent_db
from agent import orchestrator as _agent_orch
from agent import registry as _agent_registry
from agent import runtime as _agent_runtime
from agent.context import AgentContext as _AgentContext

_AGENT_STATE = {'bound': False, 'explainer': None}


def _agent_bind_runtime():
    """把主站能力注入 agent 层（只绑一次）。"""
    if _AGENT_STATE['bound']:
        return True
    if not model_ready or light_clf is None:
        return False

    def _predict(features):
        arr = np.asarray(features, dtype=float).reshape(1, -1)
        if enhanced_model_ready and enhanced_clf is not None:
            try:
                out, prob, t = enhanced_predict(arr)
                return {'output': '恶性' if int(out[0]) == 1 else '良性',
                        'raw_output': int(out[0]),
                        'confidence': float(prob[0][int(out[0])]),
                        'time': float(t), 'model_type': 'enhanced'}
            except Exception as exc:
                app.logger.warning('agent: 增强模型失败，降级轻量模型: %s', exc)
        out, prob, t = light_predict(arr)
        return {'output': '恶性' if int(out[0]) == 1 else '良性',
                'raw_output': int(out[0]),
                'confidence': float(prob[0][int(out[0])]),
                'time': float(t), 'model_type': 'light'}

    def _explain(features, prediction, confidence):
        if _AGENT_STATE['explainer'] is None:
            _AGENT_STATE['explainer'] = SimpleSHAPExplainer()
        return _AGENT_STATE['explainer'].explain_single_prediction(
            features, prediction, confidence)

    from agent.rag import index as _rag_index

    _agent_runtime.get().bind(
        rag=_rag_index,
        predict=_predict,
        explain=_explain,
        fetch_records=lambda uid, page, size: get_predictions_from_admin(
            uid, page=page, page_size=size),
        fetch_stats=lambda uid: get_statistics_from_admin(uid),
    )
    _agent_db.init_schema()
    _AGENT_STATE['bound'] = True
    print('Agent 运行时已绑定')
    return True


def _agent_ctx(question):
    role_id = session.get('role_id')
    if role_id is None:
        role_id = 1 if session.get('username') == 'admin' else 3
    return _AgentContext(
        user_id=session.get('user_id', session.get('username', 'anonymous')),
        role_id=int(role_id),
        lang=session.get('lang', 'zh'),
        question=question,
    )


def _agent_values(raw):
    """统一处理 30 维输入；缺省时回退到最近一次预测。"""
    if raw is None:
        last = session.get('last_prediction') or {}
        return last.get('data')
    if not isinstance(raw, (list, tuple)):
        raise ValueError('values 必须是数组')
    values = [float(v) for v in raw]
    if len(values) != 30:
        raise ValueError('values 需要 30 个数值，实际 %d 个' % len(values))
    return values


@app.route('/api/agent/run', methods=['POST'])
def api_agent_run():
    """Agent 主入口（SSE）。"""
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'ok': False, 'error': '模型尚未就绪，请稍后重试'}), 503

    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'ok': False, 'error': '缺少 question'}), 400

    try:
        values = _agent_values(data.get('values'))
    except (TypeError, ValueError) as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    ctx = _agent_ctx(question)
    require_confirm = bool(data.get('require_confirm'))

    def generate():
        try:
            for event, payload in _agent_orch.stream(ctx, question, values,
                                                     require_confirm=require_confirm):
                yield 'event: %s\ndata: %s\n\n' % (
                    event, json.dumps(payload, ensure_ascii=False, default=str))
        except Exception as exc:  # noqa: BLE001
            app.logger.exception('agent run 失败')
            yield 'event: error\ndata: %s\n\n' % json.dumps(
                {'error': str(exc)}, ensure_ascii=False)

    from flask import Response
    resp = Response(generate(), mimetype='text/event-stream')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp


@app.route('/api/agent/run-sync', methods=['POST'])
def api_agent_run_sync():
    """同步版（调试/评测用，直接返回 JSON）。"""
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'ok': False, 'error': '模型尚未就绪'}), 503

    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'ok': False, 'error': '缺少 question'}), 400

    try:
        values = _agent_values(data.get('values'))
    except (TypeError, ValueError) as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    ctx = _agent_ctx(question)
    result = _agent_orch.run(ctx, question, values,
                             require_confirm=bool(data.get('require_confirm')))
    result.pop('facts', None)
    result['steps'] = result.get('steps', [])
    return jsonify({'ok': True, 'result': result})


@app.route('/api/agent/runs', methods=['GET'])
def api_agent_runs():
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    _agent_db.init_schema()
    runs = _agent_db.list_runs(session.get('user_id', session.get('username')), 20)
    return jsonify({'ok': True, 'runs': runs})


@app.route('/api/agent/runs/<run_id>', methods=['GET'])
def api_agent_run_detail(run_id):
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    _agent_db.init_schema()
    run = _agent_db.get_run(run_id)
    if not run:
        return jsonify({'ok': False, 'error': 'run 不存在'}), 404
    me = str(session.get('user_id', session.get('username')))
    if str(run.get('user_id')) != me and session.get('username') != 'admin':
        return jsonify({'ok': False, 'error': '无权查看'}), 403
    return jsonify({'ok': True, 'run': run})


_SAMPLE_DF = None


@app.route('/api/samples/random', methods=['GET'])
def api_samples_random():
    """返回一条来自数据集的真实样本，保证落在训练分布内。"""
    global _SAMPLE_DF
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403

    try:
        if _SAMPLE_DF is None:
            import pandas as _pd
            _SAMPLE_DF = _pd.read_csv('Breast Cancer Data.csv')
        df = _SAMPLE_DF
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': '数据读取失败: %s' % exc}), 500

    label = (request.args.get('label') or '').lower()
    if label in ('benign', 'b', '良性'):
        subset = df[df.iloc[:, 1].astype(str).str.strip() == 'B']
    elif label in ('malignant', 'm', '恶性'):
        subset = df[df.iloc[:, 1].astype(str).str.strip() == 'M']
    else:
        subset = df

    if len(subset) == 0:
        return jsonify({'ok': False, 'error': '没有符合条件的样本'}), 404

    row = subset.sample(1).iloc[0]
    values = [round(float(v), 4) for v in row.iloc[2:32]]
    diagnosis = str(row.iloc[1]).strip()

    return jsonify({
        'ok': True,
        'label': 'M' if diagnosis == 'M' else 'B',
        'label_zh': '恶性' if diagnosis == 'M' else '良性',
        'features': values,
    })


@app.route('/api/agent/inspect', methods=['GET'])
def api_agent_inspect():
    """主动巡检：不等用户提问，先报告最近记录里的异常。"""
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'ok': False, 'error': '模型尚未就绪'}), 503

    from agent import uncertainty as _unc

    user_id = session.get('user_id', session.get('username'))
    page = get_predictions_from_admin(user_id, page=1, page_size=50) or {}
    items = page.get('items') or []

    low_confidence = []
    outliers = []
    weird_labels = []
    standard = {'良性', '恶性', 'Benign', 'Malignant'}

    for item in items:
        label = str(item.get('prediction_result') or '')
        confidence = float(item.get('confidence') or 0)
        calibrated = _unc.calibrate(confidence)

        if label not in standard:
            weird_labels.append({'id': item.get('id'), 'label': label})

        if calibrated < 0.80:
            low_confidence.append({'id': item.get('id'), 'label': label,
                                   'calibrated': round(calibrated, 3)})

        features = item.get('features') or {}
        vector = [features.get('feature_%d' % i) for i in range(1, 31)]
        if all(v is not None for v in vector):
            distance = _unc.mahalanobis([float(v) for v in vector])
            d_abstain = float((_unc.config().get('mahalanobis') or {}).get('d_abstain', 1e9))
            if distance > d_abstain:
                outliers.append({'id': item.get('id'), 'distance': round(distance, 2),
                                 'threshold': round(d_abstain, 2)})

    findings = []
    if outliers:
        findings.append('发现 %d 条记录的输入明显偏离训练分布（如 #%s，马氏距离 %s），'
                        '这些记录的结论可靠性较低。'
                        % (len(outliers), outliers[0]['id'], outliers[0]['distance']))
    if low_confidence:
        findings.append('有 %d 条记录校准后置信度低于 0.80（如 #%s），建议复核。'
                        % (len(low_confidence), low_confidence[0]['id']))
    if weird_labels:
        findings.append('有 %d 条记录的结果字段不是标准值（如「%s」），可能是历史测试数据。'
                        % (len(weird_labels), weird_labels[0]['label']))
    if not findings:
        findings.append('最近 %d 条记录未发现明显异常。' % len(items))

    return jsonify({
        'ok': True,
        'scanned': len(items),
        'findings': findings,
        'details': {
            'outliers': outliers[:5],
            'low_confidence': low_confidence[:5],
            'weird_labels': weird_labels[:5],
        },
    })


@app.route('/api/agent/graph', methods=['GET'])
def api_agent_graph():
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    from agent import orchestrator as _orch
    return jsonify({'ok': True, 'graph': _orch.get_graph().describe(),
                    'labels': _orch.NODE_LABELS})


@app.route('/api/agent/runs/<run_id>/replay', methods=['GET'])
def api_agent_replay(run_id):
    """回放：返回检查点 + 已记录的步骤，可看状态快照。"""
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    run = _agent_db.get_run(run_id)
    if not run:
        return jsonify({'ok': False, 'error': 'run 不存在'}), 404
    me = str(session.get('user_id', session.get('username')))
    if str(run.get('user_id')) != me and session.get('username') != 'admin':
        return jsonify({'ok': False, 'error': '无权查看'}), 403

    checkpoint = _agent_db.load_checkpoint(run_id)
    return jsonify({
        'ok': True,
        'run_id': run_id,
        'run': run,
        'checkpoint': checkpoint,
        'can_resume': bool(checkpoint and checkpoint.get('next_node')),
        'summary': {
            'status': run.get('status'),
            'intent': run.get('intent'),
            'steps': len(run.get('steps') or []),
            'latency_ms': run.get('latency_ms'),
        },
    })


@app.route('/api/agent/resume', methods=['POST'])
def api_agent_resume():
    """从检查点恢复（中断后确认继续）。"""
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'ok': False, 'error': '模型尚未就绪'}), 503

    data = request.get_json(silent=True) or {}
    run_id = (data.get('run_id') or '').strip()
    if not run_id:
        return jsonify({'ok': False, 'error': '缺少 run_id'}), 400

    ctx = _agent_ctx('')
    try:
        result = _agent_orch.resume(run_id, ctx, confirmed=bool(data.get('confirmed', True)))
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 404
    except Exception as exc:  # noqa: BLE001
        app.logger.exception('resume 失败')
        return jsonify({'ok': False, 'error': str(exc)[:200]}), 500

    result.pop('facts', None)
    return jsonify({'ok': True, 'result': result})


@app.route('/api/agent/tools', methods=['GET'])
def api_agent_tools():
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    _agent_bind_runtime()
    from agent import llm as _agent_llm
    from agent.rag import index as _rag_index
    return jsonify({'ok': True,
                    'tools': _agent_registry.describe_tools(),
                    'llm': _agent_llm.usage(),
                    'rag': _rag_index.stats(),
                    'runtime': _agent_runtime.get().status()})


@app.route('/api/rag/search', methods=['GET'])
def api_rag_search():
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    from agent.rag import index as _rag_index
    query = (request.args.get('q') or '').strip()
    if not query:
        return jsonify({'ok': False, 'error': '缺少 q'}), 400
    k = min(int(request.args.get('k', 5) or 5), 20)
    return jsonify({'ok': True, 'query': query, 'hits': _rag_index.search(query, k)})


@app.route('/api/cases/similar', methods=['POST'])
def api_cases_similar():
    if 'username' not in session:
        return jsonify({'ok': False, 'error': '请先登录'}), 403
    if not _agent_bind_runtime():
        return jsonify({'ok': False, 'error': '模型尚未就绪'}), 503

    data = request.get_json(silent=True) or {}
    try:
        values = _agent_values(data.get('values'))
    except (TypeError, ValueError) as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    if values is None:
        return jsonify({'ok': False, 'error': '缺少 30 维特征'}), 400

    ctx = _agent_ctx('similar_cases')
    from agent import registry as _reg
    result = _reg.call_tool(ctx, 'similar_cases', {'features': values, 'k': int(data.get('k', 5))})
    return jsonify({'ok': result.ok, 'data': result.data, 'error': result.error})


def init_shap_in_background():
	"""后台初始化SHAP解释器"""
	global global_shap_explainer, shap_ready
	
	print("后台初始化SHAP解释器...")
	try:
		# 确保数据集文件存在
		if not os.path.exists('Breast Cancer Data.csv'):
			print("错误：数据集文件不存在")
			return
		
		# SimpleSHAPExplainer内部会自动训练分类器，不需要传入外部模型
		global_shap_explainer = SimpleSHAPExplainer()
		print("SHAP解释器初始化完成!")
		with model_lock:
			shap_ready = True
	except Exception as e:
		print(f"初始化SHAP解释器失败: {e}")
		import traceback
		traceback.print_exc()
		# 即使初始化失败，也设置一个基本的就绪状态，避免永久阻塞
		with model_lock:
			shap_ready = True  # 设置为True，但global_shap_explainer仍为None，会在请求时处理

def train_light_model_in_background():
	"""后台训练轻量化优化模型"""
	global light_clf, light_sc, light_feature_selector, model_ready
	
	print("后台线程启动，开始训练轻量化优化模型...")
	try:
		train_light_model()
		from light_optimization import light_clf as lt_clf, light_sc as lt_sc, light_feature_selector as lt_selector
		light_clf, light_sc, light_feature_selector = lt_clf, lt_sc, lt_selector
		print("轻量化优化模型训练完成!")
		with model_lock:
			model_ready = True
		
		# 启动增强型模型训练（提高置信度）
		enhanced_thread = threading.Thread(target=train_enhanced_model_in_background, daemon=True)
		enhanced_thread.start()
	except Exception as e:
		print(f"后台训练轻量化模型失败: {e}")

def train_enhanced_model_in_background():
	"""后台训练增强型模型（提高置信度）"""
	global enhanced_clf, enhanced_preprocessor, enhanced_feature_selector, enhanced_model_ready
	
	print("后台线程启动，开始训练增强型模型（提高置信度）...")
	try:
		train_enhanced_model()
		from enhanced_model import enhanced_clf as ec_clf, enhanced_preprocessor as ec_pre, enhanced_feature_selector as ec_selector
		enhanced_clf, enhanced_preprocessor, enhanced_feature_selector = ec_clf, ec_pre, ec_selector
		print("增强型模型训练完成! - 置信度将显著提升")
		with model_lock:
			enhanced_model_ready = True
	except Exception as e:
		print(f"后台训练增强型模型失败: {e}")



_MODELS_LOADED = False


def init_models_once():
    """加载模型与 SHAP 解释器（幂等）。

    必须在 import 时调用：gunicorn 不会执行 __main__，
    否则线上会一直停在"模型加载中"。
    """
    global _MODELS_LOADED, light_clf, light_sc, light_feature_selector, model_ready
    global enhanced_clf, enhanced_preprocessor, enhanced_feature_selector, enhanced_model_ready

    if _MODELS_LOADED:
        return
    _MODELS_LOADED = True

    loaded_lt_clf, loaded_lt_sc, _unused_label, loaded_lt_selector = load_light_model()
    if loaded_lt_clf is None:
        print("未找到已保存的轻量化优化模型，启动后台训练...")
        threading.Thread(target=train_light_model_in_background, daemon=True).start()
        print("应用启动中，模型将在后台训练...")
    else:
        light_clf, light_sc, light_feature_selector = (
            loaded_lt_clf, loaded_lt_sc, loaded_lt_selector)
        model_ready = True
        print("已加载保存的轻量化优化模型!")

        loaded = load_enhanced_model()
        enhanced_loaded, _sc, _le, enhanced_sel, enhanced_pre = loaded
        if enhanced_loaded is None:
            print("未找到已保存的增强型模型，启动后台训练...")
            threading.Thread(target=train_enhanced_model_in_background, daemon=True).start()
        else:
            enhanced_clf = enhanced_loaded
            enhanced_preprocessor = enhanced_pre
            enhanced_feature_selector = enhanced_sel
            enhanced_model_ready = True
            print("已加载保存的增强型模型! - 置信度将显著提升")

    threading.Thread(target=init_shap_in_background, daemon=True).start()
    print("SHAP 解释器后台初始化已启动...")


init_models_once()


if __name__=='__main__':
	init_models_once()

# 保存管理后台进程引用
	admin_process = None

	# 启动管理后台
	admin_dir = os.path.join(os.path.dirname(__file__), 'admin_backend')
	admin_app_path = os.path.join(admin_dir, 'app.py')
	if os.path.exists(admin_app_path):
		print("正在启动管理后台...")
		env = os.environ.copy()
		env['FROM_SUBPROCESS'] = 'true'
		admin_process = subprocess.Popen(
			[sys.executable, admin_app_path], 
			env=env, 
			cwd=admin_dir,
			creationflags=subprocess.CREATE_NEW_CONSOLE
		)

	def cleanup_admin_process(signum, frame):
		"""清理管理后台子进程"""
		if admin_process and admin_process.poll() is None:
			print("\n正在关闭管理后台...")
			try:
				admin_process.terminate()
				admin_process.wait(timeout=3)
				print("管理后台已关闭")
			except subprocess.TimeoutExpired:
				print("强制终止管理后台...")
				admin_process.kill()
				print("管理后台已强制终止")
		sys.exit(0)

	# 注册信号处理
	signal.signal(signal.SIGINT, cleanup_admin_process)
	signal.signal(signal.SIGTERM, cleanup_admin_process)

	host = '127.0.0.1'
	port = 5000
	print('\n' + '='*60)
	print('乳腺癌检测系统启动成功！')
	print('用户端访问地址: http://{}:{}'.format(host, port))
	print('管理后台访问地址: http://127.0.0.1:5001')
	print('='*60 + '\n')
	
	try:
		app.run(host=host, port=port, debug=True, threaded=True, use_reloader=False)
	finally:
		# 程序退出时清理
		if admin_process and admin_process.poll() is None:
			print("\n正在关闭管理后台...")
			try:
				admin_process.terminate()
				admin_process.wait(timeout=3)
				print("管理后台已关闭")
			except subprocess.TimeoutExpired:
				print("强制终止管理后台...")
				admin_process.kill()
				print("管理后台已强制终止")

