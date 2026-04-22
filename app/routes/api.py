from flask import Blueprint, request, jsonify, session, current_app
from app import db
from app.models import Poll, Option, VoteRecord, VoteSession
from app.utils.security import (
    get_client_ip,
    get_session_id,
    check_rate_limit,
    validate_captcha,
    check_vote_permission_with_lock,
    validate_options_for_poll,
    validate_poll_vote_type,
    record_vote_records,
    get_poll_results,
    can_view_results
)
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

api = Blueprint('api', __name__)

@api.route('/vote', methods=['POST'])
def submit_vote():
    try:
        rate_ok, rate_msg = check_rate_limit()
        if not rate_ok:
            return jsonify({
                'success': False,
                'message': rate_msg,
                'error_type': 'rate_limit'
            }), 429
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '无效的请求格式',
                'error_type': 'invalid_request'
            }), 400
        
        poll_id = data.get('poll_id')
        option_ids = data.get('option_ids', [])
        captcha_input = data.get('captcha', '')
        
        if not poll_id:
            return jsonify({
                'success': False,
                'message': '缺少投票ID',
                'error_type': 'missing_param'
            }), 400
        
        try:
            poll_id = int(poll_id)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': '无效的投票ID格式',
                'error_type': 'invalid_param'
            }), 400
        
        captcha_ok, captcha_msg, remaining_attempts = validate_captcha(captcha_input)
        if not captcha_ok:
            return jsonify({
                'success': False,
                'message': captcha_msg,
                'error_type': 'captcha_error',
                'captcha_error': True,
                'remaining_attempts': remaining_attempts
            }), 400
        
        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({
                'success': False,
                'message': '投票不存在',
                'error_type': 'poll_not_found'
            }), 404
        
        if not poll.is_voting_open():
            return jsonify({
                'success': False,
                'message': '投票尚未开始或已结束',
                'error_type': 'poll_closed'
            }), 403
        
        options_ok, valid_option_ids, options_msg = validate_options_for_poll(poll_id, option_ids)
        if not options_ok:
            return jsonify({
                'success': False,
                'message': options_msg,
                'error_type': 'invalid_options'
            }), 400
        
        vote_type_ok, vote_type_msg = validate_poll_vote_type(poll, valid_option_ids)
        if not vote_type_ok:
            return jsonify({
                'success': False,
                'message': vote_type_msg,
                'error_type': 'vote_type_violation'
            }), 400
        
        ip_address = get_client_ip()
        user_agent = request.user_agent.string if request.user_agent else ''
        session_id = get_session_id()
        
        try:
            can_vote_flag, vote_msg = check_vote_permission_with_lock(poll_id, ip_address, session_id)
            
            if not can_vote_flag:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': vote_msg,
                    'error_type': 'already_voted'
                }), 403
            
            vote_ok, vote_msg = record_vote_records(
                poll_id, 
                valid_option_ids, 
                ip_address, 
                user_agent, 
                session_id
            )
            
            if not vote_ok:
                db.session.rollback()
                VoteSession.query.filter_by(
                    poll_id=poll_id,
                    ip_address=ip_address,
                    session_id=session_id
                ).delete()
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'message': vote_msg,
                    'error_type': 'vote_failed'
                }), 500
            
            results = get_poll_results(poll_id)
            
            return jsonify({
                'success': True,
                'message': '投票成功！',
                'results': results
            })
            
        except IntegrityError as e:
            db.session.rollback()
            limit_hours = current_app.config.get('VOTE_IP_LIMIT_HOURS', 24)
            return jsonify({
                'success': False,
                'message': f'您已经投过票了，{limit_hours}小时内不能重复投票',
                'error_type': 'already_voted'
            }), 403
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': '数据库操作失败，请稍后重试',
                'error_type': 'database_error'
            }), 500
        
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'投票失败：{str(e)}',
                'error_type': 'unknown_error'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '服务器内部错误',
            'error_type': 'server_error'
        }), 500

@api.route('/results/<int:poll_id>', methods=['GET'])
def get_results(poll_id):
    try:
        rate_ok, rate_msg = check_rate_limit()
        if not rate_ok:
            return jsonify({
                'success': False,
                'message': rate_msg
            }), 429
        
        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({
                'success': False,
                'message': '投票不存在'
            }), 404
        
        if not can_view_results(poll):
            return jsonify({
                'success': False,
                'message': '该投票结果未公开，请联系管理员'
            }), 403
        
        results = get_poll_results(poll_id)
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取结果失败'
        }), 500

@api.route('/polls/active', methods=['GET'])
def get_active_polls():
    try:
        active_polls = Poll.query.filter_by(is_active=True).order_by(Poll.created_at.desc()).all()
        
        polls_data = []
        for poll in active_polls:
            polls_data.append({
                'id': poll.id,
                'title': poll.title,
                'description': poll.description,
                'vote_type': poll.vote_type,
                'max_choices': poll.max_choices,
                'total_votes': poll.get_total_votes(),
                'is_results_public': poll.is_results_public
            })
        
        return jsonify({
            'success': True,
            'data': polls_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取投票列表失败'
        }), 500

@api.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response
