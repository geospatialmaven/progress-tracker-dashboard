from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from functools import wraps
import os
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gm-progress-tracker-2025-secret-key')

# Use PostgreSQL on Render, SQLite locally
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///gm_dashboard.db')
if _db_url.startswith('postgres://'):          # Render gives postgres://, SQLAlchemy needs postgresql://
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.jinja_env.globals['timedelta'] = timedelta
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to access the dashboard.'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'

# ─── MODELS ──────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False)  # super_admin, developer, client
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    specialization = db.Column(db.String(200))
    avatar_color = db.Column(db.String(20), default='#10b981')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_initials(self):
        parts = self.name.split()
        return ''.join([p[0] for p in parts[:2]]).upper()

    @property
    def role_label(self):
        labels = {'super_admin': 'Super Admin', 'developer': 'Developer', 'client': 'Client'}
        return labels.get(self.role, 'Unknown')

    @property
    def role_color(self):
        colors = {'super_admin': '#6366f1', 'developer': '#10b981', 'client': '#f59e0b'}
        return colors.get(self.role, '#6b7280')


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(200), nullable=False)
    client_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    project_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='planning')
    priority = db.Column(db.String(10), default='medium')
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget_estimated = db.Column(db.Float, default=0)
    budget_actual = db.Column(db.Float, default=0)
    location = db.Column(db.String(200))
    country = db.Column(db.String(100))
    coordinator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    client_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    overall_progress = db.Column(db.Integer, default=0)
    tags = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    coordinator = db.relationship('User', foreign_keys=[coordinator_id])
    client_user = db.relationship('User', foreign_keys=[client_user_id])
    sections = db.relationship('Section', backref='project', lazy=True,
                               cascade='all, delete-orphan', order_by='Section.order_num')
    objectives = db.relationship('Objective', backref='project', lazy=True, cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='project', lazy=True, cascade='all, delete-orphan')
    cost_items = db.relationship('CostItem', backref='project', lazy=True, cascade='all, delete-orphan')

    def calc_progress(self):
        sects = Section.query.filter_by(project_id=self.id).all()
        if not sects:
            return 0
        return int(sum(s.progress for s in sects) / len(sects))

    def days_remaining(self):
        if not self.end_date:
            return None
        return (self.end_date - date.today()).days

    @property
    def status_color(self):
        colors = {
            'planning': '#6366f1', 'active': '#10b981',
            'on_hold': '#f59e0b', 'completed': '#3b82f6', 'cancelled': '#ef4444'
        }
        return colors.get(self.status, '#6b7280')

    @property
    def priority_color(self):
        return {'low': '#10b981', 'medium': '#f59e0b', 'high': '#ef4444'}.get(self.priority, '#6b7280')


class TOR(db.Model):
    __tablename__ = 'tors'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), unique=True)
    background = db.Column(db.Text, default='')
    purpose = db.Column(db.Text, default='')
    scope_of_work = db.Column(db.Text, default='')
    specific_objectives = db.Column(db.Text, default='')
    deliverables = db.Column(db.Text, default='')
    methodology = db.Column(db.Text, default='')
    data_requirements = db.Column(db.Text, default='')
    software_tools = db.Column(db.Text, default='')
    qualifications = db.Column(db.Text, default='')
    reporting_requirements = db.Column(db.Text, default='')
    timeline_notes = db.Column(db.Text, default='')
    version = db.Column(db.String(10), default='1.0')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    project = db.relationship('Project', backref=db.backref('tor', uselist=False))


class Objective(db.Model):
    __tablename__ = 'objectives'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    obj_type = db.Column(db.String(20), default='secondary')
    priority = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')
    target_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    section_type = db.Column(db.String(30))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)
    order_num = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='section', lazy=True,
                            cascade='all, delete-orphan', order_by='Task.created_at')
    assignments = db.relationship('SectionAssignment', backref='section', lazy=True, cascade='all, delete-orphan')

    @property
    def type_icon(self):
        icons = {
            'analysis': 'bi-bar-chart-line', 'writeup': 'bi-pencil-square',
            'learning': 'bi-book', 'fieldwork': 'bi-geo-alt',
            'reporting': 'bi-file-earmark-text', 'data_collection': 'bi-satellite',
            'qc': 'bi-check-circle'
        }
        return icons.get(self.section_type, 'bi-folder2')

    @property
    def type_color(self):
        colors = {
            'analysis': '#6366f1', 'writeup': '#10b981', 'learning': '#f59e0b',
            'fieldwork': '#ef4444', 'reporting': '#3b82f6', 'data_collection': '#8b5cf6',
            'qc': '#06b6d4'
        }
        return colors.get(self.section_type, '#6b7280')

    @property
    def type_label(self):
        labels = {
            'analysis': 'Analysis', 'writeup': 'Write-up', 'learning': 'Learning',
            'fieldwork': 'Fieldwork', 'reporting': 'Reporting',
            'data_collection': 'Data Collection', 'qc': 'Quality Control'
        }
        return labels.get(self.section_type, self.section_type.title())


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='todo')
    priority = db.Column(db.String(10), default='medium')
    progress = db.Column(db.Integer, default=0)
    story_points = db.Column(db.Integer, default=0)
    sprint_label = db.Column(db.String(50), default='')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])

    @property
    def priority_color(self):
        return {'low': '#10b981', 'medium': '#f59e0b', 'high': '#ef4444', 'critical': '#dc2626'}.get(self.priority, '#6b7280')

    @property
    def status_color(self):
        return {'todo': '#6b7280', 'in_progress': '#3b82f6', 'review': '#f59e0b',
                'completed': '#10b981', 'blocked': '#ef4444'}.get(self.status, '#6b7280')

    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and self.status != 'completed'


class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date)
    status = db.Column(db.String(20), default='upcoming')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CostItem(db.Model):
    __tablename__ = 'cost_items'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    category = db.Column(db.String(100))
    description = db.Column(db.String(200))
    unit = db.Column(db.String(50))
    quantity = db.Column(db.Float, default=1)
    unit_cost_estimated = db.Column(db.Float, default=0)
    unit_cost_actual = db.Column(db.Float, default=0)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_estimated(self):
        return (self.quantity or 0) * (self.unit_cost_estimated or 0)

    @property
    def total_actual(self):
        return (self.quantity or 0) * (self.unit_cost_actual or 0)


class SectionAssignment(db.Model):
    __tablename__ = 'section_assignments'
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assignment_role = db.Column(db.String(50), default='contributor')
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')


