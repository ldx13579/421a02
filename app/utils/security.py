import time
from collections import defaultdict
from datetime import datetime, timedelta
from flask import request, session, current_app
from app import db
from app.models import VoteRecord, Poll, Option

class RateLimiter:
    _requests = defaultdict(lambda: {'count': 0, 'reset_time': 0})
    
    @classmethod
    def is_allowed(cls, key, limit, window_seconds):
        current_time = time.time()
        request_data = cls._requests[key]
        
        if current_time > request_data['reset_time']:
            request_data['count'] = 0
            request_data['reset_time'] = current_time + window_seconds
        
        if request_data['count'] >= limit:
            return False
        
        request_data['count'] += 1
        return True
    
    @classmethod
    def get_remaining(cls, key, limit):
        request_data = cls._requests.get(key, {'count': 0})
        return max(0, limit - request_data['count'])

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.headers.get("X-Real-IP"):
        ip = request.headers.get("X-Real-IP")
    else:
        ip = request.remote_addr or '127.0.0.1'
    return ip

def get_session_id():
    return session.sid if hasattr(session, 'sid') else str(id(session))

def check_rate_limit():
    ip = get_client_ip()
    
    vote_limit = current_app.config.get('RATE_LIMIT_VOTE_PER_MINUTE', 5)
    if not RateLimiter.is_allowed(f'vote_{ip}', vote_limit, 60):
        return False, f'请求过于频繁，请稍后再试。每分钟最多 {vote_limit} 次投票请求。'
    
    general_limit = current_app.config.get('RATE_LIMIT_GENERAL_PER_MINUTE', 30)
    if not RateLimiter.is_allowed(f'general_{ip}', general_limit, 60):
        return False, '请求过于频繁，请稍后再试。'
    
    return True, 'OK'

def validate_captcha(user_input):
    stored_captcha = session.pop('captcha', None)
    
    if not stored_captcha:
        return False, '验证码已过期，请刷新后重试'
    
    if not user_input:
        return False, '请输入验证码'
    
    if user_input.strip().upper() != stored_captcha.upper():
        return False, '验证码错误'
    
    return True, '验证通过'

def check_vote_permission_atomic(poll_id, ip_address, session_id):
    limit_hours = current_app.config.get('VOTE_IP_LIMIT_HOURS', 24)
    cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
    
    existing_vote = db.session.query(VoteRecord).filter(
        VoteRecord.poll_id == poll_id,
        VoteRecord.voted_at >= cutoff_time,
        db.or_(
            VoteRecord.ip_address == ip_address,
            VoteRecord.session_id == session_id
        )
    ).with_for_update().first()
    
    return existing_vote is None

def validate_options_for_poll(poll_id, option_ids):
    if not option_ids:
        return False, [], '请选择投票选项'
    
    if not isinstance(option_ids, list):
        option_ids = [option_ids]
    
    option_ids = [int(opt_id) for opt_id in option_ids if str(opt_id).isdigit()]
    
    if not option_ids:
        return False, [], '无效的选项格式'
    
    valid_options = db.session.query(Option.id).filter(
        Option.poll_id == poll_id,
        Option.id.in_(option_ids)
    ).all()
    
    valid_option_ids = [opt[0] for opt in valid_options]
    
    invalid_ids = set(option_ids) - set(valid_option_ids)
    if invalid_ids:
        return False, [], f'存在无效的投票选项'
    
    return True, valid_option_ids, '验证通过'

def validate_poll_vote_type(poll, option_ids):
    if poll.vote_type == 'single':
        if len(option_ids) > 1:
            return False, '该投票仅支持单选'
    elif poll.vote_type == 'multiple':
        if len(option_ids) > poll.max_choices:
            return False, f'最多只能选择 {poll.max_choices} 个选项'
    
    if len(option_ids) == 0:
        return False, '请至少选择一个选项'
    
    return True, '验证通过'

def record_vote_atomic(poll_id, option_ids, ip_address, user_agent, session_id):
    try:
        for option_id in option_ids:
            vote_record = VoteRecord(
                poll_id=poll_id,
                option_id=option_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                voted_at=datetime.utcnow()
            )
            db.session.add(vote_record)
        
        db.session.commit()
        return True, '投票成功'
    except Exception as e:
        db.session.rollback()
        return False, f'投票失败: {str(e)}'

def get_poll_results(poll_id):
    poll = Poll.query.get(poll_id)
    if not poll:
        return None
    
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
