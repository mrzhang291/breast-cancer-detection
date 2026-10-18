#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强型AI深度分析模块
提供高级数据分析、多维度评估和智能报告生成功能
"""

import numpy as np
import json
import hashlib
from datetime import datetime
from functools import lru_cache

# 特征正常值范围参考（基于乳腺癌数据集统计）
FEATURE_RANGES = {
    'Radius Mean': (6.981, 28.11),
    'Texture Mean': (9.71, 39.28),
    'Perimeter Mean': (43.79, 188.5),
    'Area Mean': (143.5, 2501),
    'Smoothness Mean': (0.05263, 0.1634),
    'Compactness Mean': (0.01938, 0.3454),
    'Concavity Mean': (0.0, 0.4268),
    'Concave Points Mean': (0.0, 0.2012),
    'Symmetry Mean': (0.106, 0.304),
    'Fractal Dimension Mean': (0.05504, 0.09744),
    'Radius SE': (0.1115, 2.873),
    'Texture SE': (0.3602, 4.885),
    'Perimeter SE': (0.757, 21.98),
    'Area SE': (6.802, 542.2),
    'Smoothness SE': (0.001713, 0.03113),
    'Compactness SE': (0.002252, 0.1354),
    'Concavity SE': (0.0, 0.396),
    'Concave Points SE': (0.0, 0.05279),
    'Symmetry SE': (0.007882, 0.07895),
    'Fractal Dimension SE': (0.000895, 0.02984),
    'Radius Worst': (7.93, 36.04),
    'Texture Worst': (12.02, 49.54),
    'Perimeter Worst': (50.41, 251.2),
    'Area Worst': (185.2, 4254),
    'Smoothness Worst': (0.07117, 0.2226),
    'Compactness Worst': (0.02729, 1.058),
    'Concavity Worst': (0.0, 1.252),
    'Concave Points Worst': (0.0, 0.291),
    'Symmetry Worst': (0.1565, 0.6638),
    'Fractal Dimension Worst': (0.05884, 0.2075)
}

FEATURE_NAMES = [
    'Radius Mean', 'Texture Mean', 'Perimeter Mean', 'Area Mean',
    'Smoothness Mean', 'Compactness Mean', 'Concavity Mean', 'Concave Points Mean',
    'Symmetry Mean', 'Fractal Dimension Mean', 'Radius SE', 'Texture SE',
    'Perimeter SE', 'Area SE', 'Smoothness SE', 'Compactness SE',
    'Concavity SE', 'Concave Points SE', 'Symmetry SE', 'Fractal Dimension SE',
    'Radius Worst', 'Texture Worst', 'Perimeter Worst', 'Area Worst',
    'Smoothness Worst', 'Compactness Worst', 'Concavity Worst', 'Concave Points Worst',
    'Symmetry Worst', 'Fractal Dimension Worst'
]

class AIAnalysisEnhancer:
    """增强型AI分析器"""
    
    def __init__(self):
        self.analysis_cache = {}
    
    def analyze_feature_abnormalities(self, data):
        """分析特征数据的异常情况"""
        abnormalities = []
        warnings = []
        
        for i, (name, value) in enumerate(zip(FEATURE_NAMES, data)):
            if name in FEATURE_RANGES:
                min_val, max_val = FEATURE_RANGES[name]
                if value < min_val:
                    abnormalities.append({
                        'feature': name,
                        'value': round(value, 4),
                        'normal_range': f"{min_val:.4f} - {max_val:.4f}",
                        'status': '低于正常范围',
                        'severity': 'warning'
                    })
                elif value > max_val:
                    abnormalities.append({
                        'feature': name,
                        'value': round(value, 4),
                        'normal_range': f"{min_val:.4f} - {max_val:.4f}",
                        'status': '高于正常范围',
                        'severity': 'danger'
                    })
        
        # 统计关键特征指标
        radius_mean = data[0]
        texture_mean = data[1]
        perimeter_mean = data[2]
        area_mean = data[3]
        
        # 肿瘤大小评估
        if area_mean > 1000:
            warnings.append("肿瘤面积较大，建议进一步检查")
        if perimeter_mean > 100:
            warnings.append("肿瘤周长超过平均值，需要关注")
        
        return {
            'abnormal_count': len(abnormalities),
            'abnormal_features': abnormalities,
            'warnings': warnings
        }
    
    def calculate_feature_statistics(self, data):
        """计算特征数据的统计信息"""
        arr = np.array(data)
        
        stats = {
            'mean': float(np.mean(arr)),
            'median': float(np.median(arr)),
            'std': float(np.std(arr)),
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
            'range': float(np.max(arr) - np.min(arr)),
            'variance': float(np.var(arr)),
            'skewness': float(self._calculate_skewness(arr)),
            'kurtosis': float(self._calculate_kurtosis(arr))
        }
        return stats
    
    def _calculate_skewness(self, data):
        """计算偏度"""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 3)
    
    def _calculate_kurtosis(self, data):
        """计算峰度"""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 4) - 3
    
    def generate_feature_importance_summary(self, data):
        """生成特征重要性摘要"""
        # 基于领域知识的特征重要性权重
        importance_weights = {
            'Radius Mean': 1.0, 'Texture Mean': 0.8, 'Perimeter Mean': 1.0,
            'Area Mean': 1.0, 'Smoothness Mean': 0.5, 'Compactness Mean': 0.7,
            'Concavity Mean': 0.8, 'Concave Points Mean': 0.9, 'Symmetry Mean': 0.6,
            'Fractal Dimension Mean': 0.4, 'Radius SE': 0.6, 'Texture SE': 0.5,
            'Perimeter SE': 0.6, 'Area SE': 0.6, 'Smoothness SE': 0.3,
            'Compactness SE': 0.4, 'Concavity SE': 0.5, 'Concave Points SE': 0.6,
            'Symmetry SE': 0.3, 'Fractal Dimension SE': 0.2, 'Radius Worst': 1.0,
            'Texture Worst': 0.8, 'Perimeter Worst': 1.0, 'Area Worst': 1.0,
            'Smoothness Worst': 0.5, 'Compactness Worst': 0.7, 'Concavity Worst': 0.8,
            'Concave Points Worst': 0.9, 'Symmetry Worst': 0.6, 'Fractal Dimension Worst': 0.4
        }
        
        # 计算加权重要性分数
        scores = []
        for i, name in enumerate(FEATURE_NAMES):
            weight = importance_weights.get(name, 0.5)
            # 归一化值到0-1范围
            if name in FEATURE_RANGES:
                min_val, max_val = FEATURE_RANGES[name]
                norm_val = (data[i] - min_val) / (max_val - min_val + 1e-10)
            else:
                norm_val = 0.5
            scores.append((name, data[i], weight * norm_val))
        
        # 排序并取前10个最重要的特征
        scores.sort(key=lambda x: x[2], reverse=True)
        top_features = scores[:10]
        
        return [{
            'name': name,
            'value': round(val, 4),
            'importance_score': round(score, 4)
        } for name, val, score in top_features]
    
    def validate_analysis_result(self, result, prediction_output, confidence):
        """验证分析结果的质量"""
        validation = {
            'valid': True,
            'checks': [],
            'quality_score': 0.0
        }
        
        checks = [
            {'name': '包含预测解读', 'pattern': '预测结果|良性|恶性', 'required': True},
            {'name': '包含置信度分析', 'pattern': '置信度|可靠', 'required': True},
            {'name': '包含特征分析', 'pattern': '特征|Radius|Texture|Perimeter|Area', 'required': True},
            {'name': '包含医学建议', 'pattern': '建议|检查|医生', 'required': True},
            {'name': '包含情感关怀', 'pattern': '关怀|安慰|鼓励|祝福', 'required': True},
            {'name': '包含免责声明', 'pattern': '仅供参考|不能替代|专业医生', 'required': True}
        ]
        
        passed_checks = 0
        for check in checks:
            import re
            found = bool(re.search(check['pattern'], result))
            validation['checks'].append({
                'name': check['name'],
                'passed': found,
                'required': check['required']
            })
            if found:
                passed_checks += 1
            elif check['required']:
                validation['valid'] = False
        
        validation['quality_score'] = passed_checks / len(checks)
        
        return validation
    
    def generate_enhanced_analysis_prompt(self, output, confidence, data, 
                                          analysis_depth='deep', 
                                          detail_level='high',
                                          include_emotional_support=True,
                                          language='zh'):
        """生成增强型分析提示词（支持中英文）"""
        
        # 分析特征异常
        abnormality_info = self.analyze_feature_abnormalities(data)
        stats = self.calculate_feature_statistics(data)
        top_features = self.generate_feature_importance_summary(data)
        
        # 构建异常特征描述
        abnormal_desc = ""
        if abnormality_info['abnormal_count'] > 0:
            if language == 'zh':
                abnormal_desc = "\n**异常特征列表：**\n"
            else:
                abnormal_desc = "\n**Abnormal Features List:**\n"
            for abn in abnormality_info['abnormal_features']:
                severity_icon = "🔴" if abn['severity'] == 'danger' else "🟡"
                status_text = abn['status'] if language == 'zh' else self._translate_status(abn['status'])
                range_label = "正常范围" if language == 'zh' else "normal range"
                abnormal_desc += f"{severity_icon} {abn['feature']}: {abn['value']} ({status_text}, {range_label}: {abn['normal_range']})\n"
        
        # 构建统计摘要
        if language == 'zh':
            stats_summary = f"""
