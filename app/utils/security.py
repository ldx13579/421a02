import time
from datetime import datetime, timedelta
from flask import request, session, current_app
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import VoteRecord, Poll, Option, VoteSession, RateLimit

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.headers.get("X-Real-IP"):
        ip = request.headers.get("X-Real-IP")
    else:
        ip = request.remote_addr or '127.0.0.1'
    return ip

def get_session_id():
    if '_vote_session_id' not in session:
        import uuid
        session['_vote_session_id'] = str(uuid.uuid4())
    return session['_vote_session_id']

def store_captcha(code):
    expire_seconds = current_app.config.get('CAPTCHA_EXPIRE_SECONDS', 300)
    session['captcha_data'] = {
        'code': code.upper(),
        'created_at': time.time(),
        'attempts': 0,
        'expire_seconds': expire_seconds
    }

def validate_captcha(user_input):
    captcha_data = session.get('captcha_data')
    
    if not captcha_data:
        return False, '验证码已过期或不存在，请刷新后重试', 0
    
    code = captcha_data.get('code', '')
    created_at = captcha_data.get('created_at', 0)
    attempts = captcha_data.get('attempts', 0)
    expire_seconds = captcha_data.get('expire_seconds', 300)
    max_attempts = current_app.config.get('CAPTCHA_MAX_ATTEMPTS', 3)
    
    if time.time() - created_at > expire_seconds:
        session.pop('captcha_data', None)
        return False, '验证码已过期，请刷新后重试', 0
    
    if not user_input or not user_input.strip():
        return False, '请输入验证码', max_attempts - attempts
    
    user_input_upper = user_input.strip().upper()
    
    if user_input_upper != code:
        attempts += 1
        session['captcha_data']['attempts'] = attempts
        
        remaining = max_attempts - attempts
        
        if remaining <= 0:
            session.pop('captcha_data', None)
            return False, '验证码错误次数过多，请刷新后重试', 0
        
        if remaining == 1:
            return False, f'验证码错误，还剩 {remaining} 次机会', remaining
        
        return False, f'验证码错误，还剩 {remaining} 次机会', remaining
    
    session.pop('captcha_data', None)
    return True, '验证通过', 0

class DatabaseRateLimiter:
    
    @classmethod
    def _cleanup_expired(cls):
        try:
            now = datetime.utcnow()
            expired = RateLimit.query.filter(RateLimit.reset_at < now).all()
            for record in expired:
                db.session.delete(record)
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    @classmethod
    def is_allowed(cls, key, limit, window_seconds):
        cls._cleanup_expired()
        
        now = datetime.utcnow()
        reset_at = now + timedelta(seconds=window_seconds)
        
        try:
            record = RateLimit.query.filter_by(key=key).with_for_update().first()
            
            if record:
                if now > record.reset_at:
                    record.count = 1
                    record.reset_at = reset_at
                    db.session.commit()
                    return True
                
                if record.count >= limit:
                    return False
                
                record.count += 1
                db.session.commit()
                return True
            else:
                new_record = RateLimit(
                    key=key,
                    count=1,
                    reset_at=reset_at
                )
                db.session.add(new_record)
                db.session.commit()
                return True
                
        except IntegrityError:
            db.session.rollback()
            record = RateLimit.query.filter_by(key=key).first()
            if record:
                if record.count >= limit:
                    return False
                record.count += 1
                db.session.commit()
                return True
            return False
        except Exception:
            db.session.rollback()
            return True
    
    @classmethod
    def get_remaining(cls, key, limit):
        try:
            record = RateLimit.query.filter_by(key=key).first()
            if record:
                return max(0, limit - record.count)
            return limit
        except Exception:
            return limit

def check_rate_limit():
    ip = get_client_ip()
    
    vote_limit = current_app.config.get('RATE_LIMIT_VOTE_PER_MINUTE', 5)
    if not DatabaseRateLimiter.is_allowed(f'vote_{ip}', vote_limit, 60):
        return False, f'请求过于频繁，请稍后再试。每分钟最多 {vote_limit} 次投票请求。'
    
    general_limit = current_app.config.get('RATE_LIMIT_GENERAL_PER_MINUTE', 30)
    if not DatabaseRateLimiter.is_allowed(f'general_{ip}', general_limit, 60):
        return False, '请求过于频繁，请稍后再试。'
    
    return True, 'OK'

def check_vote_permission_with_lock(poll_id, ip_address, session_id):
    limit_hours = current_app.config.get('VOTE_IP_LIMIT_HOURS', 24)
    cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
    
    try:
        vote_session = VoteSession(
            poll_id=poll_id,
            ip_address=ip_address,
            session_id=session_id,
            voted_at=datetime.utcnow()
        )
        db.session.add(vote_session)
        db.session.flush()
        return True, None
        
    except IntegrityError:
        db.session.rollback()
        
        existing = VoteSession.query.filter(
            VoteSession.poll_id == poll_id,
            VoteSession.ip_address == ip_address,
            VoteSession.session_id == session_id
        ).with_for_update().first()
        
        if existing:
            if existing.voted_at >= cutoff_time:
                return False, f'您已经投过票了，{limit_hours}小时内不能重复投票'
            else:
                existing.voted_at = datetime.utcnow()
                db.session.flush()
                return True, None
        else:
            return False, '投票验证失败，请稍后重试'

def validate_options_for_poll(poll_id, option_ids):
    if not option_ids:
        return False, [], '请选择投票选项'
    
    if not isinstance(option_ids, list):
        option_ids = [option_ids]
    
    try:
        option_ids = [int(opt_id) for opt_id in option_ids]
    except (ValueError, TypeError):
        return False, [], '无效的选项格式'
    
    if not option_ids:
        return False, [], '请选择投票选项'
    
    valid_options = db.session.query(Option.id).filter(
        Option.poll_id == poll_id,
        Option.id.in_(option_ids)
    ).all()
    
    valid_option_ids = [opt[0] for opt in valid_options]
    
    if len(valid_option_ids) != len(option_ids):
        return False, [], '存在无效的投票选项'
    
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

def record_vote_records(poll_id, option_ids, ip_address, user_agent, session_id):
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

def can_view_results(poll):
    if poll.is_results_public:
        return True
    
    return False
