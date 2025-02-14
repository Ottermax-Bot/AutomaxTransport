from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
import os

app = Flask(__name__)

# Securely load database credentials from environment variables
db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/defaultdb')

# Ensure database URL is formatted correctly for SQLAlchemy
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define a sample User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

@app.route('/')
def home():
    return "Automax Transport - Web App Running!"

@app.route('/runmigrations')
def run_migrations():
    with app.app_context():
        upgrade()
    return "Migrations Applied Successfully!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