**数据统计摘要：**
- 平均值: {stats['mean']:.4f}
- 中位数: {stats['median']:.4f}
- 标准差: {stats['std']:.4f}
- 数据范围: [{stats['min']:.4f}, {stats['max']:.4f}]
- 偏度: {stats['skewness']:.4f}
- 峰度: {stats['kurtosis']:.4f}
"""
        else:
            stats_summary = f"""
**Data Statistics Summary:**
- Mean: {stats['mean']:.4f}
- Median: {stats['median']:.4f}
- Standard Deviation: {stats['std']:.4f}
- Range: [{stats['min']:.4f}, {stats['max']:.4f}]
- Skewness: {stats['skewness']:.4f}
- Kurtosis: {stats['kurtosis']:.4f}
"""
        
        # 构建重要特征列表
        if language == 'zh':
            important_features = "\n**关键特征重要性排序（前10位）：**\n"
            importance_label = "重要性评分"
        else:
            important_features = "\n**Top 10 Feature Importance Ranking:**\n"
            importance_label = "importance score"
        for i, feat in enumerate(top_features, 1):
            important_features += f"{i}. {feat['name']}: {feat['value']} ({importance_label}: {feat['importance_score']:.2f})\n"
        
        # 确定分析深度
        if language == 'zh':
            depth_instructions = {
                'shallow': "请提供简洁的分析，突出重点即可。",
                'normal': "请提供全面但不过于深入的分析。",
                'deep': "请提供非常深入、详细的专业分析，包括医学背景和最新研究成果。"
            }
        else:
            depth_instructions = {
                'shallow': "Provide concise analysis, just highlight the key points.",
                'normal': "Provide comprehensive but not overly deep analysis.",
                'deep': "Provide very in-depth, detailed professional analysis, including medical background and latest research findings."
            }
        
        # 确定详细程度
        if language == 'zh':
            detail_instructions = {
                'low': "使用简洁的语言，避免过多技术术语。",
                'medium': "使用适中的语言，适当解释专业术语。",
                'high': "使用专业医学术语，提供详细的技术解释。"
            }
        else:
            detail_instructions = {
                'low': "Use concise language, avoid excessive technical jargon.",
                'medium': "Use moderate language, explain technical terms appropriately.",
                'high': "Use professional medical terminology, provide detailed technical explanations."
            }
        
        # 情感支持内容
        if language == 'zh':
            emotional_content = {
                'Benign': """请用温暖、鼓励的语言表达祝贺，并提醒定期复查的重要性，给予积极的健康祝福。强调保持健康生活方式的重要性。""",
                '良性': """请用温暖、鼓励的语言表达祝贺，并提醒定期复查的重要性，给予积极的健康祝福。强调保持健康生活方式的重要性。""",
                'Malignant': """请用关怀、安慰的语言表达理解和支持，强调早期发现的重要性，给予战胜疾病的信心和鼓励。提供希望和积极的康复建议。""",
                '恶性': """请用关怀、安慰的语言表达理解和支持，强调早期发现的重要性，给予战胜疾病的信心和鼓励。提供希望和积极的康复建议。"""
            }
        else:
            emotional_content = {
                'Benign': """Use warm, encouraging language to express congratulations, remind about the importance of regular check-ups, and give positive health wishes. Emphasize the importance of maintaining a healthy lifestyle.""",
                '良性': """Use warm, encouraging language to express congratulations, remind about the importance of regular check-ups, and give positive health wishes. Emphasize the importance of maintaining a healthy lifestyle.""",
                'Malignant': """Use caring, comforting language to express understanding and support, emphasize the importance of early detection, give confidence and encouragement to overcome the disease. Provide hope and positive rehabilitation suggestions.""",
                '恶性': """Use caring, comforting language to express understanding and support, emphasize the importance of early detection, give confidence and encouragement to overcome the disease. Provide hope and positive rehabilitation suggestions."""
            }
        
        # 获取翻译后的输出结果
        translated_output = output
        if language == 'en':
            if output == '良性':
                translated_output = 'Benign'
            elif output == '恶性':
                translated_output = 'Malignant'
        
        # 构建完整提示词
        if language == 'zh':
            prompt = f"""