class Deliverable(db.Model):
    __tablename__ = 'deliverables'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_qa_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # Stages: draft | qa_review | admin_review | client_review | completed | revision
    stage = db.Column(db.String(30), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project')
    section = db.relationship('Section')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assigned_qa = db.relationship('User', foreign_keys=[assigned_qa_id])
    events = db.relationship('DeliverableEvent', backref='deliverable', lazy=True,
                             cascade='all, delete-orphan', order_by='DeliverableEvent.created_at')
    comments = db.relationship('DeliverableComment', backref='deliverable', lazy=True,
                               cascade='all, delete-orphan', order_by='DeliverableComment.created_at')

    @property
    def stage_color(self):
        return {'draft':'#6b7280','qa_review':'#3b82f6','admin_review':'#6366f1',
                'client_review':'#f59e0b','completed':'#10b981','revision':'#ef4444'}.get(self.stage,'#6b7280')

    @property
    def stage_label(self):
        return {'draft':'Draft','qa_review':'In QA Review','admin_review':'Admin Review',
                'client_review':'Client Review','completed':'Completed','revision':'Needs Revision'}.get(self.stage, self.stage)

    def open_comments(self):
        return [c for c in self.comments if c.status != 'closed' and c.parent_id is None]

    def client_visible_comments(self):
        return [c for c in self.comments if c.is_client_visible or c.author.role == 'client']


class DeliverableEvent(db.Model):
    __tablename__ = 'deliverable_events'
    id = db.Column(db.Integer, primary_key=True)
    deliverable_id = db.Column(db.Integer, db.ForeignKey('deliverables.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_type = db.Column(db.String(40))
    stage_from = db.Column(db.String(30), default='')
    stage_to = db.Column(db.String(30), default='')
    note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')


class DeliverableComment(db.Model):
    __tablename__ = 'deliverable_comments'
    id = db.Column(db.Integer, primary_key=True)
    deliverable_id = db.Column(db.Integer, db.ForeignKey('deliverables.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text, nullable=False)
    is_client_visible = db.Column(db.Boolean, default=False)
    # open | dev_resolved | qa_resolved | closed
    status = db.Column(db.String(20), default='open')
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime)
    parent_id = db.Column(db.Integer, db.ForeignKey('deliverable_comments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', foreign_keys=[author_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])
    replies = db.relationship('DeliverableComment', foreign_keys=[parent_id], lazy=True)

    @property
    def status_label(self):
        return {'open':'Open','dev_resolved':'Dev Resolved (Awaiting QA)',
                'qa_resolved':'QA Verified (Awaiting Admin)','closed':'Closed'}.get(self.status, self.status)

    @property
    def status_color(self):
        return {'open':'#ef4444','dev_resolved':'#f59e0b','qa_resolved':'#3b82f6','closed':'#10b981'}.get(self.status,'#6b7280')


class TaskAssignmentRequest(db.Model):
    __tablename__ = 'task_assignment_requests'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assign_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.String(300), default='')
    forward_type = db.Column(db.String(50), default='')  # e.g. 'QA', 'Write-up', 'Review', 'General'
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_note = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    task = db.relationship('Task')
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])
    assign_to = db.relationship('User', foreign_keys=[assign_to_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    action = db.Column(db.String(40))  # task_done, task_created, project_created, status_changed, etc.
    description = db.Column(db.String(300))
    icon = db.Column(db.String(40), default='bi-activity')
    color = db.Column(db.String(20), default='#10b981')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')
    project = db.relationship('Project')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── DECORATORS ──────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            flash('Administrator access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def not_client(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role == 'client':
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_globals():
    pending = 0
    if current_user.is_authenticated and current_user.role == 'super_admin':
        pending = TaskAssignmentRequest.query.filter_by(status='pending').count()
    return {'pending_approvals': pending}


def log_act(action, description, project_id=None, icon='bi-activity', color='#10b981'):
    """Append an activity log entry to the current session (caller must commit)."""
    try:
        db.session.add(ActivityLog(
            user_id=current_user.id, project_id=project_id,
            action=action, description=description, icon=icon, color=color
        ))
    except Exception:
        pass


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('public/home.html')


@app.route('/app')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=True)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'developer')
        department = request.form.get('department', '').strip()
        specialization = request.form.get('specialization', '').strip()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('login') + '?tab=signup')
        if role not in ('developer', 'client'):
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('login') + '?tab=signup')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('login') + '?tab=signup')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('login') + '?tab=signup')
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return redirect(url_for('login') + '?tab=signup')

        colors = ['#10b981', '#6366f1', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444', '#06b6d4']
        user = User(
            name=name, email=email, role=role,
            department=department, specialization=specialization,
            avatar_color=random.choice(colors)
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created! Welcome, {name}. Please sign in.', 'success')
        return redirect(url_for('login'))
    return redirect(url_for('login') + '?tab=signup')


@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    if current_user.role == 'super_admin':
        projects = Project.query.order_by(Project.updated_at.desc()).limit(6).all()
        all_projects = Project.query.all()
        users = User.query.filter(User.role != 'client').all()
        total_tasks = Task.query.count()
        active_count = Project.query.filter_by(status='active').count()
        completed_count = Project.query.filter_by(status='completed').count()
        planning_count = Project.query.filter_by(status='planning').count()
        overdue_tasks = [t for t in Task.query.all() if t.is_overdue()]
        upcoming_milestones = Milestone.query.filter(
            Milestone.date >= today,
            Milestone.date <= today + timedelta(days=30),
            Milestone.status == 'upcoming'
        ).order_by(Milestone.date).limit(5).all()
    elif current_user.role == 'developer':
        assigned_sections = db.session.query(Section).join(SectionAssignment).filter(
            SectionAssignment.user_id == current_user.id).all()
        project_ids = list(set(s.project_id for s in assigned_sections))
        all_projects = Project.query.filter(Project.id.in_(project_ids)).all() if project_ids else []
        projects = all_projects[:6]
        users = []
        total_tasks = Task.query.filter_by(assigned_to_id=current_user.id).count()
        active_count = sum(1 for p in all_projects if p.status == 'active')
        completed_count = sum(1 for p in all_projects if p.status == 'completed')
        planning_count = sum(1 for p in all_projects if p.status == 'planning')
        overdue_tasks = [t for t in Task.query.filter_by(assigned_to_id=current_user.id).all() if t.is_overdue()]
        upcoming_milestones = []
        for p in all_projects:
            for ms in p.milestones:
                if ms.date and ms.date >= today and ms.status == 'upcoming':
                    upcoming_milestones.append(ms)
        upcoming_milestones = sorted(upcoming_milestones, key=lambda m: m.date)[:5]
    else:  # client
        all_projects = Project.query.filter_by(client_user_id=current_user.id).all()
        projects = all_projects
        users = []
        total_tasks = 0
        active_count = sum(1 for p in all_projects if p.status == 'active')
        completed_count = sum(1 for p in all_projects if p.status == 'completed')
        planning_count = sum(1 for p in all_projects if p.status == 'planning')
        overdue_tasks = []
        upcoming_milestones = []
        for p in all_projects:
            for ms in p.milestones:
                if ms.date and ms.date >= today and ms.status == 'upcoming':
                    upcoming_milestones.append(ms)
        upcoming_milestones = sorted(upcoming_milestones, key=lambda m: m.date)[:5]

    for p in projects:
        p.overall_progress = p.calc_progress()

    return render_template('dashboard.html',
        projects=projects, users=users, total_tasks=total_tasks,
        active_count=active_count, completed_count=completed_count,
        planning_count=planning_count, overdue_tasks=overdue_tasks,
        upcoming_milestones=upcoming_milestones, today=today,
        total_projects=len(all_projects)
    )


@app.route('/projects')
@login_required
def projects_list():
    if current_user.role == 'super_admin':
        projects = Project.query.order_by(Project.created_at.desc()).all()
        developers = User.query.filter(User.role.in_(['super_admin', 'developer'])).all()
        clients = User.query.filter_by(role='client').all()
    elif current_user.role == 'developer':
        # Projects where the developer is assigned to any section
        assigned_sections = db.session.query(Section).join(SectionAssignment).filter(
            SectionAssignment.user_id == current_user.id).all()
        project_ids = set(s.project_id for s in assigned_sections)
        # Also include projects where developer is the coordinator
        coordinated_ids = {p.id for p in Project.query.filter_by(coordinator_id=current_user.id).all()}
        project_ids.update(coordinated_ids)
        projects = Project.query.filter(Project.id.in_(project_ids)).order_by(
            Project.updated_at.desc()).all() if project_ids else []
        developers = []
        clients = []
    else:  # client
        projects = Project.query.filter_by(client_user_id=current_user.id).order_by(
            Project.updated_at.desc()).all()
        developers = []
        clients = []

    for p in projects:
        p.overall_progress = p.calc_progress()

    return render_template('projects/list.html', projects=projects, developers=developers, clients=clients)


@app.route('/projects', methods=['POST'])
@login_required
@not_client
def create_project():
    try:
        count = Project.query.count() + 1
        code = f"GM-{date.today().year}-{count:03d}"
        project = Project(
            code=code,
            name=request.form['name'],
            client_name=request.form.get('client_name', ''),
            description=request.form.get('description', ''),
            project_type=request.form.get('project_type', ''),
            status=request.form.get('status', 'planning'),
            priority=request.form.get('priority', 'medium'),
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form.get('start_date') else None,
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None,
            budget_estimated=float(request.form.get('budget_estimated', 0) or 0),
            location=request.form.get('location', ''),
            country=request.form.get('country', ''),
            coordinator_id=request.form.get('coordinator_id') or current_user.id,
            client_user_id=request.form.get('client_user_id') or None,
            tags=request.form.get('tags', '')
        )
        db.session.add(project)
        db.session.flush()
        db.session.add(TOR(project_id=project.id))
        log_act('project_created', f'Created project "{project.name[:60]}"', project.id, 'bi-folder-plus', '#8b5cf6')
        db.session.commit()
        flash(f'Project <strong>{project.name}</strong> created!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('projects_list'))


@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if current_user.role == 'client' and project.client_user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    if current_user.role == 'developer':
        is_coordinator = project.coordinator_id == current_user.id
        is_assigned = SectionAssignment.query.join(Section).filter(
            Section.project_id == project_id,
            SectionAssignment.user_id == current_user.id
        ).first() is not None
        if not is_coordinator and not is_assigned:
            flash('Access denied. You are not assigned to this project.', 'danger')
            return redirect(url_for('projects_list'))

    project.overall_progress = project.calc_progress()
    sections = Section.query.filter_by(project_id=project_id).order_by(Section.order_num).all()
    developers = User.query.filter(User.role.in_(['super_admin', 'developer'])).all()
    all_users = User.query.all()
    objs = Objective.query.filter_by(project_id=project_id).order_by(Objective.obj_type, Objective.priority).all()
    cost_items = CostItem.query.filter_by(project_id=project_id).all()
    total_est = sum(c.total_estimated for c in cost_items)
    total_act = sum(c.total_actual for c in cost_items)
    obj_stats = {
        'total': len(objs),
        'completed': sum(1 for o in objs if o.status == 'completed'),
        'in_progress': sum(1 for o in objs if o.status == 'in_progress'),
        'pending': sum(1 for o in objs if o.status == 'pending'),
    }
    all_tasks = [t for s in sections for t in s.tasks]
    task_stats = {
        'total': len(all_tasks),
        'completed': sum(1 for t in all_tasks if t.status == 'completed'),
        'in_progress': sum(1 for t in all_tasks if t.status == 'in_progress'),
        'todo': sum(1 for t in all_tasks if t.status == 'todo'),
        'blocked': sum(1 for t in all_tasks if t.status == 'blocked'),
    }

    return render_template('projects/detail.html',
        project=project, sections=sections, developers=developers,
        all_users=all_users, objs=objs, obj_stats=obj_stats,
        cost_items=cost_items, total_est=total_est, total_act=total_act,
        all_tasks=all_tasks, task_stats=task_stats, today=date.today()
    )


@app.route('/projects/<int:project_id>/update', methods=['POST'])
@login_required
@not_client
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    try:
        for f in ['name', 'client_name', 'description', 'project_type', 'status',
                  'priority', 'location', 'country', 'tags']:
            val = request.form.get(f)
            if val is not None:
                setattr(project, f, val)
        for f in ['budget_estimated', 'budget_actual']:
            val = request.form.get(f)
            if val is not None:
                setattr(project, f, float(val or 0))
        if request.form.get('start_date'):
            project.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        if request.form.get('end_date'):
            project.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        if request.form.get('coordinator_id'):
            project.coordinator_id = int(request.form['coordinator_id'])
        if request.form.get('client_user_id'):
            project.client_user_id = int(request.form['client_user_id'])
        project.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Project updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    name = project.name
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{name}" deleted.', 'info')
    return redirect(url_for('projects_list'))


# TOR
@app.route('/projects/<int:project_id>/tor/update', methods=['POST'])
@login_required
@not_client
def update_tor(project_id):
    tor = TOR.query.filter_by(project_id=project_id).first()
    if not tor:
        tor = TOR(project_id=project_id)
        db.session.add(tor)
    for field in ['background', 'purpose', 'scope_of_work', 'specific_objectives',
                  'deliverables', 'methodology', 'data_requirements', 'software_tools',
                  'qualifications', 'reporting_requirements', 'timeline_notes']:
        setattr(tor, field, request.form.get(field, ''))
    tor.version = request.form.get('version', tor.version)
    tor.last_updated = datetime.utcnow()
    db.session.commit()
    flash('TOR saved!', 'success')
    return redirect(url_for('project_detail', project_id=project_id) + '#tor')


# Objectives
@app.route('/projects/<int:project_id>/objectives', methods=['POST'])
@login_required
@not_client
def add_objective(project_id):
    data = request.get_json() or {}
    obj = Objective(
        project_id=project_id,
        title=data.get('title', ''),
        description=data.get('description', ''),
        obj_type=data.get('obj_type', 'secondary'),
        priority=int(data.get('priority', 1)),
        status=data.get('status', 'pending'),
        target_date=datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None
    )
    db.session.add(obj)
    db.session.commit()
    return jsonify({'success': True, 'id': obj.id, 'title': obj.title,
                    'status': obj.status, 'obj_type': obj.obj_type})


@app.route('/objectives/<int:obj_id>', methods=['PUT', 'DELETE'])
@login_required
@not_client
def manage_objective(obj_id):
    obj = Objective.query.get_or_404(obj_id)
    if request.method == 'DELETE':
        db.session.delete(obj)
        db.session.commit()
        return jsonify({'success': True})
    data = request.get_json() or {}
    for field in ['title', 'description', 'obj_type', 'status']:
        if field in data:
            setattr(obj, field, data[field])
    if 'priority' in data:
        obj.priority = int(data['priority'])
    db.session.commit()
    return jsonify({'success': True})


# Sections
@app.route('/projects/<int:project_id>/sections', methods=['POST'])
@login_required
@not_client
def add_section(project_id):
    data = request.get_json() or request.form
    max_order = db.session.query(db.func.max(Section.order_num)).filter_by(project_id=project_id).scalar() or 0
    section = Section(
        project_id=project_id,
        section_type=data.get('section_type', 'analysis'),
        name=data.get('name', ''),
        description=data.get('description', ''),
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
        status=data.get('status', 'pending'),
        progress=int(data.get('progress', 0)),
        order_num=max_order + 1
    )
    db.session.add(section)
    db.session.flush()
    assignees = data.getlist('assignees') if hasattr(data, 'getlist') else data.get('assignees', [])
    for uid in assignees:
        if uid:
            db.session.add(SectionAssignment(section_id=section.id, user_id=int(uid)))
    db.session.commit()
    return jsonify({'success': True, 'id': section.id, 'redirect': url_for('project_detail', project_id=project_id)})


@app.route('/sections/<int:section_id>', methods=['PUT'])
@login_required
@not_client
def update_section(section_id):
    section = Section.query.get_or_404(section_id)
    data = request.get_json() or {}
    for field in ['name', 'description', 'status', 'section_type']:
        if field in data:
            setattr(section, field, data[field])
    if 'progress' in data:
        section.progress = min(100, max(0, int(data['progress'])))
    if data.get('start_date'):
        section.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if data.get('end_date'):
        section.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    db.session.commit()
    project = Project.query.get(section.project_id)
    if project:
        project.overall_progress = project.calc_progress()
        db.session.commit()
    return jsonify({'success': True, 'progress': section.progress})


@app.route('/sections/<int:section_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    db.session.delete(section)
    db.session.commit()
    return jsonify({'success': True})


# Tasks
@app.route('/sections/<int:section_id>/tasks', methods=['POST'])
@login_required
@not_client
def add_task(section_id):
    data = request.get_json() or {}
    task = Task(
        section_id=section_id,
        title=data.get('title', ''),
        description=data.get('description', ''),
        assigned_to_id=data.get('assigned_to_id') or None,
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data.get('due_date') else None,
        status=data.get('status', 'todo'),
        priority=data.get('priority', 'medium'),
        progress=int(data.get('progress', 0)),
        notes=data.get('notes', '')
    )
    db.session.add(task)
    db.session.flush()
    proj_id = task.section.project_id if task.section else None
    log_act('task_created', f'Created task "{task.title[:60]}"', proj_id, 'bi-plus-circle', '#6366f1')
    db.session.commit()
    assigned_name = task.assigned_to.name if task.assigned_to else 'Unassigned'
    return jsonify({'success': True, 'id': task.id, 'title': task.title,
                    'status': task.status, 'priority': task.priority,
                    'assigned': assigned_name, 'progress': task.progress})


@app.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if current_user.role == 'developer' and task.assigned_to_id != current_user.id:
        return jsonify({'error': 'Not authorized'}), 403
    data = request.get_json() or {}
    old_status = task.status
    for field in ['title', 'description', 'status', 'priority', 'notes', 'sprint_label']:
        if field in data:
            setattr(task, field, data[field])
    if 'story_points' in data:
        task.story_points = int(data['story_points'] or 0)
    if 'progress' in data:
        task.progress = min(100, max(0, int(data['progress'])))
    if 'assigned_to_id' in data:
        task.assigned_to_id = data['assigned_to_id'] or None
    if data.get('due_date'):
        task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
    # Activity logging
    proj_id = task.section.project_id if task.section else None
    new_status = data.get('status', old_status)
    if new_status == 'completed' and old_status != 'completed':
        log_act('task_done', f'Completed task "{task.title[:60]}"', proj_id, 'bi-check-circle-fill', '#10b981')
    elif new_status != old_status:
        label = new_status.replace('_', ' ').title()
        log_act('status_changed', f'Moved "{task.title[:55]}" → {label}', proj_id, 'bi-arrow-left-right', '#3b82f6')
    db.session.commit()
    return jsonify({'success': True})


@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
@not_client
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})


# Milestones
@app.route('/projects/<int:project_id>/milestones', methods=['POST'])
@login_required
@not_client
def add_milestone(project_id):
    data = request.get_json() or {}
    ms = Milestone(
        project_id=project_id,
        title=data.get('title', ''),
        description=data.get('description', ''),
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else None,
        status=data.get('status', 'upcoming')
    )
    db.session.add(ms)
    db.session.commit()
    return jsonify({'success': True, 'id': ms.id, 'title': ms.title})


@app.route('/milestones/<int:ms_id>', methods=['PUT', 'DELETE'])
@login_required
@not_client
def manage_milestone(ms_id):
    ms = Milestone.query.get_or_404(ms_id)
    if request.method == 'DELETE':
        db.session.delete(ms)
        db.session.commit()
        return jsonify({'success': True})
    data = request.get_json() or {}
    for field in ['title', 'description', 'status']:
        if field in data:
            setattr(ms, field, data[field])
    if data.get('date'):
        ms.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    db.session.commit()
    return jsonify({'success': True})


# Costs
@app.route('/projects/<int:project_id>/costs', methods=['POST'])
@login_required
@not_client
def add_cost(project_id):
    data = request.get_json() or {}
    cost = CostItem(
        project_id=project_id,
        category=data.get('category', 'other'),
        description=data.get('description', ''),
        unit=data.get('unit', 'lump sum'),
        quantity=float(data.get('quantity', 1)),
        unit_cost_estimated=float(data.get('unit_cost_estimated', 0)),
        unit_cost_actual=float(data.get('unit_cost_actual', 0)),
        currency=data.get('currency', 'USD')
    )
    db.session.add(cost)
    db.session.commit()
    return jsonify({'success': True, 'id': cost.id,
                    'total_est': cost.total_estimated, 'total_act': cost.total_actual})


@app.route('/costs/<int:cost_id>', methods=['DELETE'])
@login_required
@not_client
def delete_cost(cost_id):
    cost = CostItem.query.get_or_404(cost_id)
    db.session.delete(cost)
    db.session.commit()
    return jsonify({'success': True})


# Section Assignment
@app.route('/sections/<int:section_id>/assign', methods=['POST'])
@login_required
@not_client
def assign_section(section_id):
    data = request.get_json() or {}
    user_id = data.get('user_id')
    existing = SectionAssignment.query.filter_by(section_id=section_id, user_id=user_id).first()
    if not existing:
        db.session.add(SectionAssignment(section_id=section_id, user_id=int(user_id),
                                         assignment_role=data.get('role', 'contributor')))
        db.session.commit()
    return jsonify({'success': True})


@app.route('/sections/<int:section_id>/unassign/<int:user_id>', methods=['DELETE'])
@login_required
@not_client
def unassign_section(section_id, user_id):
    assignment = SectionAssignment.query.filter_by(section_id=section_id, user_id=user_id).first()
    if assignment:
        db.session.delete(assignment)
        db.session.commit()
    return jsonify({'success': True})


# Team
@app.route('/team')
@login_required
@admin_required
def team():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('team.html', users=users)


@app.route('/team/users', methods=['POST'])
@login_required
@admin_required
def add_user():
    email = request.form.get('email', '').strip().lower()
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'danger')
        return redirect(url_for('team'))
    colors = ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#06b6d4', '#ec4899']
    user = User(
        name=request.form['name'], email=email,
        role=request.form.get('role', 'developer'),
        department=request.form.get('department', ''),
        phone=request.form.get('phone', ''),
        specialization=request.form.get('specialization', ''),
        avatar_color=random.choice(colors)
    )
    user.set_password(request.form.get('password', 'changeme123'))
    db.session.add(user)
    db.session.commit()
    flash(f'User {user.name} added!', 'success')
    return redirect(url_for('team'))


@app.route('/team/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot disable yourself'}), 400
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': user.is_active})


