from flask import Blueprint, request, jsonify, send_file
from models import db, PredictionRecord, User, OperationLog
from auth import requires_permission, get_jwt_identity
import json
import io
import pandas as pd
from datetime import datetime
from sqlalchemy import or_

prediction_api = Blueprint('prediction_api', __name__)

# 预测结果转换映射
RESULT_MAP = {
    '良性': '良性',
    '恶性': '恶性',
    'Benign': '良性',
    'Malignant': '恶性',
    'benign': '良性',
    'malignant': '恶性',
    'BENIGN': '良性',
    'MALIGNANT': '恶性'
}

def get_benign_values():
    return ['良性', 'Benign', 'benign', 'BENIGN']

def get_malignant_values():
    return ['恶性', 'Malignant', 'malignant', 'MALIGNANT']

def convert_result(result):
    return RESULT_MAP.get(result, result)

@prediction_api.route('/api/predictions', methods=['GET'])
@requires_permission('prediction_view')
def get_predictions():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_id = request.args.get('user_id', type=int)
    search = request.args.get('search')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    date_str = request.args.get('date', '')
    if date_str and not start_time:
        start_time = f'{date_str}T00:00:00'
        end_time = f'{date_str}T23:59:59'
    prediction_result = request.args.get('prediction_result') or request.args.get('result')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    query = PredictionRecord.query.options(db.joinedload(PredictionRecord.user))
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if search:
        # 支持按用户名搜索
        query = query.join(User).filter(or_(User.username.like(f'%{search}%'), PredictionRecord.user_id == search))
    if start_time:
        query = query.filter(PredictionRecord.created_at >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(PredictionRecord.created_at <= datetime.fromisoformat(end_time))
    if prediction_result:
        # 支持中英文查询
        if prediction_result in ['良性', 'benign', 'Benign', 'BENIGN']:
            query = query.filter(PredictionRecord.prediction_result.in_(get_benign_values()))
        elif prediction_result in ['恶性', 'malignant', 'Malignant', 'MALIGNANT']:
            query = query.filter(PredictionRecord.prediction_result.in_(get_malignant_values()))
        else:
            query = query.filter_by(prediction_result=prediction_result)
    
    if sort_order == 'desc':
        query = query.order_by(getattr(PredictionRecord, sort_by).desc())
    else:
        query = query.order_by(getattr(PredictionRecord, sort_by))
    
    pagination = query.paginate(page=page, per_page=page_size)
    
    # 返回转换后的数据
    items = []
    for record in pagination.items:
        record_dict = record.to_dict()
        record_dict['prediction_result'] = convert_result(record_dict['prediction_result'])
        # 确保 username 字段存在
        if 'username' not in record_dict or record_dict['username'] is None:
            # 尝试直接从用户关系获取
            if record.user:
                record_dict['username'] = record.user.username
            else:
                record_dict['username'] = str(record.user_id)
        items.append(record_dict)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size
        }
    }), 200

@prediction_api.route('/api/predictions/<int:record_id>', methods=['GET'])
@requires_permission('prediction_view')
def get_prediction(record_id):
    record = PredictionRecord.query.get(record_id)
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在', 'data': {}}), 404
    
    record_dict = record.to_dict()
    record_dict['prediction_result'] = convert_result(record_dict['prediction_result'])
    return jsonify({'code': 200, 'message': 'success', 'data': record_dict}), 200