你是一位专业的乳腺癌医疗分析专家，拥有丰富的临床经验和医学知识。

{'='*70}
📋 【分析参数配置】
{'='*70}
- 分析深度: {depth_instructions[analysis_depth]}
- 详细程度: {detail_instructions[detail_level]}
- 情感支持: {'包含' if include_emotional_support else '不包含'}

{'='*70}
📊 【患者预测数据】
{'='*70}
- 预测结果: {output}
- 预测置信度: {confidence * 100:.2f}%
- 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*70}
📈 【数据统计摘要】
{'='*70}
{stats_summary}

{'='*70}
🔑 【关键特征重要性】
{'='*70}
{important_features}

{'='*70}
⚠️ 【异常特征警告】
{'='*70}
{abnormal_desc if abnormal_desc else '未发现明显异常特征'}

{'='*70}
📝 【完整特征数据（30项）】
{'='*70}
"""
            for i in range(len(FEATURE_NAMES)):
                prompt += f"{FEATURE_NAMES[i]}: {data[i]:.4f}\n"
            
            prompt += f"""
{'='*70}
🎯 【分析任务要求】
{'='*70}

请专注于分析用户提供的具体数据，避免阐述基本概念。按照以下结构提供专业分析报告（用中文回答）：

---

## 一、预测结果解读 🔬
- 直接说明预测结果：{output}，置信度：{confidence * 100:.2f}%
- 基于当前数据特征解释为什么得出此预测结果
- 分析该结果在当前数据背景下的可靠性