@app.route('/team/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_pass = request.form.get('new_password', 'changeme123')
    user.set_password(new_pass)
    db.session.commit()
    return jsonify({'success': True})


# My Tasks
@app.route('/my-tasks')
@login_required
def my_tasks():
    if current_user.role == 'client':
        return redirect(url_for('dashboard'))
    tasks = Task.query.filter_by(assigned_to_id=current_user.id).order_by(Task.due_date).all()
    import json as _json
    tasks_json = _json.dumps([{
        'id': t.id,
        'title': t.title,
        'status': t.status,
        'priority': t.priority,
        'priority_color': t.priority_color,
        'status_color': t.status_color,
        'progress': t.progress,
        'story_points': t.story_points or 0,
        'sprint_label': t.sprint_label or '',
        'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None,
        'due_fmt': t.due_date.strftime('%d %b') if t.due_date else None,
        'overdue': t.is_overdue(),
        'notes': (t.notes or '')[:80],
        'project': t.section.project.name[:35] if t.section and t.section.project else '',
        'section': t.section.name[:30] if t.section else '',
        'section_color': t.section.type_color if t.section else '#6b7280',
    } for t in tasks])
    sprints = sorted(set(t.sprint_label for t in tasks if t.sprint_label))
    return render_template('my_tasks.html', tasks=tasks, today=date.today(),
                           tasks_json=tasks_json, sprints=sprints)


# ── DELIVERABLE REVIEW PIPELINE ──────────────────────────────────────────────

STAGE_ORDER = ['draft','qa_review','admin_review','client_review','completed']

def _add_event(deliverable, event_type, stage_from, stage_to, note=''):
    db.session.add(DeliverableEvent(
        deliverable_id=deliverable.id, user_id=current_user.id,
        event_type=event_type, stage_from=stage_from, stage_to=stage_to, note=note
    ))
    deliverable.stage = stage_to
    deliverable.updated_at = datetime.utcnow()


@app.route('/projects/<int:project_id>/progress')
@login_required
def project_progress(project_id):
    project = Project.query.get_or_404(project_id)
    # Access control
    if current_user.role == 'client' and project.client_user_id != current_user.id:
        abort(403)
    deliverables = Deliverable.query.filter_by(project_id=project_id).order_by(
        Deliverable.updated_at.desc()).all()
    sections = Section.query.filter_by(project_id=project_id).all()
    all_users = User.query.filter(User.is_active==True).all()
    qa_users = User.query.filter(User.role.in_(['super_admin','developer']), User.is_active==True).all()
    return render_template('projects/progress.html', project=project,
                           deliverables=deliverables, sections=sections,
                           all_users=all_users, qa_users=qa_users)


@app.route('/projects/<int:project_id>/progress', methods=['POST'])
@login_required
@not_client
def create_deliverable(project_id):
    data = request.get_json() or {}
    d = Deliverable(
        project_id=project_id,
        section_id=data.get('section_id') or None,
        title=data.get('title','').strip(),
        description=data.get('description',''),
        created_by_id=current_user.id,
        assigned_qa_id=data.get('assigned_qa_id') or None,
        stage='draft'
    )
    db.session.add(d)
    db.session.flush()
    db.session.add(DeliverableEvent(deliverable_id=d.id, user_id=current_user.id,
        event_type='created', stage_from='', stage_to='draft', note='Deliverable created'))
    log_act('deliverable_created', f'Created deliverable "{d.title[:50]}"', project_id, 'bi-file-earmark-plus', '#8b5cf6')
    db.session.commit()
    return jsonify({'success':True, 'id':d.id, 'title':d.title})


@app.route('/deliverables/<int:d_id>')
@login_required
def deliverable_detail(d_id):
    d = Deliverable.query.get_or_404(d_id)
    project = d.project
    if current_user.role == 'client':
        if project.client_user_id != current_user.id:
            abort(403)
        # Client sees only client-visible comments
        visible_comments = d.client_visible_comments()
    else:
        visible_comments = [c for c in d.comments if c.parent_id is None]
    all_users = User.query.filter(User.is_active==True).all()
    qa_users = User.query.filter(User.role.in_(['super_admin','developer']), User.is_active==True).all()
    return render_template('projects/deliverable_detail.html', d=d, project=project,
                           visible_comments=visible_comments, all_users=all_users, qa_users=qa_users)


def _check_deliverable_access(d):
    """Return (allowed, error_msg) based on current_user role vs stage."""
    stage = d.stage
    role = current_user.role
    if role == 'client' and d.project.client_user_id != current_user.id:
        return False, 'Access denied.'
    return True, None


@app.route('/deliverables/<int:d_id>/submit', methods=['POST'])
@login_required
@not_client
def deliverable_submit(d_id):
    d = Deliverable.query.get_or_404(d_id)
    note = request.get_json(silent=True) or {}
    note = note.get('note','')
    old = d.stage
    new = 'qa_review'
    _add_event(d, 'submitted', old, new, note or 'Submitted for QA review')
    log_act('deliverable_submitted', f'Submitted "{d.title[:50]}" for QA review', d.project_id, 'bi-send', '#3b82f6')
    db.session.commit()
    flash(f'"{d.title}" submitted to QA Review.', 'success')
    return redirect(url_for('deliverable_detail', d_id=d_id))


@app.route('/deliverables/<int:d_id>/qa-approve', methods=['POST'])
@login_required
def deliverable_qa_approve(d_id):
    d = Deliverable.query.get_or_404(d_id)
    note = (request.form.get('note','') or '').strip()
    old = d.stage
    _add_event(d, 'qa_approved', old, 'admin_review', note or 'QA approved. Forwarded to Admin/CTO.')
    log_act('qa_approved', f'QA approved "{d.title[:50]}"', d.project_id, 'bi-patch-check-fill', '#6366f1')
    db.session.commit()
    flash(f'QA approved. Sent to Admin for review.', 'success')
    return redirect(url_for('deliverable_detail', d_id=d_id))


@app.route('/deliverables/<int:d_id>/qa-sendback', methods=['POST'])
@login_required
def deliverable_qa_sendback(d_id):
    d = Deliverable.query.get_or_404(d_id)
    note = (request.form.get('note','') or '').strip()
    if not note:
        flash('Please provide a reason for sending back.', 'danger')
        return redirect(url_for('deliverable_detail', d_id=d_id))
    _add_event(d, 'qa_rejected', d.stage, 'revision', note)
    # Add a visible comment
    db.session.add(DeliverableComment(deliverable_id=d.id, author_id=current_user.id,
        content=f'[QA Feedback] {note}', is_client_visible=False, status='open'))
    log_act('qa_rejected', f'QA sent back "{d.title[:50]}" for revision', d.project_id, 'bi-arrow-counterclockwise', '#ef4444')
    db.session.commit()
    flash('Sent back to developer for revision.', 'info')
    return redirect(url_for('deliverable_detail', d_id=d_id))


@app.route('/deliverables/<int:d_id>/admin-send-client', methods=['POST'])
@login_required
@admin_required
def deliverable_admin_send_client(d_id):
    d = Deliverable.query.get_or_404(d_id)
    note = (request.form.get('note','') or '').strip()
    # Mark selected comments as client-visible
    visible_ids = request.form.getlist('visible_comment_ids')
    for cid in visible_ids:
        c = DeliverableComment.query.get(int(cid))
        if c and c.deliverable_id == d.id:
            c.is_client_visible = True
    _add_event(d, 'admin_approved', d.stage, 'client_review', note or 'Admin approved. Sent to client for review.')
    log_act('admin_approved', f'Admin approved "{d.title[:50]}" → sent to client', d.project_id, 'bi-shield-fill-check', '#10b981')
    db.session.commit()
    flash('Approved and sent to client for review.', 'success')
    return redirect(url_for('deliverable_detail', d_id=d_id))


@app.route('/deliverables/<int:d_id>/admin-sendback', methods=['POST'])
@login_required
@admin_required
def deliverable_admin_sendback(d_id):
    d = Deliverable.query.get_or_404(d_id)
    target = request.form.get('target','qa_review')  # qa_review or revision
    note = (request.form.get('note','') or '').strip()
    if not note:
        flash('Please provide feedback.', 'danger')
        return redirect(url_for('deliverable_detail', d_id=d_id))
    label = 'QA team' if target == 'qa_review' else 'developer'
    _add_event(d, 'admin_rejected', d.stage, target, note)
    db.session.add(DeliverableComment(deliverable_id=d.id, author_id=current_user.id,
        content=f'[Admin Feedback → {label}] {note}', is_client_visible=False, status='open'))
    log_act('admin_sendback', f'Admin sent back "{d.title[:50]}" to {label}', d.project_id, 'bi-arrow-counterclockwise', '#f59e0b')
    db.session.commit()
    flash(f'Sent back to {label} with feedback.', 'info')
    return redirect(url_for('deliverable_detail', d_id=d_id))


@app.route('/deliverables/<int:d_id>/client-approve', methods=['POST'])
@login_required
def deliverable_client_approve(d_id):
    d = Deliverable.query.get_or_404(d_id)
    if current_user.role == 'client' and d.project.client_user_id != current_user.id:
        abort(403)
    note = (request.form.get('note','') or '').strip()
    _add_event(d, 'client_approved', d.stage, 'completed', note or 'Client approved. Deliverable completed.')
    log_act('client_approved', f'Client approved "{d.title[:50]}" — COMPLETED', d.project_id, 'bi-check-circle-fill', '#10b981')
    db.session.commit()
    flash('Deliverable approved and marked as completed!', 'success')
    return redirect(url_for('deliverable_detail', d_id=d_id))


@app.route('/deliverables/<int:d_id>/client-sendback', methods=['POST'])
@login_required
def deliverable_client_sendback(d_id):
    d = Deliverable.query.get_or_404(d_id)
    if current_user.role == 'client' and d.project.client_user_id != current_user.id:
        abort(403)
    note = (request.form.get('note','') or '').strip()
    if not note:
        flash('Please provide feedback before sending back.', 'danger')
        return redirect(url_for('deliverable_detail', d_id=d_id))
    _add_event(d, 'client_sendback', d.stage, 'admin_review', note)
    db.session.add(DeliverableComment(deliverable_id=d.id, author_id=current_user.id,
        content=note, is_client_visible=True, status='open'))
    log_act('client_sendback', f'Client sent back "{d.title[:50]}" for revision', d.project_id, 'bi-arrow-counterclockwise', '#f59e0b')
    db.session.commit()
    flash('Feedback submitted. Returned to admin for review.', 'info')
    return redirect(url_for('deliverable_detail', d_id=d_id))


# Comments
@app.route('/deliverables/<int:d_id>/comments', methods=['POST'])
@login_required
def add_deliverable_comment(d_id):
    d = Deliverable.query.get_or_404(d_id)
    if current_user.role == 'client' and d.project.client_user_id != current_user.id:
        abort(403)
    data = request.get_json() or {}
    content = (data.get('content','') or '').strip()
    if not content:
        return jsonify({'error':'Empty comment'}), 400
    is_client_visible = (current_user.role == 'client') or bool(data.get('is_client_visible'))
    c = DeliverableComment(
        deliverable_id=d_id, author_id=current_user.id,
        content=content, is_client_visible=is_client_visible,
        parent_id=data.get('parent_id') or None
    )
    db.session.add(c)
    db.session.flush()
    db.session.add(DeliverableEvent(deliverable_id=d_id, user_id=current_user.id,
        event_type='comment_added', stage_from=d.stage, stage_to=d.stage,
        note=content[:100]))
    db.session.commit()
    return jsonify({'success':True, 'id':c.id,
                    'author': current_user.name, 'initials': current_user.get_initials(),
                    'avatar_color': current_user.avatar_color,
                    'content': c.content, 'ts': c.created_at.strftime('%d %b, %H:%M'),
                    'is_client_visible': c.is_client_visible})


@app.route('/deliverable-comments/<int:c_id>/resolve', methods=['POST'])
@login_required
def resolve_comment(c_id):
    c = DeliverableComment.query.get_or_404(c_id)
    role = current_user.role
    data = request.get_json() or {}
    old_status = c.status
    if role in ('developer',) and c.status == 'open':
        c.status = 'dev_resolved'
        label = 'Marked as resolved by developer — awaiting QA verification'
    elif (role in ('super_admin','developer') and c.status == 'dev_resolved'):
        # QA verifies
        c.status = 'qa_resolved'
        label = 'QA verified resolution — awaiting admin review'
    elif role == 'super_admin' and c.status in ('qa_resolved','dev_resolved','open'):
        c.status = 'closed'
        label = 'Closed by admin'
    else:
        return jsonify({'error':'Cannot resolve at this stage'}), 400
    c.resolved_by_id = current_user.id
    c.resolved_at = datetime.utcnow()
    db.session.add(DeliverableEvent(deliverable_id=c.deliverable_id, user_id=current_user.id,
        event_type='comment_resolved', stage_from=old_status, stage_to=c.status, note=label))
    db.session.commit()
    return jsonify({'success':True, 'new_status': c.status,
                    'status_label': c.status_label, 'status_color': c.status_color, 'label': label})


@app.route('/deliverable-comments/<int:c_id>/toggle-visible', methods=['POST'])
@login_required
@admin_required
def toggle_comment_visibility(c_id):
    c = DeliverableComment.query.get_or_404(c_id)
    c.is_client_visible = not c.is_client_visible
    db.session.commit()
    return jsonify({'success':True, 'is_client_visible': c.is_client_visible})


# ── TASK FORWARDING & APPROVALS ──────────────────────────────────────────────

@app.route('/tasks/<int:task_id>/forward', methods=['POST'])
@login_required
def forward_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}
    assign_to_id = data.get('assign_to_id')
    if not assign_to_id:
        return jsonify({'error': 'No assignee selected'}), 400

    # Admin can assign directly without approval
    if current_user.role == 'super_admin':
        task.assigned_to_id = int(assign_to_id)
        proj_id = task.section.project_id if task.section else None
        target = User.query.get(int(assign_to_id))
        log_act('task_assigned', f'Assigned "{task.title[:50]}" to {target.name if target else "user"}',
                proj_id, 'bi-person-check-fill', '#6366f1')
        db.session.commit()
        return jsonify({'success': True, 'direct': True,
                        'message': f'Task assigned to {target.name if target else "user"} directly.'})

    # Developer / Client → create a pending request
    req = TaskAssignmentRequest(
        task_id=task_id,
        requested_by_id=current_user.id,
        assign_to_id=int(assign_to_id),
        message=data.get('message', ''),
        forward_type=data.get('forward_type', 'General')
    )
    db.session.add(req)
    proj_id = task.section.project_id if task.section else None
    target = User.query.get(int(assign_to_id))
    log_act('forward_requested', f'Requested to forward "{task.title[:45]}" → {target.name if target else "user"} (pending approval)',
            proj_id, 'bi-send', '#f59e0b')
    db.session.commit()
    return jsonify({'success': True, 'direct': False,
                    'message': 'Forward request submitted. Waiting for admin approval.'})


