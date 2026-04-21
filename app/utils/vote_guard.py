from datetime import datetime, timedelta
from flask import request, current_app
from app import db
from app.models import VoteRecord

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.headers.get("X-Real-IP"):
        ip = request.headers.get("X-Real-IP")
    else:
        ip = request.remote_addr or '127.0.0.1'
    return ip

def has_voted_recently(poll_id, ip_address=None, session_id=None):
    if ip_address is None:
        ip_address = get_client_ip()
    
    limit_hours = current_app.config.get('VOTE_IP_LIMIT_HOURS', 24)
    cutoff_time = datetime.utcnow() - timedelta(hours=limit_hours)
    
    query = VoteRecord.query.filter(
        VoteRecord.poll_id == poll_id,
        VoteRecord.voted_at >= cutoff_time
    )
    
    if ip_address:
        query = query.filter(VoteRecord.ip_address == ip_address)
    
    if session_id:
        query = query.filter(VoteRecord.session_id == session_id)
    
    return query.first() is not None

def get_user_agent():
    return request.user_agent.string if request.user_agent else ''

def get_session_id():
    from flask import session
    return session.get('_id', '')

def record_vote(poll_id, option_ids, ip_address=None, user_agent=None, session_id=None):
    if ip_address is None:
        ip_address = get_client_ip()
    if user_agent is None:
        user_agent = get_user_agent()
    if session_id is None:
        session_id = get_session_id()
    
    if not isinstance(option_ids, list):
        option_ids = [option_ids]
    
    for option_id in option_ids:
        vote_record = VoteRecord(
            poll_id=poll_id,
            option_id=option_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        db.session.add(vote_record)
    
    db.session.commit()
    return True

def can_vote(poll):
    if not poll.is_voting_open():
        return False, '投票尚未开始或已结束'
    
    ip_address = get_client_ip()
    session_id = get_session_id()
    
    if has_voted_recently(poll.id, ip_address, session_id):
        limit_hours = current_app.config.get('VOTE_IP_LIMIT_HOURS', 24)
        return False, f'您已经投过票了，{limit_hours}小时内不能重复投票'
    
    return True, '可以投票'
