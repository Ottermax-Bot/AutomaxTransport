from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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

@app.route('/')
def home():
    return "Automax Transport - Web App Running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port, debug=True)
