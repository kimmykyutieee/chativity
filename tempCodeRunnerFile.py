from flask import Flask  # <- this was missing

app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/")
def home():
    return "Hello, Chativity!"

if __name__ == "__main__":
    app.run(debug=True)
