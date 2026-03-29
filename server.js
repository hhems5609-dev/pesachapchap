import os
from flask import Flask, render_template

app = Flask(__name__)

# =========================
# Home route – serves your main HTML page
@app.route("/")
def home():
    # Make sure your main HTML is templates/index.html
    return render_template("index.html")

# =========================
# Other routes (example: keep your original routes)
@app.route("/hello")
def hello():
    return "Hello from your original app!"

# =========================
if __name__ == "__main__":
    # Render requires dynamic port
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
