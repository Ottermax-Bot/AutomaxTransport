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
)
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

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="driver")  # driver, manager, admin
    branch = db.Column(db.String(50), nullable=True)  # For managers

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Job Model
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    branch = db.Column(db.String(50), nullable=False)  # Branch creating the job
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(50), default="Pending")  # Pending, In Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    stops = db.relationship("JobStop", backref="job", lazy=True)

class JobStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)  # Step 1, Step 2, etc.
    location = db.Column(db.String(255), nullable=False)
    estimated_drive_time = db.Column(db.Integer, nullable=True)  # Minutes
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Fixed SQLAlchemy 2.0 issue

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    predefined_users = {
        "admin": {"password": "adminpass", "role": "admin"},
        "manager": {"password": "managerpass", "role": "manager", "branch": "Rome"},
        "driver": {"password": "driverpass", "role": "driver"},
    }

    if request.method == 'POST':
        username = request.form['username'].lower()  # Make login case-insensitive
        password = request.form['password']

        if username in predefined_users and predefined_users[username]["password"] == password:
            # Create a mock user object for session handling
            user = User(id=999, username=username, role=predefined_users[username]["role"], branch=predefined_users[username].get("branch"))
            login_user(user)
            return redirect(url_for('dashboard'))
        
        return render_template("login.html", error="Invalid credentials!")

    return render_template("login.html")


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == "admin":
        return render_template("admin_dashboard.html", user=current_user)
    elif current_user.role == "manager":
        jobs = Job.query.filter_by(branch=current_user.branch).all()
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
        branch = current_user.branch
        new_job = Job(description=description, branch=branch, created_by=current_user.id)
        db.session.add(new_job)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template("post_job.html")

@app.route('/accept_job/<int:job_id>', methods=['POST'])
@login_required
def accept_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.assigned_driver_id is None and current_user.role == "driver":
        job.assigned_driver_id = current_user.id
        job.status = "In Progress"
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/reset_database', methods=["GET"])
@login_required
def reset_database():
    if current_user.role != "admin":
        return "Unauthorized. Only admins can reset the database.", 403

    try:
        db.session.remove()
        db.drop_all()
        db.create_all()
        return "Database has been reset successfully!", 200
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route('/run_migrations', methods=['GET'])
@login_required
def run_migrations():
    if current_user.role != "admin":
        return "Unauthorized. Only admins can run migrations.", 403

    try:
        from flask_migrate import upgrade
        upgrade()
        return "Database migrations applied successfully!", 200
    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