@app.route('/admin/approvals')
@login_required
@admin_required
def admin_approvals():
    pending = TaskAssignmentRequest.query.filter_by(status='pending').order_by(
        TaskAssignmentRequest.created_at.desc()).all()
    history = TaskAssignmentRequest.query.filter(
        TaskAssignmentRequest.status != 'pending').order_by(
        TaskAssignmentRequest.reviewed_at.desc()).limit(30).all()
    all_users = User.query.filter(User.role != 'client').all()
    return render_template('admin/approvals.html', pending=pending, history=history, all_users=all_users)


@app.route('/admin/approvals/<int:req_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_assignment(req_id):
    req = TaskAssignmentRequest.query.get_or_404(req_id)
    req.status = 'approved'
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by_id = current_user.id
    # Actually perform the assignment
    task = req.task
    task.assigned_to_id = req.assign_to_id
    proj_id = task.section.project_id if task.section else None
    log_act('assignment_approved', f'Approved forward of "{task.title[:45]}" → {req.assign_to.name}',
            proj_id, 'bi-check-circle-fill', '#10b981')
    db.session.commit()
    flash(f'Assignment approved — "{task.title[:50]}" now assigned to {req.assign_to.name}.', 'success')
    return redirect(url_for('admin_approvals'))


@app.route('/admin/approvals/<int:req_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_assignment(req_id):
    req = TaskAssignmentRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by_id = current_user.id
    req.admin_note = request.form.get('note', '')
    proj_id = req.task.section.project_id if req.task and req.task.section else None
    log_act('assignment_rejected', f'Rejected forward of "{req.task.title[:45]}"',
            proj_id, 'bi-x-circle-fill', '#ef4444')
    db.session.commit()
    flash(f'Assignment rejected.', 'info')
    return redirect(url_for('admin_approvals'))


@app.route('/api/users')
@login_required
def api_users():
    users = User.query.filter(User.is_active == True, User.role != 'client').all()
    return jsonify([{'id': u.id, 'name': u.name, 'role': u.role_label,
                     'avatar_color': u.avatar_color, 'initials': u.get_initials()} for u in users])


# Activity feed API
@app.route('/api/activity')
@login_required
def api_activity():
    if current_user.role == 'super_admin':
        logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(30).all()
    else:
        logs = ActivityLog.query.filter_by(user_id=current_user.id).order_by(
            ActivityLog.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': l.id,
        'action': l.action,
        'description': l.description,
        'icon': l.icon,
        'color': l.color,
        'user': l.user.name if l.user else '?',
        'initials': l.user.get_initials() if l.user else '?',
        'avatar_color': l.user.avatar_color if l.user else '#10b981',
        'project': l.project.name[:40] if l.project else None,
        'ts': l.created_at.strftime('%d %b, %H:%M'),
        'ago': _time_ago(l.created_at)
    } for l in logs])


