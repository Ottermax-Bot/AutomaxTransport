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

# User model
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

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    branch = db.Column(db.String(50), nullable=False)  # Branch creating the job
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(50), default="Pending")  # Pending, In Progress, Paused, Completed
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
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/run-migrations', methods=['GET'])
def run_migrations():
    """Run database migrations to apply schema changes."""
    from flask_migrate import upgrade
    try:
        upgrade()  # Apply migrations
        return "Database migrations applied successfully!", 200
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route("/reset-database", methods=["GET"])
@login_required  # Ensures only logged-in users can run this
def reset_database():
    """Reset the database by dropping and recreating all tables."""
    if current_user.role != "admin":
        return "Unauthorized. Only admins can reset the database.", 403

    from flask_migrate import upgrade
    try:
        db.drop_all()  # Drop tables
        db.create_all()  # Recreate tables
        upgrade()  # Apply migrations
        return "Database has been reset successfully!", 200
    except Exception as e:
        return f"An error occurred during database reset: {e}", 500



@app.route('/create_admin')
def create_admin():
    with app.app_context():
        try:
            admin_user = User.query.filter_by(username='Admin').first()
            if not admin_user:
                admin_user = User(username='Admin', role='admin')
                admin_user.set_password('Password')
                db.session.add(admin_user)
                db.session.commit()
            return "Admin user created successfully!"
        except Exception as e:
            db.session.rollback()
            return f"Error creating admin: {str(e)}"

@app.route('/createmanager')
def create_manager():
    with app.app_context():
        try:
            manager_user = User.query.filter_by(username='Manager').first()
            if not manager_user:
                manager_user = User(username='Manager', role='manager', branch="Rome")
                manager_user.set_password('Password')
                db.session.add(manager_user)
                db.session.commit()
            return "Manager user created successfully!"
        except Exception as e:
            db.session.rollback()
            return f"Error creating manager: {str(e)}"

@app.route('/createdriver')
def create_driver():
    with app.app_context():
        try:
            driver_user = User.query.filter_by(username='Driver').first()
            if not driver_user:
                driver_user = User(username='Driver', role='driver')
                driver_user.set_password('Password')
                db.session.add(driver_user)
                db.session.commit()
            return "Driver user created successfully!"
        except Exception as e:
            db.session.rollback()
            return f"Error creating driver: {str(e)}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form  
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        return render_template("login.html", error="Invalid credentials!")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

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

@app.route('/post_job', methods=['GET', 'POST'])  # Ensuring both GET and POST methods
@login_required
def post_job():
    if current_user.role not in ["admin", "manager"]:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':  # Ensuring POST handling
        description = request.form.get('description')
        branch = current_user.branch  # Auto-assign based on manager's branch

        if not description:
            return "Job description cannot be empty", 400

        new_job = Job(description=description, branch=branch, created_by=current_user.id)
        db.session.add(new_job)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template("post_job.html")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