@prediction_api.route('/api/predictions', methods=['POST'])
def add_prediction():
    """接收用户端预测数据并保存到管理端数据库"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空', 'data': {}}), 400
        
        user_id = data.get('user_id')
        username = data.get('username')
        all_30_features_json = data.get('all_30_features_json')
        prediction_result = data.get('prediction_result')
        confidence = data.get('confidence')
        
        if not all([user_id, all_30_features_json, prediction_result, confidence]):
            return jsonify({'code': 400, 'message': '缺少必要参数', 'data': {}}), 400
        
        record = PredictionRecord(
            user_id=user_id,
            all_30_features_json=all_30_features_json,
            prediction_result=prediction_result,
            confidence=confidence,
            created_at=datetime.now()
        )
        
        db.session.add(record)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'id': record.id}
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"保存预测记录失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/public/user/predictions', methods=['GET'])
def get_public_user_predictions():
    """公开接口：根据user_id获取用户的预测记录（前端用户系统使用）"""
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少user_id参数', 'data': {}}), 400

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        result_filter = request.args.get('result_filter')
        sort_by = request.args.get('sort_by', 'newest')

        query = PredictionRecord.query.filter_by(user_id=user_id)

        if result_filter:
            if result_filter == 'Malignant':
                query = query.filter(PredictionRecord.prediction_result.in_(get_malignant_values()))
            elif result_filter == 'Benign':
                query = query.filter(PredictionRecord.prediction_result.in_(get_benign_values()))

        if sort_by == 'newest':
            query = query.order_by(PredictionRecord.created_at.desc())
        elif sort_by == 'oldest':
            query = query.order_by(PredictionRecord.created_at.asc())
        elif sort_by == 'confidence_high':
            query = query.order_by(PredictionRecord.confidence.desc())
        elif sort_by == 'confidence_low':
            query = query.order_by(PredictionRecord.confidence.asc())

        pagination = query.paginate(page=page, per_page=page_size)

        items = []
        for record in pagination.items:
            record_dict = {
                'id': record.id,
                'prediction_result': convert_result(record.prediction_result),
                'confidence': record.confidence,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'features': json.loads(record.all_30_features_json) if record.all_30_features_json else {}
            }
            items.append(record_dict)

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'page_size': page_size
            }
        }), 200

    except Exception as e:
        print(f"获取用户预测记录失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/public/user/statistics', methods=['GET'])
def get_public_user_statistics():
    """公开接口：根据user_id获取用户的预测统计信息（前端用户系统使用）"""
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少user_id参数', 'data': {}}), 400

        total = PredictionRecord.query.filter_by(user_id=user_id).count()
        malignant = PredictionRecord.query.filter(
            PredictionRecord.user_id == user_id,
            PredictionRecord.prediction_result.in_(get_malignant_values())
        ).count()
        benign = PredictionRecord.query.filter(
            PredictionRecord.user_id == user_id,
            PredictionRecord.prediction_result.in_(get_benign_values())
        ).count()
        
        # 计算平均置信度
        records = PredictionRecord.query.filter_by(user_id=user_id).all()
        avg_confidence = sum(r.confidence for r in records) / len(records) if records else 0

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'malignant': malignant,
                'benign': benign,
                'avg_confidence': avg_confidence
            }
        }), 200

    except Exception as e:
        print(f"获取用户统计信息失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/public/user/record/<int:record_id>', methods=['GET'])
def get_public_user_record(record_id):
    """公开接口：根据记录ID获取记录详情（前端用户系统使用）"""
    try:
        record = PredictionRecord.query.get(record_id)
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': {}}), 404
        
        # 解析30个特征
        import json
        features = []
        if record.all_30_features_json:
            try:
                features_data = json.loads(record.all_30_features_json)
                # 按顺序提取30个特征值（与app.py中保存时的键名一致）
                feature_order = [f'feature_{i+1}' for i in range(30)]
                for key in feature_order:
                    features.append(float(features_data.get(key, 0)))
            except:
                features = [0.0] * 30
        else:
            features = [0.0] * 30
        
        # 返回元组格式的数据（匹配前端模板期望的格式）
        record_data = [
            record.id,
            record.user.username if record.user else '',
            record.prediction_result,
            record.confidence,
            record.created_at.isoformat() if record.created_at else '',
        ] + features
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': record_data
        }), 200
        
    except Exception as e:
        print(f"获取记录详情失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/user/predictions', methods=['GET'])
def get_user_predictions():
    """获取当前用户的预测记录（无需特殊权限，用户只能查看自己的记录）"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        result_filter = request.args.get('result_filter')
        sort_by = request.args.get('sort_by', 'newest')

        query = PredictionRecord.query.filter_by(user_id=current_user_id)

        if result_filter:
            if result_filter == 'Malignant':
                query = query.filter(PredictionRecord.prediction_result.in_(get_malignant_values()))
            elif result_filter == 'Benign':
                query = query.filter(PredictionRecord.prediction_result.in_(get_benign_values()))

        if sort_by == 'newest':
            query = query.order_by(PredictionRecord.created_at.desc())
        elif sort_by == 'oldest':
            query = query.order_by(PredictionRecord.created_at.asc())
        elif sort_by == 'confidence_high':
            query = query.order_by(PredictionRecord.confidence.desc())
        elif sort_by == 'confidence_low':
            query = query.order_by(PredictionRecord.confidence.asc())

        pagination = query.paginate(page=page, per_page=page_size)

        items = []
        for record in pagination.items:
            record_dict = {
                'id': record.id,
                'prediction_result': convert_result(record.prediction_result),
                'confidence': record.confidence,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'features': json.loads(record.all_30_features_json) if record.all_30_features_json else {}
            }
            items.append(record_dict)

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'page_size': page_size
            }
        }), 200

    except Exception as e:
        print(f"获取用户预测记录失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/user/predictions/<int:record_id>', methods=['GET'])
def get_user_prediction(record_id):
    """获取当前用户的单条预测记录"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401

        record = PredictionRecord.query.filter_by(id=record_id, user_id=current_user_id).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': {}}), 404

        record_dict = {
            'id': record.id,
            'prediction_result': convert_result(record.prediction_result),
            'confidence': record.confidence,
            'created_at': record.created_at.isoformat() if record.created_at else None,
            'features': json.loads(record.all_30_features_json) if record.all_30_features_json else {}
        }

        return jsonify({'code': 200, 'message': 'success', 'data': record_dict}), 200

    except Exception as e:
        print(f"获取预测记录失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/user/statistics', methods=['GET'])
def get_user_statistics():
    """获取当前用户的预测统计信息"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'code': 401, 'message': '未授权', 'data': {}}), 401

        total = PredictionRecord.query.filter_by(user_id=current_user_id).count()
        benign = PredictionRecord.query.filter(
            PredictionRecord.user_id == current_user_id,
            PredictionRecord.prediction_result.in_(get_benign_values())
        ).count()
        malignant = PredictionRecord.query.filter(
            PredictionRecord.user_id == current_user_id,
            PredictionRecord.prediction_result.in_(get_malignant_values())
        ).count()

        records = PredictionRecord.query.filter_by(user_id=current_user_id).all()
        avg_confidence = sum(r.confidence for r in records) / len(records) if records else 0

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'benign': benign,
                'malignant': malignant,
                'avg_confidence': avg_confidence
            }
        }), 200

    except Exception as e:
        print(f"获取用户统计失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': {}}), 500

@prediction_api.route('/api/predictions/<int:record_id>', methods=['DELETE'])
@requires_permission('prediction_delete')
def delete_prediction(record_id):
    record = PredictionRecord.query.get(record_id)
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在', 'data': {}}), 404
    
    db.session.delete(record)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'删除预测记录: {record_id}')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@prediction_api.route('/api/predictions/batch_delete', methods=['POST'])
