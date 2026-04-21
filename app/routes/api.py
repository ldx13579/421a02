from flask import Blueprint, request, jsonify, session
from app import db
from app.models import Poll, Option, VoteRecord
from app.utils import (
    can_vote,
    record_vote,
    get_client_ip,
    get_session_id
)
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/vote', methods=['POST'])
def submit_vote():
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '无效的请求数据'
        }), 400
    
    poll_id = data.get('poll_id')
    option_ids = data.get('option_ids', [])
    captcha_input = data.get('captcha', '').strip().upper()
    
    if not poll_id:
        return jsonify({
            'success': False,
            'message': '缺少投票ID'
        }), 400
    
    if not option_ids:
        return jsonify({
            'success': False,
            'message': '请选择投票选项'
        }), 400
    
    captcha_session = session.get('captcha', '').upper()
    if not captcha_input or captcha_input != captcha_session:
        return jsonify({
            'success': False,
            'message': '验证码错误，请重试',
            'captcha_error': True
        }), 400
    
    poll = Poll.query.get(poll_id)
    if not poll:
        return jsonify({
            'success': False,
            'message': '投票不存在'
        }), 404
    
    can_vote_flag, vote_message = can_vote(poll)
    if not can_vote_flag:
        return jsonify({
            'success': False,
            'message': vote_message
        }), 403
    
    valid_options = poll.options.with_entities(Option.id).all()
    valid_option_ids = [opt[0] for opt in valid_options]
    
    if not all(opt_id in valid_option_ids for opt_id in option_ids):
        return jsonify({
            'success': False,
            'message': '存在无效的投票选项'
        }), 400
    
    if poll.vote_type == 'single' and len(option_ids) > 1:
        return jsonify({
            'success': False,
            'message': '该投票仅支持单选'
        }), 400
    
    if poll.vote_type == 'multiple' and len(option_ids) > poll.max_choices:
        return jsonify({
            'success': False,
            'message': f'最多只能选择{poll.max_choices}个选项'
        }), 400
    
    try:
        ip_address = get_client_ip()
        user_agent = request.user_agent.string if request.user_agent else ''
        session_id = get_session_id()
        
        record_vote(poll_id, option_ids, ip_address, user_agent, session_id)
        
        session['captcha'] = ''
        
        results = get_poll_results(poll_id)
        
        return jsonify({
            'success': True,
            'message': '投票成功！',
            'results': results
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'投票失败：{str(e)}'
        }), 500

@api.route('/results/<int:poll_id>', methods=['GET'])
def get_results(poll_id):
    poll = Poll.query.get(poll_id)
    if not poll:
        return jsonify({
            'success': False,
            'message': '投票不存在'
        }), 404
    
    results = get_poll_results(poll_id)
    
    return jsonify({
        'success': True,
        'data': results
    })

def get_poll_results(poll_id):
    poll = Poll.query.get(poll_id)
    options = poll.options.order_by(Option.order, Option.id).all()
    
    total_votes = poll.get_total_votes()
    
    results = {
        'poll_id': poll_id,
        'total_votes': total_votes,
        'options': []
    }
    
    for option in options:
        vote_count = option.get_vote_count()
        percentage = option.get_vote_percentage()
        results['options'].append({
            'id': option.id,
            'text': option.text,
            'votes': vote_count,
            'percentage': percentage
        })
    
    return results

@api.route('/polls/active', methods=['GET'])
def get_active_polls():
    active_polls = Poll.query.filter_by(is_active=True).order_by(Poll.created_at.desc()).all()
    
    polls_data = []
    for poll in active_polls:
        polls_data.append({
            'id': poll.id,
            'title': poll.title,
            'description': poll.description,
            'vote_type': poll.vote_type,
            'max_choices': poll.max_choices,
            'total_votes': poll.get_total_votes()
        })
    
    return jsonify({
        'success': True,
        'data': polls_data
    })