## 二、数据特征深度分析 🧬
- **关键特征分析**：详细分析Radius Mean、Texture Mean、Perimeter Mean、Area Mean等核心特征的具体数值及其对预测的影响
- **异常特征识别**：重点分析超出正常范围的特征指标，说明其临床意义和潜在风险
- **特征关联分析**：分析各特征之间的关联性及其对预测结果的共同作用
- **数据质量评估**：评估数据的完整性和一致性

## 三、风险因素评估 🎯
- 基于特征数据识别具体的风险因素
- 分析各项指标的异常程度及其对健康的影响
- 评估当前数据所反映的整体风险水平

## 四、针对性建议 🏥
- 根据特征数据的具体情况提供个性化建议
- 指出需要重点关注和监测的指标
- 提供后续检查和复查的具体建议

## 五、情感关怀与支持 💝
{emotional_content.get(output, emotional_content['Benign'])}

## 六、重要声明 ⚠️
- 本分析基于您提供的数据特征，仅供参考
- 不能替代专业医生的诊断和建议
- 建议及时咨询医疗专业人士进行进一步检查

---

请确保分析报告：
- 专注于数据分析，避免解释基本医学概念
- 基于具体数值进行深入解读
- 提供个性化、针对性的建议
- 保持专业性和同理心
"""
        else:
            # English prompt
            prompt = f"""
You are a professional breast cancer medical analysis expert with rich clinical experience and medical knowledge.

{'='*70}
📋 【Analysis Parameters】
{'='*70}
- Analysis Depth: {depth_instructions[analysis_depth]}
- Detail Level: {detail_instructions[detail_level]}
- Emotional Support: {'Include' if include_emotional_support else 'Exclude'}

{'='*70}
📊 【Patient Prediction Data】
{'='*70}
- Prediction Result: {translated_output}
- Prediction Confidence: {confidence * 100:.2f}%
- Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*70}
📈 【Data Statistics Summary】
{'='*70}
{stats_summary}

