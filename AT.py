# Step 2.1: User Authentication & Role Management

from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os, datetime

# Load environment variables from .env file (if present)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")  # Change this in production!

# SQLAlchemy Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://automaxsql_user:BxYaSA6x1cpBCymyo0t3cUuzDcF8gAKg@dpg-cunpfc8gph6c73f0u7n0-a/automaxsql"
)  # Read from environment variable or fallback to hardcoded URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Ensure all required dependencies are installed
try:
    import flask_login
except ImportError:
    raise ImportError("Missing 'flask_login'. Run 'pip install flask-login' and restart.")

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="driver")  # driver, manager, admin
    branch = db.Column(db.String(50), nullable=True)  # For managers

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    branch = db.Column(db.String(50), nullable=False)  # Branch creating the job
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(50), default="Pending")  # Pending, In Progress, Paused, Completed
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Multi-stop locations
    stops = db.relationship("JobStop", backref="job", lazy=True)

class JobStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)  # Step 1, Step 2, etc.
    location = db.Column(db.String(255), nullable=False)
    estimated_drive_time = db.Column(db.Integer, nullable=True)  # Minutes
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def session_timeout_check():
    session.permanent = True  # Ensures session is tracked properly
    session.modified = True  # Updates session timestamp

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/createdb')
def create_db():
    with app.app_context():
        try:
            db.create_all()
            return "Database created successfully!"
        except Exception as e:
            return f"Database creation failed: {str(e)}"

@app.route('/updatedb')
def update_db():
    with app.app_context():
        try:
            from flask_migrate import upgrade
            upgrade()
            return "Database migrations applied successfully!"
        except Exception as e:
            return f"Migration update failed: {str(e)}"

@app.route('/create_admin')
def create_admin():
    with app.app_context():
        admin_user = User.query.filter_by(username='Admin').first()
        if not admin_user:
            admin_user = User(username='Admin', role='admin')
            admin_user.set_password('Password')
            db.session.add(admin_user)
            db.session.commit()
        return "Admin user created successfully!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form  # Check if 'Remember Me' was selected
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        return render_template("login.html", error="Invalid credentials!")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    return render_template("logout.html", username=username)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == "admin":
        return render_template("admin_dashboard.html", user=current_user)
    elif current_user.role == "manager":
        jobs = Job.query.filter((Job.branch == current_user.branch) | (Job.branch.is_(None))).all()
        return render_template("manager_dashboard.html", user=current_user, jobs=jobs)
    else:
        available_jobs = Job.query.filter_by(assigned_driver_id=None).all()
        accepted_jobs = Job.query.filter_by(assigned_driver_id=current_user.id).all()
        return render_template("driver_dashboard.html", user=current_user, available_jobs=available_jobs, accepted_jobs=accepted_jobs)



@app.route('/post_job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.role not in ["admin", "manager"]:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        description = request.form['description']
        branch = request.form['branch']
        stops = request.form.getlist('stops[]')

        new_job = Job(description=description, branch=branch, created_by=current_user.id)
        db.session.add(new_job)
        db.session.commit()

        # Add stops
        for idx, stop in enumerate(stops):
            new_stop = JobStop(job_id=new_job.id, sequence=idx + 1, location=stop)
            db.session.add(new_stop)
        
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template("post_job.html")


@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    if current_user.role != "admin" and current_user.branch != job.branch:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        job.description = request.form['description']
        job.pickup_location = request.form['pickup_location']
        job.dropoff_location = request.form['dropoff_location']
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template("edit_job.html", job=job)

@app.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    if current_user.role != "admin" and current_user.branch != job.branch:
        return redirect(url_for('dashboard'))

    db.session.delete(job)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/accept_job/<int:job_id>', methods=['POST'])
@login_required
def accept_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.assigned_driver_id is None and current_user.role == "driver":
        job.assigned_driver_id = current_user.id
        job.status = "In Progress"
        db.session.commit()
    return redirect(url_for('dashboard'))



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
