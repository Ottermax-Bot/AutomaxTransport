from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return "Automax Transport - Web App Running!"

if __name__ == '__main__':
    app.run(debug=True)