{'='*70}
🔑 【Key Feature Importance】
{'='*70}
{important_features}

{'='*70}
⚠️ 【Abnormal Feature Warnings】
{'='*70}
{abnormal_desc if abnormal_desc else 'No significant abnormal features detected'}

{'='*70}
📝 【Complete Feature Data (30 items)】
{'='*70}
"""
            for i in range(len(FEATURE_NAMES)):
                prompt += f"{FEATURE_NAMES[i]}: {data[i]:.4f}\n"
            
            prompt += f"""
{'='*70}
🎯 【Analysis Task Requirements】
{'='*70}

Please focus on analyzing the specific data provided by the user, avoid explaining basic concepts. Provide a professional analysis report according to the following structure (answer in English):

---

## I. Prediction Result Interpretation 🔬
- Directly state the prediction result: {translated_output}, Confidence: {confidence * 100:.2f}%
- Explain why this prediction result was reached based on current data features
- Analyze the reliability of this result in the context of current data

## II. In-depth Feature Analysis 🧬
- **Key Feature Analysis**: Analyze in detail the specific values of core features such as Radius Mean, Texture Mean, Perimeter Mean, Area Mean and their impact on prediction
- **Abnormal Feature Identification**: Focus on analyzing feature indicators that are outside the normal range, explain their clinical significance and potential risks
- **Feature Correlation Analysis**: Analyze the correlations between features and their combined effect on prediction results
- **Data Quality Assessment**: Assess data completeness and consistency

## III. Risk Factor Assessment 🎯
- Identify specific risk factors based on feature data
- Analyze the degree of abnormality of each indicator and its impact on health
- Assess the overall risk level reflected by current data

## IV. Targeted Recommendations 🏥
- Provide personalized recommendations based on specific feature data
- Point out indicators that need special attention and monitoring
- Provide specific recommendations for follow-up examinations and rechecks

## V. Emotional Care and Support 💝
{emotional_content.get(output, emotional_content['Benign'])}

## VI. Important Notice ⚠️
- This analysis is based on the data features you provided and is for reference only
- It cannot replace diagnosis and advice from professional doctors
- It is recommended to consult medical professionals promptly for further examination

---

Please ensure the analysis report:
- Focuses on data analysis, avoiding explanations of basic medical concepts
- Provides in-depth interpretation based on specific values
- Offers personalized, targeted recommendations
- Maintains professionalism and empathy
"""
        
        return prompt
    
    def _translate_status(self, status):
        """翻译状态信息"""
        translations = {
            '低于正常范围': 'below normal range',
            '高于正常范围': 'above normal range',
            '正常': 'normal'
        }
        return translations.get(status, status)
    
    def generate_analysis_report(self, output, confidence, data, options=None):
        """生成完整的分析报告（支持多语言）"""
        if options is None:
            options = {}
        
        # 获取分析选项
        analysis_depth = options.get('depth', 'deep')
        detail_level = options.get('detail', 'high')
        include_emotional = options.get('emotional_support', True)
        language = options.get('language', 'zh')
        
        # 生成增强型提示词
        prompt = self.generate_enhanced_analysis_prompt(
            output, confidence, data,
            analysis_depth=analysis_depth,
            detail_level=detail_level,
            include_emotional_support=include_emotional,
            language=language
        )
        
        return prompt
    
    def cache_analysis_result(self, key, result, validation):
        """缓存分析结果"""
        self.analysis_cache[key] = {
            'result': result,
            'validation': validation,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_cached_analysis(self, key):
        """获取缓存的分析结果"""
        cached = self.analysis_cache.get(key)
        if cached:
            # 检查缓存是否过期（10分钟）
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if (datetime.now() - cache_time).total_seconds() < 600:
                return cached['result']
        return None
    
    def generate_cache_key(self, output, confidence, data, analysis_depth='deep', detail_level='high', include_emotional=True, language='zh'):
        """生成缓存键 - 包含分析参数和语言以确保不同配置返回不同结果"""
        data_str = json.dumps(data)
        key_str = f"{output}_{confidence}_{data_str}_{analysis_depth}_{detail_level}_{include_emotional}_{language}"
        return hashlib.md5(key_str.encode()).hexdigest()

# 全局分析器实例
analysis_enhancer = AIAnalysisEnhancer()
