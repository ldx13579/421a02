from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.models import Admin, Poll, Option, VoteRecord

admin = Blueprint('admin', __name__)

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = Admin.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('admin/login.html')

@admin.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功退出登录', 'success')
    return redirect(url_for('admin.login'))

@admin.route('/')
@admin.route('/dashboard')
@login_required
def dashboard():
    total_polls = Poll.query.count()
    active_polls = Poll.query.filter_by(is_active=True).count()
    total_votes = VoteRecord.query.count()
    
    recent_polls = Poll.query.order_by(Poll.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        total_polls=total_polls,
        active_polls=active_polls,
        total_votes=total_votes,
        recent_polls=recent_polls
    )

@admin.route('/polls')
@login_required
def polls():
    all_polls = Poll.query.order_by(Poll.created_at.desc()).all()
    return render_template('admin/polls.html', polls=all_polls)

@admin.route('/poll/create', methods=['GET', 'POST'])
@login_required
def create_poll():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        vote_type = request.form.get('vote_type', 'single')
        max_choices = int(request.form.get('max_choices', 1))
        is_active = request.form.get('is_active') == 'on'
        
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        end_time = None
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        if not title:
            flash('投票标题不能为空', 'danger')
            return redirect(request.url)
        
        poll = Poll(
            title=title,
            description=description,
            vote_type=vote_type,
            max_choices=max_choices,
            is_active=is_active,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(poll)
        db.session.flush()
        
        options_text = request.form.get('options', '').strip().split('\n')
        for i, opt_text in enumerate(options_text):
            opt_text = opt_text.strip()
            if opt_text:
                option = Option(
                    poll_id=poll.id,
                    text=opt_text,
                    order=i
                )
                db.session.add(option)
        
        db.session.commit()
        flash('投票创建成功', 'success')
        return redirect(url_for('admin.polls'))
    
    return render_template('admin/poll_form.html', poll=None)

@admin.route('/poll/<int:poll_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    options = poll.options.order_by(Option.order, Option.id).all()
    
    if request.method == 'POST':
        poll.title = request.form.get('title', '').strip()
        poll.description = request.form.get('description', '').strip()
        poll.vote_type = request.form.get('vote_type', 'single')
        poll.max_choices = int(request.form.get('max_choices', 1))
        poll.is_active = request.form.get('is_active') == 'on'
        
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        
        if start_time_str:
            try:
                poll.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            poll.start_time = None
        
        if end_time_str:
            try:
                poll.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            poll.end_time = None
        
        if not poll.title:
            flash('投票标题不能为空', 'danger')
            return redirect(request.url)
        
        options_text = request.form.get('options', '').strip().split('\n')
        for opt in options:
            db.session.delete(opt)
        
        for i, opt_text in enumerate(options_text):
            opt_text = opt_text.strip()
            if opt_text:
                option = Option(
                    poll_id=poll.id,
                    text=opt_text,
                    order=i
                )
                db.session.add(option)
        
        db.session.commit()
        flash('投票更新成功', 'success')
        return redirect(url_for('admin.polls'))
    
    options_text = '\n'.join([opt.text for opt in options])
    return render_template('admin/poll_form.html', poll=poll, options_text=options_text)

@admin.route('/poll/<int:poll_id>/delete', methods=['POST'])
@login_required
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    db.session.delete(poll)
    db.session.commit()
    flash('投票已删除', 'success')
    return redirect(url_for('admin.polls'))

@admin.route('/poll/<int:poll_id>/toggle', methods=['POST'])
@login_required
def toggle_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    poll.is_active = not poll.is_active
    db.session.commit()
    
    status = '已激活' if poll.is_active else '已禁用'
    flash(f'投票{status}', 'success')
    return redirect(url_for('admin.polls'))

@admin.route('/poll/<int:poll_id>/results')
@login_required
def poll_results(poll_id):
    poll = Poll.query.get_or_404(poll_id)
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
        'admin/poll_results.html',
        poll=poll,
        results=results_data,
        total_votes=total_votes
    )

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        admin_user = Admin.query.first()
        
        if new_username:
            existing = Admin.query.filter(
                Admin.username == new_username,
                Admin.id != admin_user.id
            ).first()
            if existing:
                flash('用户名已存在', 'danger')
                return redirect(request.url)
            admin_user.username = new_username
        
        if new_password:
            if new_password != confirm_password:
                flash('两次输入的密码不一致', 'danger')
                return redirect(request.url)
            if len(new_password) < 6:
                flash('密码长度至少6位', 'danger')
                return redirect(request.url)
            admin_user.set_password(new_password)
        
        db.session.commit()
        flash('设置更新成功', 'success')
        return redirect(request.url)
    
    admin_user = Admin.query.first()
    return render_template('admin/settings.html', admin=admin_user)
