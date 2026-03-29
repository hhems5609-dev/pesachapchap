import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to Pesachapchap!"

@app.route("/hello")
def hello():
    return "Hello from your original app!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