@requires_permission('prediction_delete')
def batch_delete_predictions():
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({'code': 400, 'message': '缺少ID列表', 'data': {}}), 400
    
    PredictionRecord.query.filter(PredictionRecord.id.in_(data['ids'])).delete(synchronize_session=False)
    db.session.commit()
    
    log_operation(get_jwt_identity(), f'批量删除预测记录: {len(data["ids"])}条')
    
    return jsonify({'code': 200, 'message': 'success', 'data': {}}), 200

@prediction_api.route('/api/predictions/export', methods=['GET'])
@requires_permission('prediction_export')
def export_predictions():
    user_id = request.args.get('user_id', type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    prediction_result = request.args.get('prediction_result')
    format_type = request.args.get('format', 'csv')
    
    query = PredictionRecord.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_time:
        query = query.filter(PredictionRecord.created_at >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(PredictionRecord.created_at <= datetime.fromisoformat(end_time))
    if prediction_result:
        # 支持中英文查询
        if prediction_result in ['良性', 'benign', 'Benign', 'BENIGN']:
            query = query.filter(PredictionRecord.prediction_result.in_(get_benign_values()))
        elif prediction_result in ['恶性', 'malignant', 'Malignant', 'MALIGNANT']:
            query = query.filter(PredictionRecord.prediction_result.in_(get_malignant_values()))
        else:
            query = query.filter_by(prediction_result=prediction_result)
    
    records = query.all()
    
    data = []
    for record in records:
        features = json.loads(record.all_30_features_json)
        row = {
            'id': record.id,
            'user_id': record.user_id,
            'username': record.user.username if record.user else '',
            'prediction_result': convert_result(record.prediction_result),
            'confidence': record.confidence,
            'created_at': record.created_at.isoformat() if record.created_at else ''
        }
        row.update(features)
        data.append(row)
    
    df = pd.DataFrame(data)
    
    if format_type == 'excel':
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(output, download_name='predictions.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')), download_name='predictions.csv', mimetype='text/csv')

def log_operation(user_id, operation):
    log = OperationLog(
        user_id=user_id,
        operation=operation,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        created_at=datetime.now()
    )
    db.session.add(log)
    db.session.commit()

# ==================== 内部调用：主站删除接口 ====================
# 主站（5000）通过本机回环调用，带共享令牌，避免把删除能力暴露成完全公开的接口。
import os as _os

INTERNAL_TOKEN = _os.environ.get('INTERNAL_TOKEN', 'dsh-local-internal')


def _check_internal():
    return request.headers.get('X-Internal-Token') == INTERNAL_TOKEN


@prediction_api.route('/api/public/user/record/<int:record_id>', methods=['DELETE'])
def public_delete_record(record_id):
    """按记录 ID 删除，并校验归属用户。"""
    if not _check_internal():
        return jsonify({'code': 403, 'message': 'forbidden', 'data': {}}), 403

    user_id = request.args.get('user_id', type=int)
    record = PredictionRecord.query.get(record_id)
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在', 'data': {}}), 404
    if user_id is not None and record.user_id != user_id:
        return jsonify({'code': 403, 'message': '无权删除他人记录', 'data': {}}), 403

    db.session.delete(record)
    db.session.commit()
    return jsonify({'code': 200, 'message': 'success', 'data': {'id': record_id}}), 200


@prediction_api.route('/api/public/user/predictions/clear', methods=['POST'])
def public_clear_records():
    """清空某个用户的全部预测记录。"""
    if not _check_internal():
        return jsonify({'code': 403, 'message': 'forbidden', 'data': {}}), 403

    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if user_id is None:
        return jsonify({'code': 400, 'message': '缺少 user_id', 'data': {}}), 400

    deleted = PredictionRecord.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'code': 200, 'message': 'success', 'data': {'deleted': deleted}}), 200