def _time_ago(dt):
    diff = datetime.utcnow() - dt
    s = int(diff.total_seconds())
    if s < 60: return 'just now'
    if s < 3600: return f'{s // 60}m ago'
    if s < 86400: return f'{s // 3600}h ago'
    return f'{s // 86400}d ago'


# API
@app.route('/api/projects/<int:project_id>/chart-data')
@login_required
def project_chart_data(project_id):
    sections = Section.query.filter_by(project_id=project_id).all()
    cost_items = CostItem.query.filter_by(project_id=project_id).all()
    categories = {}
    for c in cost_items:
        categories[c.category] = categories.get(c.category, 0) + c.total_estimated
    return jsonify({
        'sections': {'labels': [s.name for s in sections], 'data': [s.progress for s in sections], 'colors': [s.type_color for s in sections]},
        'budget': {'labels': list(categories.keys()), 'data': list(categories.values())}
    })


# ─── ACCOMPLISHED PROJECTS ───────────────────────────────────────────────────

ACCOMPLISHED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Accomplished Projects')

_TYPE_MAP = [
    ('flood', 'Flood Risk Assessment'), ('glof', 'Glacial Lake Outburst Flood Analysis'),
    ('snow', 'Snow Cover & Runoff Analysis'), ('drought', 'Drought Monitoring'),
    ('landslide', 'Landslide Susceptibility Mapping'), ('urban', 'Urban Analysis'),
    ('crop', 'Crop Monitoring & Agriculture'), ('agri', 'Agricultural Analysis'),
    ('climate', 'Climate Change Assessment'), ('soil', 'Land Degradation Analysis'),
    ('ecological', 'Ecological Assessment'), ('suitability', 'Site Suitability Analysis'),
    ('runoff', 'Hydrological Analysis'), ('catchment', 'Hydrological Analysis'),
    ('basin', 'Hydrological Analysis'), ('dam', 'Hydrological Analysis'),
]
_COUNTRY_MAP = {
    'sindh': 'Pakistan', 'karachi': 'Pakistan', 'peshawar': 'Pakistan', 'swat': 'Pakistan',
    'chitral': 'Pakistan', 'gilgit': 'Pakistan', 'hunza': 'Pakistan', 'kaghan': 'Pakistan',
    'nowshera': 'Pakistan', 'bannu': 'Pakistan', 'mulkhow': 'Pakistan', 'dera': 'Pakistan',
    'indus': 'Pakistan', 'pakistan': 'Pakistan', 'himalayan': 'Pakistan/India/Nepal',
    'thailand': 'Thailand', 'ulaanbaatar': 'Mongolia', 'poyang': 'China', 'suparco': 'Pakistan',
}

