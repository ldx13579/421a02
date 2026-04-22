from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, make_response, abort
from app import db
from app.models import Poll, Option
from app.utils import (
    generate_captcha, 
    create_captcha_image, 
    can_vote, 
    record_vote,
    get_client_ip,
    get_session_id
)
from app.utils.security import store_captcha, can_view_results

main = Blueprint('main', __name__)

@main.route('/')
def index():
    active_polls = Poll.query.filter_by(is_active=True).order_by(Poll.created_at.desc()).all()
    return render_template('index.html', polls=active_polls)

@main.route('/poll/<int:poll_id>')
def poll_detail(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    options = poll.options.order_by(Option.order, Option.id).all()
    
    can_vote_flag, vote_message = can_vote(poll)
    
    captcha_text = generate_captcha()
    store_captcha(captcha_text)
    
    return render_template(
        'poll_detail.html',
        poll=poll,
        options=options,
        can_vote=can_vote_flag,
        vote_message=vote_message
    )

@main.route('/results/<int:poll_id>')
def results(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    
    if not can_view_results(poll):
        abort(403, description='该投票结果未公开，请联系管理员')
    
    options = poll.options.order_by(Option.order, Option.id).all()
    
    results_data = []
    total_votes = poll.get_total_votes()
    
    for option in options:
        vote_count = option.get_vote_count()
        percentage = option.get_vote_percentage()
        results_data.append({
            'id': option.id,
            'text': option.text,
            'votes': vote_count,
            'percentage': percentage
        })
    
    return render_template(
        'results.html',
        poll=poll,
        results=results_data,
        total_votes=total_votes
    )

@main.route('/captcha')
def captcha():
    captcha_text = generate_captcha()
    store_captcha(captcha_text)
    
    image_buffer = create_captcha_image(captcha_text)
    
    response = make_response(image_buffer.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@main.route('/refresh-captcha')
def refresh_captcha():
    captcha_text = generate_captcha()
    store_captcha(captcha_text)
    
    image_buffer = create_captcha_image(captcha_text)
    
    response = make_response(image_buffer.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
