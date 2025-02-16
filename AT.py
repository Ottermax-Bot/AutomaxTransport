from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os, datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")  # Change this in production!

# Securely load database credentials from environment variables
db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/defaultdb')

# Ensure database URL is formatted correctly for SQLAlchemy
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=15)  # Auto logout after 15 min inactivity

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
    return render_template("index.html")

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
    return render_template("dashboard.html", user=current_user)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