def _detect_type(name):
    nl = name.lower()
    for kw, ptype in _TYPE_MAP:
        if kw in nl:
            return ptype
    return 'GIS Analysis'

def _detect_country(name):
    nl = name.lower()
    for kw, c in _COUNTRY_MAP.items():
        if kw in nl:
            return c
    return 'Pakistan'

def _scan_stats(folder_path):
    img = excel = doc = other = 0
    cover = None
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.gif'):
                img += 1
                if not cover:
                    rel = os.path.relpath(os.path.join(root, f), folder_path)
                    cover = rel.replace('\\', '/')
            elif ext in ('.xlsx', '.xls'):
                excel += 1
            elif ext in ('.docx', '.doc', '.pdf'):
                doc += 1
            else:
                other += 1
    return {'images': img, 'excels': excel, 'docs': doc, 'other': other,
            'total': img + excel + doc + other, 'cover': cover}

def _folder_contents(base, rel=''):
    target = os.path.join(base, rel) if rel else base
    result = {'folders': [], 'images': [], 'files': []}
    if not os.path.isdir(target):
        return result
    try:
        for item in sorted(os.listdir(target)):
            if item.startswith('.'):
                continue
            full = os.path.join(target, item)
            item_rel = (rel + '/' + item).lstrip('/') if rel else item
            if os.path.isdir(full):
                ic = sum(1 for _, _, fs in os.walk(full)
                         for f in fs if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')))
                result['folders'].append({'name': item, 'path': item_rel, 'img_count': ic})
            else:
                ext = os.path.splitext(item)[1].lower()
                entry = {'name': item, 'path': item_rel, 'ext': ext,
                         'is_image': ext in ('.jpg', '.jpeg', '.png', '.gif')}
                if entry['is_image']:
                    result['images'].append(entry)
                else:
                    result['files'].append(entry)
    except PermissionError:
        pass
    return result


@app.route('/accomplished')
@login_required
def accomplished_list():
    if not os.path.exists(ACCOMPLISHED_PATH):
        return render_template('accomplished/offline.html')
    projects = []
    for name in sorted(os.listdir(ACCOMPLISHED_PATH)):
        fp = os.path.join(ACCOMPLISHED_PATH, name)
        if not os.path.isdir(fp) or name.startswith('.'):
            continue
        stats = _scan_stats(fp)
        existing = Project.query.filter(Project.name == name, Project.status == 'completed').first()
        projects.append({
            'name': name, 'stats': stats,
            'type': _detect_type(name), 'country': _detect_country(name),
            'in_db': existing is not None, 'db_id': existing.id if existing else None,
        })
    return render_template('accomplished/index.html', projects=projects,
                           total=len(projects))


@app.route('/accomplished/view/<path:folder_name>')
@login_required
def accomplished_project(folder_name):
    safe = os.path.basename(folder_name)
    base = os.path.join(ACCOMPLISHED_PATH, safe)
    if not os.path.isdir(base):
        flash('Project folder not found.', 'danger')
        return redirect(url_for('accomplished_list'))
    rel = request.args.get('path', '')
    if rel:
        full = os.path.normpath(os.path.join(base, rel))
        if not full.startswith(os.path.normpath(base)):
            abort(403)
    contents = _folder_contents(base, rel)
    stats = _scan_stats(base)
    crumbs = [{'name': safe, 'path': ''}]
    if rel:
        parts = rel.replace('\\', '/').split('/')
        for i, p in enumerate(parts):
            crumbs.append({'name': p, 'path': '/'.join(parts[:i + 1])})
    existing = Project.query.filter(Project.name == safe).first()
    return render_template('accomplished/project.html',
                           folder_name=safe, rel_path=rel,
                           contents=contents, stats=stats,
                           breadcrumb=crumbs, db_project=existing)


@app.route('/accomplished/file/<path:filepath>')
@login_required
def serve_accomplished(filepath):
    safe = os.path.normpath(os.path.join(ACCOMPLISHED_PATH, filepath))
    if not safe.startswith(os.path.normpath(ACCOMPLISHED_PATH)):
        abort(403)
    return send_from_directory(os.path.dirname(safe), os.path.basename(safe))


@app.route('/accomplished/import/<path:folder_name>', methods=['POST'])
@login_required
@not_client
def import_accomplished(folder_name):
    safe = os.path.basename(folder_name)
    fp = os.path.join(ACCOMPLISHED_PATH, safe)
    if not os.path.isdir(fp):
        return jsonify({'error': 'Not found'}), 404
    existing = Project.query.filter_by(name=safe).first()
    if existing:
        return jsonify({'success': True, 'id': existing.id, 'already': True})
    count = Project.query.count() + 1
    mdate = datetime.fromtimestamp(os.path.getmtime(fp)).date()
    p = Project(
        code=f'GM-DONE-{count:03d}', name=safe,
        project_type=_detect_type(safe), status='completed', priority='medium',
        country=_detect_country(safe), location=_detect_country(safe),
        overall_progress=100, end_date=mdate,
        description=f'Completed {_detect_type(safe)} project. View outputs in the Accomplished Projects gallery.'
    )
    db.session.add(p)
    db.session.flush()
    db.session.add(TOR(project_id=p.id))
    db.session.commit()
    return jsonify({'success': True, 'id': p.id})


@app.route('/accomplished/import-all', methods=['POST'])
@login_required
@admin_required
def import_all_accomplished():
    if not os.path.exists(ACCOMPLISHED_PATH):
        return jsonify({'error': 'Folder not found'}), 404
    imported = 0
    skipped = 0
    for name in sorted(os.listdir(ACCOMPLISHED_PATH)):
        fp = os.path.join(ACCOMPLISHED_PATH, name)
        if not os.path.isdir(fp) or name.startswith('.'):
            continue
        if Project.query.filter_by(name=name).first():
            skipped += 1
            continue
        count = Project.query.count() + 1
        mdate = datetime.fromtimestamp(os.path.getmtime(fp)).date()
        p = Project(
            code=f'GM-DONE-{count:03d}', name=name,
            project_type=_detect_type(name), status='completed', priority='medium',
            country=_detect_country(name), location=_detect_country(name),
            overall_progress=100, end_date=mdate,
            description=f'Completed {_detect_type(name)} project.'
        )
        db.session.add(p)
        db.session.flush()
        db.session.add(TOR(project_id=p.id))
        imported += 1
    db.session.commit()
    return jsonify({'success': True, 'imported': imported, 'skipped': skipped})


# ─── SEED DATA ────────────────────────────────────────────────────────────────

def seed_data():
    if User.query.count() > 0:
        return
    print("\n[GM] Seeding Geospatial Maven Dashboard...")

    admin = User(name='Admin User', email='admin@geospatialmaven.com',
                 role='super_admin', department='Management',
                 specialization='GIS & Remote Sensing Strategy', avatar_color='#6366f1')
    admin.set_password('admin123')

    dev1 = User(name='Sarah Ahmed', email='sarah@geospatialmaven.com',
                role='developer', department='GIS Analysis',
                specialization='Remote Sensing, NDVI, Satellite Imagery', avatar_color='#10b981')
    dev1.set_password('dev123')

    dev2 = User(name='Usman Khan', email='usman@geospatialmaven.com',
                role='developer', department='Spatial Analysis',
                specialization='Hydrological Modeling, ArcGIS, Flood Mapping', avatar_color='#3b82f6')
    dev2.set_password('dev123')

    dev3 = User(name='Fatima Malik', email='fatima@geospatialmaven.com',
                role='developer', department='Research & Writing',
                specialization='Technical Report Writing, Literature Review', avatar_color='#ec4899')
    dev3.set_password('dev123')

    client1 = User(name='UNDP Pakistan', email='client@undp.org',
                   role='client', department='Environment & Climate', avatar_color='#f59e0b')
    client1.set_password('client123')

    client2 = User(name='WWF South Asia', email='projects@wwf.org',
                   role='client', department='Conservation', avatar_color='#f59e0b')
    client2.set_password('client123')

    db.session.add_all([admin, dev1, dev2, dev3, client1, client2])
    db.session.flush()

    today = date.today()

    # Project 1
    p1 = Project(
        code='GM-2025-001', name='Flood Risk Assessment – Sindh Province',
        client_name='UNDP Pakistan', client_user_id=client1.id,
        description='Comprehensive flood risk assessment using multi-temporal SAR imagery and GIS analysis for Sindh Province to support disaster risk reduction and early warning systems.',
        project_type='Flood Risk Assessment', status='active', priority='high',
        start_date=today - timedelta(days=45), end_date=today + timedelta(days=75),
        budget_estimated=45000.0, budget_actual=19800.0,
        location='Sindh Province', country='Pakistan',
        coordinator_id=admin.id, tags='flood,risk,sindh,sentinel-1,sar,gis'
    )

    # Project 2
    p2 = Project(
        code='GM-2025-002', name='Land Cover Change Detection – Mangrove Ecosystems',
        client_name='WWF South Asia', client_user_id=client2.id,
        description='Multi-temporal land cover change detection using Landsat and Sentinel-2 imagery to assess mangrove deforestation patterns along the coastal belt.',
        project_type='Land Use & Land Cover Mapping', status='planning', priority='medium',
        start_date=today + timedelta(days=10), end_date=today + timedelta(days=120),
        budget_estimated=32000.0, budget_actual=0,
        location='Coastal Belt, Sindh & Balochistan', country='Pakistan',
        coordinator_id=admin.id, tags='landcover,mangrove,landsat,sentinel-2,change-detection'
    )

    # Project 3
    p3 = Project(
        code='GM-2025-003', name='Urban Heat Island Mapping – Lahore Metropolitan',
        client_name='Punjab Urban Unit', client_user_id=None,
        description='Thermal analysis and Urban Heat Island mapping for Lahore using Landsat 8/9 thermal bands to support urban planning and green infrastructure decisions.',
        project_type='Urban Planning Analysis', status='completed', priority='medium',
        start_date=today - timedelta(days=120), end_date=today - timedelta(days=10),
        budget_estimated=28000.0, budget_actual=27200.0,
        location='Lahore', country='Pakistan',
        coordinator_id=dev1.id, tags='uhi,thermal,lahore,urban,landsat'
    )

    db.session.add_all([p1, p2, p3])
    db.session.flush()

    # TORs
    db.session.add(TOR(
        project_id=p1.id, version='1.2',
        background='The 2022 Pakistan floods affected over 33 million people, with Sindh being the worst-hit province. This assessment provides data-driven insights for future flood risk management.',
        purpose='Conduct a comprehensive flood risk assessment using geospatial tools and satellite imagery to identify vulnerable areas and support disaster preparedness.',
        scope_of_work='(1) Multi-temporal SAR data collection and preprocessing\n(2) DEM analysis and hydrological modeling\n(3) Historical flood extent mapping (2010–2024)\n(4) Population vulnerability assessment\n(5) Risk zonation mapping\n(6) Final report with maps and recommendations',
        deliverables='1. Flood extent maps (historical 2010–2024)\n2. Vulnerability maps by district\n3. Risk assessment GIS geodatabase\n4. Comprehensive technical report\n5. Executive summary for policymakers\n6. Interactive web map (ArcGIS Online)',
        methodology='Multi-source remote sensing using Sentinel-1 SAR (C-band), optical imagery from Sentinel-2, SRTM/ALOS DEM analysis, hydrological modeling (HEC-RAS, SWAT), and field validation.',
        data_requirements='Sentinel-1 SAR imagery (2010–2024), SRTM/ALOS DEM 12.5m, MODIS Terra flood data, Pakistan Census 2023, district boundary shapefiles, infrastructure datasets.',
        software_tools='ArcGIS Pro 3.x, QGIS 3.x, Google Earth Engine (JavaScript API), SNAP 9.0, HEC-RAS 6.x, Python (GeoPandas, Rasterio, NumPy, Matplotlib)',
        qualifications='Senior GIS Analyst (5+ years), Remote Sensing Specialist (SAR experience), Hydrological Modeling Expert, Technical Report Writer',
    ))
    db.session.add(TOR(project_id=p2.id, version='1.0',
        background='Mangrove ecosystems along Pakistan\'s coastline are critically threatened by land use change, shrimp farming, and climate change.',
        purpose='Quantify mangrove loss/gain patterns using multi-temporal satellite imagery and assess key drivers of change.',
        deliverables='1. Classified land cover maps (2000, 2010, 2015, 2020, 2024)\n2. Change detection matrices\n3. Transition probability maps\n4. Technical report with conservation recommendations',
        methodology='Object-based image analysis (OBIA) and supervised classification using Random Forest algorithm on Landsat and Sentinel-2 composites processed in Google Earth Engine.',
        software_tools='Google Earth Engine, ArcGIS Pro, ERDAS IMAGINE, Python, R (randomForest package)',
    ))

    # Sections for Project 1
    sec_data = [
        ('data_collection', 'Data Collection & Preprocessing', 'Acquire and preprocess Sentinel-1 SAR, Sentinel-2, and auxiliary datasets.', today - timedelta(days=45), today - timedelta(days=20), 'completed', 100, 1),
        ('analysis', 'Hydrological Modeling & Flood Mapping', 'DEM analysis, hydrological modeling, and historical flood extent mapping.', today - timedelta(days=20), today + timedelta(days=20), 'in_progress', 65, 2),
        ('analysis', 'Vulnerability & Risk Assessment', 'Population vulnerability analysis and multi-criteria risk zonation.', today + timedelta(days=15), today + timedelta(days=45), 'pending', 0, 3),
        ('writeup', 'Report Writing & Visualization', 'Comprehensive technical report, executive summary, and stakeholder maps.', today + timedelta(days=40), today + timedelta(days=68), 'pending', 0, 4),
        ('learning', 'Methodology Documentation', 'Document replicable methodology and lessons learned for future projects.', today + timedelta(days=60), today + timedelta(days=75), 'pending', 0, 5),
    ]

    sections_p1 = []
    for st, name, desc, sd, ed, status, prog, order in sec_data:
        s = Section(project_id=p1.id, section_type=st, name=name, description=desc,
                    start_date=sd, end_date=ed, status=status, progress=prog, order_num=order)
        db.session.add(s)
        sections_p1.append(s)
    db.session.flush()

    s1, s2, s3, s4, s5 = sections_p1
    db.session.add_all([
        SectionAssignment(section_id=s1.id, user_id=dev1.id, assignment_role='lead'),
        SectionAssignment(section_id=s1.id, user_id=dev2.id, assignment_role='contributor'),
        SectionAssignment(section_id=s2.id, user_id=dev2.id, assignment_role='lead'),
        SectionAssignment(section_id=s2.id, user_id=dev1.id, assignment_role='contributor'),
        SectionAssignment(section_id=s3.id, user_id=dev2.id, assignment_role='lead'),
        SectionAssignment(section_id=s3.id, user_id=dev3.id, assignment_role='contributor'),
        SectionAssignment(section_id=s4.id, user_id=dev3.id, assignment_role='lead'),
        SectionAssignment(section_id=s4.id, user_id=dev1.id, assignment_role='reviewer'),
        SectionAssignment(section_id=s5.id, user_id=dev1.id, assignment_role='contributor'),
    ])

    # Tasks for Project 1
    task_defs = [
        (s1.id, 'Download Sentinel-1 SAR time series (2010–2024)', dev1.id, today - timedelta(days=45), today - timedelta(days=38), 'completed', 'high', 100),
        (s1.id, 'Preprocess SRTM/ALOS DEM – mosaicking & void filling', dev2.id, today - timedelta(days=42), today - timedelta(days=35), 'completed', 'high', 100),
        (s1.id, 'Collect and validate district boundary shapefiles', dev1.id, today - timedelta(days=38), today - timedelta(days=28), 'completed', 'medium', 100),
        (s1.id, 'Download census data and population rasters', dev3.id, today - timedelta(days=35), today - timedelta(days=22), 'completed', 'medium', 100),
        (s2.id, 'Flow accumulation and watershed delineation', dev2.id, today - timedelta(days=20), today - timedelta(days=5), 'completed', 'critical', 100),
        (s2.id, 'SAR flood extent mapping – 2022 event', dev1.id, today - timedelta(days=18), today + timedelta(days=5), 'in_progress', 'critical', 80),
        (s2.id, 'Historical flood mapping (2010, 2015, 2020)', dev1.id, today - timedelta(days=10), today + timedelta(days=15), 'in_progress', 'high', 45),
        (s2.id, 'HEC-RAS hydraulic modeling setup', dev2.id, today - timedelta(days=5), today + timedelta(days=20), 'in_progress', 'high', 30),
        (s3.id, 'Population exposure analysis', dev2.id, today + timedelta(days=15), today + timedelta(days=30), 'todo', 'high', 0),
        (s3.id, 'Multi-criteria vulnerability index calculation', dev3.id, today + timedelta(days=18), today + timedelta(days=38), 'todo', 'medium', 0),
        (s4.id, 'Draft executive summary', dev3.id, today + timedelta(days=40), today + timedelta(days=55), 'todo', 'medium', 0),
        (s4.id, 'Compile final maps and cartographic layout', dev1.id, today + timedelta(days=45), today + timedelta(days=62), 'todo', 'medium', 0),
        (s5.id, 'Write methodology guide with code examples', dev1.id, today + timedelta(days=60), today + timedelta(days=72), 'todo', 'low', 0),
    ]
    for tid, title, uid, sd, dd, status, prio, prog in task_defs:
        db.session.add(Task(section_id=tid, title=title, assigned_to_id=uid,
                            start_date=sd, due_date=dd, status=status, priority=prio, progress=prog))

    # Objectives
    obj_defs = [
        (p1.id, 'Map historical flood extents 2010–2024 for Sindh', 'Use SAR imagery to produce multi-year flood extent maps with accuracy > 85%.', 'primary', 1, 'in_progress', today + timedelta(days=20)),
        (p1.id, 'Identify high-risk flood zones by district', 'Delineate 500-year floodplain areas and classify districts by risk level.', 'primary', 2, 'pending', today + timedelta(days=40)),
        (p1.id, 'Develop population vulnerability index', 'Create a composite vulnerability index incorporating population density, infrastructure, and socioeconomic factors.', 'primary', 3, 'pending', today + timedelta(days=55)),
        (p1.id, 'Deliver interactive web map for stakeholders', 'Publish project outputs on ArcGIS Online for real-time stakeholder access.', 'secondary', 1, 'pending', today + timedelta(days=70)),
        (p1.id, 'Document replicable methodology for future projects', 'Create step-by-step methodology guide that can be applied to other provinces.', 'secondary', 2, 'pending', today + timedelta(days=73)),
        (p2.id, 'Classify land cover for 5 time periods (2000–2024)', 'Achieve overall accuracy > 90% using Random Forest classification.', 'primary', 1, 'pending', today + timedelta(days=60)),
        (p2.id, 'Quantify mangrove area change (net gain/loss)', 'Generate change statistics by district and calculate annual deforestation rate.', 'primary', 2, 'pending', today + timedelta(days=80)),
        (p3.id, 'Map UHI intensity for 2015 and 2023', 'Compare thermal data to identify hotspot areas and temperature gradients.', 'primary', 1, 'completed', today - timedelta(days=30)),
    ]
    for pid, title, desc, otype, prio, status, tdate in obj_defs:
        db.session.add(Objective(project_id=pid, title=title, description=desc,
                                  obj_type=otype, priority=prio, status=status, target_date=tdate))

    # Milestones
    ms_defs = [
        (p1.id, 'Data Collection Complete', today - timedelta(days=20), 'reached', 'All SAR imagery and auxiliary datasets collected and preprocessed.'),
        (p1.id, 'Flood Mapping Complete', today + timedelta(days=20), 'upcoming', 'Historical flood extents and hydraulic model outputs finalized.'),
        (p1.id, 'Draft Report Submitted', today + timedelta(days=55), 'upcoming', 'First draft of technical report submitted to UNDP for review.'),
        (p1.id, 'Final Delivery', today + timedelta(days=75), 'upcoming', 'All deliverables submitted and signed off by client.'),
        (p2.id, 'Project Kickoff', today + timedelta(days=10), 'upcoming', 'Team onboarding and project inception meeting.'),
        (p3.id, 'Project Complete', today - timedelta(days=10), 'reached', 'All deliverables accepted by Punjab Urban Unit.'),
    ]
    for pid, title, mdate, status, desc in ms_defs:
        db.session.add(Milestone(project_id=pid, title=title, date=mdate, status=status, description=desc))

    # Costs
    cost_defs = [
        (p1.id, 'personnel', 'Senior GIS Analyst (3 months)', 'month', 3, 5000, 4800),
        (p1.id, 'personnel', 'Remote Sensing Specialist (2.5 months)', 'month', 2.5, 4500, 4500),
        (p1.id, 'personnel', 'Technical Writer (1 month)', 'month', 1, 2500, 0),
        (p1.id, 'software', 'ArcGIS Pro License', 'license', 1, 1500, 1500),
        (p1.id, 'data_acquisition', 'Commercial SAR Imagery', 'lump sum', 1, 8000, 7200),
        (p1.id, 'travel', 'Field Validation – Sindh (2 trips)', 'trip', 2, 3000, 0),
        (p1.id, 'other', 'Report Design & Printing', 'lump sum', 1, 1500, 0),
        (p2.id, 'personnel', 'GIS Analyst (4 months)', 'month', 4, 4500, 0),
        (p2.id, 'software', 'ERDAS IMAGINE License', 'license', 1, 2500, 0),
        (p2.id, 'data_acquisition', 'Landsat Archive Processing', 'lump sum', 1, 5000, 0),
        (p3.id, 'personnel', 'GIS Analyst (3 months)', 'month', 3, 4500, 4500),
        (p3.id, 'software', 'ArcGIS Pro License', 'license', 1, 1500, 1500),
        (p3.id, 'other', 'Cartographic Design', 'lump sum', 1, 2500, 2200),
    ]
    for pid, cat, desc, unit, qty, est, act in cost_defs:
        db.session.add(CostItem(project_id=pid, category=cat, description=desc,
                                 unit=unit, quantity=qty, unit_cost_estimated=est, unit_cost_actual=act))

    db.session.commit()
    p1.overall_progress = p1.calc_progress()
    p2.overall_progress = p2.calc_progress()
    p3.overall_progress = 100
    db.session.commit()

    print("\n[GM] Seed data created!")
    print("-" * 40)
    print("  Super Admin : admin@geospatialmaven.com / admin123")
    print("  Developer   : sarah@geospatialmaven.com / dev123")
    print("  Developer   : usman@geospatialmaven.com / dev123")
    print("  Client      : client@undp.org / client123")
    print("-" * 40)


with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
